"""
Regret Calculator - Calcul du score de regret contrefactuel.

Compare les résultats réels (path A) aux alternatives simulées (B1-B4).
Apprend localement par institut/profil cliente.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class OutcomeMetric(Enum):
    """Métriques d'outcome pour calcul regret."""
    RETURNED_7D = "returned_7d"       # Cliente revenue à J+7
    RETURNED_30D = "returned_30d"     # Cliente revenue à J+30
    PURCHASED = "purchased"           # A acheté le produit recommandé
    BASKET_VALUE = "basket_value"     # Valeur panier
    SATISFACTION = "satisfaction"     # Score satisfaction (si NPS)
    CANCELLED = "cancelled"           # A annulé/retourné


@dataclass
class OutcomeData:
    """Données d'outcome pour une décision."""
    decision_id: str
    returned_7d: bool = False
    returned_30d: bool = False
    purchased: bool = False
    basket_value: float = 0.0
    satisfaction: Optional[float] = None  # 1-5
    cancelled: bool = False
    collected_at: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id,
            "returned_7d": self.returned_7d,
            "returned_30d": self.returned_30d,
            "purchased": self.purchased,
            "basket_value": self.basket_value,
            "satisfaction": self.satisfaction,
            "cancelled": self.cancelled,
            "collected_at": self.collected_at
        }


@dataclass
class RegretScore:
    """Score de regret pour une décision."""
    decision_id: str
    real_path_score: float = 0.0
    best_shadow_score: float = 0.0
    best_shadow_type: str = ""
    regret: float = 0.0  # best_shadow - real (positif = on aurait pu faire mieux)
    confidence: float = 0.0
    analysis: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id,
            "real_path_score": self.real_path_score,
            "best_shadow_score": self.best_shadow_score,
            "best_shadow_type": self.best_shadow_type,
            "regret": self.regret,
            "confidence": self.confidence,
            "analysis": self.analysis
        }


class RegretCalculator:
    """
    Calculateur de regret contrefactuel.
    
    Formule:
    Regret = Score(meilleur shadow path estimé) - Score(path réel observé)
    
    Si Regret > 0: On aurait pu faire mieux
    Si Regret ≤ 0: La décision était optimale
    """
    
    # Poids des métriques pour le score
    WEIGHTS = {
        "returned": 0.3,      # 30% poids retour cliente
        "purchased": 0.25,    # 25% poids achat
        "basket": 0.2,        # 20% poids panier
        "satisfaction": 0.15, # 15% poids satisfaction
        "not_cancelled": 0.1  # 10% poids non-annulation
    }
    
    def __init__(self):
        self._postgres = None
    
    def _ensure_db(self):
        if self._postgres:
            return
        
        try:
            from backend.memory import get_memory_system
            memory = get_memory_system()
            if hasattr(memory, '_postgres'):
                self._postgres = memory._postgres
        except Exception as e:
            logger.warning(f"⚠️ DB connection: {e}")
    
    def calculate_outcome_score(self, outcome: OutcomeData) -> float:
        """
        Calcule le score d'un outcome observé.
        
        Score = weighted sum of:
        - returned (0/1)
        - purchased (0/1)
        - basket_value (normalisé)
        - satisfaction (normalisé)
        - not_cancelled (0/1)
        
        Returns:
            Score entre 0 et 1
        """
        scores = {
            "returned": 1.0 if outcome.returned_7d or outcome.returned_30d else 0.0,
            "purchased": 1.0 if outcome.purchased else 0.0,
            "basket": min(outcome.basket_value / 100.0, 1.0),  # Normalize à 100€
            "satisfaction": (outcome.satisfaction or 3.0) / 5.0,  # Default 3/5
            "not_cancelled": 0.0 if outcome.cancelled else 1.0
        }
        
        total = sum(
            scores[key] * weight 
            for key, weight in self.WEIGHTS.items()
        )
        
        return round(total, 3)
    
    def estimate_shadow_score(
        self,
        shadow_path: Dict,
        real_outcome: OutcomeData,
        institut_id: Optional[str] = None
    ) -> Tuple[float, float]:
        """
        Estime le score qu'aurait eu un shadow path.
        
        Basé sur:
        - Historique institut (si disponible)
        - Heuristiques par type de path
        - Comparaison basket estimé vs réel
        
        Returns:
            (score_estimé, confidence)
        """
        path_type = shadow_path.get("path_type", "unknown")
        estimated_basket = shadow_path.get("estimated_basket", 0)
        
        # Heuristiques par type
        base_scores = {
            "cheaper": 0.55,    # Budget = moins de risque, mais moins de valeur
            "premium": 0.45,    # Premium = plus risqué, mais plus de valeur si ça marche
            "minimal": 0.5,     # Minimal = safe mais engagement faible
            "safe": 0.6         # Safe = fidélisation prioritaire
        }
        
        base = base_scores.get(path_type, 0.5)
        
        # Ajustement si cliente a bien réagi au réel
        if real_outcome.returned_30d and real_outcome.purchased:
            # Le réel a bien marché, shadows probablement moins bons
            base *= 0.85
        elif real_outcome.cancelled:
            # Le réel a mal marché, shadows peut-être meilleurs
            base *= 1.15
        
        # Ajustement basket
        if estimated_basket > 0 and real_outcome.basket_value > 0:
            ratio = estimated_basket / real_outcome.basket_value
            if 0.5 < ratio < 1.5:
                # Basket proche → plus de confiance
                base *= 1.05
        
        # Clamp entre 0 et 1
        estimated = max(0.0, min(1.0, base))
        
        # Confidence (heuristique)
        confidence = 0.4  # Base: 40% confidence
        
        # Plus d'historique institut → plus de confidence
        if institut_id and self._has_institut_history(institut_id):
            confidence += 0.2
        
        return round(estimated, 3), round(confidence, 3)
    
    def _has_institut_history(self, institut_id: str, min_decisions: int = 50) -> bool:
        """Vérifie si on a assez d'historique pour cet institut."""
        if not self._postgres:
            return False
        
        try:
            result = self._postgres.fetch_one("""
                SELECT COUNT(*) as count FROM counterfactual_decisions
                WHERE institut_id = %s AND outcome_7d IS NOT NULL
            """, (institut_id,))
            return result and result.get("count", 0) >= min_decisions
        except:
            return False
    
    def calculate_regret(
        self,
        decision_id: str,
        real_outcome: OutcomeData,
        shadow_paths: List[Dict]
    ) -> RegretScore:
        """
        Calcule le regret pour une décision.
        
        Args:
            decision_id: ID décision
            real_outcome: Outcome observé
            shadow_paths: Liste des shadow paths générés
        
        Returns:
            RegretScore avec analyse
        """
        real_score = self.calculate_outcome_score(real_outcome)
        
        best_shadow_score = 0.0
        best_shadow_type = ""
        best_confidence = 0.0
        
        for shadow in shadow_paths:
            score, confidence = self.estimate_shadow_score(shadow, real_outcome)
            
            # Pondérer par confidence
            weighted_score = score * confidence
            
            if weighted_score > best_shadow_score:
                best_shadow_score = score
                best_shadow_type = shadow.get("path_type", "unknown")
                best_confidence = confidence
        
        regret = round(best_shadow_score - real_score, 3)
        
        # Analyse
        if regret > 0.15:
            analysis = f"Regret significatif: {best_shadow_type} aurait été meilleur"
        elif regret > 0:
            analysis = f"Regret mineur: {best_shadow_type} légèrement meilleur"
        elif regret > -0.1:
            analysis = "Décision optimale"
        else:
            analysis = "Décision excellente, mieux que toutes les alternatives"
        
        return RegretScore(
            decision_id=decision_id,
            real_path_score=real_score,
            best_shadow_score=best_shadow_score,
            best_shadow_type=best_shadow_type,
            regret=regret,
            confidence=best_confidence,
            analysis=analysis
        )
    
    def get_institut_insights(self, institut_id: str, days: int = 30) -> Dict:
        """
        Génère des insights pour un institut basé sur le regret.
        
        Returns:
            {
                "avg_regret": float,
                "optimal_rate": float,  # % décisions optimales
                "top_improvements": [...],  # Actions à améliorer
                "recommendations": [...]
            }
        """
        self._ensure_db()
        
        if not self._postgres:
            return {"error": "Database not available"}
        
        try:
            # Récupérer décisions avec outcomes
            decisions = self._postgres.fetch_all("""
                SELECT decision_id, shadow_paths, outcome_7d, outcome_30d, regret_score
                FROM counterfactual_decisions
                WHERE institut_id = %s 
                AND timestamp > NOW() - INTERVAL '%s days'
                AND outcome_7d IS NOT NULL
            """, (institut_id, days))
            
            if not decisions:
                return {"message": "Pas assez de données", "count": 0}
            
            regrets = [d.get("regret_score", 0) for d in decisions if d.get("regret_score")]
            
            avg_regret = sum(regrets) / len(regrets) if regrets else 0
            optimal_count = sum(1 for r in regrets if r <= 0)
            optimal_rate = optimal_count / len(regrets) if regrets else 0
            
            # Top patterns de regret
            shadow_regrets = {}
            for d in decisions:
                if d.get("regret_score", 0) > 0.1:
                    # Analyser quel shadow path aurait été meilleur
                    shadows = json.loads(d.get("shadow_paths", "[]"))
                    for s in shadows:
                        ptype = s.get("path_type", "unknown")
                        shadow_regrets[ptype] = shadow_regrets.get(ptype, 0) + 1
            
            top_improvements = sorted(
                shadow_regrets.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            
            recommendations = []
            if top_improvements:
                if top_improvements[0][0] == "cheaper":
                    recommendations.append("Proposer plus souvent des alternatives budget")
                elif top_improvements[0][0] == "premium":
                    recommendations.append("Les clientes acceptent le premium, ne pas hésiter")
                elif top_improvements[0][0] == "safe":
                    recommendations.append("Privilégier la sécurité sur l'upsell")
            
            return {
                "institut_id": institut_id,
                "period_days": days,
                "total_decisions": len(decisions),
                "with_outcome": len(regrets),
                "avg_regret": round(avg_regret, 3),
                "optimal_rate": round(optimal_rate * 100, 1),
                "top_improvements": top_improvements,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"❌ Institut insights: {e}")
            return {"error": str(e)}


# Singleton
_regret_calculator: Optional[RegretCalculator] = None


def get_regret_calculator() -> RegretCalculator:
    global _regret_calculator
    if _regret_calculator is None:
        _regret_calculator = RegretCalculator()
    return _regret_calculator
