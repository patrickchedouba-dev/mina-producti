"""
State Store — Mémoire persistante de la boucle autonome L6.

Court terme : Redis (TTL 24h par défaut).
Long terme  : PostgreSQL (table autonomy_state).
Survie aux redémarrages obligatoire.
Fallback : dict en mémoire si Redis ET PostgreSQL indisponibles.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 86400  # 24 heures

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS autonomy_state (
    key         VARCHAR(256) PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class StateStore:
    """Mémoire persistante pour la boucle autonome."""

    def __init__(self, redis_url: Optional[str] = None, postgres_url: Optional[str] = None):
        self._redis_url = redis_url or os.getenv("REDIS_URL", "")
        self._pg_url = postgres_url or os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", ""))
        self._redis = None
        self._pg_conn = None
        self._pg_ready = False
        self._memory: Dict[str, Any] = {}

    def _get_redis(self):
        if self._redis is not None:
            try:
                self._redis.ping()
                return self._redis
            except Exception:
                self._redis = None
        if not self._redis_url:
            return None
        try:
            import redis as redis_lib
            self._redis = redis_lib.Redis.from_url(self._redis_url, decode_responses=True)
            self._redis.ping()
            return self._redis
        except Exception as exc:
            logger.warning("Redis indisponible: %s", exc)
            self._redis = None
            return None

    def _get_pg(self):
        if self._pg_conn is not None:
            try:
                cur = self._pg_conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                return self._pg_conn
            except Exception:
                self._pg_conn = None
        if not self._pg_url:
            return None
        try:
            import psycopg2
            self._pg_conn = psycopg2.connect(self._pg_url)
            self._pg_conn.autocommit = True
            return self._pg_conn
        except Exception as exc:
            logger.warning("PostgreSQL indisponible: %s", exc)
            return None

    def _ensure_pg_table(self):
        if self._pg_ready:
            return
        conn = self._get_pg()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(_CREATE_TABLE_SQL)
                cur.close()
                self._pg_ready = True
            except Exception as exc:
                logger.warning("Impossible de créer autonomy_state: %s", exc)

    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur (Redis → PostgreSQL → mémoire)."""
        r = self._get_redis()
        if r:
            try:
                raw = r.get(f"autonomy:{key}")
                if raw is not None:
                    return json.loads(raw)
            except Exception:
                pass
        self._ensure_pg_table()
        conn = self._get_pg()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT value FROM autonomy_state WHERE key = %s", (key,))
                row = cur.fetchone()
                cur.close()
                if row:
                    return row[0]
            except Exception:
                pass
        return self._memory.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = _DEFAULT_TTL):
        """Persiste une valeur. Redis avec TTL, PostgreSQL upsert."""
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        r = self._get_redis()
        if r:
            try:
                if ttl:
                    r.setex(f"autonomy:{key}", ttl, serialized)
                else:
                    r.set(f"autonomy:{key}", serialized)
            except Exception as exc:
                logger.warning("Échec Redis: %s", exc)
        self._ensure_pg_table()
        conn = self._get_pg()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO autonomy_state (key, value, updated_at) VALUES (%s, %s, %s) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at",
                    (key, serialized, datetime.now(timezone.utc).isoformat()),
                )
                cur.close()
            except Exception as exc:
                logger.warning("Échec PostgreSQL: %s", exc)
        self._memory[key] = value

    def delete(self, key: str):
        """Supprime une clé de tous les backends."""
        r = self._get_redis()
        if r:
            try:
                r.delete(f"autonomy:{key}")
            except Exception:
                pass
        conn = self._get_pg()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM autonomy_state WHERE key = %s", (key,))
                cur.close()
            except Exception:
                pass
        self._memory.pop(key, None)

    def get_all(self) -> Dict[str, Any]:
        """Retourne toutes les clés/valeurs."""
        self._ensure_pg_table()
        conn = self._get_pg()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT key, value FROM autonomy_state")
                rows = cur.fetchall()
                cur.close()
                return {r[0]: r[1] for r in rows}
            except Exception:
                pass
        return dict(self._memory)
