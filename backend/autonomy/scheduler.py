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

    def _make_job_func(self, trigger: BaseTrigger):
        """Crée la fonction de job pour un trigger."""
        engine = self._engine
        journal = self._journal

        def job_func():
            try:
                result = trigger.run(engine=engine)
                journal.log_action(
                    trigger_id=trigger.id,
                    signal=trigger.build_signal().get("description", ""),
                    decision="agir" if result.get("executed") else "abstenir",
                    niveau=trigger.niveau.value,
                    action=str(result.get("decision", {}).get("action", "")),
                    resultat=result.get("resultat", "inconnu"),
                )
            except Exception as exc:
                logger.error("Erreur trigger [%s]: %s", trigger.id, exc)
                journal.log_action(
                    trigger_id=trigger.id,
                    signal="erreur_execution",
                    decision="echec",
                    niveau=trigger.niveau.value,
                    action=str(exc),
                    resultat="echec",
                )

        job_func.__name__ = f"job_{trigger.id}"
        return job_func

    def register_all(self):
        """Enregistre tous les triggers dans le scheduler."""
        if self._scheduler is None:
            self._build_scheduler()

        for trigger in ALL_TRIGGERS:
            job_id = f"autonomy_{trigger.id}"

            # Supprimer l'ancien job s'il existe (re-register propre)
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)

            func = self._make_job_func(trigger)

            if trigger.schedule_type == "interval":
                self._scheduler.add_job(
                    func,
                    "interval",
                    id=job_id,
                    replace_existing=True,
                    **trigger.schedule_args,
                )
            elif trigger.schedule_type == "cron":
                self._scheduler.add_job(
                    func,
                    "cron",
                    id=job_id,
                    replace_existing=True,
                    **trigger.schedule_args,
                )

            logger.info(
                "📅 Trigger enregistré: %s [%s] %s",
                trigger.id, trigger.schedule_type, trigger.schedule_args,
            )

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
