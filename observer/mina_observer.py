#!/usr/bin/env python3
"""
MINA Observer - Système de Monitoring Central

Surveille en temps réel les événements Mina et déclenche des alertes
si des anomalies sont détectées.

Usage:
    python -m observer.mina_observer
    ou
    python observer/mina_observer.py --watch

Auteur: Patrick Chedouba
Date: 23 décembre 2024
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict
from threading import Thread, Event
import signal

# Ajouter le projet au path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# CONFIGURATION
# ============================================================================

# Chemins
EVENTS_LOG_PATH = PROJECT_ROOT / "shared" / "logs" / "mina_events.jsonl"
CONFIG_PATH = PROJECT_ROOT / "shared" / "config" / "observer_config.json"

# Seuils d'alerte
THRESHOLDS = {
    "error_rate_percent": 10,       # Alerte si > 10% erreurs
    "latency_critical_ms": 10000,   # Alerte si latence > 10s
    "latency_warning_ms": 5000,     # Warning si latence > 5s
    "consecutive_errors": 5,         # Alerte après 5 erreurs consécutives
    "health_check_interval_s": 30,   # Check santé toutes les 30s
    "metrics_window_minutes": 5,     # Fenêtre glissante 5 min
    "alert_cooldown_minutes": 10,    # Anti-spam: 1 alerte/10 min
}

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MinaObserver")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class MinaEvent:
    """Événement Mina (requête/réponse)."""
    timestamp: datetime
    event_type: str          # "request", "response", "error", "health"
    institut_id: Optional[str] = None
    latency_ms: Optional[int] = None
    language: Optional[str] = None
    conversation_state: Optional[str] = None
    error_message: Optional[str] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, data: Dict) -> "MinaEvent":
        """Parse un événement depuis JSON."""
        ts = data.get("timestamp")
        if isinstance(ts, str):
            try:
                timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()
            
        return cls(
            timestamp=timestamp,
            event_type=data.get("event_type", "unknown"),
            institut_id=data.get("institut_id"),
            latency_ms=data.get("latency_ms"),
            language=data.get("language"),
            conversation_state=data.get("conversation_state"),
            error_message=data.get("error_message"),
            success=data.get("success", True),
            metadata=data.get("metadata", {})
        )


@dataclass
class InstitutMetrics:
    """Métriques agrégées par institut."""
    institut_id: str
    total_requests: int = 0
    total_errors: int = 0
    total_latency_ms: int = 0
    consecutive_errors: int = 0
    last_event_time: Optional[datetime] = None
    languages_used: Dict[str, int] = field(default_factory=dict)
    states_detected: Dict[str, int] = field(default_factory=dict)
    
    @property
    def error_rate(self) -> float:
        """Taux d'erreur en pourcentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.total_errors / self.total_requests) * 100
    
    @property
    def avg_latency_ms(self) -> float:
        """Latence moyenne."""
        successful = self.total_requests - self.total_errors
        if successful == 0:
            return 0.0
        return self.total_latency_ms / successful


@dataclass
class Alert:
    """Alerte déclenchée."""
    timestamp: datetime
    level: str              # "warning", "critical", "recovery"
    category: str           # "error_rate", "latency", "consecutive", "health"
    message: str
    institut_id: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None


# ============================================================================
# MINA OBSERVER - COMPOSANT CENTRAL
# ============================================================================

class MinaObserver:
    """
    Système de monitoring central pour MINA.
    
    Responsabilités:
    - Lecture continue des événements (mina_events.jsonl)
    - Agrégation des métriques par institut
    - Détection d'anomalies (error rate, latence, erreurs consécutives)
    - Déclenchement d'alertes
    - Rapport temps réel console
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialise l'Observer."""
        self.config = config or THRESHOLDS.copy()
        
        # Métriques par institut
        self.metrics: Dict[str, InstitutMetrics] = defaultdict(
            lambda: InstitutMetrics(institut_id="unknown")
        )
        
        # Métriques globales
        self.global_metrics = {
            "total_events": 0,
            "total_errors": 0,
            "start_time": datetime.now(),
            "last_event_time": None,
        }
        
        # Alertes
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self.last_alert_time: Dict[str, datetime] = {}  # Anti-spam par catégorie
        
        # Contrôle
        self.stop_event = Event()
        self.file_position = 0
        
        # Callbacks alerting (sera injecté par AlertManager)
        self.on_alert_callback = None
        
        logger.info("🔭 MINA Observer initialisé")
        logger.info(f"   Events log: {EVENTS_LOG_PATH}")
        logger.info(f"   Seuils: error_rate={self.config['error_rate_percent']}%, "
                    f"latency_critical={self.config['latency_critical_ms']}ms")
    
    # -------------------------------------------------------------------------
    # LECTURE ÉVÉNEMENTS
    # -------------------------------------------------------------------------
    
    def read_events(self, since_position: int = 0) -> List[MinaEvent]:
        """
        Lit les nouveaux événements depuis le fichier JSONL.
        
        Args:
            since_position: Position dans le fichier (bytes)
            
        Returns:
            Liste des nouveaux événements
        """
        events = []
        
        if not EVENTS_LOG_PATH.exists():
            return events
        
        try:
            with open(EVENTS_LOG_PATH, 'r', encoding='utf-8') as f:
                f.seek(since_position)
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        event = MinaEvent.from_json(data)
                        events.append(event)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Ligne JSON invalide: {e}")
                    except Exception as e:
                        logger.error(f"Erreur parsing événement: {e}")
                
                # Sauvegarder position
                self.file_position = f.tell()
                
        except Exception as e:
            logger.error(f"Erreur lecture {EVENTS_LOG_PATH}: {e}")
        
        return events
    
    # -------------------------------------------------------------------------
    # TRAITEMENT ÉVÉNEMENTS
    # -------------------------------------------------------------------------
    
    def process_event(self, event: MinaEvent):
        """
        Traite un événement et met à jour les métriques.
        
        Args:
            event: Événement à traiter
        """
        institut_id = event.institut_id or "global"
        
        # Initialiser métriques institut si nécessaire
        if institut_id not in self.metrics:
            self.metrics[institut_id] = InstitutMetrics(institut_id=institut_id)
        
        metrics = self.metrics[institut_id]
        
        # Mettre à jour compteurs
        metrics.total_requests += 1
        metrics.last_event_time = event.timestamp
        self.global_metrics["total_events"] += 1
        self.global_metrics["last_event_time"] = event.timestamp
        
        # Traiter selon type
        if event.event_type == "error" or not event.success:
            metrics.total_errors += 1
            metrics.consecutive_errors += 1
            self.global_metrics["total_errors"] += 1
        else:
            metrics.consecutive_errors = 0
            if event.latency_ms:
                metrics.total_latency_ms += event.latency_ms
        
        # Langues
        if event.language:
            metrics.languages_used[event.language] = \
                metrics.languages_used.get(event.language, 0) + 1
        
        # États conversationnels
        if event.conversation_state:
            metrics.states_detected[event.conversation_state] = \
                metrics.states_detected.get(event.conversation_state, 0) + 1
        
        # Vérifier anomalies
        self._check_anomalies(event, metrics)
    
    # -------------------------------------------------------------------------
    # DÉTECTION ANOMALIES
    # -------------------------------------------------------------------------
    
    def _check_anomalies(self, event: MinaEvent, metrics: InstitutMetrics):
        """
        Vérifie si l'événement ou les métriques dépassent les seuils.
        
        Args:
            event: Événement courant
            metrics: Métriques de l'institut
        """
        # 1. Taux d'erreur élevé
        if metrics.total_requests >= 10:  # Minimum d'échantillons
            if metrics.error_rate > self.config["error_rate_percent"]:
                self._trigger_alert(
                    level="critical",
                    category="error_rate",
                    message=f"Taux d'erreur critique: {metrics.error_rate:.1f}%",
                    institut_id=metrics.institut_id,
                    value=metrics.error_rate,
                    threshold=self.config["error_rate_percent"]
                )
        
        # 2. Latence critique
        if event.latency_ms:
            if event.latency_ms > self.config["latency_critical_ms"]:
                self._trigger_alert(
                    level="critical",
                    category="latency",
                    message=f"Latence critique: {event.latency_ms}ms",
                    institut_id=metrics.institut_id,
                    value=event.latency_ms,
                    threshold=self.config["latency_critical_ms"]
                )
            elif event.latency_ms > self.config["latency_warning_ms"]:
                self._trigger_alert(
                    level="warning",
                    category="latency",
                    message=f"Latence élevée: {event.latency_ms}ms",
                    institut_id=metrics.institut_id,
                    value=event.latency_ms,
                    threshold=self.config["latency_warning_ms"]
                )
        
        # 3. Erreurs consécutives
        if metrics.consecutive_errors >= self.config["consecutive_errors"]:
            self._trigger_alert(
                level="critical",
                category="consecutive",
                message=f"{metrics.consecutive_errors} erreurs consécutives",
                institut_id=metrics.institut_id,
                value=metrics.consecutive_errors,
                threshold=self.config["consecutive_errors"]
            )
        
        # 4. Erreur critique spécifique
        if event.error_message and event.event_type == "error":
            critical_keywords = ["timeout", "connection", "crash", "fatal"]
            if any(kw in event.error_message.lower() for kw in critical_keywords):
                self._trigger_alert(
                    level="critical",
                    category="error_critical",
                    message=f"Erreur critique: {event.error_message[:100]}",
                    institut_id=metrics.institut_id
                )
    
    def _trigger_alert(
        self,
        level: str,
        category: str,
        message: str,
        institut_id: Optional[str] = None,
        value: Optional[float] = None,
        threshold: Optional[float] = None
    ):
        """
        Déclenche une alerte si le cooldown est respecté.
        
        Args:
            level: "warning" ou "critical"
            category: Type d'alerte
            message: Description
            institut_id: Institut concerné
            value: Valeur mesurée
            threshold: Seuil dépassé
        """
        now = datetime.now()
        cooldown_key = f"{category}_{institut_id or 'global'}"
        
        # Anti-spam: respecter cooldown
        if cooldown_key in self.last_alert_time:
            last_time = self.last_alert_time[cooldown_key]
            cooldown = timedelta(minutes=self.config["alert_cooldown_minutes"])
            if now - last_time < cooldown:
                return  # Ignorer, en cooldown
        
        # Créer alerte
        alert = Alert(
            timestamp=now,
            level=level,
            category=category,
            message=message,
            institut_id=institut_id,
            value=value,
            threshold=threshold
        )
        
        # Enregistrer
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        self.last_alert_time[cooldown_key] = now
        
        # Log
        emoji = "🔴" if level == "critical" else "🟡"
        logger.warning(f"{emoji} ALERTE [{level.upper()}] {category}: {message}")
        
        # Callback externe (AlertManager)
        if self.on_alert_callback:
            try:
                self.on_alert_callback(alert)
            except Exception as e:
                logger.error(f"Erreur callback alerte: {e}")
    
    # -------------------------------------------------------------------------
    # MONITORING CONTINU
    # -------------------------------------------------------------------------
    
    def watch(self, poll_interval: float = 1.0):
        """
        Mode surveillance continue (boucle principale).
        
        Args:
            poll_interval: Intervalle de lecture en secondes
        """
        logger.info("🔍 Démarrage surveillance continue...")
        logger.info(f"   Poll interval: {poll_interval}s")
        logger.info("   Ctrl+C pour arrêter")
        print()
        
        # Gérer SIGINT/SIGTERM proprement
        def signal_handler(signum, frame):
            logger.info("⏹️  Arrêt demandé...")
            self.stop_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Lire position initiale (fin du fichier)
        if EVENTS_LOG_PATH.exists():
            with open(EVENTS_LOG_PATH, 'r') as f:
                f.seek(0, 2)  # Aller à la fin
                self.file_position = f.tell()
        
        last_report_time = datetime.now()
        report_interval = timedelta(seconds=30)
        
        # Boucle principale
        while not self.stop_event.is_set():
            try:
                # Lire nouveaux événements
                events = self.read_events(self.file_position)
                
                for event in events:
                    self.process_event(event)
                    self._print_event(event)
                
                # Rapport périodique
                if datetime.now() - last_report_time > report_interval:
                    self.print_summary()
                    last_report_time = datetime.now()
                
                # Pause
                time.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Erreur boucle monitoring: {e}")
                time.sleep(5)  # Pause plus longue sur erreur
        
        logger.info("👋 Surveillance terminée")
        self.print_summary()
    
    def _print_event(self, event: MinaEvent):
        """Affiche un événement en console."""
        status = "✅" if event.success else "❌"
        latency = f"{event.latency_ms}ms" if event.latency_ms else "-"
        lang = event.language or "fr"
        state = event.conversation_state or "-"
        
        print(f"  {status} {event.timestamp.strftime('%H:%M:%S')} | "
              f"{event.event_type:8} | {lang} | {latency:>6} | {state}")
    
    # -------------------------------------------------------------------------
    # RAPPORTS
    # -------------------------------------------------------------------------
    
    def print_summary(self):
        """Affiche un résumé des métriques."""
        print()
        print("=" * 60)
        print(f"📊 MINA Observer - Résumé {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        
        # Global
        uptime = datetime.now() - self.global_metrics["start_time"]
        print(f"\n⏱️  Uptime: {str(uptime).split('.')[0]}")
        print(f"📨 Total événements: {self.global_metrics['total_events']}")
        print(f"❌ Total erreurs: {self.global_metrics['total_errors']}")
        
        # Par institut
        if self.metrics:
            print(f"\n📍 Métriques par institut:")
            for institut_id, m in sorted(self.metrics.items()):
                if m.total_requests > 0:
                    print(f"   {institut_id}: "
                          f"{m.total_requests} req, "
                          f"{m.error_rate:.1f}% err, "
                          f"{m.avg_latency_ms:.0f}ms avg")
        
        # Alertes actives
        if self.active_alerts:
            print(f"\n🚨 Alertes actives: {len(self.active_alerts)}")
            for alert in self.active_alerts[-5:]:  # 5 dernières
                print(f"   [{alert.level}] {alert.message}")
        
        print("=" * 60)
        print()
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le status complet pour API."""
        return {
            "status": "running" if not self.stop_event.is_set() else "stopped",
            "uptime_seconds": (datetime.now() - self.global_metrics["start_time"]).total_seconds(),
            "total_events": self.global_metrics["total_events"],
            "total_errors": self.global_metrics["total_errors"],
            "active_alerts": len(self.active_alerts),
            "institutes": {
                k: {
                    "requests": v.total_requests,
                    "error_rate": v.error_rate,
                    "avg_latency_ms": v.avg_latency_ms,
                }
                for k, v in self.metrics.items()
            }
        }


# ============================================================================
# CLI
# ============================================================================

def main():
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(
        description="MINA Observer - Système de Monitoring"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Mode surveillance continue"
    )
    parser.add_argument(
        "--poll-interval", "-p",
        type=float,
        default=1.0,
        help="Intervalle de lecture (secondes)"
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Afficher résumé actuel et quitter"
    )
    
    args = parser.parse_args()
    
    observer = MinaObserver()
    
    if args.summary:
        # Lire tous les événements et afficher résumé
        events = observer.read_events(0)
        for event in events:
            observer.process_event(event)
        observer.print_summary()
    elif args.watch:
        observer.watch(poll_interval=args.poll_interval)
    else:
        # Mode par défaut: résumé
        events = observer.read_events(0)
        for event in events:
            observer.process_event(event)
        observer.print_summary()


if __name__ == "__main__":
    main()
