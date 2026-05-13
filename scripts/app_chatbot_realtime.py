#!/usr/bin/env python3
"""
Mina Realtime - Version temps réel avec Gemini Live API.
Ce script est une version modifiée de app_chatbot.py pour le mode temps réel.

Usage:
    MINA_REALTIME_ENABLED=true streamlit run scripts/app_chatbot_realtime.py
"""

import os
import sys
import asyncio

# Configuration du path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# Vérifier le feature flag
from backend.feature_flags import is_realtime_enabled

if not is_realtime_enabled():
    st.warning("⚠️ Mode temps réel désactivé. Définissez MINA_REALTIME_ENABLED=true")
    st.info("Utilisez `scripts/app_chatbot.py` pour le mode standard.")
    st.stop()

# Imports temps réel
from app.components.realtime_audio import realtime_voice_chat, create_realtime_page
from utils.qdrant_utils import get_qdrant_client
from utils.embedding_utils import get_embedding
from backend.realtime_client import create_rag_provider


# =============================================================================
# CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Mina Realtime - Body Minute",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    .main-title {
        text-align: center;
        color: #e91e63;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        text-align: center;
        color: #888;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    .mode-badge {
        display: inline-block;
        background: linear-gradient(90deg, #e91e63, #9c27b0);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .info-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Header
    st.markdown('<h1 class="main-title">🎙️ MINA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle"><span class="mode-badge">MODE TEMPS RÉEL</span></p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Parlez naturellement, Mina répond instantanément</p>', unsafe_allow_html=True)
    
    # Initialiser RAG provider
    @st.cache_resource
    def get_rag_provider():
        try:
            qdrant = get_qdrant_client()
            return create_rag_provider(qdrant, get_embedding)
        except Exception as e:
            st.warning(f"RAG non disponible: {e}")
            return None
    
    rag_provider = get_rag_provider()
    
    # Zone principale
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    
    # Composant audio temps réel
    realtime_voice_chat(rag_provider=rag_provider)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Instructions
    with st.expander("ℹ️ Comment ça marche ?"):
        st.markdown("""
        ### Mode Temps Réel avec Gemini Live
        
        1. **Appuyez sur le micro** 🎤 pour commencer à parler
        2. **Parlez naturellement** - pas besoin d'attendre
        3. **Mina répond en streaming** - la réponse commence immédiatement
        4. **Interrompez-la** en parlant - elle s'arrête et vous écoute
        
        ### Avantages
        - ⚡ Latence < 500ms vs 3-5s en mode classique
        - 🛑 Barge-in: vous pouvez couper la parole à Mina
        - 🎯 Contexte métier: Mina utilise toujours la base Body Minute
        """)
    
    # Fallback vers mode classique
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Passer en mode classique", use_container_width=True):
            st.switch_page("scripts/app_chatbot.py")
    
    # Footer
    st.markdown("""
    <div style="text-align: center; margin-top: 40px; color: #666; font-size: 0.8rem;">
        Mina Realtime v1.0 | Branche dev-realtime | Gemini Live API
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
