import os
os.environ['HOME'] = '/home/jupyter'
os.chdir('/home/jupyter/mina_fichiers')

#!/usr/bin/env python3
"""
Body Touch - Interface Vocale Mina Body Minute.
Un Bouton = Une Voix = Une Réponse.

Usage:
    streamlit run scripts/app_chatbot.py
"""

import os
import sys
import uuid
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Configuration du path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Charger .env
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from audio_recorder_streamlit import audio_recorder

# Module d'apprentissage Mina
from mina_learning import detect_correction, extract_correction_content, store_learning, search_learnings, get_learning_stats

# ========== PHASE 3 REFACTORING: Imports centralisés ==========
# Utilitaires Qdrant/Embeddings (Phase 2)
from utils.qdrant_utils import get_qdrant_client as _get_qdrant_client_base
from utils.embedding_utils import get_embedding_model as _get_embedding_model_base, get_embedding, get_embedding_cached

# Configuration et styles (Phase 3)
from app.config import (
    BLEU_PROFOND, ROSE_FUCHSIA, ROSE_CLAIR, BLANC, GRIS_CLAIR,
    COLLECTION_PRODUCTS, FAQ_RESPONSES, END_CONVERSATION_KEYWORDS,
    get_seasonal_tip, LOG_FILE_PATH
)
from app.styles import BODY_TOUCH_CSS, HEADER_HTML, FOOTER_HTML, get_response_html
from app.components.audio_handler import transcribe_audio, text_to_speech
from app.components.product_display import get_product_cards_for_response
from app.constants import PRODUITS_VALIDES, get_produits_for_prompt

# ========== PRODUCT VISION V2 ==========
from backend.product_vision import (
    identify_product, 
    log_scan_attempt, 
    generate_product_explanation,
    detect_language,
    ProductMatch,
    CONFIDENCE_THRESHOLD
)


# =============================================================================
# LOGGING INTERACTIONS V1.5
# =============================================================================

def log_interaction(transcript: str, response: str, latencies: dict):
    """Sauvegarde interaction dans fichier JSONL pour analyse benchmark."""
    interaction = {
        "timestamp": datetime.now().isoformat(),
        "question": transcript,
        "response": response,
        "word_count": len(response.split()),
        "latencies": latencies
    }
    
    log_file = Path(LOG_FILE_PATH)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(interaction, ensure_ascii=False) + "\n")
    
    # ===== MEMORY SYSTEM INTEGRATION =====
    try:
        from backend.feature_flags import is_memory_enabled
        if is_memory_enabled():
            from backend.memory import get_memory_system
            
            # Récupérer session_id et client_id depuis session state
            session_id = st.session_state.get("session_id", str(uuid.uuid4()))
            client_id = st.session_state.get("client_id")
            
            # Stocker dans le système de mémoire
            memory = get_memory_system()
            memory.store_interaction(
                session_id=session_id,
                client_id=client_id,
                user_message=transcript,
                assistant_message=response,
                metadata={"latencies": latencies}
            )
    except Exception as e:
        print(f"⚠️ [Memory] Erreur stockage: {e}")


def detect_client_id() -> str:
    """
    Détecte ou génère l'identifiant client.
    
    Recherche dans l'ordre:
    1. client_id existant dans session_state
    2. Numéro de téléphone si disponible
    3. Génère un nouveau UUID
    
    Returns:
        Identifiant client (UUID ou phone)
    """
    # Déjà en session
    if "client_id" in st.session_state and st.session_state.client_id:
        return st.session_state.client_id
    
    # Potentiellement depuis un formulaire/login futur
    phone = st.session_state.get("client_phone")
    if phone:
        return f"phone:{phone}"
    
    # Nouveau client - générer UUID
    client_id = f"anon:{uuid.uuid4().hex[:12]}"
    st.session_state.client_id = client_id
    return client_id


# =============================================================================
# CONFIGURATION IMPORTÉE DEPUIS app/config.py
# STYLES IMPORTÉS DEPUIS app/styles.py
# AUDIO IMPORTÉ DEPUIS app/components/audio_handler.py
# =============================================================================


# CSS BODY_TOUCH_CSS importé depuis app/styles.py (voir ligne 44)

# =============================================================================
# CLIENTS
# =============================================================================

# Wrappers avec Streamlit cache pour les clients partagés
@st.cache_resource
def get_qdrant_client():
    """Client Qdrant avec cache Streamlit."""
    return _get_qdrant_client_base()

@st.cache_resource
def get_embedding_model():
    """Modèle d'embedding avec cache Streamlit."""
    return _get_embedding_model_base()

# get_embedding et get_embedding_cached importés depuis utils.embedding_utils


@st.cache_resource
def get_llm_client():
    """Client LLM - Optimisé qualité + vitesse."""
    from google import genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    return genai.GenerativeModel("gemini-2.0-flash", generation_config={
        "temperature": 0.3,  # V1.5: Précision factuelle
        "max_output_tokens": 120  # V1.5: STRICT - 2 phrases max
    })


@st.cache_resource
def initialize_clients():
    """Pré-warmer tous les clients API au démarrage (évite cold start)."""
    print("🔥 Pré-chargement des clients API...")
    return {
        'qdrant': get_qdrant_client(),
        'embedding': get_embedding_model(),
        'llm': get_llm_client(),
    }


# Charger au démarrage de l'app
_CLIENTS = initialize_clients()


# =============================================================================\n# AUDIO: transcribe_audio et text_to_speech importés depuis app/components/audio_handler.py\n# =============================================================================


# =============================================================================
# RECHERCHE MINA
# =============================================================================

def search_mina_simple(question: str) -> str:
    """RAG ultra-simple : Retrieve -> Generate. Optimisé latence."""
    try:
        client = get_qdrant_client()
        query_vector = get_embedding(question)
        
        # Récupérer 2 chunks seulement
        results = client.query_points(
            collection_name=COLLECTION_PRODUCTS,
            query=query_vector,
            limit=2,
            with_payload=True
        )
        
        # Extraire texte des sources (court)
        context = ""
        if results.points:
            for hit in results.points[:2]:
                text = hit.payload.get("text", "")[:400]
                context += text + "\n"
        
        # Prompt ULTRA-SIMPLE (moins de tokens = plus rapide)
        prompt = f"""Contexte: {context[:800]}

Question: {question}

Réponds en 1-2 phrases, ton professionnel et chaleureux (tutoiement)."""

        # Générer AVEC STREAMING
        model = get_llm_client()
        response = model.generate_content(prompt, stream=True)
        
        # Collecter les chunks streamés
        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
        
        return full_response
        
    except Exception as e:
        return f"Désolée, je n'ai pas pu répondre. ({str(e)[:50]})"

def truncate_smart(text: str, max_chars: int = 1500) -> str:
    """Tronque texte à phrase complète (pas brutal)."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind('.')
    if last_period > 0:
        return truncated[:last_period + 1]
    return truncated


def search_mina_streaming(question: str, placeholder):
    """Streaming avec qualité métier + timing séparé RAG/LLM."""
    
    question_normalized = question.lower().strip()
    
    # === MODE COMPARATEUR ===
    comparison_keywords = ["compare", "comparaison", "différence", "versus", "vs", "ou bien", "lequel", "laquelle"]
    is_comparison = any(kw in question_normalized for kw in comparison_keywords)
    
    # === FAQ BYPASS (réponse instantanée) ===
    for key, faq_response in FAQ_RESPONSES.items():
        if key in question_normalized:
            print(f"⚡ [FAQ] Bypass RAG - Réponse instantanée pour '{key}'")
            # Remplacer le conseil saisonnier dynamiquement
            if faq_response == "SEASONAL_TIP":
                faq_response = get_seasonal_tip()
            placeholder.markdown(f"💆 **Mina:** {faq_response}")
            placeholder.t_rag = 0
            placeholder.t_llm = 0
            return faq_response
    
    try:
        import time as t
        
        # === RAG ===
        t_rag_start = t.time()
        client = get_qdrant_client()
        query_vector = list(get_embedding_cached(question))  # V1.5: Cache LRU
        
        # V1.5: limit 3 + score_threshold 0.7
        results = client.query_points(
            collection_name=COLLECTION_PRODUCTS,
            query=query_vector,
            limit=3,  # V1.5: Réduit de 4→3
            score_threshold=0.5,  # V1.5: Abaissé de 0.7 pour plus de résultats
            with_payload=True
        )
        
        # Collecter le contexte
        context = ""
        if results.points:
            for i, hit in enumerate(results.points[:3], 1):
                text = hit.payload.get("text", "")[:500]
                context += f"[{i}] {text}\n\n"
        
        t_rag = t.time() - t_rag_start
        print(f"⏱️ [RAG] {t_rag:.2f}s")
        
        # === LLM ===
        t_llm_start = t.time()
        
        # Prompt adapté selon le mode
        if is_comparison:
            print("📊 [COMPARATEUR] Mode comparaison activé")
            prompt = f"""Tu es Mina, experte beauté Body Minute. La cliente veut COMPARER des soins/produits.

DOCUMENTATION BODY MINUTE:
{truncate_smart(context, 2000)}

QUESTION: {question}

FORMAT OBLIGATOIRE - Réponds avec un TABLEAU COMPARATIF:
| Critère | [Produit 1] | [Produit 2] |
|---------|-------------|-------------|
| Type de peau | ... | ... |
| Bénéfices | ... | ... |
| Prix indicatif | ... | ... |
| Durée | ... | ... |

Après le tableau, UNE phrase de recommandation personnalisée. Tutoiement."""
        else:
            # Prompt V1.7: Plus souple - recommande depuis la documentation
            # ===== PRODUCT VISION V2: Injecter le contexte produit si disponible =====
            product_context = ""
            last_product = st.session_state.get("last_confirmed_product")
            if last_product:
                product_context = f"""
📦 CONTEXTE PRODUIT ACTIF:
La cliente vient de scanner "{last_product.get('product_name', '')}" ({last_product.get('price_eur', '')}€).
Si elle parle de "ce produit", "l'utiliser", "ça" → c'est de celui-ci.

"""
            
            prompt = f"""Tu es Mina, conseillère beauté Body Minute. TON : chaleureux, professionnel, tutoiement.
{product_context}RÈGLES:
1. Réponds en 2 phrases maximum, très concis
2. Base-toi UNIQUEMENT sur la DOCUMENTATION ci-dessous pour recommander des produits
3. Cite les noms de produits tels qu'ils apparaissent dans la documentation
4. Si un produit n'est pas dans la documentation, propose une alternative proche ou dis "je peux te conseiller sur nos gammes"
5. Ne JAMAIS inventer de produit qui n'existe pas

⚠️ HORS-SCOPE: Si la question est hors beauté/soins → "Je suis spécialisée Body Minute, je ne peux pas t'aider sur ça."

DOCUMENTATION BODY MINUTE:
{truncate_smart(context, 1500)}

QUESTION: {question}

RÉPONSE (2 phrases max, tutoiement):"""

        model = get_llm_client()
        response = model.generate_content(prompt, stream=True)
        
        # Afficher en temps réel
        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                placeholder.markdown(f"💆 **Mina:** {full_response}")
        
        t_llm = t.time() - t_llm_start
        print(f"⏱️ [LLM] {t_llm:.2f}s")
        
        # Stocker timing pour log total
        placeholder.t_rag = t_rag
        placeholder.t_llm = t_llm
        
        return full_response
        
    except Exception as e:
        return f"Erreur: {str(e)[:50]}"


# =============================================================================
# DIAGNOSTIC PEAU PAR PHOTO (BODY HOME)
# =============================================================================

def analyze_skin_photo(image_bytes: bytes, placeholder) -> str:
    """Analyse photo de peau avec Gemini Vision + recommandations produits."""
    try:
        from google import genai
        from PIL import Image
        import io
        
        # Convertir bytes en Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Client Gemini avec vision
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = get_llm_client()  # V1.5: Utilise config optimisée
        
        # Récupérer les produits Body Minute pour contexte
        client = get_qdrant_client()
        # Recherche générique de produits soins visage
        query_vector = get_embedding("soins visage peau hydratation sébum")
        results = client.query_points(
            collection_name=COLLECTION_PRODUCTS,
            query=query_vector,
            limit=5,
            with_payload=True
        )
        
        products_context = ""
        if results.points:
            for hit in results.points[:5]:
                text = hit.payload.get("text", "")[:300]
                products_context += text + "\n\n"
        
        # Prompt esthéticienne experte
        prompt = f"""Tu es Mina, esthéticienne experte Body Minute spécialisée en diagnostic de peau.

ANALYSE CETTE PHOTO du visage de la cliente.

DIAGNOSTIC À FAIRE :
1. Type de peau (normale, sèche, grasse, mixte, sensible)
2. Signes visibles : déshydratation (stries, tiraillements), excès de sébum (zone T brillante), rougeurs, imperfections, rides
3. Zones à traiter

PRODUITS BODY MINUTE DISPONIBLES :
{products_context[:1500]}

CONSIGNES :
- Sois bienveillante et professionnelle (tutoiement)
- NE DONNE AUCUN AVIS MÉDICAL
- Propose un protocole de soins adapté avec produits Body Minute
- 3-4 phrases maximum

DIAGNOSTIC ESTHÉTIQUE :"""

        placeholder.markdown("🔍 *Mina analyse ta peau...*")
        
        # Générer avec image + streaming
        response = model.generate_content([prompt, image], stream=True)
        
        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                placeholder.markdown(f"👩‍⚕️ **Diagnostic Mina:** {full_response}")
        
        return full_response
        
    except Exception as e:
        return f"Erreur d'analyse: {str(e)[:80]}"


def analyze_product_photo(image_bytes: bytes, user_question: str, placeholder) -> str:
    """
    Identifie un produit Body Minute via photo + répond dans la langue de la cliente.
    Utilise Gemini Vision pour lire l'étiquette du produit.
    """
    try:
        from google import genai
        from PIL import Image
        import io
        import json
        
        # Convertir bytes en Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Client Gemini avec vision
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = get_llm_client()
        
        # Charger la base de produits pour contexte
        products_path = Path(__file__).parent.parent / "data" / "products_external.json"
        products_context = ""
        try:
            with open(products_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for p in data.get('products', [])[:50]:
                    products_context += f"- {p.get('product_name', '')}: {p.get('price_eur', '')}€\n"
        except Exception:
            products_context = "Produits Body Minute disponibles."
        
        # Prompt multilingue intelligent
        prompt = f"""Tu es Mina, conseillère beauté Body Minute. Une cliente te montre un produit en photo.

OBJECTIF : Identifier le produit sur la photo et répondre dans la MÊME LANGUE que la cliente.

QUESTION DE LA CLIENTE : "{user_question}"
(Détecte la langue et réponds dans cette langue)

ÉTAPES :
1. Lis l'étiquette/packaging du produit sur la photo
2. Identifie le nom du produit Body Minute
3. Donne les informations essentielles : prix, bénéfices, conseils d'utilisation
4. Réponds dans la langue de la question (français, arabe, anglais, etc.)

PRODUITS BODY MINUTE DISPONIBLES :
{products_context}

Si tu ne reconnais pas le produit, demande poliment une meilleure photo.

RÉPONSE (3-4 phrases, ton professionnel et chaleureux) :"""

        placeholder.markdown("📦 *Mina identifie le produit...*")
        
        # Générer avec image + streaming
        response = model.generate_content([prompt, image], stream=True)
        
        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                placeholder.markdown(f"📦 **Mina :** {full_response}")
        
        return full_response
        
    except Exception as e:
        return f"Erreur d'identification: {str(e)[:80]}"
# APPLICATION BODY TOUCH
# =============================================================================

def main():
    st.set_page_config(
        page_title="Body Touch - Mina",
        page_icon="💆",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Injecter CSS
    st.markdown(BODY_TOUCH_CSS, unsafe_allow_html=True)
    
    # Session state - incluant l'HISTORIQUE DE CONVERSATION
    if "response" not in st.session_state:
        st.session_state.response = None
    if "question" not in st.session_state:
        st.session_state.question = None
    if "audio_response" not in st.session_state:
        st.session_state.audio_response = None
    if "audio_key" not in st.session_state:
        st.session_state.audio_key = str(uuid.uuid4())
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "conversation_mode" not in st.session_state:
        st.session_state.conversation_mode = False
    if "continue_listening" not in st.session_state:
        st.session_state.continue_listening = False
    if "turbo_mode" not in st.session_state:
        st.session_state.turbo_mode = False
    if "show_camera" not in st.session_state:
        st.session_state.show_camera = False
    if "skin_analysis" not in st.session_state:
        st.session_state.skin_analysis = None
    if "show_qr_scanner" not in st.session_state:
        st.session_state.show_qr_scanner = False
    if "qr_product" not in st.session_state:
        st.session_state.qr_product = None
    if "show_product_scanner" not in st.session_state:
        st.session_state.show_product_scanner = False
    if "product_scan_result" not in st.session_state:
        st.session_state.product_scan_result = None
    if "product_scan_question" not in st.session_state:
        st.session_state.product_scan_question = "C'est quoi ce produit ?"
    # ===== PRODUCT VISION V2: Nouveaux états =====
    if "pending_product_match" not in st.session_state:
        st.session_state.pending_product_match = None  # ProductMatch en attente de confirmation
    if "last_confirmed_product" not in st.session_state:
        st.session_state.last_confirmed_product = None  # Produit confirmé pour contexte conversationnel
    if "scan_reprise_count" not in st.session_state:
        st.session_state.scan_reprise_count = 0  # Compteur de reprises photo
    # ===== AGENT MODE: Session et Client IDs =====
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())  # ID unique pour cette session
    if "client_id" not in st.session_state:
        st.session_state.client_id = None  # Sera détecté par detect_client_id()
    # ===================
    # HEADER / LOGO
    # ===================
    st.markdown("""
    <div class="logo-container">
        <div class="logo-text">✨ MINA</div>
        <div class="logo-subtitle">VOTRE ASSISTANTE BODY MINUTE</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===================
    # BOUTON BODY TOUCH
    # ===================
    st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Toggle Mode Conversation
        conversation_mode = st.checkbox(
            "🔄 Mode Conversation Continue",
            key="conversation_mode_toggle",
            value=st.session_state.conversation_mode,
            help="Activer pour converser sans re-cliquer"
        )
        st.session_state.conversation_mode = conversation_mode
        
        # Toggle Mode Turbo (skip TTS)
        turbo_mode = st.checkbox(
            "⚡ Mode Turbo (texte seul)",
            key="turbo_mode_toggle",
            value=st.session_state.turbo_mode,
            help="Réponse instantanée sans audio"
        )
        st.session_state.turbo_mode = turbo_mode
        
        # Toggle Mode Temps Réel (Gemini Live)
        try:
            from backend.feature_flags import is_realtime_enabled
            realtime_available = is_realtime_enabled()
        except:
            realtime_available = False
        
        if realtime_available:
            realtime_mode = st.checkbox(
                "🔴 Mode Temps Réel (bêta)",
                key="realtime_mode_toggle",
                value=st.session_state.get("realtime_mode", False),
                help="Conversation en streaming - latence ultra-faible"
            )
            st.session_state.realtime_mode = realtime_mode
        else:
            st.session_state.realtime_mode = False
        
        # Bouton Diagnostic Photo
        if st.checkbox("📷 Diagnostic Peau", key="skin_diag_check", label_visibility="visible"):
            st.session_state.show_camera = True
            st.session_state.skin_analysis = None
        
        # Checkbox QR Scanner (ancien)
        # if st.checkbox("📱 Scanner QR", key="qr_scan_check", label_visibility="visible"):
        #     st.session_state.show_qr_scanner = True
        
        # NOUVEAU: Scanner Photo Produit
        if st.checkbox("📦 Scanner un Produit", key="product_scan_check", label_visibility="visible"):
            st.session_state.show_product_scanner = True
            st.session_state.product_scan_result = None
        
        if st.session_state.get("realtime_mode", False):
            st.markdown("""
            <div style="text-align: center;">
                <p style="color: #e91e63; margin-bottom: 1rem;">🔴 Mode Temps Réel - Latence ultra-faible !</p>
            </div>
            """, unsafe_allow_html=True)
        elif st.session_state.turbo_mode:
            st.markdown("""
            <div style="text-align: center;">
                <p style="color: #FF9800; margin-bottom: 1rem;">⚡ Mode Turbo - Réponse texte instantanée !</p>
            </div>
            """, unsafe_allow_html=True)
        elif st.session_state.conversation_mode:
            st.markdown("""
            <div style="text-align: center;">
                <p style="color: #4CAF50; margin-bottom: 1rem;">🎙️ Mode conversation actif - Parlez librement !</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center;">
                <p style="color: #b0b0b0; margin-bottom: 1rem;">🎙️ Appuyez et parlez</p>
            </div>
            """, unsafe_allow_html=True)
        
        # ===== MODE TEMPS RÉEL OU CLASSIQUE =====
        if st.session_state.get("realtime_mode", False):
            # Mode Temps Réel - Utiliser le composant realtime_voice_chat
            try:
                from app.components.realtime_audio import realtime_voice_chat
                
                st.markdown("""
                <div style="text-align: center; padding: 0.5rem; background: rgba(233,30,99,0.1); border-radius: 12px; margin-bottom: 1rem;">
                    <p style="color: #e91e63; font-size: 0.9rem;">⚡ Latence ultra-faible activée</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Composant realtime
                realtime_voice_chat(height=300)
                audio_bytes = None  # Désactiver le flow classique
                
            except Exception as e:
                # Fallback vers mode classique si erreur
                print(f"⚠️ [Realtime] Fallback classique: {e}")
                st.warning("Mode temps réel indisponible, fallback classique activé")
                st.session_state.realtime_mode = False
                audio_bytes = audio_recorder(
                    text="",
                    recording_color=ROSE_FUCHSIA,
                    neutral_color=GRIS_CLAIR,
                    icon_name="microphone",
                    icon_size="3x",
                    pause_threshold=0.9,
                    sample_rate=48000
                )
        else:
            # Mode Classique - Audio Recorder standard
            audio_bytes = audio_recorder(
                text="",
                recording_color=ROSE_FUCHSIA,
                neutral_color=GRIS_CLAIR,
                icon_name="microphone",
                icon_size="3x",
                pause_threshold=0.9 if not st.session_state.conversation_mode else 1.2,
                sample_rate=48000
            )
    
    # ===================
    # DIAGNOSTIC PHOTO (Caméra)
    # ===================
    if st.session_state.show_camera:
        with st.container():
            st.markdown("""
            <div style="text-align: center; padding: 1rem; background: rgba(233,30,99,0.1); border-radius: 12px; margin: 1rem 0;">
                <p style="color: #e91e63; font-weight: 500;">📸 Prenez une photo de votre peau</p>
                <p style="color: #888; font-size: 0.85rem;">⚠️ Conseil beauté uniquement, pas d'avis médical</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Capture caméra
            photo = st.camera_input("", key="skin_camera", label_visibility="collapsed")
            
            if photo is not None:
                # Photo prise ! Traitement immédiat
                t_start = time.time()
                
                with st.spinner("🔍 Mina analyse ta peau..."):
                    # Placeholder pour le diagnostic
                    diag_placeholder = st.empty()
                    diag_placeholder.markdown("🔍 *Analyse en cours...*")
                    
                    # Appeler la fonction d'analyse
                    analysis_result = analyze_skin_photo(photo.getvalue(), diag_placeholder)
                    
                    # Sauvegarder le résultat
                    st.session_state.skin_analysis = analysis_result
                    st.session_state.question = "Diagnostic peau"
                    st.session_state.response = analysis_result
                    
                    # Ajouter à l'historique
                    st.session_state.conversation_history.append({
                        "question": "📷 Diagnostic peau",
                        "response": analysis_result,
                        "timestamp": time.strftime("%H:%M")
                    })
                    
                    # TTS si pas en mode turbo
                    if not st.session_state.turbo_mode:
                        audio_response = text_to_speech(analysis_result)
                        if audio_response:
                            st.session_state.audio_response = audio_response
                            st.session_state.audio_key = str(uuid.uuid4())
                    
                    t_total = time.time() - t_start
                    print(f"⏱️ [DIAGNOSTIC PHOTO] {t_total:.2f}s")
                
                # Fermer la caméra automatiquement
                st.session_state.show_camera = False
                st.rerun()
            
            # Bouton pour annuler
            if st.button("❌ Annuler", key="cancel_camera"):
                st.session_state.show_camera = False
                st.rerun()
    
    # Afficher le résultat du diagnostic si disponible
    if st.session_state.skin_analysis and not st.session_state.show_camera:
        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.success(f"💆 **Diagnostic Mina :**\n\n{st.session_state.skin_analysis}")
        
        # === PHASE 4: AFFICHAGE CARTES PRODUITS RECOMMANDÉS ===
        product_cards_html = get_product_cards_for_response(st.session_state.skin_analysis, max_cards=2)
        if product_cards_html:
            st.markdown(product_cards_html, unsafe_allow_html=True)
        
        # Effacer après affichage pour ne pas persister
        if st.button("✓ Compris", key="clear_diag"):
            st.session_state.skin_analysis = None
            st.rerun()
    
    # ===================
    # SCANNER PRODUIT PHOTO V2 (avec confirmation)
    # ===================
    if st.session_state.show_product_scanner:
        with st.container():
            st.markdown("""
            <div style="text-align: center; padding: 1rem; background: rgba(233,30,99,0.1); border-radius: 12px; margin: 1rem 0;">
                <p style="color: #e91e63; font-weight: 600; font-size: 1.1rem;">📦 Scanner un Produit</p>
                <p style="color: #888; font-size: 0.9rem;">Montrez le produit à Mina, posez votre question dans n'importe quelle langue !</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Input pour la question (optionnel, multilingue)
            user_question = st.text_input(
                "💬 Votre question (en français, arabe, anglais...)",
                value=st.session_state.product_scan_question,
                placeholder="C'est quoi ce produit ? / What is this? / ما هذا؟",
                key="product_question_input"
            )
            st.session_state.product_scan_question = user_question
            
            # Capture caméra pour le produit
            product_photo = st.camera_input("📸 Prenez en photo le produit", key="product_scanner_camera", label_visibility="collapsed")
            
            if product_photo is not None:
                t_start = time.time()
                image_bytes = product_photo.getvalue()
                
                with st.spinner("📦 Mina identifie le produit..."):
                    # ===== PRODUCT VISION V2: Nouvelle identification =====
                    try:
                        match = identify_product(image_bytes)
                        user_lang = detect_language(user_question)
                        
                        # Logger la tentative
                        log_scan_attempt(
                            match=match,
                            user_question=user_question,
                            user_language=user_lang,
                            reprise_count=st.session_state.scan_reprise_count,
                            save_failed_image=(match.status in ("AUCUN_MATCH", "ERROR")),
                            image_bytes=image_bytes
                        )
                        
                        t_total = time.time() - t_start
                        print(f"⏱️ [PRODUCT SCAN V2] {t_total:.2f}s - Status: {match.status} - Confidence: {match.confidence:.2f}")
                        
                        # Sauvegarder le match en attente de confirmation
                        st.session_state.pending_product_match = match
                        st.session_state.show_product_scanner = False
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"🔌 Erreur technique: {str(e)[:80]}")
                        print(f"❌ [PRODUCT SCAN] Exception: {e}")
            
            # Bouton pour annuler
            if st.button("❌ Annuler", key="cancel_product_scanner"):
                st.session_state.show_product_scanner = False
                st.session_state.scan_reprise_count = 0
                st.rerun()
    
    # ===================
    # CONFIRMATION PRODUIT V2
    # ===================
    if st.session_state.pending_product_match and not st.session_state.show_product_scanner:
        match = st.session_state.pending_product_match
        
        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        
        # Cas 1: Produit trouvé avec confiance suffisante
        if match.status == "FOUND" and match.confidence >= CONFIDENCE_THRESHOLD and match.product_data:
            product = match.product_data
            
            # Afficher la carte produit pour confirmation
            st.markdown(f"""
            <div style="background: #fff; border: 2px solid #e91e63; border-radius: 12px; padding: 1rem; text-align: center; margin: 1rem 0;">
                <img src="{product.get('image_url', '')}" style="max-width: 150px; max-height: 180px; border-radius: 8px; margin-bottom: 10px;" />
                <h3 style="color: #333; margin: 0.5rem 0;">{product.get('product_name', 'Produit')}</h3>
                <p style="color: #e91e63; font-size: 1.2rem; font-weight: bold;">{product.get('price_eur', '')} €</p>
                <p style="color: #666; font-size: 0.9rem;">Confiance: {match.confidence:.0%}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info(f"🤔 **Est-ce bien ce produit ?**")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Oui, c'est ça", key="confirm_product_yes", use_container_width=True):
                    # Confirmer et générer l'explication
                    st.session_state.last_confirmed_product = product
                    user_lang = detect_language(st.session_state.product_scan_question)
                    
                    explanation = generate_product_explanation(
                        match=match,
                        user_question=st.session_state.product_scan_question,
                        target_language=user_lang
                    )
                    
                    st.session_state.product_scan_result = explanation
                    st.session_state.question = f"📦 {st.session_state.product_scan_question}"
                    st.session_state.response = explanation
                    
                    # Log confirmation
                    log_scan_attempt(
                        match=match,
                        user_question=st.session_state.product_scan_question,
                        user_language=user_lang,
                        confirmed=True
                    )
                    
                    # TTS MULTILINGUE - Voix native selon langue détectée
                    if not st.session_state.turbo_mode:
                        audio_response = text_to_speech(explanation, language=user_lang)
                        if audio_response:
                            st.session_state.audio_response = audio_response
                            st.session_state.audio_key = str(uuid.uuid4())
                    
                    st.session_state.pending_product_match = None
                    st.session_state.scan_reprise_count = 0
                    st.rerun()
                    
            with col2:
                if st.button("❌ Non, autre produit", key="confirm_product_no", use_container_width=True):
                    # Log refus
                    log_scan_attempt(
                        match=match,
                        user_question=st.session_state.product_scan_question,
                        confirmed=False
                    )
                    st.session_state.pending_product_match = None
                    st.session_state.scan_reprise_count += 1
                    st.session_state.show_product_scanner = True  # Réouvrir la caméra
                    st.rerun()
        
        # Cas 2: Aucun match ou confiance insuffisante
        elif match.status == "AUCUN_MATCH" or (match.status == "FOUND" and match.confidence < CONFIDENCE_THRESHOLD):
            st.warning(f"""🤔 **Je n'arrive pas à identifier ce produit avec certitude.**
            
*Raison: {match.reason}*

Peux-tu reprendre une photo plus nette ou me dire le nom du produit ?""")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📸 Nouvelle photo", key="retry_photo", use_container_width=True):
                    st.session_state.pending_product_match = None
                    st.session_state.scan_reprise_count += 1
                    st.session_state.show_product_scanner = True
                    st.rerun()
            with col2:
                if st.button("🎤 Demander vocalement", key="fallback_vocal", use_container_width=True):
                    st.session_state.pending_product_match = None
                    st.session_state.show_product_scanner = False
                    st.info("👆 Utilise le micro pour me dire le nom du produit !")
                    st.rerun()
        
        # Cas 3: Plusieurs produits détectés
        elif match.status == "MULTIPLE":
            st.info("""📦 **Je vois plusieurs produits sur la photo !**
            
Peux-tu me montrer un seul produit à la fois ?""")
            
            if st.button("📸 Reprendre la photo", key="retry_single", use_container_width=True):
                st.session_state.pending_product_match = None
                st.session_state.show_product_scanner = True
                st.rerun()
        
        # Cas 4: Erreur technique
        elif match.status == "ERROR":
            st.error(f"""🔌 **Désolée, je n'arrive pas à analyser l'image pour le moment.**
            
*{match.reason}*

Peux-tu me dire le nom du produit ?""")
            
            if st.button("✓ OK", key="dismiss_error", use_container_width=True):
                st.session_state.pending_product_match = None
                st.rerun()
    
    # Afficher le résultat du scan produit si disponible (après confirmation)
    if st.session_state.product_scan_result and not st.session_state.show_product_scanner and not st.session_state.pending_product_match:
        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.success(f"📦 **Mina :**\n\n{st.session_state.product_scan_result}")
        
        # Afficher la carte produit si disponible
        if st.session_state.last_confirmed_product:
            product = st.session_state.last_confirmed_product
            st.markdown(f"""
            <div style="display: inline-flex; margin: 10px 0;">
                <div style="width: 150px; border: 1px solid #e91e63; border-radius: 10px; padding: 10px; background: #fff; text-align: center;">
                    <img src="{product.get('image_url', '')}" style="width: 100px; height: 120px; object-fit: contain; border-radius: 5px;" />
                    <div style="margin-top: 8px; font-size: 13px; font-weight: 600; color: #333;">{product.get('product_name', '')}</div>
                    <div style="color: #e91e63; font-weight: bold; font-size: 14px; margin: 5px 0;">{product.get('price_eur', '')} €</div>
                    <a href="{product.get('product_url', '#')}" target="_blank" style="display: inline-block; background: #e91e63; color: #fff; padding: 8px 16px; border-radius: 20px; text-decoration: none; font-size: 12px;">VOIR</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Effacer après affichage
        if st.button("✓ Compris", key="clear_product_scan"):
            st.session_state.product_scan_result = None
            st.rerun()
    
    # ===================
    # QR CODE SCANNER (legacy)
    if st.session_state.show_qr_scanner:
        with st.container():
            st.markdown("""
            <div style="text-align: center; padding: 1rem; background: rgba(76,175,80,0.1); border-radius: 12px; margin: 1rem 0;">
                <p style="color: #4CAF50; font-weight: 500;">📱 Scannez le QR code du produit</p>
                <p style="color: #888; font-size: 0.85rem;">Mina vous explique le produit instantanément</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Capture caméra pour QR
            qr_photo = st.camera_input("", key="qr_camera", label_visibility="collapsed")
            
            if qr_photo is not None:
                with st.spinner("📱 Lecture du QR code..."):
                    try:
                        # Utiliser pyzbar pour décoder le QR (nécessite installation)
                        from PIL import Image
                        import io
                        
                        image = Image.open(io.BytesIO(qr_photo.getvalue()))
                        
                        # Essayer de décoder le QR
                        try:
                            from pyzbar.pyzbar import decode
                            qr_codes = decode(image)
                            
                            if qr_codes:
                                qr_data = qr_codes[0].data.decode('utf-8')
                                print(f"📱 [QR] Code scanné: {qr_data}")
                                
                                # Rechercher le produit dans Qdrant
                                query_vector = list(get_embedding_cached(qr_data))
                                client = get_qdrant_client()
                                results = client.query_points(
                                    collection_name=COLLECTION_PRODUCTS,
                                    query=query_vector,
                                    limit=1,
                                    with_payload=True
                                )
                                
                                if results.points:
                                    product_info = results.points[0].payload.get("text", "")[:500]
                                    st.session_state.qr_product = product_info
                                    st.session_state.question = f"Produit: {qr_data}"
                                    st.session_state.response = product_info
                                else:
                                    st.session_state.qr_product = f"Produit '{qr_data}' non trouvé dans la base."
                            else:
                                st.session_state.qr_product = "Aucun QR code détecté. Réessayez."
                        except ImportError:
                            # Si pyzbar n'est pas installé, utiliser le texte de l'image comme recherche
                            st.session_state.qr_product = "Module QR non installé. Utilisez le micro pour demander un produit."
                    except Exception as e:
                        st.session_state.qr_product = f"Erreur: {e}"
                
                st.session_state.show_qr_scanner = False
                st.rerun()
            
            if st.button("❌ Annuler", key="cancel_qr"):
                st.session_state.show_qr_scanner = False
                st.rerun()
    
    # Afficher le résultat du QR si disponible
    if st.session_state.qr_product:
        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.info(f"📱 **Produit scanné :**\n\n{st.session_state.qr_product}")
        if st.button("✓ OK", key="clear_qr"):
            st.session_state.qr_product = None
            st.rerun()
    # ===================
    # TRAITEMENT AUDIO
    # ===================
    if audio_bytes:
        # Protection contre le retraitement: hash de l'audio
        import hashlib
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        
        # Initialiser le dernier hash traité
        if "last_audio_hash" not in st.session_state:
            st.session_state.last_audio_hash = None
        
        # Ne traiter que si c'est un NOUVEL audio
        if audio_hash != st.session_state.last_audio_hash:
            st.session_state.last_audio_hash = audio_hash
            
            # ===== TIMING LOGS V1.5 =====
            t_start = time.time()
        
            with st.spinner("🎧 Écoute en cours..."):
                # 1. Speech-to-Text
                t_stt_start = time.time()
                question = transcribe_audio(audio_bytes)
                t_stt = time.time() - t_stt_start
                print(f"\n⏱️ [STT] {t_stt:.2f}s")
                
                if question:
                    st.session_state.question = question
                    
                    # Afficher transcription utilisateur
                    st.info(f"📝 **Toi :** {question}")
                    
                    # Placeholder pour affichage streaming
                    response_placeholder = st.empty()
                    response_placeholder.markdown("💭 *Mina réfléchit...*")
                    
                    # 2. Recherche et réponse (Mode Agent ou RAG classique)
                    try:
                        from backend.feature_flags import is_agent_enabled
                        use_agent = is_agent_enabled()
                    except:
                        use_agent = False
                    
                    if use_agent:
                        # ===== MODE AGENT REACT =====
                        try:
                            from backend.agent import get_orchestrator
                            
                            session_id = st.session_state.session_id
                            client_id = detect_client_id()
                            
                            orchestrator = get_orchestrator()
                            agent_result = orchestrator.process(
                                user_input=question,
                                session_id=session_id,
                                client_id=client_id
                            )
                            
                            response = agent_result.response
                            
                            # Log outils appelés
                            if agent_result.tools_called:
                                tools_str = ", ".join([t["tool"] for t in agent_result.tools_called])
                                print(f"🔧 [Agent] Outils: {tools_str}")
                            print(f"⏱️ [Agent] {agent_result.processing_time_ms}ms, {agent_result.iterations} iter")
                            
                            # Stocker timing
                            response_placeholder.t_rag = 0
                            response_placeholder.t_llm = agent_result.processing_time_ms / 1000
                            
                        except Exception as e:
                            print(f"⚠️ [Agent] Erreur, fallback RAG: {e}")
                            response = search_mina_streaming(question, response_placeholder)
                    else:
                        # ===== MODE RAG CLASSIQUE =====
                        response = search_mina_streaming(question, response_placeholder)
                    
                    st.session_state.response = response
                    
                    # Récupérer timing AVANT de nettoyer le placeholder
                    t_rag = getattr(response_placeholder, 't_rag', 0)
                    t_llm = getattr(response_placeholder, 't_llm', 0)
                    
                    # Nettoyer le placeholder pour éviter conflit DOM
                    response_placeholder.empty()
                    
                    # Afficher réponse texte (composant stable)
                    st.success(f"💬 **Mina :** {response}")
                    
                    # === PHASE 4: AFFICHAGE CARTES PRODUITS ===
                    product_cards_html = get_product_cards_for_response(response, max_cards=2)
                    if product_cards_html:
                        # Container isolé pour les cartes produits
                        with st.container():
                            st.markdown(product_cards_html, unsafe_allow_html=True)
                    
                    # Ajouter à l'historique
                    st.session_state.conversation_history.append({
                        "question": question,
                        "response": response,
                        "timestamp": time.strftime("%H:%M")
                    })
                    
                    # 3. Text-to-Speech (skip si Mode Turbo)
                    if st.session_state.turbo_mode:
                        t_tts = 0
                        print("⚡ [TURBO] TTS skipped - Mode texte seul")
                    else:
                        with st.spinner("🗣️ Je prépare ma voix..."):
                            t_tts_start = time.time()
                            audio_response = text_to_speech(response)
                            t_tts = time.time() - t_tts_start
                        print(f"⏱️ [TTS] {t_tts:.2f}s")
                        
                        if audio_response:
                            st.session_state.audio_response = audio_response
                            st.session_state.audio_key = str(uuid.uuid4())
                    
                    # TOTAL
                    t_total = time.time() - t_start
                    # Sécurité: s'assurer que les valeurs sont des floats
                    t_rag = float(t_rag) if isinstance(t_rag, (int, float)) else 0.0
                    t_llm = float(t_llm) if isinstance(t_llm, (int, float)) else 0.0
                    t_tts = float(t_tts) if isinstance(t_tts, (int, float)) else 0.0
                    print(f"⏱️ [TOTAL] {t_total:.2f}s")
                    print(f"   Détail: STT={t_stt:.1f}s | RAG={t_rag:.1f}s | LLM={t_llm:.1f}s | TTS={t_tts:.1f}s")
                    
                    # Logger interaction pour benchmark
                    log_interaction(
                        question,
                        response,
                        {"stt": t_stt, "rag": t_rag, "llm": t_llm, "tts": t_tts, "total": t_total}
                    )
                    
                    # === MODE CONVERSATION CONTINUE ===
                    # Vérifier si fin de conversation
                    question_lower = question.lower()
                    end_conversation = any(keyword in question_lower for keyword in END_CONVERSATION_KEYWORDS)
                    
                    if end_conversation:
                        st.session_state.conversation_mode = False
                        st.session_state.continue_listening = False
                        print("👋 [CONVERSATION] Fin de conversation détectée")
                    elif st.session_state.conversation_mode:
                        # Continuer à écouter après un délai
                        st.session_state.continue_listening = True
                        print("🔄 [CONVERSATION] Re-écoute automatique activée")
                        
                else:
                    st.warning("Je n'ai pas compris. Pourriez-vous répéter ?")
    
    # ===================
    # AFFICHAGE RÉPONSE
    # ===================
    if st.session_state.question and st.session_state.response:
        st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)
        
        # Question posée
        st.markdown(f"""
        <div class="response-container">
            <div class="question-text">"{st.session_state.question}"</div>
            <div class="response-title">💆 Mina répond :</div>
            <div class="response-text">{st.session_state.response}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Lecture audio si disponible - AUTOPLAY
        if st.session_state.audio_response:
            # Log TTFS (Time To First Sound)
            print(f"\n🔊 [TTFS] Audio prêt à jouer - latence totale jusqu'au son")
            st.markdown("""
            <div style="text-align: center; margin-top: 1rem;">
                <p style="color: #b0b0b0;">🔊 Mina parle...</p>
            </div>
            """, unsafe_allow_html=True)
            # Autoplay pour que Mina parle automatiquement
            st.audio(st.session_state.audio_response, format="audio/mp3", autoplay=True)
            
            # Mode conversation continue - Afficher message d'invitation
            if st.session_state.conversation_mode and st.session_state.continue_listening:
                st.markdown("""
                <div style="text-align: center; margin-top: 1rem;">
                    <p style="color: #4CAF50; font-size: 1.1rem;">🎤 Continue à parler quand tu veux...</p>
                    <p style="color: #888; font-size: 0.9rem;">(Dis "au revoir" pour terminer)</p>
                </div>
                """, unsafe_allow_html=True)
    
    # ===================
    # HISTORIQUE CONVERSATION
    # ===================
    if len(st.session_state.conversation_history) > 1:
        with st.expander("📜 Historique de la conversation", expanded=False):
            for i, exchange in enumerate(reversed(st.session_state.conversation_history[:-1])):
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.05); padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;">
                    <div style="color: #888; font-size: 0.75rem;">{exchange['timestamp']}</div>
                    <div style="color: #e91e63; font-weight: 500;">📝 {exchange['question']}</div>
                    <div style="color: #fff; margin-top: 0.3rem;">💬 {exchange['response'][:100]}{'...' if len(exchange['response']) > 100 else ''}</div>
                </div>
                """, unsafe_allow_html=True)
                if i >= 4:  # Limiter à 5 derniers échanges
                    break
    
    # ===================
    # FOOTER
    # ===================
    st.markdown("<div style='height: 3rem'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8rem;">
        Body Touch by Body Minute • Propulsé par Mina AI
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
