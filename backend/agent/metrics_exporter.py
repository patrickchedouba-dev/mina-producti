"""
Prometheus Metrics Exporter - Métriques Regret-Zero pour monitoring.

Expose les métriques au format Prometheus pour Grafana.
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Metrics cache
_metrics_cache: Dict = {}
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 60


def _refresh_metrics():
    """Rafraîchit les métriques depuis la DB."""
    global _metrics_cache, _cache_timestamp
    
    now = datetime.now()
    if _cache_timestamp and (now - _cache_timestamp).seconds < CACHE_TTL_SECONDS:
        return
    
    metrics = {
        "decisions_total": 0,
        "decisions_with_outcome": 0,
        "avg_regret": 0.0,
        "optimal_rate": 0.0,
        "shadow_paths_generated": 0,
        "cache_hit_rate": 0.0,
        "experiments_active": 0,
        "by_institut": {}
    }
    
    try:
        from backend.memory import get_memory_system
        memory = get_memory_system()
        
        if not hasattr(memory, '_postgres') or not memory._postgres:
            _metrics_cache = metrics
            _cache_timestamp = now
            return
        
        postgres = memory._postgres
        
        # Global metrics
        result = postgres.fetch_one("""
            SELECT 
                COUNT(*) as total,
                COUNT(outcome_7d) as with_outcome,
                AVG(COALESCE(regret_score, 0)) as avg_regret
            FROM counterfactual_decisions
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """, ())
        
        if result:
            metrics["decisions_total"] = result.get("total", 0)
            metrics["decisions_with_outcome"] = result.get("with_outcome", 0)
            metrics["avg_regret"] = float(result.get("avg_regret", 0) or 0)
        
        # Optimal rate
        result = postgres.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE regret_score <= 0) as optimal,
                COUNT(*) as total
            FROM counterfactual_decisions
            WHERE regret_score IS NOT NULL
            AND timestamp > NOW() - INTERVAL '24 hours'
        """, ())
        
        if result and result.get("total", 0) > 0:
            metrics["optimal_rate"] = result["optimal"] / result["total"]
        
        # Shadow paths generated
        result = postgres.fetch_one("""
            SELECT COUNT(*) as count FROM counterfactual_decisions
            WHERE shadow_paths IS NOT NULL
            AND timestamp > NOW() - INTERVAL '24 hours'
        """, ())
        
        if result:
            metrics["shadow_paths_generated"] = result.get("count", 0)
        
        # Active experiments
        result = postgres.fetch_one("""
            SELECT COUNT(*) as count FROM ab_experiments
            WHERE status = 'running'
        """, ())
        
        if result:
            metrics["experiments_active"] = result.get("count", 0)
        
        # Per-institut metrics
        results = postgres.fetch_all("""
            SELECT 
                institut_id,
                COUNT(*) as decisions,
                AVG(COALESCE(regret_score, 0)) as avg_regret
            FROM counterfactual_decisions
            WHERE institut_id IS NOT NULL
            AND timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY institut_id
        """, ())
        
        if results:
            for row in results:
                institut = row.get("institut_id")
                metrics["by_institut"][institut] = {
                    "decisions": row.get("decisions", 0),
                    "avg_regret": float(row.get("avg_regret", 0) or 0)
                }
        
    except Exception as e:
        logger.warning(f"⚠️ Refresh metrics: {e}")
    
    _metrics_cache = metrics
    _cache_timestamp = now


def get_prometheus_metrics() -> str:
    """
    Retourne les métriques au format Prometheus.
    
    Returns:
        Texte format OpenMetrics
    """
    _refresh_metrics()
    
    lines = [
        "# HELP mina_decisions_total Total counterfactual decisions",
        "# TYPE mina_decisions_total gauge",
        f"mina_decisions_total {_metrics_cache.get('decisions_total', 0)}",
        "",
        "# HELP mina_decisions_with_outcome Decisions with outcome collected",
        "# TYPE mina_decisions_with_outcome gauge",
        f"mina_decisions_with_outcome {_metrics_cache.get('decisions_with_outcome', 0)}",
        "",
        "# HELP mina_regret_avg Average regret score",
        "# TYPE mina_regret_avg gauge",
        f"mina_regret_avg {_metrics_cache.get('avg_regret', 0):.4f}",
        "",
        "# HELP mina_optimal_rate Rate of optimal decisions",
        "# TYPE mina_optimal_rate gauge",
        f"mina_optimal_rate {_metrics_cache.get('optimal_rate', 0):.4f}",
        "",
        "# HELP mina_shadow_paths Shadow paths generated",
        "# TYPE mina_shadow_paths gauge",
        f"mina_shadow_paths {_metrics_cache.get('shadow_paths_generated', 0)}",
        "",
        "# HELP mina_experiments_active Active A/B experiments",
        "# TYPE mina_experiments_active gauge",
        f"mina_experiments_active {_metrics_cache.get('experiments_active', 0)}",
        ""
    ]
    
    # Per-institut metrics
    for institut, data in _metrics_cache.get("by_institut", {}).items():
        lines.append(f'mina_decisions_by_institut{{institut="{institut}"}} {data["decisions"]}')
        lines.append(f'mina_regret_by_institut{{institut="{institut}"}} {data["avg_regret"]:.4f}')
    
    return "\n".join(lines)


def get_metrics_json() -> Dict:
    """Retourne les métriques au format JSON."""
    _refresh_metrics()
    return _metrics_cache


def get_health_status() -> Dict:
    """Retourne le statut de santé du système."""
    _refresh_metrics()
    
    # Checks
    checks = {
        "counterfactual_enabled": os.getenv("MINA_COUNTERFACTUAL_ENABLED", "false").lower() == "true",
        "has_recent_decisions": _metrics_cache.get("decisions_total", 0) > 0,
        "optimal_rate_healthy": _metrics_cache.get("optimal_rate", 0) >= 0.6,
        "regret_under_threshold": _metrics_cache.get("avg_regret", 1) < 0.2
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "metrics_summary": {
            "decisions_24h": _metrics_cache.get("decisions_total", 0),
            "optimal_rate": f"{_metrics_cache.get('optimal_rate', 0)*100:.1f}%",
            "avg_regret": f"{_metrics_cache.get('avg_regret', 0):.3f}"
        },
        "timestamp": datetime.now().isoformat()
    }
