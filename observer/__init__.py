"""
MINA Observer Package
Système de monitoring et observabilité pour MINA.

Modules:
- mina_observer: Monitoring central et détection anomalies
- alert_manager: Alertes SMS (Twilio) et Email (SMTP)
- health_monitor: Health checks des services
- metrics_collector: Agrégation des métriques

Usage:
    from observer import MinaObserver, AlertManager, HealthChecker

Auteur: Patrick Chedouba
Date: 23 décembre 2024
"""

from observer.mina_observer import MinaObserver, MinaEvent, Alert
from observer.alert_manager import AlertManager
from observer.health_monitor import HealthChecker, HealthMonitor, HealthServer
from observer.metrics_collector import MetricsCollector

__all__ = [
    "MinaObserver",
    "MinaEvent",
    "Alert",
    "AlertManager",
    "HealthChecker",
    "HealthMonitor",
    "HealthServer",
    "MetricsCollector",
]

__version__ = "1.0.0"
