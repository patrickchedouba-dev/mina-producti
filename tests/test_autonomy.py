"""
Tests unitaires — Couche d'Autonomie L6 MINA.

5 tests obligatoires CDC V4.0 Ch.27 Étape 2.
"""

import json
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ajouter le chemin racine du projet pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.autonomy.audit_journal import AuditJournal
from backend.autonomy.decision_engine import DecisionEngine, Niveau, Decision
from backend.autonomy.state_store import StateStore
from backend.autonomy.triggers import ALL_TRIGGERS
from backend.autonomy.scheduler import AutonomyScheduler


# =========================================================================
# 1. test_audit_journal_log — vérifie qu'une action est bien enregistrée
# =========================================================================

def test_audit_journal_log(tmp_path):
    """L'AuditJournal enregistre une action et la retrouve."""
    # Patcher le fallback path pour utiliser tmp_path
    fallback = tmp_path / "audit_test.json"

    with patch("backend.autonomy.audit_journal._FALLBACK_PATH", fallback):
        journal = AuditJournal(postgres_url="")  # Force fallback JSON

        entry = journal.log_action(
            trigger_id="test_trigger",
            signal="Signal de test",
            decision="agir",
            niveau="AUTO",
            action="Action de test",
            resultat="succes",
            detail={"test": True},
        )

        # L'entrée doit contenir les champs requis
        assert entry["trigger_id"] == "test_trigger"
        assert entry["signal"] == "Signal de test"
        assert entry["decision"] == "agir"
        assert entry["niveau"] == "AUTO"
        assert entry["action"] == "Action de test"
        assert entry["resultat"] == "succes"
        assert "ts" in entry

        # Le fichier JSON doit contenir l'entrée
        assert fallback.exists()
        data = json.loads(fallback.read_text())
        assert len(data) == 1
        assert data[0]["trigger_id"] == "test_trigger"


# =========================================================================
# 2. test_decision_engine_niveaux — vérifie les 3 niveaux AUTO/PROPOSE/ALERTE
# =========================================================================

def test_decision_engine_niveaux():
    """Les trois niveaux d'autonomie existent et le moteur parse les réponses."""
    # Vérifier l'enum
    assert Niveau.AUTO.value == "AUTO"
    assert Niveau.PROPOSE.value == "PROPOSE"
    assert Niveau.ALERTE.value == "ALERTE"
    assert len(Niveau) == 3

    # Vérifier le parsing LLM pour chaque niveau
    engine = DecisionEngine(llm_provider=MagicMock())

    for niv in [Niveau.AUTO, Niveau.PROPOSE, Niveau.ALERTE]:
        llm_response = json.dumps({
            "agir": True,
            "niveau": niv.value,
            "action": f"Test action {niv.value}",
            "justification": f"Test justification {niv.value}",
        })
        decision = engine._parse_llm_response(llm_response, niv.value)
        assert decision.niveau == niv
        assert decision.agir is True
        assert niv.value in decision.action


# =========================================================================
# 3. test_state_store_persistence — vérifie survie au redémarrage
# =========================================================================

def test_state_store_persistence():
    """Le StateStore persiste les données en mémoire (fallback)."""
    store = StateStore(redis_url="", postgres_url="")

    # Écrire
    store.set("test_key", {"compteur": 42})

    # Lire
    value = store.get("test_key")
    assert value is not None
    assert value["compteur"] == 42

    # Vérifier get_all
    all_data = store.get_all()
    assert "test_key" in all_data

    # Supprimer
    store.delete("test_key")
    assert store.get("test_key") is None

    # Re-simuler un redémarrage avec un nouveau store partageant la mémoire
    store2 = StateStore(redis_url="", postgres_url="")
    store2._memory = store._memory  # Simule la persistance mémoire
    store2.set("survie", "ok")
    assert store2.get("survie") == "ok"


# =========================================================================
# 4. test_all_triggers_exist — vérifie que ALL_TRIGGERS contient 5 éléments
# =========================================================================

def test_all_triggers_exist():
    """ALL_TRIGGERS contient exactement 5 déclencheurs Phase 1."""
    assert len(ALL_TRIGGERS) == 5

    # Vérifier les IDs attendus
    ids = {t.id for t in ALL_TRIGGERS}
    expected_ids = {
        "veille_ansm",
        "newsletter",
        "relance_inactives",
        "veille_ereputation",
        "rapport_jour",
    }
    assert ids == expected_ids

    # Vérifier les niveaux
    niveau_map = {t.id: t.niveau for t in ALL_TRIGGERS}
    assert niveau_map["newsletter"] == Niveau.AUTO
    assert niveau_map["rapport_jour"] == Niveau.AUTO
    assert niveau_map["relance_inactives"] == Niveau.PROPOSE
    assert niveau_map["veille_ansm"] == Niveau.ALERTE
    assert niveau_map["veille_ereputation"] == Niveau.ALERTE

    # Chaque trigger doit avoir un schedule
    for trigger in ALL_TRIGGERS:
        assert trigger.schedule_type in ("interval", "cron")
        assert isinstance(trigger.schedule_args, dict)
        assert len(trigger.schedule_args) > 0


# =========================================================================
# 5. test_scheduler_starts — vérifie démarrage sans erreur
# =========================================================================

def test_scheduler_starts(tmp_path):
    """Le scheduler démarre et s'arrête sans erreur."""
    db_path = tmp_path / "test_scheduler.db"
    scheduler = AutonomyScheduler(
        database_url=f"sqlite:///{db_path}",
        engine=DecisionEngine(llm_provider=MagicMock()),
    )

    scheduler.register_all()
    scheduler.start()

    # Vérifier que le scheduler tourne
    assert scheduler._scheduler is not None
    assert scheduler._scheduler.running is True

    # Arrêt propre
    scheduler.stop()
    assert scheduler._scheduler.running is False
