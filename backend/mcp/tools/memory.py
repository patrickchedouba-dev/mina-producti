"""
Outil MCP Memory - Accès mémoire client.

Utilise backend/memory/memory_system.py pour le stockage.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_client_context(client_id: str) -> Dict[str, Any]:
    """
    Récupère le contexte complet d'un client.
    
    Combine le profil client, l'historique des conversations,
    et les préférences pour personnaliser la réponse.
    
    Args:
        client_id: Identifiant unique du client
        
    Returns:
        Dict avec:
        - profile: Profil client (type de peau, préférences)
        - history_summary: Résumé des conversations passées
        - last_products: Derniers produits consultés
        - success: True si récupéré avec succès
    """
    logger.info(f"👤 [MCP:memory] Récupération contexte client: {client_id[:8]}...")
    
    try:
        from backend.memory import get_memory_system
        
        memory = get_memory_system()
        profile = memory.get_client_profile(client_id)
        
        if profile:
            logger.info(f"✅ [MCP:memory] Profil trouvé pour {client_id[:8]}")
            return {
                "success": True,
                "client_id": client_id,
                "profile": {
                    "skin_type": profile.get("skin_type"),
                    "preferences": profile.get("preferences", {}),
                    "visit_count": profile.get("visit_count", 0),
                    "last_visit": profile.get("last_visit")
                },
                "last_products": profile.get("last_products", []),
                "is_returning_client": profile.get("visit_count", 0) > 1
            }
        else:
            logger.info(f"ℹ️ [MCP:memory] Nouveau client: {client_id[:8]}")
            return {
                "success": True,
                "client_id": client_id,
                "profile": None,
                "last_products": [],
                "is_returning_client": False,
                "message": "Nouveau client, pas d'historique"
            }
            
    except Exception as e:
        logger.error(f"❌ [MCP:memory] Erreur récupération contexte: {e}")
        return {
            "success": False,
            "client_id": client_id,
            "error": str(e)
        }


def store_client_info(
    client_id: str,
    info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stocke une information sur le client.
    
    Permet de mémoriser des préférences, le type de peau,
    ou d'autres informations découvertes pendant la conversation.
    
    Args:
        client_id: Identifiant unique du client
        info: Informations à stocker. Clés supportées:
            - skin_type: Type de peau (grasse, sèche, mixte, normale)
            - preferences: Dict de préférences (marques, ingrédients...)
            - notes: Notes libres sur le client
            
    Returns:
        Dict avec:
        - success: True si stocké avec succès
        - stored: Informations effectivement stockées
    """
    logger.info(f"💾 [MCP:memory] Stockage info client: {client_id[:8]}... - {list(info.keys())}")
    
    try:
        from backend.memory import get_memory_system
        
        memory = get_memory_system()
        
        # Extraire les infos à stocker
        skin_type = info.get("skin_type")
        preferences = info.get("preferences")
        
        success = memory.update_client_profile(
            client_id=client_id,
            skin_type=skin_type,
            preferences=preferences
        )
        
        if success:
            logger.info(f"✅ [MCP:memory] Info stockée pour {client_id[:8]}")
            return {
                "success": True,
                "client_id": client_id,
                "stored": info,
                "message": "Informations client mémorisées"
            }
        else:
            return {
                "success": False,
                "client_id": client_id,
                "error": "Échec du stockage"
            }
            
    except Exception as e:
        logger.error(f"❌ [MCP:memory] Erreur stockage info: {e}")
        return {
            "success": False,
            "client_id": client_id,
            "error": str(e)
        }


# Métadonnées des outils pour le LLM
GET_CLIENT_CONTEXT_METADATA = {
    "name": "get_client_context",
    "description": "Récupère le profil et l'historique d'un client pour personnaliser les recommandations. Utilise cet outil quand tu as un client_id et que tu veux adapter ta réponse à son profil.",
    "parameters": {
        "type": "object",
        "properties": {
            "client_id": {
                "type": "string",
                "description": "Identifiant unique du client"
            }
        },
        "required": ["client_id"]
    }
}

STORE_CLIENT_INFO_METADATA = {
    "name": "store_client_info",
    "description": "Mémorise une information sur le client (type de peau, préférences, etc.) pour les futures interactions. Utilise cet outil quand le client mentionne son type de peau ou ses préférences.",
    "parameters": {
        "type": "object",
        "properties": {
            "client_id": {
                "type": "string",
                "description": "Identifiant unique du client"
            },
            "info": {
                "type": "object",
                "description": "Informations à stocker. Exemple: {\"skin_type\": \"mixte\", \"preferences\": {\"bio\": true}}"
            }
        },
        "required": ["client_id", "info"]
    }
}
