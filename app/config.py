#!/usr/bin/env python3
"""
Configuration Body Minute - Constantes, couleurs, FAQ, conseils saisonniers.
Module centralisé pour toutes les configurations de l'application Body Touch.
"""

import os
from datetime import datetime

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
# FAQ BYPASS - Réponses instantanées (skip RAG+LLM)
# =============================================================================

    "bonjour": "Bonjour ! Comment puis-je t'aider aujourd'hui ?",
    "salut": "Salut ! Qu'est-ce qui te ferait plaisir ?",
    "merci": "Avec plaisir ! Autre chose ?",
    "au revoir": "À bientôt ! Prends soin de toi !",
    "bye": "À très vite !",
    "horaires": "On est ouvert du lundi au samedi, 9h-19h. Tu veux prendre RDV ?",
    "ouvert": "On est ouvert du lundi au samedi, 9h-19h. Tu veux prendre RDV ?",
    "rdv": "Pour prendre rendez-vous, appelle ton institut ou utilise l'appli Body Minute !",
    "rendez-vous": "Pour prendre rendez-vous, appelle ton institut ou utilise l'appli Body Minute !",
    "prix": "Les prix varient selon les soins. Tu veux des infos sur quel type de soin ?",
    "tarif": "Les tarifs varient selon les soins. Tu veux des infos sur quel type de soin ?",
    "conseil": "SEASONAL_TIP",
    "conseil du jour": "SEASONAL_TIP",
    "astuce": "SEASONAL_TIP",
}

# =============================================================================
# MOTS CLÉS DE FIN DE CONVERSATION
# =============================================================================

END_CONVERSATION_KEYWORDS = ["au revoir", "bye", "merci c'est tout", "stop", "arrête", "fin"]

# =============================================================================
# CONSEILS BEAUTÉ SAISONNIERS
# =============================================================================

    1: "❄️ En janvier, protège ta peau du froid ! L'hydratation profonde est essentielle. Essaie notre soin Hydratempo !",
    2: "❄️ Février = peau sèche ! Pense aux masques nourrissants et à bien hydrater matin et soir.",
    3: "🌸 Le printemps arrive ! C'est le moment de détoxifier ta peau avec un soin S-Détox.",
    4: "🌸 Avril = renouveau ! Un gommage doux pour éliminer les cellules mortes de l'hiver.",
    5: "☀️ Le soleil revient ! Pense à la protection UV et à l'hydratation légère.",
    6: "☀️ Juin = préparation été ! Soins minceur et raffermissants pour être au top !",
    7: "🏖️ En plein été, hydratation et après-soleil sont tes meilleurs amis !",
    8: "🏖️ Août chaud ! Soins légers, brume rafraîchissante, et beaucoup d'eau.",
    9: "🍂 Rentrée = détox ! Répare ta peau après l'été avec nos soins régénérants.",
    10: "🍂 Octobre doré ! Prépare ta peau au froid avec une routine hydratante.",
    11: "🍁 Novembre frais ! Intensifie l'hydratation et protège du vent.",
    12: "🎄 Décembre festif ! Éclat garanti avec nos soins Facialiste 100% Éclat !"
}


def get_seasonal_tip() -> str:
    """Retourne le conseil beauté du mois."""
    month = datetime.now().month


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
