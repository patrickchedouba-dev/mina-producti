"""
Circuit Breaker Pattern pour LLM calls.

Protège contre les pannes en cascade:
- CLOSED: Normal
- OPEN: Trop d'erreurs, coupe les appels
- HALF_OPEN: Test si service revenu
"""

import logging
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """États du circuit breaker."""
    CLOSED = "closed"      # Normal - appels autorisés
    OPEN = "open"          # Coupé - appels bloqués
    HALF_OPEN = "half_open"  # Test - 1 appel autorisé


@dataclass
class CircuitStats:
    """Statistiques du circuit."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_calls: int = 0
    total_failures: int = 0


class CircuitBreaker:
    """
    Circuit Breaker pour protéger les appels LLM.
    
    Usage:
    ```python
    breaker = CircuitBreaker(failure_threshold=5, timeout=60)
    
    try:
        result = await breaker.call(llm.generate, prompt)
    except CircuitOpenError:
        # Circuit ouvert, utiliser fallback
        pass
    ```
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        name: str = "default"
    ):
        """
        Args:
            failure_threshold: Nombre d'échecs avant OPEN
            success_threshold: Nombre de succès en HALF_OPEN pour CLOSE
            timeout: Secondes avant de passer de OPEN à HALF_OPEN
            name: Nom du circuit (pour logs)
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._stats = CircuitStats()
    
    @property
    def state(self) -> CircuitState:
        """État actuel du circuit."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Vérifie si timeout écoulé pour tenter un reset."""
        if self._last_failure_time is None:
            return True
        
        elapsed = datetime.now() - self._last_failure_time
        return elapsed > timedelta(seconds=self.timeout)
    
    def _transition_to(self, new_state: CircuitState, reason: str = ""):
        """Transition d'état avec logging."""
        old_state = self._state
        self._state = new_state
        
        if old_state != new_state:
            logger.info(f"🔌 Circuit [{self.name}]: {old_state.value} → {new_state.value} ({reason})")
    
    def record_success(self):
        """Enregistre un succès."""
        self._stats.total_calls += 1
        self._stats.success_count += 1
        self._stats.last_success_time = datetime.now()
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            
            if self._success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED, f"{self._success_count} succès consécutifs")
                self._failure_count = 0
                self._success_count = 0
        
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    def record_failure(self, error: Exception = None):
        """Enregistre un échec."""
        self._stats.total_calls += 1
        self._stats.total_failures += 1
        self._failure_count += 1
        self._success_count = 0
        self._last_failure_time = datetime.now()
        self._stats.last_failure_time = self._last_failure_time
        
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN, "échec en HALF_OPEN")
        
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN, f"{self._failure_count} échecs consécutifs")
    
    def allow_request(self) -> bool:
        """Vérifie si une requête est autorisée."""
        if self._state == CircuitState.CLOSED:
            return True
        
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN, f"timeout {self.timeout}s écoulé")
                return True
            return False
        
        # HALF_OPEN - autorise une requête test
        return True
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Appelle une fonction avec protection circuit breaker.
        
        Args:
            func: Fonction async à appeler
            *args, **kwargs: Arguments de la fonction
        
        Returns:
            Résultat de la fonction
        
        Raises:
            CircuitOpenError: Si circuit ouvert
            Exception: Exception originale si échec
        """
        if not self.allow_request():
            raise CircuitOpenError(
                f"Circuit [{self.name}] OPEN - {self.failure_threshold} échecs, "
                f"retry dans {self.timeout}s"
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        
        except Exception as e:
            self.record_failure(e)
            raise
    
    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Version synchrone de call()."""
        if not self.allow_request():
            raise CircuitOpenError(
                f"Circuit [{self.name}] OPEN - {self.failure_threshold} échecs"
            )
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        
        except Exception as e:
            self.record_failure(e)
            raise
    
    def get_stats(self) -> dict:
        """Retourne les statistiques du circuit."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "total_calls": self._stats.total_calls,
            "total_failures": self._stats.total_failures,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None
        }
    
    def reset(self):
        """Reset manuel du circuit."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info(f"🔄 Circuit [{self.name}] reset manuellement")


class CircuitOpenError(Exception):
    """Exception levée quand le circuit est ouvert."""
    pass
