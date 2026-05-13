"""
Package outils MCP pour Mina.

Chaque module expose des outils appelables via le protocole MCP.
"""

from .knowledge import search_knowledge
from .memory import get_client_context, store_client_info
from .vision import analyze_skin_image
from .conversation import detect_conversation_state
from .notifications import send_notification
from .crm import get_crm_outcomes, check_client_return, get_client_visits

__all__ = [
    "search_knowledge",
    "get_client_context",
    "store_client_info",
    "analyze_skin_image",
    "detect_conversation_state",
    "send_notification",
    "get_crm_outcomes",
    "check_client_return",
    "get_client_visits",
]

