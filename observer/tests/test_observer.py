#!/usr/bin/env python3
"""
Tests unitaires pour MINA Observer.

Usage:
    python -m pytest observer/tests/test_observer.py -v

Auteur: Patrick Chedouba
Date: 23 décembre 2024
"""

import sys
import os
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import unittest

# Ajouter le projet au path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from observer.mina_observer import MinaObserver, MinaEvent, Alert, THRESHOLDS
from observer.metrics_collector import MetricsCollector
from observer.health_monitor import HealthChecker, HealthCheckResult


# ============================================================================
# TESTS MINA OBSERVER
# ============================================================================

class TestMinaEvent(unittest.TestCase):
    """Tests pour MinaEvent."""
    
    def test_from_json_basic(self):
        """Parse un événement JSON simple."""
        data = {
            "timestamp": "2024-12-23T10:00:00",
            "event_type": "request",
            "latency_ms": 500,
            "success": True,
            "language": "fr",
        }
        event = MinaEvent.from_json(data)
        
        self.assertEqual(event.event_type, "request")
        self.assertEqual(event.latency_ms, 500)
        self.assertTrue(event.success)
        self.assertEqual(event.language, "fr")
    
    def test_from_json_error(self):
        """Parse un événement erreur."""
        data = {
            "timestamp": "2024-12-23T10:00:00",
            "event_type": "error",
            "success": False,
            "error_message": "Connection timeout",
        }
        event = MinaEvent.from_json(data)
        
        self.assertEqual(event.event_type, "error")
        self.assertFalse(event.success)
        self.assertEqual(event.error_message, "Connection timeout")
    
    def test_from_json_missing_fields(self):
        """Gère les champs manquants gracieusement."""
        data = {"event_type": "request"}
        event = MinaEvent.from_json(data)
        
        self.assertIsNone(event.latency_ms)
        self.assertIsNone(event.language)
        self.assertTrue(event.success)  # Défaut


class TestMinaObserver(unittest.TestCase):
    """Tests pour MinaObserver."""
    
    def setUp(self):
        """Crée un observer avec fichier temporaire."""
        self.temp_dir = tempfile.mkdtemp()
        self.events_file = Path(self.temp_dir) / "mina_events.jsonl"
        
        # Patcher le chemin
        self.original_path = __import__('observer.mina_observer', fromlist=['EVENTS_LOG_PATH'])
        
        self.observer = MinaObserver()
    
    def test_init(self):
        """Observer s'initialise correctement."""
        self.assertIsNotNone(self.observer)
        self.assertEqual(len(self.observer.metrics), 0)
        self.assertEqual(self.observer.global_metrics["total_events"], 0)
    
    def test_process_event_success(self):
        """Traite un événement réussi."""
        event = MinaEvent(
            timestamp=datetime.now(),
            event_type="request",
            latency_ms=500,
            success=True,
            language="fr",
            institut_id="BM-PARIS-01",
        )
        
        self.observer.process_event(event)
        
        self.assertEqual(self.observer.global_metrics["total_events"], 1)
        self.assertEqual(self.observer.global_metrics["total_errors"], 0)
        
        metrics = self.observer.metrics["BM-PARIS-01"]
        self.assertEqual(metrics.total_requests, 1)
        self.assertEqual(metrics.total_errors, 0)
        self.assertEqual(metrics.total_latency_ms, 500)
    
    def test_process_event_error(self):
        """Traite un événement erreur."""
        event = MinaEvent(
            timestamp=datetime.now(),
            event_type="error",
            success=False,
            error_message="Timeout",
            institut_id="BM-LYON-01",
        )
        
        self.observer.process_event(event)
        
        self.assertEqual(self.observer.global_metrics["total_errors"], 1)
        
        metrics = self.observer.metrics["BM-LYON-01"]
        self.assertEqual(metrics.total_errors, 1)
        self.assertEqual(metrics.consecutive_errors, 1)
    
    def test_consecutive_errors_reset(self):
        """Les erreurs consécutives se réinitialisent après succès."""
        # 3 erreurs
        for _ in range(3):
            self.observer.process_event(MinaEvent(
                timestamp=datetime.now(),
                event_type="error",
                success=False,
                institut_id="TEST",
            ))
        
        self.assertEqual(self.observer.metrics["TEST"].consecutive_errors, 3)
        
        # 1 succès
        self.observer.process_event(MinaEvent(
            timestamp=datetime.now(),
            event_type="request",
            success=True,
            institut_id="TEST",
        ))
        
        self.assertEqual(self.observer.metrics["TEST"].consecutive_errors, 0)
    
    def test_error_rate_calculation(self):
        """Calcule correctement le taux d'erreur."""
        # 8 succès, 2 erreurs = 20%
        for _ in range(8):
            self.observer.process_event(MinaEvent(
                timestamp=datetime.now(),
                event_type="request",
                success=True,
                institut_id="TEST",
            ))
        
        for _ in range(2):
            self.observer.process_event(MinaEvent(
                timestamp=datetime.now(),
                event_type="error",
                success=False,
                institut_id="TEST",
            ))
        
        metrics = self.observer.metrics["TEST"]
        self.assertAlmostEqual(metrics.error_rate, 20.0, places=1)
    
    def test_language_tracking(self):
        """Compte les langues utilisées."""
        languages = ["fr", "fr", "en", "ar", "fr"]
        for lang in languages:
            self.observer.process_event(MinaEvent(
                timestamp=datetime.now(),
                event_type="request",
                success=True,
                language=lang,
                institut_id="TEST",
            ))
        
        metrics = self.observer.metrics["TEST"]
        self.assertEqual(metrics.languages_used["fr"], 3)
        self.assertEqual(metrics.languages_used["en"], 1)
        self.assertEqual(metrics.languages_used["ar"], 1)


class TestAnomalyDetection(unittest.TestCase):
    """Tests pour la détection d'anomalies."""
    
    def setUp(self):
        self.observer = MinaObserver()
        self.alerts_triggered = []
        
        # Capturer les alertes
        original_trigger = self.observer._trigger_alert
        def capture_alert(**kwargs):
            self.alerts_triggered.append(kwargs)
        self.observer._trigger_alert = capture_alert
    
    def test_latency_critical_alert(self):
        """Alerte sur latence critique."""
        event = MinaEvent(
            timestamp=datetime.now(),
            event_type="request",
            latency_ms=15000,  # > 10000 (seuil)
            success=True,
            institut_id="TEST",
        )
        
        self.observer.process_event(event)
        
        critical_alerts = [a for a in self.alerts_triggered if a["level"] == "critical"]
        self.assertGreater(len(critical_alerts), 0)
        self.assertEqual(critical_alerts[0]["category"], "latency")
    
    def test_latency_warning_alert(self):
        """Warning sur latence élevée."""
        event = MinaEvent(
            timestamp=datetime.now(),
            event_type="request",
            latency_ms=7000,  # > 5000, < 10000
            success=True,
            institut_id="TEST",
        )
        
        self.observer.process_event(event)
        
        warning_alerts = [a for a in self.alerts_triggered if a["level"] == "warning"]
        self.assertGreater(len(warning_alerts), 0)
    
    def test_consecutive_errors_alert(self):
        """Alerte après 5 erreurs consécutives."""
        for i in range(5):
            self.observer.process_event(MinaEvent(
                timestamp=datetime.now(),
                event_type="error",
                success=False,
                institut_id="TEST",
            ))
        
        consecutive_alerts = [a for a in self.alerts_triggered if a["category"] == "consecutive"]
        self.assertGreater(len(consecutive_alerts), 0)


# ============================================================================
# TESTS METRICS COLLECTOR
# ============================================================================

class TestMetricsCollector(unittest.TestCase):
    """Tests pour MetricsCollector."""
    
    def setUp(self):
        self.collector = MetricsCollector(window_seconds=60)
    
    def test_record_request(self):
        """Enregistre une requête."""
        self.collector.record_request(
            latency_ms=500,
            success=True,
            language="fr",
        )
        
        self.assertEqual(self.collector.total_requests, 1)
        self.assertEqual(self.collector.by_language["fr"], 1)
    
    def test_error_counting(self):
        """Compte les erreurs correctement."""
        self.collector.record_request(latency_ms=100, success=True)
        self.collector.record_request(latency_ms=100, success=False)
        self.collector.record_request(latency_ms=100, success=False)
        
        self.assertEqual(self.collector.total_requests, 3)
        self.assertEqual(self.collector.total_errors, 2)
    
    def test_window_stats(self):
        """Calcule les stats sur fenêtre."""
        for latency in [100, 200, 300, 400, 500]:
            self.collector.record_request(latency_ms=latency, success=True)
        
        stats = self.collector.get_window_stats()
        
        self.assertEqual(stats.request_count, 5)
        self.assertEqual(stats.latency_p50, 300)  # Médiane
    
    def test_reset(self):
        """Reset remet les compteurs à zéro."""
        self.collector.record_request(latency_ms=100, success=True)
        self.collector.reset()
        
        self.assertEqual(self.collector.total_requests, 0)


# ============================================================================
# TESTS HEALTH CHECKER
# ============================================================================

class TestHealthChecker(unittest.TestCase):
    """Tests pour HealthChecker."""
    
    def test_health_check_result(self):
        """HealthCheckResult se crée correctement."""
        result = HealthCheckResult(
            service="test",
            healthy=True,
            latency_ms=50.5,
            status_code=200,
        )
        
        self.assertTrue(result.healthy)
        self.assertEqual(result.latency_ms, 50.5)
        
        d = result.to_dict()
        self.assertEqual(d["service"], "test")
        self.assertTrue(d["healthy"])
    
    @patch('urllib.request.urlopen')
    def test_check_endpoint_success(self, mock_urlopen):
        """Check endpoint retourne healthy sur 200."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        checker = HealthChecker(endpoints={
            "test": {"url": "http://test.com", "timeout": 5}
        })
        result = checker.check_endpoint("test", {"url": "http://test.com", "timeout": 5})
        
        self.assertTrue(result.healthy)
        self.assertEqual(result.status_code, 200)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    unittest.main()
