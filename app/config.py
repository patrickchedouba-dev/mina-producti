#!/usr/bin/env python3
"""
Configuration Body Minute — Constantes, couleurs, configuration LLM/TTS.
Module centralisé pour toutes les configurations de l'application Body Touch.
CDC V4.0 Ch.25 : aucun contenu textuel hardcodé.
"""

import os

# =============================================================================
# COULEURS BODY MINUTE
# =============================================================================

BLEU_PROFOND = "#1a1a2e"
ROSE_FUCHSIA = "#e91e63"
ROSE_CLAIR = "#ff4081"
BLANC = "#ffffff"
GRIS_CLAIR = "#b0b0b0"

# =============================================================================
# COLLECTIONS QDRANT
# =============================================================================

COLLECTION_PRODUCTS = os.getenv("QDRANT_COLLECTION_NAME", "bodyminute_docs")

# =============================================================================
# DÉTECTION SALUTATIONS SOCIALES (remplace FAQ_BYPASS — CDC V4.0 Ch.25)
# =============================================================================


def is_social_greeting(message: str) -> bool:
    """Détecte si le message est une salutation sociale simple."""
    greetings = ["bonjour", "salut", "merci", "au revoir", "bye"]
    return message.strip().lower() in greetings

# =============================================================================
# MOTS CLÉS DE FIN DE CONVERSATION
# =============================================================================

END_CONVERSATION_KEYWORDS = ["au revoir", "bye", "merci c'est tout", "stop", "arrête", "fin"]

# =============================================================================
# CONSEIL BEAUTÉ VIA LLM (remplace SEASONAL_TIPS — CDC V4.0 Ch.25)
# =============================================================================


def get_seasonal_tip(llm_provider=None) -> str:
    """Génère un conseil beauté du moment via le LLM — aucun contenu hardcodé."""
    from datetime import datetime
    month = datetime.now().month
    month_names = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril",
        5: "mai", 6: "juin", 7: "juillet", 8: "août",
        9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    if llm_provider is None:
        try:
            from backend.llm.provider import get_llm_provider
            llm_provider = get_llm_provider()
        except Exception:
            return ""
    prompt = f"Donne un conseil beauté court et engageant pour le mois de {month_names[month]} adapté aux clientes d'un institut Body Minute. Maximum 2 phrases."
    try:
        response = llm_provider.generate_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100,
        )
        return response.text.strip()
    except Exception:
        return ""

# =============================================================================
# CONFIGURATION LLM
# =============================================================================

LLM_CONFIG = {
    "model": "gemini-2.0-flash",
    "temperature": 0.3,
    "max_output_tokens": 120,
}

# =============================================================================
# CONFIGURATION TTS MULTILINGUE
# =============================================================================

TTS_CONFIG = {
    "default_voice": "fr-FR-Neural2-A",
    "speaking_rate": 1.15,
    "pitch": 0.0,
    "sample_rate_hertz": 22050,
    "max_chars": 500,
}

# Mapping langue -> voix native Google TTS (Neural2 pour qualité pro)
# Documentation: https://cloud.google.com/text-to-speech/docs/voices
TTS_VOICES = {
    "fr": {"language_code": "fr-FR", "name": "fr-FR-Neural2-A", "gender": "FEMALE"},
    "en": {"language_code": "en-US", "name": "en-US-Neural2-F", "gender": "FEMALE"},
    "ar": {"language_code": "ar-XA", "name": "ar-XA-Wavenet-A", "gender": "FEMALE"},
    "es": {"language_code": "es-ES", "name": "es-ES-Neural2-A", "gender": "FEMALE"},
    "de": {"language_code": "de-DE", "name": "de-DE-Neural2-A", "gender": "FEMALE"},
    "it": {"language_code": "it-IT", "name": "it-IT-Neural2-A", "gender": "FEMALE"},
    "pt": {"language_code": "pt-BR", "name": "pt-BR-Neural2-A", "gender": "FEMALE"},
    "zh": {"language_code": "cmn-CN", "name": "cmn-CN-Wavenet-A", "gender": "FEMALE"},
    "ja": {"language_code": "ja-JP", "name": "ja-JP-Neural2-B", "gender": "FEMALE"},
    "ko": {"language_code": "ko-KR", "name": "ko-KR-Neural2-A", "gender": "FEMALE"},
    "ru": {"language_code": "ru-RU", "name": "ru-RU-Wavenet-A", "gender": "FEMALE"},
    "hi": {"language_code": "hi-IN", "name": "hi-IN-Neural2-A", "gender": "FEMALE"},
    "tr": {"language_code": "tr-TR", "name": "tr-TR-Wavenet-A", "gender": "FEMALE"},
    "nl": {"language_code": "nl-NL", "name": "nl-NL-Wavenet-A", "gender": "FEMALE"},
    "pl": {"language_code": "pl-PL", "name": "pl-PL-Wavenet-A", "gender": "FEMALE"},
}

# Langues alternatives pour STT (détection automatique)
STT_ALTERNATIVE_LANGUAGES = [
    "en-US",   # Anglais
    "ar-SA",   # Arabe
    "es-ES",   # Espagnol
    "de-DE",   # Allemand
    "it-IT",   # Italien
    "pt-BR",   # Portugais
    "zh-CN",   # Chinois
    "ja-JP",   # Japonais
    "ko-KR",   # Coréen
    "ru-RU",   # Russe
    "hi-IN",   # Hindi
    "tr-TR",   # Turc
]

# =============================================================================
# CHEMINS
# =============================================================================

LOG_FILE_PATH = "/home/jupyter/mina_fichiers/mina-bêta/logs/benchmark_interactions.jsonl"
