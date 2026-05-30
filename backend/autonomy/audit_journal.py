"""
Journal d'audit — Reddition de comptes L6.

Chaque action autonome est tracée avec :
- horodatage ISO, trigger_id, signal perçu,
- décision prise, niveau, action exécutée, résultat.

Stockage principal : PostgreSQL (table audit_journal).
Fallback : fichier JSON /tmp/mina_audit.json.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL DDL — exécuté au premier appel si la table n'existe pas
# ---------------------------------------------------------------------------
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_journal (
    id          SERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trigger_id  VARCHAR(64),
    signal      TEXT,
    decision    VARCHAR(16),
    niveau      VARCHAR(16),
    action      TEXT,
    resultat    VARCHAR(16),
    detail      JSONB
);
"""

_INSERT_SQL = """
INSERT INTO audit_journal (ts, trigger_id, signal, decision, niveau, action, resultat, detail)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

_FALLBACK_PATH = Path(os.getenv("MINA_AUDIT_FALLBACK", "/tmp/mina_audit.json"))


class AuditJournal:
    """Journal de reddition de comptes pour la boucle autonome."""

    def __init__(self, postgres_url: Optional[str] = None):
        self._pg_url = postgres_url or os.getenv(
            "DATABASE_URL",
            os.getenv("POSTGRES_URL", ""),
        )
        self._conn = None
        self._table_ready = False

    # ------------------------------------------------------------------
    # Connexion PostgreSQL (lazy)
    # ------------------------------------------------------------------

    def _get_connection(self):
        """Retourne une connexion PostgreSQL, ou None si indisponible."""
        if self._conn is not None:
            try:
                cur = self._conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                return self._conn
            except Exception:
                self._conn = None

        if not self._pg_url:
            return None

        try:
            import psycopg2  # type: ignore
            self._conn = psycopg2.connect(self._pg_url)
            self._conn.autocommit = True
            return self._conn
        except Exception as exc:
            logger.warning("PostgreSQL indisponible pour audit_journal: %s", exc)
            return None

    def _ensure_table(self):
        """Crée la table si nécessaire."""
        if self._table_ready:
            return
        conn = self._get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(_CREATE_TABLE_SQL)
                cur.close()
                self._table_ready = True
            except Exception as exc:
                logger.warning("Impossible de créer la table audit_journal: %s", exc)

    # ------------------------------------------------------------------
    # Fallback JSON
    # ------------------------------------------------------------------

    def _append_json(self, entry: Dict[str, Any]):
        """Ajoute une entrée au fichier JSON de fallback."""
        entries: List[Dict] = []
        if _FALLBACK_PATH.exists():
            try:
                entries = json.loads(_FALLBACK_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                entries = []
        entries.append(entry)
        try:
            _FALLBACK_PATH.write_text(
                json.dumps(entries, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("Impossible d'écrire le fallback JSON: %s", exc)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def log_action(
        self,
        trigger_id: str,
        signal: str,
        decision: str,
        niveau: str,
        action: str,
        resultat: str,
        detail: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Enregistre une action autonome dans le journal."""
        ts = datetime.now(timezone.utc).isoformat()
        entry = {
            "ts": ts,
            "trigger_id": trigger_id,
            "signal": signal,
            "decision": decision,
            "niveau": niveau,
            "action": action,
            "resultat": resultat,
            "detail": detail or {},
        }

        self._ensure_table()
        conn = self._get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    _INSERT_SQL,
                    (
                        ts,
                        trigger_id,
                        signal,
                        decision,
                        niveau,
                        action,
                        resultat,
                        json.dumps(detail or {}, default=str),
                    ),
                )
                cur.close()
                logger.info("📝 Audit journal [PG]: %s → %s", trigger_id, resultat)
                return entry
            except Exception as exc:
                logger.warning("Échec écriture PG, fallback JSON: %s", exc)

        # Fallback fichier JSON
        self._append_json(entry)
        logger.info("📝 Audit journal [JSON]: %s → %s", trigger_id, resultat)
        return entry

    def log_system(self, message: str, detail: Optional[Dict] = None) -> Dict[str, Any]:
        """Enregistre un événement système (démarrage, arrêt, erreur)."""
        return self.log_action(
            trigger_id="SYSTEM",
            signal=message,
            decision="INFO",
            niveau="SYSTEM",
            action=message,
            resultat="ok",
            detail=detail,
        )

    def get_today_count(self) -> int:
        """Retourne le nombre d'entrées du jour."""
        conn = self._get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM audit_journal WHERE ts::date = CURRENT_DATE"
                )
                count = cur.fetchone()[0]
                cur.close()
                return count
            except Exception:
                pass

        # Fallback JSON
        if _FALLBACK_PATH.exists():
            try:
                entries = json.loads(_FALLBACK_PATH.read_text(encoding="utf-8"))
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                return sum(1 for e in entries if e.get("ts", "").startswith(today))
            except (json.JSONDecodeError, OSError):
                pass
        return 0

    def get_recent(self, n: int = 20) -> List[Dict[str, Any]]:
        """Retourne les n entrées les plus récentes."""
        conn = self._get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT ts, trigger_id, signal, decision, niveau, action, resultat, detail "
                    "FROM audit_journal ORDER BY ts DESC LIMIT %s",
                    (n,),
                )
                rows = cur.fetchall()
                cur.close()
                return [
                    {
                        "ts": str(r[0]),
                        "trigger_id": r[1],
                        "signal": r[2],
                        "decision": r[3],
                        "niveau": r[4],
                        "action": r[5],
                        "resultat": r[6],
                        "detail": r[7],
                    }
                    for r in rows
                ]
            except Exception:
                pass

        # Fallback JSON
        if _FALLBACK_PATH.exists():
            try:
                entries = json.loads(_FALLBACK_PATH.read_text(encoding="utf-8"))
                return list(reversed(entries[-n:]))
            except (json.JSONDecodeError, OSError):
                pass
        return []
