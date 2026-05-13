#!/usr/bin/env python3
"""
Health Check pour Mina - Vérifie l'état de tous les services.
Usage: python scripts/health_check.py
"""

import os
import sys
import time
from pathlib import Path

# Configuration du path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def check_qdrant() -> dict:
    """Vérifie la connexion Qdrant."""
    try:
        from utils.qdrant_utils import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections()
        return {
            "status": "OK",
            "collections": len(collections.collections),
            "latency_ms": 0  # TODO: mesurer
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)[:100]}


def check_gemini() -> dict:
    """Vérifie la connexion Gemini."""
    try:
        from google import genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return {"status": "ERROR", "error": "GOOGLE_API_KEY not set"}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        start = time.time()
        response = model.generate_content("Réponds 'OK' en un mot.", stream=False)
        latency_ms = int((time.time() - start) * 1000)
        
        if response.text:
            return {"status": "OK", "latency_ms": latency_ms}
        return {"status": "WARNING", "message": "Réponse vide"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)[:100]}


def check_embeddings() -> dict:
    """Vérifie le service d'embeddings."""
    try:
        from utils.embedding_utils import get_embedding
        
        start = time.time()
        vector = get_embedding("test health check")
        latency_ms = int((time.time() - start) * 1000)
        
        if len(vector) == 768:
            return {"status": "OK", "dimension": 768, "latency_ms": latency_ms}
        return {"status": "WARNING", "dimension": len(vector)}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)[:100]}


def check_products_db() -> dict:
    """Vérifie la base de produits."""
    try:
        import json
        products_path = Path(__file__).parent.parent / "data" / "products_external.json"
        
        if not products_path.exists():
            return {"status": "ERROR", "error": "Fichier products_external.json absent"}
        
        with open(products_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            products = data.get("products", [])
            return {"status": "OK", "products_count": len(products)}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)[:100]}


def check_feature_flags() -> dict:
    """Vérifie les feature flags."""
    try:
        from backend.feature_flags import get_flags
        flags = get_flags()
        return {
            "status": "OK",
            "v2_enabled": flags.v2_enabled,
            "safe_mode": flags.safe_mode,
            "fallback_enabled": flags.fallback_enabled,
            "min_score": flags.min_score
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)[:100]}


def run_health_check() -> dict:
    """Exécute le health check complet."""
    logger.info("🏥 Mina Health Check")
    logger.info("=" * 50)
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall": "HEALTHY",
        "services": {}
    }
    
    # Liste des checks
    checks = [
        ("qdrant", check_qdrant),
        ("gemini", check_gemini),
        ("embeddings", check_embeddings),
        ("products_db", check_products_db),
        ("feature_flags", check_feature_flags),
    ]
    
    for name, check_fn in checks:
        logger.info(f"Checking {name}...")
        try:
            result = check_fn()
            results["services"][name] = result
            
            status = result.get("status", "UNKNOWN")
            if status == "OK":
                logger.info(f"  ✅ {name}: OK")
            elif status == "WARNING":
                logger.info(f"  ⚠️ {name}: WARNING - {result.get('message', '')}")
            else:
                logger.info(f"  ❌ {name}: ERROR - {result.get('error', '')}")
                results["overall"] = "UNHEALTHY"
        except Exception as e:
            results["services"][name] = {"status": "ERROR", "error": str(e)[:100]}
            results["overall"] = "UNHEALTHY"
            logger.info(f"  ❌ {name}: EXCEPTION - {e}")
    
    logger.info("=" * 50)
    logger.info(f"🏥 Overall: {results['overall']}")
    
    return results


if __name__ == "__main__":
    import json
    
    results = run_health_check()
    
    # Afficher le JSON complet si demandé
    if "--json" in sys.argv:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # Exit code basé sur le statut
    sys.exit(0 if results["overall"] == "HEALTHY" else 1)
