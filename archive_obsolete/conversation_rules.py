import logging

logger = logging.getLogger(__name__)

# 1. Structure de base
class ConversationRule:
    def __init__(self, name, description):
        self.name = name
        self.description = description

# 2. Codes de statut BMAD
CONVERSATION_CODE = {
    "START": "CONV_001",
    "IN_PROGRESS": "CONV_002",
    "COMPLETED": "CONV_003",
    "ERROR": "CONV_999"
}

# 3. Logique d'orchestration (Couche 6)
def get_rule_for_state(state: str) -> ConversationRule:
    """Identifie l'intention selon l'état du dialogue."""
    return ConversationRule(name=f"Rule_{state}", description="Génération dynamique.")

def apply_rule(rule: ConversationRule, context: dict) -> dict:
    """Applique la logique métier sans phrases hardcodées."""
    logger.info(f"⚙️ Règle appliquée : {rule.name}")
    return {"status": "success", "rule_applied": rule.name}

def transform_response_with_state(response: str, state: str) -> str:
    """
    Prépare la réponse pour le canal de sortie (Vocal/Texte).
    Note BMAD : On ne modifie rien ici, on laisse le LLM s'exprimer.
    """
    return response

# 4. Paramètres globaux
CONVERSATION_SETTINGS = {
    "max_turns": 10,
    "temperature": 0.7,
    "agent_timeout": 30,
    "safety_filter_level": "BLOCK_MEDIUM_AND_ABOVE"
}
