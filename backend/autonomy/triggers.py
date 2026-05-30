"""
Déclencheurs Phase 1 — MINA Autonomie L6.

5 triggers avec leurs schedules APScheduler et niveaux d'autonomie.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .decision_engine import DecisionEngine, Niveau

logger = logging.getLogger(__name__)


class BaseTrigger(ABC):
    """Classe de base pour tous les déclencheurs autonomes."""

    id: str = ""
    schedule_type: str = "interval"  # "interval" ou "cron"
    schedule_args: Dict[str, Any] = {}
    niveau: Niveau = Niveau.ALERTE

    def __init__(self, journal=None):
        if journal is None:
            from .audit_journal import AuditJournal
            journal = AuditJournal()
        self._journal = journal

    @abstractmethod
    def build_signal(self) -> Dict[str, Any]:
        """Construit le signal à envoyer au DecisionEngine."""

    def run(self, engine: DecisionEngine = None):
        """Exécute le cycle complet : percevoir → décider → agir."""
        signal = self.build_signal()
        signal["trigger_id"] = self.id
        signal["niveau"] = self.niveau.value

        if engine is None:
            engine = DecisionEngine()

        decision = engine.evaluer(signal)
        result = engine.executer(decision)

        self._journal.log_action(
            trigger_id=self.id,
            signal=json.dumps(signal, ensure_ascii=False, default=str)[:500],
            decision="agir" if decision.agir else "abstention",
            niveau=decision.niveau.value,
            action=decision.action,
            resultat=result["resultat"],
            detail={"justification": decision.justification, "metadata": decision.metadata},
        )

        logger.info("🔁 Trigger [%s] terminé → %s", self.id, result.get("resultat"))
        return result


# ---------------------------------------------------------------------------
# 5 Déclencheurs Phase 1
# ---------------------------------------------------------------------------


class VeilleANSM(BaseTrigger):
    """Scan ANSM/RAPEX toutes les 6h — niveau ALERTE."""

    id = "veille_ansm"
    schedule_type = "interval"
    schedule_args = {"hours": 6}
    niveau = Niveau.ALERTE

    def build_signal(self) -> Dict[str, Any]:
        return {
            "description": (
                "Veille réglementaire ANSM/RAPEX : scanner les dernières alertes "
                "cosmétiques et signalements de produits dangereux."
            ),
            "contexte": {
                "sources": ["ansm.sante.fr", "ec.europa.eu/rapex"],
                "secteur": "cosmétique / esthétique",
            },
        }


class Newsletter(BaseTrigger):
    """Bulletin beauté quotidien à 6h00 — niveau AUTO."""

    id = "newsletter"
    schedule_type = "cron"
    schedule_args = {"hour": 6, "minute": 0}
    niveau = Niveau.AUTO

    def build_signal(self) -> Dict[str, Any]:
        return {
            "description": (
                "Rédiger le bulletin beauté quotidien pour les clientes. "
                "Contenu : tendances, conseils, promotions du jour."
            ),
            "contexte": {
                "format": "email HTML",
                "audience": "clientes Body Minute",
            },
        }


class RelanceInactives(BaseTrigger):
    """Relance clientes inactives à 10h00 — niveau PROPOSE."""

    id = "relance_inactives"
    schedule_type = "cron"
    schedule_args = {"hour": 10, "minute": 0}
    niveau = Niveau.PROPOSE

    def _query_inactive_count(self) -> int:
        """Compte les clientes sans visite depuis 42 jours via SQL."""
        import os
        pg_url = os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", ""))
        if not pg_url or "sqlite" in pg_url:
            logger.warning("RelanceInactives: DATABASE_URL absent ou SQLite — count=0")
            return 0
        try:
            import psycopg2
            conn = psycopg2.connect(pg_url)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM clients "
                "WHERE last_visit < NOW() - INTERVAL '42 days'"
            )
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            return count
        except Exception as exc:
            logger.warning("RelanceInactives: requête SQL échouée: %s", exc)
            return 0

    def build_signal(self) -> Dict[str, Any]:
        count = self._query_inactive_count()
        return {
            "description": (
                f"Identifier les clientes sans visite depuis 6 semaines "
                f"et préparer un message de relance personnalisé. "
                f"{count} cliente(s) éligible(s) identifiée(s)."
            ),
            "contexte": {
                "seuil_inactivite_jours": 42,
                "action_type": "SMS ou email personnalisé",
                "count_eligibles": count,
            },
        }


class VeilleEreputation(BaseTrigger):
    """Surveillance e-réputation toutes les 2h — niveau ALERTE."""

    id = "veille_ereputation"
    schedule_type = "interval"
    schedule_args = {"hours": 2}
    niveau = Niveau.ALERTE

    def build_signal(self) -> Dict[str, Any]:
        return {
            "description": (
                "Scanner les mentions Body Minute sur les réseaux sociaux, "
                "Google Reviews et forums beauté."
            ),
            "contexte": {
                "sources": ["google_reviews", "instagram", "tiktok", "forums"],
                "seuil_sentiment_negatif": -0.3,
            },
        }


class RapportJour(BaseTrigger):
    """Synthèse quotidienne pour Laurence à 19h00 — niveau AUTO."""

    id = "rapport_jour"
    schedule_type = "cron"
    schedule_args = {"hour": 19, "minute": 0}
    niveau = Niveau.AUTO

    def build_signal(self) -> Dict[str, Any]:
        return {
            "description": (
                "Générer la synthèse de fin de journée pour Laurence : "
                "actions autonomes, alertes, métriques clés."
            ),
            "contexte": {
                "destinataire": "Laurence",
                "format": "résumé structuré",
            },
        }


# ---------------------------------------------------------------------------
# Registre
# ---------------------------------------------------------------------------

ALL_TRIGGERS: List[BaseTrigger] = [
    VeilleANSM(),
    Newsletter(),
    RelanceInactives(),
    VeilleEreputation(),
    RapportJour(),
]
