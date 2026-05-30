"""
Resilient LLM Provider - Auto-fallback avec Circuit Breaker.

Architecture:
1. Gemini (primary) avec Circuit Breaker
2. Claude (fallback) si Gemini down
3. Degraded Mode si tout down

= Mina NE PLANTE JAMAIS ✅
"""

import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from .provider import LLMResponse, GeminiProvider, ClaudeProvider
from .circuit_breaker import CircuitBreaker, CircuitOpenError
from .degraded_mode import get_degraded_agent

logger = logging.getLogger(__name__)


@dataclass
class ProviderStats:
    """Statistiques d'utilisation des providers."""
    gemini_calls: int = 0
    claude_calls: int = 0
    degraded_calls: int = 0
    gemini_failures: int = 0
    claude_failures: int = 0


class ResilientLLMProvider:
    """
    Provider LLM résilient avec 3 niveaux de protection.
    
    Niveau 1: Gemini avec Circuit Breaker
    Niveau 2: Fallback Claude automatique
    Niveau 3: Degraded Mode (réponses scriptées)
    
    Usage:
    ```python
    provider = get_resilient_provider()
    response = provider.generate_sync(messages)
    # Ne lève JAMAIS d'exception - retourne toujours une réponse
    ```
    """
    
    def __init__(
        self,
        gemini_model: str = "gemini-2.5-flash",
        claude_model: str = "claude-3-haiku-20240307"
    ):
        """
        Args:
            gemini_model: Modèle Gemini à utiliser
            claude_model: Modèle Claude pour fallback
        """
        self._gemini: Optional[GeminiProvider] = None
        self._claude: Optional[ClaudeProvider] = None
        self._degraded = get_degraded_agent()
        
        self._gemini_model = gemini_model
        self._claude_model = claude_model
        
        # Circuit Breakers
        self._gemini_circuit = CircuitBreaker(
            name="gemini",
            failure_threshold=3,
            success_threshold=2,
            timeout=60
        )
        
        self._claude_circuit = CircuitBreaker(
            name="claude",
            failure_threshold=3,
            success_threshold=2,
            timeout=60
        )
        
        # Stats
        self._stats = ProviderStats()
        
        # Initialiser providers
        self._init_providers()
    
    def _init_providers(self):
        """Initialise les providers disponibles."""
        # Gemini (primary)
        if os.getenv("GOOGLE_API_KEY"):
            try:
                self._gemini = GeminiProvider(self._gemini_model)
                logger.info("🤖 Gemini Provider initialisé (primary)")
            except Exception as e:
                logger.warning(f"⚠️ Gemini init failed: {e}")
        else:
            logger.warning("⚠️ GOOGLE_API_KEY non configurée")
        
        # Claude (fallback)
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                self._claude = ClaudeProvider(self._claude_model)
                logger.info("🔄 Claude Provider initialisé (fallback)")
            except Exception as e:
                logger.warning(f"⚠️ Claude init failed: {e}")
        else:
            logger.info("ℹ️ ANTHROPIC_API_KEY non configurée (fallback désactivé)")
    
    def generate_sync(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        user_input: str = ""
    ) -> LLMResponse:
        """
        Génère une réponse avec fallback automatique.
        
        NE LÈVE JAMAIS D'EXCEPTION - retourne toujours une réponse.
        
        Args:
            messages: Messages pour le LLM
            tools: Outils disponibles
            temperature: Température
            max_tokens: Max tokens
            user_input: Input utilisateur (pour degraded mode)
        
        Returns:
            LLMResponse (toujours)
        """
        
        # Niveau 1: Essayer Gemini
        if self._gemini and self._gemini_circuit.allow_request():
            try:
                response = self._gemini.generate_sync(messages, tools, temperature, max_tokens)
                self._gemini_circuit.record_success()
                self._stats.gemini_calls += 1
                
                # Reset degraded mode si on revient à la normale
                if self._degraded.is_active():
                    self._degraded.reset()
                
                return response
                
            except Exception as e:
                self._gemini_circuit.record_failure(e)
                self._stats.gemini_failures += 1
                logger.warning(f"⚠️ Gemini failed: {e}")
        
        # Niveau 2: Fallback Claude
        if self._claude and self._claude_circuit.allow_request():
            try:
                logger.info("🔄 Fallback → Claude")
                response = self._claude.generate_sync(messages, tools, temperature, max_tokens)
                self._claude_circuit.record_success()
                self._stats.claude_calls += 1
                
                if self._degraded.is_active():
                    self._degraded.reset()
                
                return response
                
            except Exception as e:
                self._claude_circuit.record_failure(e)
                self._stats.claude_failures += 1
                logger.warning(f"⚠️ Claude failed: {e}")
        
        # Niveau 3: Degraded Mode
        logger.error("❌ Tous LLM down → Degraded Mode")
        self._stats.degraded_calls += 1
        
        degraded_response = self._degraded.get_response(user_input)
        
        return LLMResponse(
            text=degraded_response,
            finish_reason="degraded_mode"
        )
    
    async def generate(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        user_input: str = ""
    ) -> LLMResponse:
        """Version async (wrapper sync pour compatibilité)."""
        return self.generate_sync(messages, tools, temperature, max_tokens, user_input)
    
    def get_active_provider(self) -> str:
        """Retourne le nom du provider actif."""
        if self._gemini_circuit.is_closed and self._gemini:
            return "gemini"
        elif self._claude_circuit.is_closed and self._claude:
            return "claude (fallback)"
        else:
            return "degraded_mode"
    
    def get_stats(self) -> dict:
        """Retourne les statistiques d'utilisation."""
        return {
            "active_provider": self.get_active_provider(),
            "gemini": {
                "calls": self._stats.gemini_calls,
                "failures": self._stats.gemini_failures,
                "circuit": self._gemini_circuit.get_stats() if self._gemini else None
            },
            "claude": {
                "calls": self._stats.claude_calls,
                "failures": self._stats.claude_failures,
                "circuit": self._claude_circuit.get_stats() if self._claude else None
            },
            "degraded": {
                "calls": self._stats.degraded_calls,
                **self._degraded.get_stats()
            }
        }
    
    def reset_circuits(self):
        """Reset manuel des circuits (debug)."""
        self._gemini_circuit.reset()
        self._claude_circuit.reset()
        self._degraded.reset()
        logger.info("🔄 Tous les circuits reset")


# Singleton
_resilient_provider: Optional[ResilientLLMProvider] = None


def get_resilient_provider() -> ResilientLLMProvider:
    """Retourne l'instance singleton du provider résilient."""
    global _resilient_provider
    if _resilient_provider is None:
        _resilient_provider = ResilientLLMProvider()
    return _resilient_provider
