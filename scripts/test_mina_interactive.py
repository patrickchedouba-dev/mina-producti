#!/usr/bin/env python3
"""
🧪 Test Mina Interactive - Mode Debug Pré-Pilote

Interface de test pour valider les réponses Mina avant déploiement.
Permet de poser des questions en texte et voir les sources Qdrant.

Usage:
    streamlit run scripts/test_mina_interactive.py
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Optional

# Configuration du path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Charger .env
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# Utilitaires centralisés (Phase 2 Refactoring)
from utils.qdrant_utils import get_qdrant_client as _get_qdrant_client_base
from utils.embedding_utils import get_embedding

# =============================================================================
# CONFIGURATION
# =============================================================================

COLLECTION_PRODUCTS = "bodyminute_docs"

# Couleurs Body Minute
BLEU_PROFOND = "#1a1a2e"
ROSE_FUCHSIA = "#e91e63"

CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    .stApp {{
        background: linear-gradient(135deg, {BLEU_PROFOND} 0%, #16213e 100%);
        font-family: 'Poppins', sans-serif;
    }}
    
    .source-box {{
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 3px solid {ROSE_FUCHSIA};
    }}
    
    .source-header {{
        color: {ROSE_FUCHSIA};
        font-weight: 600;
        font-size: 0.9rem;
    }}
    
    .source-text {{
        color: #ccc;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }}
    
    .response-box {{
        background: rgba(233, 30, 99, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(233, 30, 99, 0.3);
    }}
    
    .score-badge {{
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-right: 0.5rem;
    }}
</style>
"""


# =============================================================================
# CLIENTS
# =============================================================================

# Wrapper Streamlit pour le client Qdrant
@st.cache_resource
def get_qdrant_client():
    """Client Qdrant avec cache Streamlit."""
    return _get_qdrant_client_base()

# get_embedding importé depuis utils.embedding_utils


# =============================================================================
# RECHERCHE MINA AVEC DEBUG
# =============================================================================

def search_mina_debug(question: str) -> Dict:
    """
    Recherche dans Qdrant et génère une réponse.
    Retourne les sources et métadonnées pour debug.
    """
    result = {
        "question": question,
        "timestamp": datetime.now().isoformat(),
        "sources": [],
        "response": "",
        "error": None
    }
    
    try:
        client = get_qdrant_client()
        query_vector = get_embedding(question)
        
        # Recherche Qdrant
        results = client.query_points(
            collection_name=COLLECTION_PRODUCTS,
            query=query_vector,
            limit=5,  # Plus de sources pour debug
            with_payload=True
        )
        
        if not results.points:
            result["response"] = "Aucun résultat trouvé dans Qdrant."
            return result
        
        # Extraire les sources avec métadonnées complètes
        sources_for_prompt = []
        for i, hit in enumerate(results.points, 1):
            source = {
                "rank": i,
                "score": round(hit.score, 4),
                "doc_type": hit.payload.get("doc_type", "info"),
                "product_name": hit.payload.get("product_name"),
                "service_name": hit.payload.get("service_name"),
                "skin_type": hit.payload.get("skin_type"),
                "product_ref": hit.payload.get("product_ref"),
                "text": hit.payload.get("text", "")[:1500],
                "source_file": hit.payload.get("source_file", "")
            }
            result["sources"].append(source)
            
            # Format pour prompt LLM
            name = source["product_name"] or source["service_name"] or source["skin_type"] or "Info"
            ref = f" ({source['product_ref']})" if source["product_ref"] else ""
            sources_for_prompt.append(
                f"[SOURCE {i}] {source['doc_type'].upper()}: {name}{ref}\n{source['text']}"
            )
        
        formatted_sources = "\n\n---\n\n".join(sources_for_prompt[:3])
        
        # Générer avec LLM - prompt V5 TERMINOLOGIE STRICTE
        from google import genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash", generation_config={"temperature": 0.4})
        
        prompt = f"""Tu es Mina, conseillère beauté experte Body Minute.

DOCUMENTS BODY MINUTE :
{formatted_sources}

QUESTION : {question}

RÈGLES TERMINOLOGIQUES STRICTES :
1. DÉSHYDRATATION = manque d'EAU uniquement. Signes : "stries de déshydratation" (JAMAIS "vergetures"), squames, tiraillements. Actif phare : Acide Hyaluronique
2. PEAU SÈCHE = manque de LIPIDES (peau alipidique). C'est un TYPE de peau permanent, pas un état passager
3. Ne confonds JAMAIS ces deux notions : si on parle de déshydratation, ne mentionne PAS les lipides
4. Points rouges post-épilation → Huile Apaisante Après Épilation (Calendula)
5. Cite les NOMS EXACTS des produits et CHIFFRES des documents

TON : Professionnel, bienveillant, tutoiement élégant. 2-3 phrases max.

RÉPONSE :"""
        
        response = model.generate_content(prompt)
        result["response"] = response.text
        
    except Exception as e:
        result["error"] = str(e)
        result["response"] = f"Erreur: {e}"
    
    return result


# =============================================================================
# APPLICATION TEST
# =============================================================================

def main():
    st.set_page_config(
        page_title="🧪 Test Mina - Debug",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown(CSS, unsafe_allow_html=True)
    
    # Session state
    if "history" not in st.session_state:
        st.session_state.history = []
    
    # ===================
    # SIDEBAR - QUESTIONS PRÉDÉFINIES
    # ===================
    with st.sidebar:
        st.markdown("### 📋 Questions de test")
        
        test_questions = [
            "Quel sérum pour les peaux déshydratées ?",
            "Comment appliquer le contour des yeux ?",
            "Quelle crème pour les peaux sensibles ?",
            "C'est quoi le soin Hydratempo ?",
            "Quel produit contre les rides ?",
            "Comment utiliser le gommage visage ?",
            "Quel soin pour les peaux grasses ?",
            "Le sérum Vitamin C, c'est bien pour quoi ?",
            "Comment prendre soin de mes lèvres ?",
            "Quelle épilation pour les peaux sensibles ?",
        ]
        
        st.markdown("**Questions rapides :**")
        for q in test_questions[:5]:
            if st.button(q[:40] + "...", key=f"q_{hash(q)}"):
                st.session_state.test_question = q
        
        st.markdown("---")
        
        if st.button("🗑️ Effacer l'historique"):
            st.session_state.history = []
            st.rerun()
        
        if st.session_state.history:
            if st.button("📥 Exporter JSON"):
                export_data = {
                    "export_date": datetime.now().isoformat(),
                    "tests": st.session_state.history
                }
                st.download_button(
                    "💾 Télécharger",
                    json.dumps(export_data, indent=2, ensure_ascii=False),
                    "mina_test_results.json",
                    "application/json"
                )
    
    # ===================
    # HEADER
    # ===================
    st.markdown("# 🧪 Test Mina - Mode Debug")
    st.markdown("*Validation pré-pilote des réponses*")
    st.markdown("---")
    
    # ===================
    # INPUT QUESTION
    # ===================
    col1, col2 = st.columns([4, 1])
    
    with col1:
        question = st.text_input(
            "💬 Pose ta question à Mina :",
            value=st.session_state.get("test_question", ""),
            placeholder="Ex: Quel sérum pour les peaux déshydratées ?",
            key="main_input"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.button("🚀 Tester", type="primary", use_container_width=True)
    
    # Clear the preset question after using it
    if "test_question" in st.session_state:
        del st.session_state.test_question
    
    # ===================
    # TRAITEMENT
    # ===================
    if submit and question:
        with st.spinner("🔍 Recherche et génération..."):
            result = search_mina_debug(question)
            st.session_state.history.insert(0, result)
    
    # ===================
    # AFFICHAGE RÉSULTATS
    # ===================
    if st.session_state.history:
        for i, result in enumerate(st.session_state.history):
            with st.expander(
                f"📝 {result['question'][:60]}...", 
                expanded=(i == 0)
            ):
                # Réponse Mina
                st.markdown("### 💆 Réponse Mina")
                st.markdown(f"""
                <div class="response-box">
                    {result['response']}
                </div>
                """, unsafe_allow_html=True)
                
                # Bouton copier pour NotebookLM
                copy_text = f"Question: {result['question']}\n\nRéponse Mina: {result['response']}"
                st.code(copy_text, language=None)
                
                # Sources utilisées
                st.markdown("### 📚 Sources Qdrant utilisées")
                for src in result["sources"][:3]:
                    name = src["product_name"] or src["service_name"] or src["skin_type"] or "Info"
                    st.markdown(f"""
                    <div class="source-box">
                        <div class="source-header">
                            #{src['rank']} | Score: {src['score']} | {src['doc_type'].upper()}: {name}
                        </div>
                        <div class="source-text">
                            {src['text'][:500]}...
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
    
    # ===================
    # FOOTER STATS
    # ===================
    if st.session_state.history:
        st.markdown(f"**Tests effectués : {len(st.session_state.history)}**")


if __name__ == "__main__":
    main()
