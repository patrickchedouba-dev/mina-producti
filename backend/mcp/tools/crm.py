"""
Outil MCP CRM - Accès aux données CRM Body Minute.

Permet à l'orchestrateur d'interroger le CRM pour:
- Récupérer les outcomes clients (retours, achats)
- Vérifier si un client est revenu
- Obtenir l'historique des visites
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def get_crm_outcomes(
    client_ids: List[str],
    days: int = 7
) -> Dict[str, Any]:
    """
    Récupère les outcomes CRM pour les clients spécifiés.
    
    Args:
        client_ids: Liste des identifiants clients
        days: Période de suivi (7 ou 30 jours)
        
    Returns:
        Dict avec:
        - success: True si récupéré avec succès
        - outcomes: Dict {client_id: outcome_data}
        - count: Nombre de clients traités
    """
    logger.info(f"📊 [MCP:crm] Récupération outcomes: {len(client_ids)} clients, J+{days}")
    
    try:
        from backend.crm import get_crm_client
        
        crm = get_crm_client()
        outcomes = crm.get_client_outcomes(client_ids, days)
        
        # Statistiques
        returned_count = sum(1 for o in outcomes.values() if o.get("returned"))
        purchased_count = sum(1 for o in outcomes.values() if o.get("purchased"))
        
        logger.info(
            f"✅ [MCP:crm] Outcomes: {returned_count}/{len(outcomes)} retours, "
            f"{purchased_count}/{len(outcomes)} achats"
        )
        
        return {
            "success": True,
            "outcomes": outcomes,
            "count": len(outcomes),
            "stats": {
                "returned": returned_count,
                "purchased": purchased_count,
                "return_rate": round(returned_count / len(outcomes) * 100, 1) if outcomes else 0
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [MCP:crm] Erreur récupération outcomes: {e}")
        return {
            "success": False,
            "error": str(e),
            "outcomes": {}
        }


def check_client_return(client_id: str) -> Dict[str, Any]:
    """
    Vérifie si un client est revenu depuis sa dernière visite.
    
    Args:
        client_id: Identifiant unique du client
        
    Returns:
        Dict avec:
        - success: True si vérifié avec succès
        - returned: True si le client est revenu récemment
        - days_since_last: Nombre de jours depuis dernière visite
        - last_visit: Date de la dernière visite
    """
    logger.info(f"🔍 [MCP:crm] Vérification retour client: {client_id[:8]}...")
    
    try:
        from backend.crm import get_crm_client
        
        crm = get_crm_client()
        result = crm.check_client_return(client_id)
        
        if result.get("returned"):
            logger.info(f"✅ [MCP:crm] Client {client_id[:8]} revenu il y a {result.get('days_since_last')} jours")
        else:
            logger.info(f"ℹ️ [MCP:crm] Client {client_id[:8]} pas de visite récente")
        
        return {
            "success": True,
            "client_id": client_id,
            **result
        }
        
    except Exception as e:
        logger.error(f"❌ [MCP:crm] Erreur vérification retour: {e}")
        return {
            "success": False,
            "client_id": client_id,
            "error": str(e)
        }


def get_client_visits(
    client_id: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    Récupère l'historique des visites d'un client.
    
    Args:
        client_id: Identifiant unique du client
        days: Nombre de jours d'historique
        
    Returns:
        Dict avec:
        - success: True si récupéré avec succès
        - visits: Liste des visites
        - total_spent: Montant total dépensé
    """
    logger.info(f"📅 [MCP:crm] Historique visites: {client_id[:8]}... ({days}j)")
    
    try:
        from backend.crm import get_crm_client
        from datetime import date, timedelta
        
        crm = get_crm_client()
        since = date.today() - timedelta(days=days)
        visits = crm.get_client_visits(client_id, since)
        
        total_spent = sum(v.get("amount", 0) for v in visits)
        
        logger.info(f"✅ [MCP:crm] {len(visits)} visites, {total_spent:.2f}€ total")
        
        return {
            "success": True,
            "client_id": client_id,
            "visits": visits,
            "visit_count": len(visits),
            "total_spent": round(total_spent, 2)
        }
        
    except Exception as e:
        logger.error(f"❌ [MCP:crm] Erreur historique visites: {e}")
        return {
            "success": False,
            "client_id": client_id,
            "error": str(e),
            "visits": []
        }


# Métadonnées des outils pour le LLM
GET_CRM_OUTCOMES_METADATA = {
    "name": "get_crm_outcomes",
    "description": "Récupère les outcomes (retours, achats) depuis le CRM pour une liste de clients. Utilisé pour le suivi J+7/J+30.",
    "parameters": {
        "type": "object",
        "properties": {
            "client_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Liste des identifiants clients"
            },
            "days": {
                "type": "integer",
                "description": "Période de suivi (7 ou 30 jours)",
                "default": 7
            }
        },
        "required": ["client_ids"]
    }
}

CHECK_CLIENT_RETURN_METADATA = {
    "name": "check_client_return",
    "description": "Vérifie si un client est revenu depuis sa dernière visite. Utile pour personnaliser l'accueil.",
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

GET_CLIENT_VISITS_METADATA = {
    "name": "get_client_visits",
    "description": "Récupère l'historique des visites d'un client (soins, montants).",
    "parameters": {
        "type": "object",
        "properties": {
            "client_id": {
                "type": "string",
                "description": "Identifiant unique du client"
            },
            "days": {
                "type": "integer",
                "description": "Nombre de jours d'historique",
                "default": 30
            }
        },
        "required": ["client_id"]
    }
}
