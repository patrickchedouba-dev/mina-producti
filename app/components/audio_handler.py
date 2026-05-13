#!/usr/bin/env python3
"""
Audio Handler V2 - Multilingue STT et TTS.
Support 15+ langues avec détection automatique et voix natives.
"""

import re
import logging
from typing import Optional, Tuple, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Streamlit est optionnel (utilisé uniquement dans contexte Streamlit)
try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

from ..config import TTS_CONFIG, TTS_VOICES, STT_ALTERNATIVE_LANGUAGES

logger = logging.getLogger(__name__)


# =============================================================================
# SPEECH-TO-TEXT CLIENT (MULTILINGUE)
# =============================================================================

# Cache le client STT (singleton)
_speech_client = None

def get_speech_client():
    """Client STT - créé une seule fois (singleton)."""
    global _speech_client
    if _speech_client is None:
        from google.cloud import speech
        _speech_client = speech.SpeechClient()
    return _speech_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True
)
def _stt_recognize_with_retry(client, config, audio):
    """Appel STT avec retry automatique (3 tentatives, backoff exponentiel)."""
    return client.recognize(config=config, audio=audio)


def transcribe_audio_multilingual(audio_bytes: bytes) -> Tuple[Optional[str], str, int, bool, str]:
    """
    Convertit l'audio en texte avec DÉTECTION AUTOMATIQUE de la langue.
    
    Utilise alternative_language_codes pour détecter automatiquement parmi
    12+ langues (FR, EN, AR, ES, DE, IT, PT, ZH, JA, KO, RU, HI, TR).
    
    Intègre également la détection de tension vocale pour le Code de la Conversation.
    
    Args:
        audio_bytes: Données audio brutes
        
    Returns:
        Tuple (texte_transcrit, code_langue, latence_ms, hesitation_detectee, tension_level)
        Exemple: ("What is this product?", "en", 1234, False, "medium")
    """
    import time
    start_time = time.time()
    
    try:
        from google.cloud import speech
        
        client = get_speech_client()
        audio = speech.RecognitionAudio(content=audio_bytes)
        
        # Configuration multilingue avec détection automatique
        configs_to_try = [
            # Format WebM/Opus (mobile browsers - Chrome, Firefox)
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="fr-FR",  # Langue principale
                alternative_language_codes=STT_ALTERNATIVE_LANGUAGES,  # 12+ langues
            ),
            # Format LINEAR16 (desktop, certains mobiles)
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=48000,
                language_code="fr-FR",
                audio_channel_count=2,
                alternative_language_codes=STT_ALTERNATIVE_LANGUAGES,
            ),
            # Format OGG_OPUS (alternative mobile)
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                sample_rate_hertz=48000,
                language_code="fr-FR",
                alternative_language_codes=STT_ALTERNATIVE_LANGUAGES,
            ),
            # AUTO-DETECT (fallback)
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                sample_rate_hertz=48000,
                language_code="fr-FR",
                alternative_language_codes=STT_ALTERNATIVE_LANGUAGES,
            ),
        ]
        
        last_error = None
        for config in configs_to_try:
            try:
                # Appel avec retry interne
                response = _stt_recognize_with_retry(client, config, audio)
                if response.results:
                    result = response.results[0]
                    transcript = result.alternatives[0].transcript
                    
                    # Extraire la langue détectée (format: "fr-FR" -> "fr")
                    detected_lang = getattr(result, 'language_code', 'fr-FR')
                    lang_short = detected_lang.split('-')[0].lower() if detected_lang else 'fr'
                    
                    # Calculer la latence
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    # Détecter les patterns d'hésitation
                    from backend.conversation_state import detect_hesitation_patterns
                    hesitation_detected = detect_hesitation_patterns(transcript)
                    
                    # Analyser la tension vocale
                    from backend.tension_analyzer import get_tension_level
                    tension_level = get_tension_level(
                        text=transcript,
                        latency_ms=latency_ms,
                        hesitation_detected=hesitation_detected
                    ).value
                    
                    print(f"✅ [STT] Transcription: '{transcript[:40]}...' | Lang: {lang_short} | Latence: {latency_ms}ms | Tension: {tension_level}")
                    return transcript, lang_short, latency_ms, hesitation_detected, tension_level
                    
            except Exception as e:
                last_error = e
                continue
        
        # Si aucun format n'a marché
        latency_ms = int((time.time() - start_time) * 1000)
        print(f"❌ [STT] Tous les formats ont échoué: {last_error}")
        return None, "fr", latency_ms, False, "medium"
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        print(f"❌ [STT] Erreur globale: {e}")
        if _HAS_STREAMLIT:
            st.error("Erreur micro: Réessayez ou vérifiez les permissions")
        return None, "fr", latency_ms, False, "medium"


def transcribe_audio(audio_bytes: bytes) -> Optional[str]:
    """
    Wrapper rétrocompatible - retourne uniquement le texte.
    Pour la version avec langue détectée, utiliser transcribe_audio_multilingual().
    """
    transcript, _, _, _, _ = transcribe_audio_multilingual(audio_bytes)
    return transcript


# =============================================================================
# TEXT-TO-SPEECH MULTILINGUE
# =============================================================================

def clean_text_for_tts(text: str) -> str:
    """Nettoie le texte du markdown pour la synthèse vocale."""
    clean_text = re.sub(r'\*+', '', text)
    clean_text = re.sub(r'_+', '', clean_text)
    clean_text = re.sub(r'#+\s*', '', clean_text)
    clean_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_text)
    clean_text = re.sub(r'`+', '', clean_text)
    return clean_text


def get_voice_for_language(lang_code: str) -> Dict:
    """
    Retourne la configuration de voix pour une langue donnée.
    
    Args:
        lang_code: Code langue court (fr, en, ar, es, etc.)
        
    Returns:
        Dict avec language_code, name, gender
    """
    return TTS_VOICES.get(lang_code, TTS_VOICES["fr"])


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True
)
def _tts_synthesize_with_retry(client, synthesis_input, voice, audio_config):
    """Appel TTS avec retry automatique (3 tentatives, backoff exponentiel)."""
    return client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )


def text_to_speech_multilingual(text: str, language: str = "fr") -> Optional[bytes]:
    """
    Convertit le texte en audio avec voix native de la langue.
    
    Supporte 15+ langues avec voix Neural2/Wavenet de qualité professionnelle:
    - FR: Française (Neural2-A)
    - EN: Américaine (Neural2-F)
    - AR: Arabe (Wavenet-A)
    - ES: Espagnole (Neural2-A)
    - ZH: Chinois Mandarin (Wavenet-A)
    - Et plus...
    
    Args:
        text: Texte à synthétiser
        language: Code langue (fr, en, ar, es, zh, etc.)
        
    Returns:
        Contenu audio MP3 en bytes ou None si erreur
    """
    try:
        from google.cloud import texttospeech
        
        client = texttospeech.TextToSpeechClient()
        
        # Nettoyer le markdown
        clean_text = clean_text_for_tts(text)
        
        # Limiter la longueur
        max_chars = TTS_CONFIG["max_chars"]
        text_for_tts = clean_text[:max_chars] if len(clean_text) > max_chars else clean_text
        
        synthesis_input = texttospeech.SynthesisInput(text=text_for_tts)
        
        # Sélectionner la voix native pour la langue
        voice_config = get_voice_for_language(language)
        
        # Mapping gender string -> enum
        gender_map = {
            "FEMALE": texttospeech.SsmlVoiceGender.FEMALE,
            "MALE": texttospeech.SsmlVoiceGender.MALE,
        }
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config["language_code"],
            name=voice_config["name"],
            ssml_gender=gender_map.get(voice_config["gender"], texttospeech.SsmlVoiceGender.FEMALE)
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=TTS_CONFIG["speaking_rate"],
            pitch=TTS_CONFIG["pitch"],
            sample_rate_hertz=TTS_CONFIG["sample_rate_hertz"]
        )
        
        # Appel avec retry automatique
        response = _tts_synthesize_with_retry(client, synthesis_input, voice, audio_config)
        
        print(f"✅ [TTS] Audio généré | Langue: {language} | Voix: {voice_config['name']}")
        return response.audio_content
        
    except Exception as e:
        # TTS optionnel, ne pas bloquer si erreur
        print(f"⚠️ [TTS] Erreur: {e}")
        return None


def text_to_speech(text: str, language: str = "fr") -> Optional[bytes]:
    """
    Alias pour text_to_speech_multilingual - rétrocompatible.
    
    Args:
        text: Texte à synthétiser
        language: Code langue (défaut: fr)
        
    Returns:
        Contenu audio MP3 en bytes ou None si erreur
    """
    return text_to_speech_multilingual(text, language)
