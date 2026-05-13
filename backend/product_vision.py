#!/usr/bin/env python3
"""
Product Vision Module v1.0 - Identification de produits par photo.

Utilise Gemini 2.0 Flash Vision pour analyser les photos de produits
et les matcher avec le catalogue Skinminute/Bodyminute.

Architecture:
    Photo → Gemini Vision → JSON structuré → ProductMatch → Confirmation UI
"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime

from google import genai
from PIL import Image
import io

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Seuil de confiance minimum pour valider un match (0.0 - 1.0)
CONFIDENCE_THRESHOLD = 0.7

# Chemin vers la base de produits
PRODUCTS_DB_PATH = Path(__file__).parent.parent / "data" / "products_external.json"

# Chemin pour les logs de scan
SCAN_LOGS_PATH = Path(__file__).parent.parent / "logs" / "product_scans.jsonl"

# Dossier pour sauvegarder les photos échouées
FAILED_SCANS_DIR = Path(__file__).parent.parent / "logs" / "failed_scans"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ProductMatch:
    """Résultat d'une identification de produit par vision."""
    status: str  # "FOUND", "AUCUN_MATCH", "MULTIPLE", "ERROR"
    confidence: float  # 0.0 - 1.0
    product_id: Optional[int]  # ID du produit dans le catalogue
    product_name: Optional[str]  # Nom du produit identifié
    product_data: Optional[Dict]  # Données complètes du produit
    reason: str  # Explication du résultat
    raw_response: str = ""  # Réponse brute de Gemini pour debug
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire (sans product_data pour le logging)."""
        d = asdict(self)
        d.pop("product_data", None)  # Exclure les données complètes
        d.pop("raw_response", None)  # Exclure la réponse brute
        return d


# =============================================================================
# BASE DE PRODUITS
# =============================================================================

_PRODUCTS_CACHE: Optional[List[Dict]] = None


def _load_products() -> List[Dict]:
    """Charge le catalogue complet des produits."""
    global _PRODUCTS_CACHE
    if _PRODUCTS_CACHE is None:
        try:
            with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                _PRODUCTS_CACHE = data.get("products", [])
                logger.info(f"✅ Catalogue chargé: {len(_PRODUCTS_CACHE)} produits")
        except Exception as e:
            logger.error(f"❌ Erreur chargement catalogue: {e}")
            _PRODUCTS_CACHE = []
    return _PRODUCTS_CACHE


def _get_product_by_id(product_id: int) -> Optional[Dict]:
    """Retrouve un produit par son ID."""
    products = _load_products()
    for p in products:
        if p.get("product_id") == product_id:
            return p
    return None


def _build_products_reference() -> str:
    """
    Construit la référence des produits pour le prompt.
    Format compact pour optimiser les tokens.
    """
    products = _load_products()
    lines = []
    for p in products:
        pid = p.get("product_id", "")
        name = p.get("product_name", "")
        ref = p.get("product_ref", "")
        ptype = p.get("product_type", "")
        ref_str = f" ({ref})" if ref else ""
        lines.append(f"- ID:{pid} | {name}{ref_str} | {ptype}")
    return "\n".join(lines)


# =============================================================================
# PROMPT GEMINI VISION
# =============================================================================

PRODUCT_VISION_PROMPT = """Tu es un système d'identification visuelle de produits Skinminute/Bodyminute.

## TÂCHE
Analyse cette photo et identifie le produit parmi le catalogue ci-dessous.
IMPORTANT: Même si l'image est sombre ou légèrement floue, essaie d'identifier le produit.
Recherche les indices visuels: couleurs de l'emballage, forme du flacon, texte visible (même partiel).

## CATALOGUE COMPLET ({product_count} produits)
{products_reference}

## RÈGLES
1. Retourne UNIQUEMENT un JSON valide, rien d'autre
2. Le champ "product_id" DOIT correspondre EXACTEMENT à un ID du catalogue
3. Si tu peux lire NE SERAIT-CE QU'UNE PARTIE du nom du produit → essaie de matcher
4. Utilise les couleurs (bleu = Hydratempo, rose = etc.) comme indices
5. Retourne "AUCUN_MATCH" SEULEMENT si tu ne vois vraiment AUCUN indice exploitable
6. Si plusieurs produits sont visibles, retourne status "MULTIPLE"

## FORMAT DE SORTIE OBLIGATOIRE (JSON uniquement)
{{
  "status": "FOUND" | "AUCUN_MATCH" | "MULTIPLE",
  "confidence": 0.0 à 1.0,
  "product_id": 12345 ou null,
  "product_name": "Nom exact du produit" ou null,
  "reason": "Courte explication de ton identification"
}}

Réponds UNIQUEMENT avec le JSON, sans texte autour."""


# =============================================================================
# IDENTIFICATION PRINCIPALE
# =============================================================================

def identify_product(image_bytes: bytes) -> ProductMatch:
    """
    Identifie un produit à partir d'une photo.
    
    Args:
        image_bytes: Image au format bytes (PNG, JPEG, etc.)
        
    Returns:
        ProductMatch avec le résultat de l'identification
    """
    try:
        # Configurer Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config={
                "temperature": 0.1,  # Très déterministe pour l'identification
                "max_output_tokens": 300
            }
        )
        
        # Charger l'image
        image = Image.open(io.BytesIO(image_bytes))
        
        # ===== PRÉTRAITEMENT POUR ÉCLAIRAGE ARTIFICIEL (Institut) =====
        # Améliore la visibilité pour les conditions de lumière tamisée
        from PIL import ImageEnhance
        
        # 1. Augmenter la luminosité (+20%)
        brightness_enhancer = ImageEnhance.Brightness(image)
        image = brightness_enhancer.enhance(1.2)
        
        # 2. Augmenter le contraste (+30%) 
        contrast_enhancer = ImageEnhance.Contrast(image)
        image = contrast_enhancer.enhance(1.3)
        
        # 3. Légère amélioration de la netteté
        sharpness_enhancer = ImageEnhance.Sharpness(image)
        image = sharpness_enhancer.enhance(1.2)
        
        logger.info("📸 Image prétraitée pour éclairage institut")
        
        # Construire le prompt avec le catalogue
        products_ref = _build_products_reference()
        products = _load_products()
        
        prompt = PRODUCT_VISION_PROMPT.format(
            product_count=len(products),
            products_reference=products_ref
        )
        
        logger.info(f"🔍 Analyse d'image en cours ({len(image_bytes)} bytes)...")
        
        # Appeler Gemini Vision
        response = model.generate_content([prompt, image])
        raw_response = response.text.strip()
        
        logger.debug(f"Réponse brute Gemini: {raw_response}")
        
        # Parser le JSON
        return _parse_vision_response(raw_response)
        
    except Exception as e:
        logger.error(f"❌ Erreur identification: {e}")
        return ProductMatch(
            status="ERROR",
            confidence=0.0,
            product_id=None,
            product_name=None,
            product_data=None,
            reason=f"Erreur technique: {str(e)[:100]}",
            raw_response=""
        )


def _parse_vision_response(raw_response: str) -> ProductMatch:
    """
    Parse la réponse JSON de Gemini Vision.
    
    Args:
        raw_response: Texte brut retourné par Gemini
        
    Returns:
        ProductMatch avec les données extraites
    """
    try:
        # Nettoyer le JSON (retirer les balises markdown si présentes)
        json_str = raw_response.strip()
        if json_str.startswith("```"):
            # Retirer les balises markdown
            lines = json_str.split("\n")
            json_str = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        
        data = json.loads(json_str)
        
        status = data.get("status", "ERROR")
        confidence = float(data.get("confidence", 0.0))
        product_id = data.get("product_id")
        product_name = data.get("product_name")
        reason = data.get("reason", "")
        
        # Valider le product_id si présent
        product_data = None
        if product_id is not None:
            product_data = _get_product_by_id(product_id)
            if product_data is None:
                logger.warning(f"⚠️ Product ID {product_id} non trouvé dans le catalogue")
                # Essayer de matcher par nom
                product_data = _find_product_by_name_fuzzy(product_name)
                if product_data:
                    product_id = product_data.get("product_id")
        
        # Appliquer le seuil de confiance
        if status == "FOUND" and confidence < CONFIDENCE_THRESHOLD:
            logger.info(f"📉 Confiance {confidence:.2f} < seuil {CONFIDENCE_THRESHOLD}")
            status = "AUCUN_MATCH"
            reason = f"Confiance insuffisante ({confidence:.0%}). {reason}"
        
        return ProductMatch(
            status=status,
            confidence=confidence,
            product_id=product_id,
            product_name=product_name,
            product_data=product_data,
            reason=reason,
            raw_response=raw_response
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur parsing JSON: {e}\nRéponse: {raw_response}")
        return ProductMatch(
            status="ERROR",
            confidence=0.0,
            product_id=None,
            product_name=None,
            product_data=None,
            reason="Impossible de parser la réponse du modèle",
            raw_response=raw_response
        )


def _find_product_by_name_fuzzy(name: Optional[str]) -> Optional[Dict]:
    """Recherche un produit par nom approximatif."""
    if not name:
        return None
    
    products = _load_products()
    name_lower = name.lower().strip()
    
    # Match exact
    for p in products:
        if p.get("product_name", "").lower() == name_lower:
            return p
    
    # Match partiel
    for p in products:
        if name_lower in p.get("product_name", "").lower():
            return p
    
    return None


# =============================================================================
# LOGGING DES SCANS
# =============================================================================

def log_scan_attempt(
    match: ProductMatch,
    user_question: str = "",
    user_language: str = "fr",
    reprise_count: int = 0,
    confirmed: Optional[bool] = None,
    save_failed_image: bool = False,
    image_bytes: Optional[bytes] = None
) -> None:
    """
    Sauvegarde une tentative de scan pour analyse métriques.
    
    Args:
        match: Résultat du scan
        user_question: Question posée par l'utilisateur
        user_language: Langue détectée (fr, en, ar, etc.)
        reprise_count: Nombre de reprises photo
        confirmed: True si confirmé, False si refusé, None si en attente
        save_failed_image: Sauvegarder l'image si échec
        image_bytes: Image à sauvegarder
    """
    try:
        # Créer le dossier logs si nécessaire
        SCAN_LOGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "status": match.status,
            "confidence": match.confidence,
            "product_id": match.product_id,
            "product_name": match.product_name,
            "reason": match.reason,
            "user_question": user_question,
            "user_language": user_language,
            "reprise_count": reprise_count,
            "confirmed": confirmed
        }
        
        # Sauvegarder l'image si échec et demandé
        if save_failed_image and image_bytes and match.status in ("AUCUN_MATCH", "ERROR"):
            FAILED_SCANS_DIR.mkdir(parents=True, exist_ok=True)
            image_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{match.status}.jpg"
            image_path = FAILED_SCANS_DIR / image_filename
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            log_entry["failed_image_path"] = str(image_path)
            logger.info(f"📸 Image échouée sauvegardée: {image_path}")
        
        # Ajouter au fichier JSONL
        with open(SCAN_LOGS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        logger.debug(f"📝 Scan loggé: {match.status} - {match.product_name}")
        
    except Exception as e:
        logger.error(f"❌ Erreur logging scan: {e}")


# =============================================================================
# GÉNÉRATION DE RÉPONSE CONVERSATIONNELLE
# =============================================================================

def generate_product_explanation(
    match: ProductMatch,
    user_question: str,
    target_language: str = "fr"
) -> str:
    """
    Génère une explication conversationnelle du produit identifié.
    
    Args:
        match: Résultat de l'identification
        user_question: Question originale de l'utilisateur
        target_language: Langue cible pour la réponse (fr, en, ar, es, zh, etc.)
        
    Returns:
        Texte explicatif pour TTS
    """
    if match.status != "FOUND" or not match.product_data:
        return ""
    
    # Mapping code langue -> nom pour prompt plus clair
    LANG_NAMES = {
        "fr": "français",
        "en": "English", 
        "ar": "العربية (Arabic)",
        "es": "español",
        "de": "Deutsch",
        "it": "italiano",
        "pt": "português",
        "zh": "中文 (Chinese)",
        "ja": "日本語 (Japanese)",
        "ko": "한국어 (Korean)",
        "ru": "русский",
        "hi": "हिंदी (Hindi)",
        "tr": "Türkçe",
    }
    
    try:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config={
                "temperature": 0.5,
                "max_output_tokens": 150
            }
        )
        
        product = match.product_data
        lang_name = LANG_NAMES.get(target_language, "français")
        
        prompt = f"""Tu es Mina, conseillère beauté Body Minute. La cliente a scanné un produit.

PRODUIT IDENTIFIÉ :
- Nom: {product.get('product_name', '')}
- Prix: {product.get('price_eur', '')}€
- Type: {product.get('product_type', '')}
- Description: {product.get('description', '')[:300]}

QUESTION DE LA CLIENTE : "{user_question}"

⚠️ INSTRUCTION CRITIQUE - LANGUE DE RÉPONSE :
Tu DOIS répondre UNIQUEMENT en {lang_name}.
Ne mélange PAS les langues. Toute ta réponse doit être dans cette langue.

STYLE : 2-3 phrases, ton chaleureux et professionnel (tutoiement en français, informal en autres langues).
Si la question est "C'est quoi ce produit ?", présente le produit et ses bénéfices.
"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"❌ Erreur génération explication: {e}")
        # Fallback simple
        product = match.product_data
        return f"C'est le {product.get('product_name', 'produit')} à {product.get('price_eur', '')}€. {product.get('description', '')[:100]}"


# =============================================================================
# DÉTECTION DE LANGUE
# =============================================================================

def detect_language(text: str) -> str:
    """
    Détecte la langue du texte (simple heuristique).
    
    Returns:
        Code langue: 'fr', 'en', 'ar', 'es', etc.
    """
    import re
    text_lower = text.lower()
    
    # Patterns arabes (caractères Unicode)
    if any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in text):
        return "ar"
    
    # Patterns espagnol (priorité car "producto" contient "product")
    spanish_markers = ["¿", "¡", "qué", "cómo", "usar", "producto"]
    if any(m in text_lower for m in spanish_markers):
        return "es"
    
    # Patterns anglais - mots complets uniquement
    english_patterns = [r'\bwhat\b', r'\bis\b', r'\bthis\b', r'\bhow\b', r'\bcan\b', r'\buse\b']
    if any(re.search(p, text_lower) for p in english_patterns):
        return "en"
    
    # Défaut français
    return "fr"


# =============================================================================
# POINT D'ENTRÉE POUR TESTS
# =============================================================================

if __name__ == "__main__":
    # Test rapide
    logging.basicConfig(level=logging.DEBUG)
    
    print("🧪 Test Product Vision Module")
    print(f"📦 Produits chargés: {len(_load_products())}")
    print(f"📝 Seuil de confiance: {CONFIDENCE_THRESHOLD}")
    print(f"📂 Logs path: {SCAN_LOGS_PATH}")
