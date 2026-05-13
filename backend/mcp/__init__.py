"""
Package MCP (Model Context Protocol) pour Mina.

Expose les capacités Mina comme outils appelables par le LLM:
- knowledge: recherche RAG dans Qdrant
- memory: accès mémoire client
- vision: analyse d'images
- conversation: détection d'état
- notifications: envoi de notifications (mock)
"""

from .mcp_client import MCPClient, get_mcp_client

__all__ = [
    "MCPClient",
    "get_mcp_client",
]
