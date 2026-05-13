"""
Logging Handler structuré pour Mina V2.

Logs JSON pour chaque interaction avec métriques Prometheus-compatible.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# Répertoire des logs
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


@dataclass
class InteractionLog:
    """Structure de log pour une interaction."""
    timestamp: str = ""
    session_id: str = ""
    client_id: Optional[str] = None
    institut_id: Optional[str] = None
    
    # Input/Output
    user_input: str = ""
    response: str = ""
    
    # Agents
    agents_called: List[str] = field(default_factory=list)
    supervisor_decision: str = ""
    
    # Tools
    tools_called: List[Dict] = field(default_factory=list)
    
    # Métriques
    latency_ms: int = 0
    iterations: int = 0
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class MinaLoggingHandler:
    """Handler de logging structuré pour Mina."""
    
    def __init__(self, log_file: str = "mina_interactions.jsonl"):
        self.log_path = LOG_DIR / log_file
        self.metrics_path = LOG_DIR / "mina_metrics.jsonl"
        logger.info(f"📝 Logging initialisé: {self.log_path}")
    
    def log_interaction(self, log: InteractionLog) -> None:
        """Enregistre une interaction complète."""
        log.timestamp = datetime.now().isoformat()
        
        # Log principal (JSONL)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(log.to_json() + "\n")
        
        # Métriques Prometheus-compatible
        self._log_metrics(log)
        
        logger.debug(f"📝 Interaction logged: {log.session_id[:8]}...")
    
    def _log_metrics(self, log: InteractionLog) -> None:
        """Log les métriques au format Prometheus."""
        metrics = {
            "timestamp": log.timestamp,
            "latency_ms": log.latency_ms,
            "success": 1 if log.success else 0,
            "agents_count": len(log.agents_called),
            "tools_count": len(log.tools_called),
            "iterations": log.iterations,
            "agents": log.agents_called
        }
        
        with open(self.metrics_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Récupère les derniers logs."""
        if not self.log_path.exists():
            return []
        
        logs = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    logs.append(json.loads(line))
                except:
                    pass
        
        return logs[-limit:]


# Singleton
_logging_handler: Optional[MinaLoggingHandler] = None


def get_logging_handler() -> MinaLoggingHandler:
    """Retourne l'instance singleton."""
    global _logging_handler
    if _logging_handler is None:
        _logging_handler = MinaLoggingHandler()
    return _logging_handler
