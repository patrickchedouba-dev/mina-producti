"""
Client MCP pour Mina.

Fournit une interface pour:
- Lister les outils disponibles (format compatible Gemini/OpenAI)
- Exécuter les outils
- Logger les appels
"""

import logging
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client MCP pour exécution d'outils par le LLM.
    
    Usage:
        client = MCPClient()
        tools = client.get_tools_for_llm()  # Pour configurer le LLM
        result = client.execute_tool("search_knowledge", {"query": "hydratation"})
    """
    
    def __init__(self):
        """Initialise le client et charge les outils."""
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._load_tools()
        logger.info(f"🔧 MCPClient initialisé avec {len(self._tools)} outils")
    
    def _load_tools(self):
        """Charge les outils disponibles."""
        from .tools import knowledge, memory, vision, conversation, notifications
        
        # Knowledge
        self._tools["search_knowledge"] = {
            "function": knowledge.search_knowledge,
            "metadata": knowledge.TOOL_METADATA
        }
        
        # Memory
        self._tools["get_client_context"] = {
            "function": memory.get_client_context,
            "metadata": memory.GET_CLIENT_CONTEXT_METADATA
        }
        self._tools["store_client_info"] = {
            "function": memory.store_client_info,
            "metadata": memory.STORE_CLIENT_INFO_METADATA
        }
        
        # Vision
        self._tools["analyze_skin_image"] = {
            "function": vision.analyze_skin_image,
            "metadata": vision.TOOL_METADATA
        }
        self._tools["identify_product_image"] = {
            "function": vision.identify_product_image,
            "metadata": vision.IDENTIFY_PRODUCT_METADATA
        }
        
        # Conversation
        self._tools["detect_conversation_state"] = {
            "function": conversation.detect_conversation_state,
            "metadata": conversation.TOOL_METADATA
        }
        
        # Notifications
        self._tools["send_notification"] = {
            "function": notifications.send_notification,
            "metadata": notifications.SEND_NOTIFICATION_METADATA
        }
        self._tools["schedule_followup"] = {
            "function": notifications.schedule_followup,
            "metadata": notifications.SCHEDULE_FOLLOWUP_METADATA
        }
    
    def get_tools_for_llm(self, format: str = "gemini") -> List[Dict]:
        """
        Retourne la liste des outils au format LLM.
        
        Args:
            format: "gemini" ou "openai"
            
        Returns:
            Liste des définitions d'outils
        """
        tools = []
        
        for name, tool_info in self._tools.items():
            metadata = tool_info["metadata"]
            
            if format == "gemini":
                # Format Gemini function calling
                tools.append({
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "parameters": metadata["parameters"]
                })
            elif format == "openai":
                # Format OpenAI function calling
                tools.append({
                    "type": "function",
                    "function": {
                        "name": metadata["name"],
                        "description": metadata["description"],
                        "parameters": metadata["parameters"]
                    }
                })
        
        return tools
    
    def get_tool_names(self) -> List[str]:
        """Retourne la liste des noms d'outils."""
        return list(self._tools.keys())
    
    def execute_tool(
        self, 
        tool_name: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Exécute un outil.
        
        Args:
            tool_name: Nom de l'outil
            params: Paramètres à passer
            
        Returns:
            Résultat de l'exécution
        """
        if tool_name not in self._tools:
            logger.error(f"❌ [MCP] Outil inconnu: {tool_name}")
            return {
                "success": False,
                "error": f"Outil '{tool_name}' non trouvé"
            }
        
        tool_func = self._tools[tool_name]["function"]
        
        logger.info(f"🔧 [MCP] Exécution: {tool_name}({list(params.keys())})")
        
        try:
            result = tool_func(**params)
            logger.info(f"✅ [MCP] {tool_name} terminé: success={result.get('success', 'N/A')}")
            return result
        except Exception as e:
            logger.error(f"❌ [MCP] Erreur {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_tool_call(self, tool_call: Dict) -> Dict[str, Any]:
        """
        Exécute un appel d'outil depuis le LLM.
        
        Args:
            tool_call: Dict avec 'name' et 'args' (format Gemini)
            
        Returns:
            Résultat de l'exécution
        """
        tool_name = tool_call.get("name")
        params = tool_call.get("args", {})
        return self.execute_tool(tool_name, params)


# Singleton
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Retourne l'instance singleton du client MCP."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
