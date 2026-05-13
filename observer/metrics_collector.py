#!/usr/bin/env python3
"""
MINA Metrics Collector - Agrégation des Métriques

Collecte, agrège et expose les métriques de performance MINA:
- Throughput (requêtes/sec)
- Latences (P50, P95, P99)
- Taux d'erreur
- Distribution par langue
- États conversationnels

Usage:
    from observer.metrics_collector import MetricsCollector
    collector = MetricsCollector()
    collector.record_request(latency_ms=150, success=True)
    stats = collector.get_stats()

Auteur: Patrick Chedouba
Date: 23 décembre 2024
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque, defaultdict
from threading import Lock
import statistics

# Ajouter le projet au path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# CONFIGURATION
# ============================================================================

# Fenêtre de métriques par défaut (5 minutes)
DEFAULT_WINDOW_SECONDS = 300

# Nombre max d'échantillons en mémoire
MAX_SAMPLES = 10000

# Chemin export métriques
METRICS_EXPORT_PATH = PROJECT_ROOT / "shared" / "metrics" / "mina_metrics.json"

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger("MetricsCollector")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class RequestSample:
    """Échantillon d'une requête."""
    timestamp: datetime
    latency_ms: float
    success: bool
    language: Optional[str] = None
    conversation_state: Optional[str] = None
    institut_id: Optional[str] = None


@dataclass
class WindowStats:
    """Statistiques sur une fenêtre de temps."""
    window_seconds: int
    request_count: int
    error_count: int
    latency_samples: List[float]
    
    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100
    
    @property
    def throughput(self) -> float:
        """Requêtes par seconde."""
        if self.window_seconds == 0:
            return 0.0
        return self.request_count / self.window_seconds
    
    @property
    def latency_p50(self) -> float:
        if not self.latency_samples:
            return 0.0
        return statistics.median(self.latency_samples)
    
    @property
    def latency_p95(self) -> float:
        if len(self.latency_samples) < 2:
            return self.latency_p50
        return statistics.quantiles(self.latency_samples, n=20)[18]  # 95th
    
    @property
    def latency_p99(self) -> float:
        if len(self.latency_samples) < 10:
            return self.latency_p95
        return statistics.quantiles(self.latency_samples, n=100)[98]  # 99th


# ============================================================================
# METRICS COLLECTOR
# ============================================================================

class MetricsCollector:
    """
    Collecteur de métriques temps réel pour MINA.
    
    Fonctionnalités:
    - Enregistrement des requêtes avec latence/status
    - Calcul de statistiques sur fenêtre glissante
    - Percentiles de latence (P50, P95, P99)
    - Distribution par langue et état conversationnel
    - Export JSON pour monitoring externe
    """
    
    def __init__(self, window_seconds: int = DEFAULT_WINDOW_SECONDS):
        """
        Initialise le collecteur.
        
        Args:
            window_seconds: Taille de la fenêtre glissante
        """
        self.window_seconds = window_seconds
        
        # Échantillons (FIFO avec limite)
        self.samples: deque = deque(maxlen=MAX_SAMPLES)
        
        # Compteurs globaux
        self.total_requests = 0
        self.total_errors = 0
        self.start_time = datetime.now()
        
        # Compteurs par dimension
        self.by_language: Dict[str, int] = defaultdict(int)
        self.by_state: Dict[str, int] = defaultdict(int)
        self.by_institut: Dict[str, int] = defaultdict(int)
        
        # Lock pour thread-safety
        self._lock = Lock()
        
        logger.info(f"📊 MetricsCollector initialisé (window: {window_seconds}s)")
    
    # -------------------------------------------------------------------------
    # ENREGISTREMENT
    # -------------------------------------------------------------------------
    
    def record_request(
        self,
        latency_ms: float,
        success: bool,
        language: Optional[str] = None,
        conversation_state: Optional[str] = None,
        institut_id: Optional[str] = None
    ):
        """
        Enregistre une requête.
        
        Args:
            latency_ms: Latence en millisecondes
            success: True si succès
            language: Code langue (fr, en, ar, ...)
            conversation_state: État conversation (HESITATION, RUSH, ...)
            institut_id: Identifiant institut
        """
        sample = RequestSample(
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            success=success,
            language=language,
            conversation_state=conversation_state,
            institut_id=institut_id,
        )
        
        with self._lock:
            self.samples.append(sample)
            self.total_requests += 1
            
            if not success:
                self.total_errors += 1
            
            if language:
                self.by_language[language] += 1
            
            if conversation_state:
                self.by_state[conversation_state] += 1
            
            if institut_id:
                self.by_institut[institut_id] += 1
    
    def record_from_event(self, event: dict):
        """
        Enregistre depuis un événement MINA.
        
        Args:
            event: Dict événement depuis mina_events.jsonl
        """
        self.record_request(
            latency_ms=event.get("latency_ms", 0),
            success=event.get("success", True),
            language=event.get("language"),
            conversation_state=event.get("conversation_state"),
            institut_id=event.get("institut_id"),
        )
    
    # -------------------------------------------------------------------------
    # STATISTIQUES
    # -------------------------------------------------------------------------
    
    def _get_window_samples(self) -> List[RequestSample]:
        """Retourne les échantillons dans la fenêtre courante."""
        cutoff = datetime.now() - timedelta(seconds=self.window_seconds)
        
        with self._lock:
            return [s for s in self.samples if s.timestamp >= cutoff]
    
    def get_window_stats(self) -> WindowStats:
        """
        Calcule les statistiques sur la fenêtre glissante.
        
        Returns:
            WindowStats avec throughput, latences, error rate
        """
        samples = self._get_window_samples()
        
        request_count = len(samples)
        error_count = sum(1 for s in samples if not s.success)
        latency_samples = [s.latency_ms for s in samples if s.success]
        
        return WindowStats(
            window_seconds=self.window_seconds,
            request_count=request_count,
            error_count=error_count,
            latency_samples=latency_samples,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne toutes les statistiques.
        
        Returns:
            Dict complet avec métriques
        """
        window = self.get_window_stats()
        uptime = datetime.now() - self.start_time
        
        with self._lock:
            by_language = dict(self.by_language)
            by_state = dict(self.by_state)
            by_institut = dict(self.by_institut)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            
            # Globaux
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "total_error_rate": (self.total_errors / max(self.total_requests, 1)) * 100,
            
            # Fenêtre glissante
            "window": {
                "seconds": self.window_seconds,
                "request_count": window.request_count,
                "error_count": window.error_count,
                "error_rate": round(window.error_rate, 2),
                "throughput_rps": round(window.throughput, 2),
                "latency_p50_ms": round(window.latency_p50, 2),
                "latency_p95_ms": round(window.latency_p95, 2),
                "latency_p99_ms": round(window.latency_p99, 2),
            },
            
            # Distributions
            "by_language": by_language,
            "by_conversation_state": by_state,
            "by_institut": dict(sorted(by_institut.items(), key=lambda x: -x[1])[:10]),
        }
    
    def get_prometheus_metrics(self) -> str:
        """
        Retourne les métriques au format Prometheus.
        
        Returns:
            String au format Prometheus exposition
        """
        stats = self.get_stats()
        window = stats["window"]
        
        lines = [
            "# HELP mina_requests_total Total requests",
            "# TYPE mina_requests_total counter",
            f'mina_requests_total {stats["total_requests"]}',
            "",
            "# HELP mina_errors_total Total errors",
            "# TYPE mina_errors_total counter",
            f'mina_errors_total {stats["total_errors"]}',
            "",
            "# HELP mina_request_duration_seconds Request latency",
            "# TYPE mina_request_duration_seconds summary",
            f'mina_request_duration_seconds{{quantile="0.5"}} {window["latency_p50_ms"]/1000}',
            f'mina_request_duration_seconds{{quantile="0.95"}} {window["latency_p95_ms"]/1000}',
            f'mina_request_duration_seconds{{quantile="0.99"}} {window["latency_p99_ms"]/1000}',
            "",
            "# HELP mina_error_rate Error rate percentage",
            "# TYPE mina_error_rate gauge",
            f'mina_error_rate {window["error_rate"]}',
            "",
        ]
        
        # Métriques par langue
        lines.append("# HELP mina_requests_by_language Requests by language")
        lines.append("# TYPE mina_requests_by_language counter")
        for lang, count in stats["by_language"].items():
            lines.append(f'mina_requests_by_language{{language="{lang}"}} {count}')
        
        return "\n".join(lines)
    
    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------
    
    def export_json(self, path: Optional[Path] = None):
        """
        Exporte les métriques en JSON.
        
        Args:
            path: Chemin du fichier (défaut: shared/metrics/)
        """
        path = path or METRICS_EXPORT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        
        stats = self.get_stats()
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"📄 Métriques exportées: {path}")
    
    # -------------------------------------------------------------------------
    # AFFICHAGE
    # -------------------------------------------------------------------------
    
    def print_stats(self):
        """Affiche les statistiques en console."""
        stats = self.get_stats()
        window = stats["window"]
        
        print()
        print("=" * 60)
        print(f"📊 MINA Metrics - {stats['timestamp'][:19]}")
        print("=" * 60)
        
        print(f"\n⏱️  Uptime: {int(stats['uptime_seconds'])}s")
        print(f"📨 Total requêtes: {stats['total_requests']}")
        print(f"❌ Total erreurs: {stats['total_errors']} ({stats['total_error_rate']:.1f}%)")
        
        print(f"\n📈 Fenêtre glissante ({window['seconds']}s):")
        print(f"   Requêtes: {window['request_count']}")
        print(f"   Throughput: {window['throughput_rps']:.2f} req/s")
        print(f"   Error rate: {window['error_rate']:.1f}%")
        print(f"   Latence P50: {window['latency_p50_ms']:.0f}ms")
        print(f"   Latence P95: {window['latency_p95_ms']:.0f}ms")
        print(f"   Latence P99: {window['latency_p99_ms']:.0f}ms")
        
        if stats["by_language"]:
            print("\n🌍 Par langue:")
            for lang, count in sorted(stats["by_language"].items(), key=lambda x: -x[1])[:5]:
                print(f"   {lang}: {count}")
        
        if stats["by_conversation_state"]:
            print("\n🧠 Par état conversationnel:")
            for state, count in sorted(stats["by_conversation_state"].items(), key=lambda x: -x[1])[:5]:
                print(f"   {state}: {count}")
        
        print("=" * 60)
    
    def reset(self):
        """Remet à zéro les compteurs."""
        with self._lock:
            self.samples.clear()
            self.total_requests = 0
            self.total_errors = 0
            self.by_language.clear()
            self.by_state.clear()
            self.by_institut.clear()
            self.start_time = datetime.now()
        
        logger.info("🔄 Métriques remises à zéro")


# ============================================================================
# CLI
# ============================================================================

def main():
    """Point d'entrée CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MINA Metrics Collector")
    parser.add_argument("--demo", action="store_true", help="Générer données demo")
    parser.add_argument("--export", action="store_true", help="Exporter JSON")
    parser.add_argument("--prometheus", action="store_true", help="Format Prometheus")
    
    args = parser.parse_args()
    
    collector = MetricsCollector()
    
    if args.demo:
        import random
        print("🎲 Génération données demo...")
        for i in range(100):
            collector.record_request(
                latency_ms=random.gauss(500, 200),
                success=random.random() > 0.05,
                language=random.choice(["fr", "en", "ar", "es"]),
                conversation_state=random.choice([None, "HESITATION", "RUSH", "CURIOSITY"]),
            )
        print(f"   {collector.total_requests} requêtes générées")
    
    if args.prometheus:
        print(collector.get_prometheus_metrics())
    elif args.export:
        collector.export_json()
    else:
        collector.print_stats()


if __name__ == "__main__":
    main()
