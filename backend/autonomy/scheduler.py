"""
Scheduler — Orchestrateur APScheduler pour la boucle autonome L6.

JobStore SQLAlchemy pour persistance.
misfire_grace_time=3600, coalesce=True.
"""

import logging
import os
from typing import Optional

from .audit_journal import AuditJournal
from .decision_engine import DecisionEngine
from .triggers import ALL_TRIGGERS, BaseTrigger

logger = logging.getLogger(__name__)

# Singleton StateStore injecté depuis run.py avant le démarrage du scheduler.
_GLOBAL_STATE_STORE = None


def _run_trigger(trigger_id: str, engine=None):
    """Fonction sérialisable par APScheduler pour exécuter un trigger."""
    from datetime import datetime, timezone
    from backend.autonomy.triggers import ALL_TRIGGERS
    from backend.autonomy.decision_engine import DecisionEngine

    trigger = next((t for t in ALL_TRIGGERS if t.id == trigger_id), None)
    if trigger is None:
        return
    if engine is None:
        engine = DecisionEngine()

    if _GLOBAL_STATE_STORE is not None:
        _GLOBAL_STATE_STORE.set(
            f"{trigger_id}:last_run",
            datetime.now(timezone.utc).isoformat(),
            ttl=None,
        )

    trigger.run(engine)


class AutonomyScheduler:
    """Planificateur de la boucle autonome MINA."""

    def __init__(
        self,
        database_url: Optional[str] = None,
        engine: Optional[DecisionEngine] = None,
        journal: Optional[AuditJournal] = None,
    ):
        self._db_url = database_url or os.getenv(
            "DATABASE_URL", os.getenv("POSTGRES_URL", "sqlite:///mina_jobs.db")
        )
        self._engine = engine or DecisionEngine()
        self._journal = journal or AuditJournal()
        self._scheduler = None

    def _build_scheduler(self):
        """Construit le BackgroundScheduler avec jobstore persistant."""
        from apscheduler.schedulers.background import BackgroundScheduler

        job_defaults = {
            "misfire_grace_time": 3600,
            "coalesce": True,
            "max_instances": 1,
        }

        # SQLAlchemy jobstore pour production (PostgreSQL).
        # MemoryJobStore pour tests / SQLite (les closures ne sont pas picklables).
        jobstores = {}
        if self._db_url and "postgresql" in self._db_url:
            from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
            jobstores["default"] = SQLAlchemyJobStore(url=self._db_url)

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores or {},
            job_defaults=job_defaults,
        )

    def register_all(self):
        """Enregistre tous les triggers dans le scheduler."""
        from apscheduler.triggers.interval import IntervalTrigger
        from apscheduler.triggers.cron import CronTrigger

        if self._scheduler is None:
            self._build_scheduler()

        for trigger in ALL_TRIGGERS:
            if trigger.schedule_type == "interval":
                apscheduler_trigger = IntervalTrigger(**trigger.schedule_args)
            else:
                apscheduler_trigger = CronTrigger(**trigger.schedule_args)
            self._scheduler.add_job(
                _run_trigger,
                apscheduler_trigger,
                args=[trigger.id],
                id=trigger.id,
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("📅 Trigger enregistré: %s [%s] %s",
                        trigger.id, trigger.schedule_type, trigger.schedule_args)

    def start(self):
        """Démarre le scheduler et log dans le journal."""
        if self._scheduler is None:
            self.register_all()
        self._scheduler.start()
        self._journal.log_system("AutonomyScheduler démarré", {
            "triggers": [t.id for t in ALL_TRIGGERS],
        })
        logger.info("🚀 AutonomyScheduler démarré avec %d triggers", len(ALL_TRIGGERS))

    def stop(self):
        """Arrête le scheduler proprement."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            self._journal.log_system("AutonomyScheduler arrêté")
            logger.info("🛑 AutonomyScheduler arrêté")
