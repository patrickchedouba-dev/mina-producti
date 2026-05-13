"""
Policy Updater - Ajuste les paramètres Mina basé sur le regret.

Apprentissage local par institut/profil.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PolicyAdjustment:
    """Ajustement de politique suggéré."""
    institut_id: str
    adjustment_type: str  # "routing", "temperature", "style"
    parameter: str
    old_value: float
    new_value: float
    reason: str
    confidence: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PolicyUpdater:
    """
    Met à jour les politiques Mina basé sur l'analyse du regret.
    
    Types d'ajustements:
    - Routing: Quel agent appeler en premier
    - Temperature: Plus/moins créatif selon contexte
    - Style: Ton de communication adapté
    """
    
    def __init__(self):
        self._adjustments: Dict[str, List[PolicyAdjustment]] = {}
    
    def analyze_and_suggest(self, institut_id: str, insights: Dict) -> List[PolicyAdjustment]:
        """
        Analyse les insights et suggère des ajustements.
        
        Args:
            institut_id: ID institut
            insights: Résultat de RegretCalculator.get_institut_insights()
        
        Returns:
            Liste d'ajustements suggérés
        """
        adjustments = []
        
        avg_regret = insights.get("avg_regret", 0)
        optimal_rate = insights.get("optimal_rate", 100)
        top_improvements = insights.get("top_improvements", [])
        
        # 1. Ajustement routing si regret élevé
        if avg_regret > 0.1 and top_improvements:
            best_shadow = top_improvements[0][0]  # ("cheaper", count)
            
            # Suggérer de favoriser ce type
            routing_weight = {
                "cheaper": ("budget_first", 0.5, 0.7),
                "premium": ("premium_acceptance", 0.3, 0.5),
                "minimal": ("minimal_viable", 0.4, 0.6),
                "safe": ("safety_priority", 0.5, 0.8)
            }
            
            if best_shadow in routing_weight:
                param, old, new = routing_weight[best_shadow]
                adjustments.append(PolicyAdjustment(
                    institut_id=institut_id,
                    adjustment_type="routing",
                    parameter=param,
                    old_value=old,
                    new_value=new,
                    reason=f"Regret moyen {avg_regret:.2f} - favoriser {best_shadow}",
                    confidence=min(0.9, avg_regret * 3)
                ))
        
        # 2. Ajustement temperature si taux optimal bas
        if optimal_rate < 60:
            # Réduire créativité pour plus de consistance
            adjustments.append(PolicyAdjustment(
                institut_id=institut_id,
                adjustment_type="temperature",
                parameter="llm_temperature",
                old_value=0.3,
                new_value=0.2,
                reason=f"Taux optimal {optimal_rate:.0f}% - réduire variabilité",
                confidence=0.6
            ))
        elif optimal_rate > 85:
            # Augmenter créativité, on peut se permettre
            adjustments.append(PolicyAdjustment(
                institut_id=institut_id,
                adjustment_type="temperature",
                parameter="llm_temperature",
                old_value=0.3,
                new_value=0.4,
                reason=f"Taux optimal {optimal_rate:.0f}% - explorer plus",
                confidence=0.5
            ))
        
        # 3. Ajustement style basé sur profil institut
        # (À enrichir avec données réelles)
        
        self._adjustments[institut_id] = adjustments
        return adjustments
    
    def apply_adjustments(
        self,
        institut_id: str,
        auto_apply: bool = False
    ) -> Dict:
        """
        Applique les ajustements suggérés.
        
        Args:
            institut_id: ID institut
            auto_apply: Si True, applique sans confirmation
        
        Returns:
            Résultat de l'application
        """
        adjustments = self._adjustments.get(institut_id, [])
        
        if not adjustments:
            return {"status": "no_adjustments", "count": 0}
        
        applied = []
        
        for adj in adjustments:
            if adj.confidence < 0.5 and not auto_apply:
                logger.info(f"⏭️ Skip low confidence: {adj.parameter}")
                continue
            
            # Stocker l'ajustement
            success = self._store_adjustment(adj)
            
            if success:
                applied.append(adj.parameter)
                logger.info(f"✅ Applied: {adj.parameter} {adj.old_value} → {adj.new_value}")
        
        return {
            "status": "applied",
            "count": len(applied),
            "parameters": applied
        }
    
    def _store_adjustment(self, adj: PolicyAdjustment) -> bool:
        """Stocke l'ajustement en base."""
        try:
            from backend.memory import get_memory_system
            memory = get_memory_system()
            
            if not hasattr(memory, '_postgres') or not memory._postgres:
                # Fallback: fichier JSON
                return self._store_to_file(adj)
            
            memory._postgres.execute("""
                CREATE TABLE IF NOT EXISTS policy_adjustments (
                    id SERIAL PRIMARY KEY,
                    institut_id VARCHAR(64),
                    adjustment_type VARCHAR(32),
                    parameter VARCHAR(64),
                    old_value FLOAT,
                    new_value FLOAT,
                    reason TEXT,
                    confidence FLOAT,
                    applied_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            memory._postgres.execute("""
                INSERT INTO policy_adjustments 
                (institut_id, adjustment_type, parameter, old_value, new_value, reason, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                adj.institut_id,
                adj.adjustment_type,
                adj.parameter,
                adj.old_value,
                adj.new_value,
                adj.reason,
                adj.confidence
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Store adjustment: {e}")
            return False
    
    def _store_to_file(self, adj: PolicyAdjustment) -> bool:
        """Fallback stockage fichier."""
        try:
            from pathlib import Path
            log_dir = Path(__file__).parent.parent.parent / "logs" / "policy"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"adjustments_{adj.institut_id}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                data = {
                    "institut_id": adj.institut_id,
                    "type": adj.adjustment_type,
                    "parameter": adj.parameter,
                    "old": adj.old_value,
                    "new": adj.new_value,
                    "reason": adj.reason,
                    "confidence": adj.confidence,
                    "timestamp": adj.created_at
                }
                f.write(json.dumps(data) + "\n")
            
            return True
        except:
            return False
    
    def get_active_policy(self, institut_id: str) -> Dict:
        """
        Récupère la politique active pour un institut.
        
        Returns:
            {
                "routing": {...},
                "temperature": 0.3,
                "style": "warm"
            }
        """
        # Defaults
        policy = {
            "routing": {
                "budget_first": 0.5,
                "premium_acceptance": 0.3,
                "safety_priority": 0.5
            },
            "temperature": 0.3,
            "style": "warm",
            "updated_at": None
        }
        
        try:
            from backend.memory import get_memory_system
            memory = get_memory_system()
            
            if hasattr(memory, '_postgres') and memory._postgres:
                # Récupérer derniers ajustements
                result = memory._postgres.fetch_all("""
                    SELECT parameter, new_value, applied_at
                    FROM policy_adjustments
                    WHERE institut_id = %s
                    ORDER BY applied_at DESC
                    LIMIT 10
                """, (institut_id,))
                
                if result:
                    for row in result:
                        param = row.get("parameter")
                        value = row.get("new_value")
                        
                        if param == "llm_temperature":
                            policy["temperature"] = value
                        elif param in policy["routing"]:
                            policy["routing"][param] = value
                    
                    policy["updated_at"] = result[0].get("applied_at")
        except:
            pass
        
        return policy


# Singleton
_policy_updater: Optional[PolicyUpdater] = None


def get_policy_updater() -> PolicyUpdater:
    global _policy_updater
    if _policy_updater is None:
        _policy_updater = PolicyUpdater()
    return _policy_updater
