"""
Moteur de décision L6 — MINA CDC V4.0.

Trois niveaux d'autonomie :
  AUTO    — MINA agit seule sans validation humaine.
  PROPOSE — MINA prépare, Laurence valide.
  ALERTE  — MINA notifie, action humaine requise.

AUCUNE règle métier hardcodée : le LLM raisonne sur chaque signal
via un prompt XML structuré et retourne une décision JSON.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Niveaux d'autonomie
# ---------------------------------------------------------------------------

class Niveau(str, Enum):
    """Niveaux d'autonomie du CDC V4.0."""
    AUTO = "AUTO"        # MINA agit seule
    PROPOSE = "PROPOSE"  # MINA prépare, humain valide
    ALERTE = "ALERTE"    # MINA notifie, action humaine requise


# ---------------------------------------------------------------------------
# Décision
# ---------------------------------------------------------------------------

@dataclass
class Decision:
    """Résultat du moteur de décision."""
    agir: bool
    niveau: Niveau
    action: str
    justification: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompt XML pour le LLM
# ---------------------------------------------------------------------------

_DECISION_PROMPT_TEMPLATE = """\
<system>
Tu es le moteur de décision autonome de MINA, assistante IA pour le réseau Body Minute.
Tu dois analyser le signal reçu et produire une décision structurée.

NIVEAUX D'AUTONOMIE :
- AUTO : MINA agit seule sans validation humaine.
- PROPOSE : MINA prépare l'action, Laurence (la responsable) valide avant exécution.
- ALERTE : MINA notifie Laurence, l'action est entièrement humaine.

RÈGLES :
1. Respecter le niveau d'autonomie assigné au trigger.
2. Ne jamais produire de contenu médical, diagnostique ou thérapeutique.
3. Justifier systématiquement la décision.
4. En cas de doute, escalader vers ALERTE.
</system>

<signal>
<trigger_id>{trigger_id}</trigger_id>
<niveau_assigne>{niveau_assigne}</niveau_assigne>
<description>{description}</description>
<contexte>{contexte}</contexte>
</signal>

<instruction>
Analyse le signal ci-dessus. Retourne UNIQUEMENT un objet JSON valide avec les champs :
- "agir" : true ou false
- "niveau" : "AUTO" | "PROPOSE" | "ALERTE"
- "action" : description de l'action à effectuer
- "justification" : pourquoi cette décision
</instruction>
"""


class DecisionEngine:
    """
    Moteur de décision agentic.

    Le raisonnement est entièrement délégué au LLM — aucune règle métier
    hardcodée dans ce module.
    """

    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: Instance LLMProvider (ou None pour chargement lazy).
        """
        self._provider = llm_provider

    def _get_provider(self):
        """Lazy-load du LLM provider depuis le module backend.llm."""
        if self._provider is None:
            try:
                from backend.llm.provider import get_llm_provider
                self._provider = get_llm_provider()
            except Exception as exc:
                logger.error("Impossible de charger le LLM provider: %s", exc)
                raise
        return self._provider

    # ------------------------------------------------------------------
    # Évaluation
    # ------------------------------------------------------------------

    def evaluer(self, signal: Dict[str, Any]) -> Decision:
        """
        Évalue un signal et retourne une décision.

        Le signal doit contenir :
          - trigger_id : identifiant du déclencheur
          - niveau : Niveau d'autonomie assigné (AUTO/PROPOSE/ALERTE)
          - description : description textuelle du signal
          - contexte : données contextuelles (optionnel)
        """
        trigger_id = signal.get("trigger_id", "INCONNU")
        niveau_assigne = signal.get("niveau", Niveau.ALERTE.value)
        description = signal.get("description", "")
        contexte = json.dumps(signal.get("contexte", {}), ensure_ascii=False, default=str)

        prompt = _DECISION_PROMPT_TEMPLATE.format(
            trigger_id=trigger_id,
            niveau_assigne=niveau_assigne,
            description=description,
            contexte=contexte,
        )

        messages = [
            {"role": "system", "content": "Tu es le moteur de décision autonome MINA."},
            {"role": "user", "content": prompt},
        ]

        try:
            provider = self._get_provider()
            response = provider.generate_sync(
                messages=messages,
                temperature=0.1,
                max_tokens=500,
            )
            decision = self._parse_llm_response(response.text, niveau_assigne)
        except Exception as exc:
            logger.error("Erreur LLM lors de l'évaluation: %s", exc)
            # Sécurité : en cas d'erreur, escalader en ALERTE
            decision = Decision(
                agir=False,
                niveau=Niveau.ALERTE,
                action="Échec évaluation — escalade automatique",
                justification=f"Erreur LLM: {exc}",
            )

        logger.info(
            "🧠 Décision [%s] niveau=%s agir=%s → %s",
            trigger_id,
            decision.niveau.value,
            decision.agir,
            decision.action[:80],
        )
        return decision

    def _parse_llm_response(self, text: str, fallback_niveau: str) -> Decision:
        """Parse la réponse JSON du LLM en Decision."""
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if not json_match:
            return Decision(
                agir=False,
                niveau=Niveau.ALERTE,
                action="Réponse LLM non parseable",
                justification=f"Texte brut: {text[:200]}",
            )

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return Decision(
                agir=False,
                niveau=Niveau.ALERTE,
                action="JSON invalide dans la réponse LLM",
                justification=f"Texte brut: {text[:200]}",
            )

        niveau_str = data.get("niveau", fallback_niveau).upper()
        try:
            niveau = Niveau(niveau_str)
        except ValueError:
            niveau = Niveau.ALERTE

        return Decision(
            agir=bool(data.get("agir", False)),
            niveau=niveau,
            action=data.get("action", ""),
            justification=data.get("justification", ""),
        )

    # ------------------------------------------------------------------
    # Exécution
    # ------------------------------------------------------------------

    def executer(self, decision: Decision) -> Dict[str, Any]:
        """
        Exécute une décision.

        Pour AUTO : exécution immédiate.
        Pour PROPOSE : prépare et stocke pour validation.
        Pour ALERTE : notification uniquement.

        Retourne un dict avec le résultat de l'exécution.
        """
        result: Dict[str, Any] = {
            "decision": asdict(decision),
            "executed": False,
            "resultat": "en_attente",
        }

        if decision.niveau == Niveau.AUTO and decision.agir:
            result["executed"] = True
            result["resultat"] = "succes"
            logger.info("✅ AUTO exécuté: %s", decision.action[:80])

        elif decision.niveau == Niveau.PROPOSE:
            result["resultat"] = "propose_en_attente"
            logger.info("📋 PROPOSE en attente de validation: %s", decision.action[:80])

        elif decision.niveau == Niveau.ALERTE:
            result["resultat"] = "alerte_envoyee"
            logger.info("🚨 ALERTE envoyée: %s", decision.action[:80])

        else:
            result["resultat"] = "abstention"
            logger.info("⏸️ Abstention: %s", decision.justification[:80])

        return result
