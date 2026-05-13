"""
Feature Flags pour Mina V2.
Gestion centralisée des flags d'activation et fallback.
"""

import os
import logging

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Gestion des feature flags Mina V2."""
    
    def __init__(self):
        self._load_flags()
    
    def _load_flags(self):
        """Charge les flags depuis les variables d'environnement."""
        self.v2_enabled = os.getenv("MINA_V2_ENABLED", "true").lower() == "true"
        self.fallback_enabled = os.getenv("MINA_FALLBACK_ENABLED", "true").lower() == "true"
        self.safe_mode = os.getenv("MINA_SAFE_MODE", "true").lower() == "true"
        self.min_score = float(os.getenv("MINA_MIN_SCORE", "0.6"))
        self.log_premium_hits = os.getenv("MINA_LOG_PREMIUM_HITS", "true").lower() == "true"
        
        # Mode temps réel Gemini Live (branche dev-realtime)
        self.realtime_enabled = os.getenv("MINA_REALTIME_ENABLED", "false").lower() == "true"
        
        # MCP Tools (beta) - Outils appelables par le LLM
        self.mcp_enabled = os.getenv("MINA_MCP_ENABLED", "false").lower() == "true"
        
        # Memory System - Mémoire persistante Redis + PostgreSQL
        self.memory_enabled = os.getenv("MINA_MEMORY_ENABLED", "false").lower() == "true"
        
        # Agent Mode - Orchestrateur agentique ReAct
        self.agent_enabled = os.getenv("MINA_AGENT_ENABLED", "false").lower() == "true"
        
        logger.info(f"Feature Flags chargés: V2={self.v2_enabled}, Fallback={self.fallback_enabled}, SafeMode={self.safe_mode}, MinScore={self.min_score}, Realtime={self.realtime_enabled}, MCP={self.mcp_enabled}, Memory={self.memory_enabled}, Agent={self.agent_enabled}")
    
    def is_v2_enabled(self) -> bool:
        """Vérifie si V2 est activé globalement."""
        return self.v2_enabled
    
    def is_fallback_enabled(self) -> bool:
        """Vérifie si le fallback V1 est activé."""
        return self.fallback_enabled
    
    def is_safe_mode_enabled(self) -> bool:
        """Vérifie si le safe mode est activé."""
        return self.safe_mode
    
    def get_min_score(self) -> float:
        """Retourne le score minimum pour une réponse premium."""
        return self.min_score
    
    def should_use_premium(self, score: float, is_premium: bool) -> bool:
        """
        Détermine si on doit utiliser la réponse premium.
        
        Args:
            score: Score de similarité du résultat
            is_premium: Le résultat est-il marqué premium
            
        Returns:
            True si on doit utiliser le template premium
        """
        if not self.v2_enabled:
            return False
        
        if not is_premium:
            return False
        
        if score < self.min_score:
            if self.log_premium_hits:
                logger.warning(f"Score insuffisant pour premium: {score:.3f} < {self.min_score}")
            return False
        
        if self.log_premium_hits:
            logger.info(f"Hit premium validé: score={score:.3f}")
        
        return True
    
    def reload(self):
        """Recharge les flags (utile pour tests ou hot-reload)."""
        self._load_flags()


# Instance singleton
_flags = None


def get_flags() -> FeatureFlags:
    """Retourne l'instance singleton des feature flags."""
    global _flags
    if _flags is None:
        _flags = FeatureFlags()
    return _flags


def is_v2_enabled() -> bool:
    """Raccourci pour vérifier si V2 est activé."""
    return get_flags().is_v2_enabled()


def should_use_premium(score: float, is_premium: bool) -> bool:
    """Raccourci pour évaluer l'utilisation premium."""
    return get_flags().should_use_premium(score, is_premium)


def is_realtime_enabled() -> bool:
    """Raccourci pour vérifier si le mode temps réel Gemini Live est activé."""
    return get_flags().realtime_enabled


def is_mcp_enabled() -> bool:
    """Raccourci pour vérifier si les outils MCP sont activés."""
    return get_flags().mcp_enabled


def is_memory_enabled() -> bool:
    """Raccourci pour vérifier si le système de mémoire est activé."""
    return get_flags().memory_enabled


def is_agent_enabled() -> bool:
    """Raccourci pour vérifier si l'orchestrateur agentique est activé."""
    return get_flags().agent_enabled


