#!/usr/bin/env python3
"""
MINA Health Monitor - Vérification Santé des Services

Surveille la disponibilité des services critiques:
- Qdrant (base vectorielle)
- Gemini API (LLM)
- Speech-to-Text API
- Text-to-Speech API

Usage:
    python observer/health_monitor.py --check
    python observer/health_monitor.py --serve   # HTTP /health endpoint

Auteur: Patrick Chedouba
Date: 23 décembre 2024
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import urllib.request
import urllib.error

# Ajouter le projet au path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# CONFIGURATION
# ============================================================================

# Endpoints à vérifier
HEALTH_ENDPOINTS = {
    "qdrant": {
        "url": os.getenv("QDRANT_URL", "http://localhost:6333") + "/health",
        "method": "GET",
        "timeout": 5,
        "critical": True,
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/",
        "method": "GET",
        "timeout": 10,
        "critical": True,
    },
    "speech_api": {
        "url": "https://speech.googleapis.com/",
        "method": "GET",
        "timeout": 10,
        "critical": True,
    },
    "tts_api": {
        "url": "https://texttospeech.googleapis.com/",
        "method": "GET",
        "timeout": 10,
        "critical": True,
    },
}

# Port du serveur health HTTP
HEALTH_SERVER_PORT = int(os.getenv("HEALTH_PORT", "8080"))

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger("HealthMonitor")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class HealthCheckResult:
    """Résultat d'un health check."""
    service: str
    healthy: bool
    latency_ms: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "healthy": self.healthy,
            "latency_ms": round(self.latency_ms, 2),
            "status_code": self.status_code,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# HEALTH CHECKER
# ============================================================================

class HealthChecker:
    """
    Vérifie la santé des services externes.
    
    Supporte:
    - HTTP GET/HEAD checks
    - Qdrant health endpoint
    - Google Cloud APIs reachability
    """
    
    def __init__(self, endpoints: Optional[Dict] = None):
        """
        Initialise le checker.
        
        Args:
            endpoints: Configuration custom des endpoints
        """
        self.endpoints = endpoints or HEALTH_ENDPOINTS.copy()
        self.last_results: Dict[str, HealthCheckResult] = {}
        
        logger.info("🏥 HealthChecker initialisé")
        logger.info(f"   Services surveillés: {list(self.endpoints.keys())}")
    
    def check_endpoint(self, name: str, config: Dict) -> HealthCheckResult:
        """
        Vérifie un endpoint HTTP.
        
        Args:
            name: Nom du service
            config: Configuration de l'endpoint
            
        Returns:
            HealthCheckResult
        """
        url = config.get("url", "")
        timeout = config.get("timeout", 5)
        
        start_time = time.time()
        
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "MINA-HealthChecker/1.0")
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                latency_ms = (time.time() - start_time) * 1000
                status_code = response.status
                
                # 2xx = healthy
                healthy = 200 <= status_code < 300
                
                return HealthCheckResult(
                    service=name,
                    healthy=healthy,
                    latency_ms=latency_ms,
                    status_code=status_code,
                )
                
        except urllib.error.HTTPError as e:
            latency_ms = (time.time() - start_time) * 1000
            # 4xx peut être OK (API accessible mais auth requise)
            healthy = 400 <= e.code < 500
            return HealthCheckResult(
                service=name,
                healthy=healthy,
                latency_ms=latency_ms,
                status_code=e.code,
                error=str(e.reason) if not healthy else None,
            )
            
        except urllib.error.URLError as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=name,
                healthy=False,
                latency_ms=latency_ms,
                error=str(e.reason),
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=name,
                healthy=False,
                latency_ms=latency_ms,
                error=str(e),
            )
    
    def check_qdrant(self) -> HealthCheckResult:
        """Vérifie spécifiquement Qdrant avec collections info."""
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY", "")
        
        start_time = time.time()
        
        try:
            req = urllib.request.Request(f"{qdrant_url}/collections")
            if api_key:
                req.add_header("api-key", api_key)
            
            with urllib.request.urlopen(req, timeout=5) as response:
                latency_ms = (time.time() - start_time) * 1000
                data = json.loads(response.read())
                
                collections = data.get("result", {}).get("collections", [])
                
                return HealthCheckResult(
                    service="qdrant",
                    healthy=True,
                    latency_ms=latency_ms,
                    status_code=response.status,
                )
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="qdrant",
                healthy=False,
                latency_ms=latency_ms,
                error=str(e),
            )
    
    def check_all(self) -> Dict[str, HealthCheckResult]:
        """
        Vérifie tous les endpoints configurés.
        
        Returns:
            Dict avec résultats par service
        """
        results = {}
        
        for name, config in self.endpoints.items():
            if name == "qdrant":
                result = self.check_qdrant()
            else:
                result = self.check_endpoint(name, config)
            
            results[name] = result
            self.last_results[name] = result
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé de la santé globale.
        
        Returns:
            Dict avec status global et détails
        """
        if not self.last_results:
            self.check_all()
        
        critical_services = [
            name for name, config in self.endpoints.items()
            if config.get("critical", False)
        ]
        
        all_healthy = all(
            self.last_results.get(name, HealthCheckResult(name, False, 0)).healthy
            for name in critical_services
        )
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                name: result.to_dict()
                for name, result in self.last_results.items()
            },
            "critical_services_healthy": all_healthy,
        }
    
    def print_status(self):
        """Affiche le status en console."""
        results = self.check_all()
        
        print()
        print("=" * 50)
        print("🏥 MINA Health Check")
        print("=" * 50)
        
        all_healthy = True
        
        for name, result in results.items():
            status = "✅" if result.healthy else "❌"
            latency = f"{result.latency_ms:.0f}ms"
            error_info = f" ({result.error})" if result.error else ""
            
            print(f"   {status} {name:15} {latency:>8}{error_info}")
            
            if not result.healthy:
                all_healthy = False
        
        print()
        if all_healthy:
            print("✅ Tous les services sont opérationnels")
        else:
            print("❌ Certains services sont indisponibles")
        print("=" * 50)


# ============================================================================
# HTTP SERVER
# ============================================================================

class HealthHTTPHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour endpoint /health."""
    
    checker = None  # Sera injecté par le serveur
    
    def log_message(self, format, *args):
        """Override pour logger proprement."""
        logger.debug(f"HTTP: {args[0]}")
    
    def do_GET(self):
        """Gère les requêtes GET."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/health/detailed":
            self._handle_health_detailed()
        elif self.path == "/ready":
            self._handle_ready()
        else:
            self._send_response(404, {"error": "Not found"})
    
    def _handle_health(self):
        """Endpoint /health simple."""
        if self.checker:
            summary = self.checker.get_summary()
            status_code = 200 if summary["status"] == "healthy" else 503
        else:
            summary = {"status": "unknown", "error": "Checker not initialized"}
            status_code = 500
        
        self._send_response(status_code, summary)
    
    def _handle_health_detailed(self):
        """Endpoint /health/detailed avec refresh."""
        if self.checker:
            self.checker.check_all()
            summary = self.checker.get_summary()
            status_code = 200 if summary["status"] == "healthy" else 503
        else:
            summary = {"status": "unknown"}
            status_code = 500
        
        self._send_response(status_code, summary)
    
    def _handle_ready(self):
        """Endpoint /ready pour Kubernetes."""
        self._send_response(200, {"ready": True})
    
    def _send_response(self, status_code: int, data: Dict):
        """Envoie une réponse JSON."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))


class HealthServer:
    """Serveur HTTP pour health checks."""
    
    def __init__(self, port: int = HEALTH_SERVER_PORT):
        self.port = port
        self.checker = HealthChecker()
        self.server = None
        self.thread = None
    
    def start(self, blocking: bool = True):
        """
        Démarre le serveur.
        
        Args:
            blocking: True pour bloquer, False pour thread
        """
        HealthHTTPHandler.checker = self.checker
        self.server = HTTPServer(("0.0.0.0", self.port), HealthHTTPHandler)
        
        logger.info(f"🌐 Health server démarré sur port {self.port}")
        logger.info(f"   Endpoints: /health, /health/detailed, /ready")
        
        if blocking:
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                logger.info("⏹️  Arrêt serveur...")
                self.server.shutdown()
        else:
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Arrête le serveur."""
        if self.server:
            self.server.shutdown()


# ============================================================================
# MONITOR CONTINU
# ============================================================================

class HealthMonitor:
    """
    Moniteur de santé continu avec alertes.
    
    Vérifie périodiquement les services et déclenche des alertes
    si un service devient indisponible.
    """
    
    def __init__(
        self,
        check_interval: int = 30,
        alert_callback: callable = None
    ):
        """
        Initialise le monitor.
        
        Args:
            check_interval: Intervalle entre checks (secondes)
            alert_callback: Fonction appelée sur alerte
        """
        self.checker = HealthChecker()
        self.check_interval = check_interval
        self.alert_callback = alert_callback
        self.running = False
        
        # État des services (pour détecter transitions)
        self.previous_status: Dict[str, bool] = {}
    
    def start(self):
        """Démarre le monitoring continu."""
        self.running = True
        logger.info(f"🔄 HealthMonitor démarré (interval: {self.check_interval}s)")
        
        while self.running:
            try:
                results = self.checker.check_all()
                
                for name, result in results.items():
                    prev_healthy = self.previous_status.get(name, True)
                    
                    # Service est tombé
                    if prev_healthy and not result.healthy:
                        self._on_service_down(name, result)
                    
                    # Service est revenu
                    elif not prev_healthy and result.healthy:
                        self._on_service_recovered(name, result)
                    
                    self.previous_status[name] = result.healthy
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Erreur monitoring: {e}")
                time.sleep(5)
    
    def stop(self):
        """Arrête le monitoring."""
        self.running = False
    
    def _on_service_down(self, name: str, result: HealthCheckResult):
        """Appelé quand un service tombe."""
        logger.error(f"🔴 SERVICE DOWN: {name}")
        
        if self.alert_callback:
            from observer.mina_observer import Alert
            alert = Alert(
                timestamp=datetime.now(),
                level="critical",
                category="health",
                message=f"Service {name} indisponible: {result.error}",
            )
            self.alert_callback(alert)
    
    def _on_service_recovered(self, name: str, result: HealthCheckResult):
        """Appelé quand un service récupère."""
        logger.info(f"🟢 SERVICE RECOVERED: {name}")
        
        if self.alert_callback:
            from observer.mina_observer import Alert
            alert = Alert(
                timestamp=datetime.now(),
                level="recovery",
                category="health",
                message=f"Service {name} rétabli (latence: {result.latency_ms:.0f}ms)",
            )
            self.alert_callback(alert)


# ============================================================================
# CLI
# ============================================================================

def main():
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(description="MINA Health Monitor")
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Vérifier la santé une fois et quitter"
    )
    parser.add_argument(
        "--serve", "-s",
        action="store_true",
        help="Démarrer serveur HTTP /health"
    )
    parser.add_argument(
        "--monitor", "-m",
        action="store_true",
        help="Mode monitoring continu"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=HEALTH_SERVER_PORT,
        help=f"Port serveur HTTP (défaut: {HEALTH_SERVER_PORT})"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=30,
        help="Intervalle checks en secondes (défaut: 30)"
    )
    
    args = parser.parse_args()
    
    if args.check:
        checker = HealthChecker()
        checker.print_status()
    
    elif args.serve:
        server = HealthServer(port=args.port)
        server.start(blocking=True)
    
    elif args.monitor:
        monitor = HealthMonitor(check_interval=args.interval)
        try:
            monitor.start()
        except KeyboardInterrupt:
            monitor.stop()
    
    else:
        # Par défaut: check simple
        checker = HealthChecker()
        checker.print_status()


if __name__ == "__main__":
    main()
