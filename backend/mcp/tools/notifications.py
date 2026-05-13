"""
Outil MCP Notifications - Envoi de notifications.

MOCK: Pour l'instant, log seulement. À implémenter plus tard.
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def send_notification(
    recipient: str,
    message: str,
    notification_type: str = "info"
) -> Dict[str, Any]:
    """
    Envoie une notification à un destinataire.
    
    MOCK: Cette fonction simule l'envoi sans réellement envoyer.
    À connecter à un service de notification (email, SMS, push) plus tard.
    
    Args:
        recipient: Destinataire (email, numéro, ou identifiant)
        message: Message à envoyer
        notification_type: Type de notification (info, reminder, promo)
        
    Returns:
        Dict avec:
        - success: True si envoi "réussi" (mock)
        - notification_id: ID fictif de la notification
        - sent_at: Timestamp
    """
    logger.info(f"🔔 [MCP:notifications] MOCK - Envoi à {recipient}: {message[:50]}...")
    
    # Générer un ID fictif
    import uuid
    notification_id = str(uuid.uuid4())[:8]
    
    # Log structuré pour analyse future
    notification_record = {
        "id": notification_id,
        "recipient": recipient,
        "message": message,
        "type": notification_type,
        "sent_at": datetime.now().isoformat(),
        "status": "MOCK_SENT"
    }
    
    logger.info(f"📤 [MCP:notifications] Notification simulée: {notification_record}")
    
    return {
        "success": True,
        "notification_id": notification_id,
        "recipient": recipient,
        "sent_at": notification_record["sent_at"],
        "status": "MOCK_SENT",
        "message": "Notification simulée (mode développement)"
    }


def schedule_followup(
    client_id: str,
    delay_days: int,
    message: str
) -> Dict[str, Any]:
    """
    Programme un suivi automatique.
    
    MOCK: Simule la programmation d'un rappel.
    
    Args:
        client_id: ID du client
        delay_days: Délai avant envoi en jours
        message: Message de suivi
        
    Returns:
        Dict avec détails de la programmation
    """
    logger.info(f"📅 [MCP:notifications] MOCK - Suivi programmé dans {delay_days}j pour {client_id[:8]}...")
    
    from datetime import timedelta
    scheduled_date = datetime.now() + timedelta(days=delay_days)
    
    return {
        "success": True,
        "client_id": client_id,
        "scheduled_for": scheduled_date.isoformat(),
        "delay_days": delay_days,
        "message_preview": message[:100],
        "status": "MOCK_SCHEDULED"
    }


# Métadonnées des outils pour le LLM
SEND_NOTIFICATION_METADATA = {
    "name": "send_notification",
    "description": "Envoie une notification à un client (email, SMS). Utilise cet outil pour envoyer des rappels de rendez-vous, des confirmations, ou des offres.",
    "parameters": {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "Email, numéro de téléphone, ou ID client"
            },
            "message": {
                "type": "string",
                "description": "Message à envoyer"
            },
            "notification_type": {
                "type": "string",
                "enum": ["info", "reminder", "promo"],
                "description": "Type de notification"
            }
        },
        "required": ["recipient", "message"]
    }
}

SCHEDULE_FOLLOWUP_METADATA = {
    "name": "schedule_followup",
    "description": "Programme un message de suivi automatique à envoyer plus tard. Utile pour les rappels soins ou fidélisation.",
    "parameters": {
        "type": "object",
        "properties": {
            "client_id": {
                "type": "string",
                "description": "ID du client"
            },
            "delay_days": {
                "type": "integer",
                "description": "Nombre de jours avant envoi"
            },
            "message": {
                "type": "string",
                "description": "Message de suivi"
            }
        },
        "required": ["client_id", "delay_days", "message"]
    }
}
