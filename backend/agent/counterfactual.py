"""
Counterfactual Agent - Regret-Zero AI

Génère des chemins alternatifs (shadow paths) pour chaque décision importante.
Ne parle jamais à la cliente - travaille en background pour apprentissage.

Architecture:
- Real Path A: Ce que Mina recommande réellement
- Shadow Paths B1-B4: Alternatives simulées (budget, premium, minimal, safe)
- Outcome Logger: Stocke pour analyse différée (J+7, J+30)
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PathType(Enum):
    """Types de chemins contrefactuels."""
    REAL = "real"              # Chemin réellement exécuté
    CHEAPER = "cheaper"        # Alternative budget réduit
    PREMIUM = "premium"        # Alternative premium
    MINIMAL = "minimal"        # Minimum viable
    SAFE = "safe"              # Ultra-conservateur


@dataclass
class CounterfactualPath:
    """Un chemin décisionnel (réel ou simulé)."""
    path_type: PathType
    diagnosis_summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    estimated_basket: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "path_type": self.path_type.value,
            "diagnosis_summary": self.diagnosis_summary,
            "recommendations": self.recommendations,
            "estimated_basket": self.estimated_basket,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }


@dataclass
class CounterfactualDecision:
    """Décision avec tous les chemins (réel + shadow)."""
    decision_id: str
    session_id: str
    client_id: Optional[str]
    institut_id: Optional[str]
    timestamp: str
    user_input: str
    context: Dict
    real_path: CounterfactualPath
    shadow_paths: List[CounterfactualPath] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id,
            "session_id": self.session_id,
            "client_id": self.client_id,
            "institut_id": self.institut_id,
            "timestamp": self.timestamp,
            "user_input": self.user_input,
            "context": self.context,
            "real_path": self.real_path.to_dict(),
            "shadow_paths": [p.to_dict() for p in self.shadow_paths]
        }


class CounterfactualAgent:
    """
    Agent contrefactuel - génère des alternatives shadow.
    
    Ne parle JAMAIS à la cliente.
    Travaille en arrière-plan pour apprentissage.
    """
    
    def __init__(self):
        self._llm = None
        self._initialized = False
    
    def _ensure_init(self):
        if self._initialized:
            return
        
        try:
            from backend.llm import get_llm_provider
            self._llm = get_llm_provider()
            self._initialized = True
            logger.info("🔮 CounterfactualAgent initialisé")
        except Exception as e:
            logger.warning(f"⚠️ CounterfactualAgent init: {e}")
    
    def generate_shadow_paths(
        self,
        real_response: str,
        user_input: str,
        context: Dict
    ) -> List[CounterfactualPath]:
        """
        Génère les chemins alternatifs (shadow) basés sur la réponse réelle.
        
        Args:
            real_response: Réponse Mina réellement donnée
            user_input: Question initiale cliente
            context: Contexte (profil, historique, institut)
        
        Returns:
            Liste de chemins shadow (cheaper, premium, minimal, safe)
        """
        self._ensure_init()
        
        if not self._llm:
            return []
        
        shadow_paths = []
        
        # Générer chaque alternative
        for path_type in [PathType.CHEAPER, PathType.PREMIUM, PathType.MINIMAL, PathType.SAFE]:
            try:
                path = self._generate_single_path(
                    path_type=path_type,
                    real_response=real_response,
                    user_input=user_input,
                    context=context
                )
                if path:
                    shadow_paths.append(path)
            except Exception as e:
                logger.warning(f"⚠️ Shadow path {path_type.value}: {e}")
        
        logger.info(f"🔮 Generated {len(shadow_paths)} shadow paths")
        return shadow_paths
    
    def _generate_single_path(
        self,
        path_type: PathType,
        real_response: str,
        user_input: str,
        context: Dict
    ) -> Optional[CounterfactualPath]:
        """Génère un chemin shadow spécifique."""
        
        # Prompt pour générer l'alternative
        prompt = self._build_counterfactual_prompt(
            path_type=path_type,
            real_response=real_response,
            user_input=user_input,
            context=context
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = self._llm.generate_sync(messages, temperature=0.5, max_tokens=300)
        
        if not response.text:
            return None
        
        # Parser la réponse (format simple)
        return self._parse_path_response(path_type, response.text)
    
    def _build_counterfactual_prompt(
        self,
        path_type: PathType,
        real_response: str,
        user_input: str,
        context: Dict
    ) -> str:
        """Construit le prompt pour générer une alternative."""
        
        path_instructions = {
            PathType.CHEAPER: "Propose une alternative MOINS CHÈRE (budget réduit de 30-50%), moins de produits, soins basiques.",
            PathType.PREMIUM: "Propose une alternative PREMIUM (+50% budget), produits haut de gamme, cures complètes.",
            PathType.MINIMAL: "Propose une alternative MINIMALE (1-2 produits max), essentiel uniquement.",
            PathType.SAFE: "Propose une alternative ULTRA-SAFE, zéro risque allergique, produits hypoallergéniques classiques."
        }
        
        return f"""Tu es un expert en recommandations cosmétiques Body Minute.

Question cliente: "{user_input}"

Réponse réelle donnée: "{real_response[:500]}"

Contexte: {json.dumps(context, ensure_ascii=False)[:300]}

INSTRUCTION: {path_instructions[path_type]}

Réponds en JSON strict:
{{
  "recommendations": ["produit1", "produit2"],
  "estimated_basket": 45.0,
  "reasoning": "Explication courte"
}}

JSON uniquement, pas de texte autour."""
    
    def _parse_path_response(self, path_type: PathType, response_text: str) -> Optional[CounterfactualPath]:
        """Parse la réponse LLM en CounterfactualPath."""
        try:
            # Extraire JSON de la réponse
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            return CounterfactualPath(
                path_type=path_type,
                recommendations=data.get("recommendations", []),
                estimated_basket=float(data.get("estimated_basket", 0)),
                reasoning=data.get("reasoning", ""),
                confidence=0.7  # Default confidence
            )
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None
    
    def create_decision_record(
        self,
        session_id: str,
        client_id: Optional[str],
        institut_id: Optional[str],
        user_input: str,
        real_response: str,
        context: Dict,
        shadow_paths: List[CounterfactualPath]
    ) -> CounterfactualDecision:
        """Crée un enregistrement de décision complet."""
        
        import uuid
        
        real_path = CounterfactualPath(
            path_type=PathType.REAL,
            diagnosis_summary="",
            recommendations=[],  # À extraire de real_response si besoin
            reasoning="Chemin réellement exécuté",
            confidence=1.0
        )
        
        return CounterfactualDecision(
            decision_id=f"cf_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            client_id=client_id,
            institut_id=institut_id,
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            context=context,
            real_path=real_path,
            shadow_paths=shadow_paths
        )


# Singleton
_counterfactual_agent: Optional[CounterfactualAgent] = None


def get_counterfactual_agent() -> CounterfactualAgent:
    """Retourne l'instance singleton."""
    global _counterfactual_agent
    if _counterfactual_agent is None:
        _counterfactual_agent = CounterfactualAgent()
    return _counterfactual_agent
