"""
Outil MCP Vision - Analyse d'images.

Réutilise backend/product_vision.py existant, ne recrée PAS la vision.
"""

import base64
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def analyze_skin_image(image_base64: str) -> Dict[str, Any]:
    """
    Analyse une image de peau pour diagnostic esthétique.
    
    Utilise Gemini Vision pour analyser la photo et suggérer
    un type de peau et des recommandations de soins.
    
    Args:
        image_base64: Image encodée en base64
        
    Returns:
        Dict avec:
        - skin_analysis: Diagnostic de peau
        - skin_type: Type de peau détecté
        - recommendations: Recommandations produits
        - success: True si analyse réussie
    """
    logger.info(f"👁️ [MCP:vision] Analyse peau - Image: {len(image_base64)//1000}KB")
    
    try:
        from google import genai
        import os
        from PIL import Image
        import io
        
        # Décoder l'image
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Configurer Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Prompt d'analyse
        prompt = """Tu es une esthéticienne experte. Analyse cette photo de peau.

RETOURNE UN JSON VALIDE avec cette structure exacte:
{
  "skin_type": "grasse" | "sèche" | "mixte" | "normale" | "sensible",
  "observations": ["observation 1", "observation 2"],
  "concerns": ["préoccupation 1", "préoccupation 2"],
  "recommendations": ["recommandation 1", "recommandation 2"]
}

IMPORTANT: 
- Ceci est un conseil esthétique, PAS médical
- Sois bienveillante et rassurante
- JSON UNIQUEMENT, pas de texte autour"""
        
        response = model.generate_content([prompt, image])
        raw_response = response.text.strip()
        
        # Parser le JSON
        import json
        # Nettoyer le markdown si présent
        if raw_response.startswith("```"):
            raw_response = raw_response.split("```")[1]
            if raw_response.startswith("json"):
                raw_response = raw_response[4:]
        
        analysis = json.loads(raw_response)
        
        logger.info(f"✅ [MCP:vision] Analyse réussie - Type: {analysis.get('skin_type')}")
        
        return {
            "success": True,
            "skin_type": analysis.get("skin_type"),
            "observations": analysis.get("observations", []),
            "concerns": analysis.get("concerns", []),
            "recommendations": analysis.get("recommendations", []),
            "raw_analysis": analysis
        }
        
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ [MCP:vision] JSON invalide, fallback texte: {e}")
        return {
            "success": True,
            "skin_type": "indéterminé",
            "observations": [raw_response[:200]],
            "concerns": [],
            "recommendations": ["Consulter en institut pour un diagnostic précis"],
            "raw_response": raw_response
        }
        
    except Exception as e:
        logger.error(f"❌ [MCP:vision] Erreur analyse: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def identify_product_image(image_base64: str) -> Dict[str, Any]:
    """
    Identifie un produit Body Minute depuis une photo.
    
    Réutilise backend/product_vision.py.
    
    Args:
        image_base64: Image encodée en base64
        
    Returns:
        Dict avec résultat d'identification
    """
    logger.info(f"📦 [MCP:vision] Identification produit - Image: {len(image_base64)//1000}KB")
    
    try:
        from backend.product_vision import identify_product
        
        # Décoder l'image
        image_bytes = base64.b64decode(image_base64)
        
        # Appeler la fonction existante
        match = identify_product(image_bytes)
        
        logger.info(f"✅ [MCP:vision] Produit: {match.status} - {match.product_name}")
        
        return {
            "success": match.status == "FOUND",
            "status": match.status,
            "confidence": match.confidence,
            "product_name": match.product_name,
            "product_id": match.product_id,
            "product_data": match.product_data,
            "reason": match.reason
        }
        
    except Exception as e:
        logger.error(f"❌ [MCP:vision] Erreur identification: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Métadonnées de l'outil pour le LLM
TOOL_METADATA = {
    "name": "analyze_skin_image",
    "description": "Analyse une photo de peau pour déterminer le type de peau et donner des recommandations de soins. C'est un conseil esthétique, pas médical.",
    "parameters": {
        "type": "object",
        "properties": {
            "image_base64": {
                "type": "string",
                "description": "Image encodée en base64"
            }
        },
        "required": ["image_base64"]
    }
}

IDENTIFY_PRODUCT_METADATA = {
    "name": "identify_product_image",
    "description": "Identifie un produit Body Minute depuis une photo de l'emballage.",
    "parameters": {
        "type": "object",
        "properties": {
            "image_base64": {
                "type": "string",
                "description": "Image du produit encodée en base64"
            }
        },
        "required": ["image_base64"]
    }
}
