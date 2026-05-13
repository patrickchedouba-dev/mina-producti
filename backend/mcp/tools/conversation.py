"""
Outil MCP Conversation - Détection d'état conversationnel.

Réutilise backend/conversation_state.py existant.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def detect_conversation_state(
    text: str,
    latency_ms: Optional[int] = None
) -> Dict[str, Any]:
    """
    Détecte l'état conversationnel à partir du texte utilisateur.
    
    Identifie des patterns comme l'hésitation, la confusion, le rush,
    etc. pour adapter le style de réponse.
    
    Args:
        text: Texte transcrit de l'utilisateur
        latency_ms: Temps de réponse en ms (optionnel)
        
    Returns:
        Dict avec:
        - state: État détecté (hesitation, rush, confusion, etc.)
        - confidence: Score de confiance
        - triggers: Mots/patterns qui ont déclenché la détection
        - recommended_strategy: Stratégie de réponse suggérée
    """
    logger.info(f"🎭 [MCP:conversation] Détection état: '{text[:50]}...'")
    
    try:
        from backend.conversation_state import detect_state, StateType
        
        # Appeler la fonction existante
        result = detect_state(text, latency_ms)
        
        # Mapper les stratégies de réponse
        strategies = {
            StateType.NEUTRAL: "standard",
            StateType.HESITATION: "reduce_choice",
            StateType.CONFUSION: "simplify",
            StateType.RUSH: "quick",
            StateType.CURIOSITY: "deepen",
            StateType.DOUBT: "reassure",
            StateType.SATURATION: "summarize",
            StateType.CONFIRMATION: "validate",
            StateType.OBJECTION: "handle",
            StateType.GREETING: "welcome"
        }
        
        strategy = strategies.get(result.state, "standard")
        
        logger.info(f"✅ [MCP:conversation] État: {result.state.value} (conf={result.confidence:.2f})")
        
        return {
            "success": True,
            "state": result.state.value,
            "confidence": round(result.confidence, 2),
            "triggers": result.triggers,
            "latency_ms": result.latency_ms,
            "recommended_strategy": strategy,
            "is_actionable": result.is_actionable()
        }
        
    except Exception as e:
        logger.error(f"❌ [MCP:conversation] Erreur détection: {e}")
        return {
            "success": False,
            "state": "neutral",
            "confidence": 0.0,
            "triggers": [],
            "recommended_strategy": "standard",
            "error": str(e)
        }


# Métadonnées de l'outil pour le LLM
TOOL_METADATA = {
    "name": "detect_conversation_state",
    "description": "Détecte l'état émotionnel/conversationnel du client (hésitation, confusion, empressé, etc.) pour adapter le style de réponse. Utilise cet outil pour personnaliser ton approche.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Le texte de l'utilisateur à analyser"
            },
            "latency_ms": {
                "type": "integer",
                "description": "Temps de réponse de l'utilisateur en millisecondes (optionnel)"
            }
        },
        "required": ["text"]
    }
}
