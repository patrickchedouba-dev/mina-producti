#!/usr/bin/env python3
"""
Mina Stats Dashboard - Tableau de bord analytics.

Affiche les statistiques d'utilisation de Mina:
- Questions les plus posées
- Produits les plus demandés
- Latences moyennes
- Pics d'utilisation

Usage:
    streamlit run scripts/mina_stats.py
"""

import json
import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# Configuration page
st.set_page_config(
    page_title="Mina Stats Dashboard",
    page_icon="📊",
    layout="wide"
)

# Chemin du fichier de logs
LOG_FILE = Path("/home/jupyter/mina_fichiers/mina-bêta/logs/benchmark_interactions.jsonl")


def load_interactions():
    """Charge les interactions depuis le fichier JSONL."""
    interactions = []
    if LOG_FILE.exists():
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    interactions.append(json.loads(line))
                except:
                    continue
    return interactions


def main():
    st.title("📊 Mina Stats Dashboard")
    st.markdown("*Tableau de bord temps réel des interactions Mina*")
    
    # Charger les données
    interactions = load_interactions()
    
    if not interactions:
        st.warning("Aucune interaction enregistrée. Utilisez Mina pour générer des données !")
        return
    
    # Métriques globales
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    total_interactions = len(interactions)
    avg_latency = sum(i.get('latencies', {}).get('total', 0) for i in interactions) / max(total_interactions, 1)
    avg_words = sum(i.get('word_count', 0) for i in interactions) / max(total_interactions, 1)
    
    # Calculer interactions des dernières 24h
    now = datetime.now()
    recent = [i for i in interactions if 'timestamp' in i and 
              (now - datetime.fromisoformat(i['timestamp'])) < timedelta(hours=24)]
    
    with col1:
        st.metric("📝 Total Interactions", total_interactions)
    with col2:
        st.metric("⏱️ Latence Moyenne", f"{avg_latency:.1f}s")
    with col3:
        st.metric("📏 Mots / Réponse", f"{avg_words:.0f}")
    with col4:
        st.metric("🕐 Dernières 24h", len(recent))
    
    st.markdown("---")
    
    # Deux colonnes pour les graphiques
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("❓ Questions les plus posées")
        questions = [i.get('question', '').lower()[:50] for i in interactions if i.get('question')]
        question_counts = Counter(questions).most_common(10)
        
        if question_counts:
            for q, count in question_counts:
                st.write(f"**{count}x** — {q}")
        else:
            st.info("Pas encore de données")
    
    with col_right:
        st.subheader("⏱️ Répartition Latence")
        latencies = {
            "STT": [],
            "RAG": [],
            "LLM": [],
            "TTS": []
        }
        for i in interactions:
            lat = i.get('latencies', {})
            if lat:
                for key in latencies:
                    val = lat.get(key.lower(), 0)
                    if val:
                        latencies[key].append(val)
        
        for key, values in latencies.items():
            if values:
                avg = sum(values) / len(values)
                st.write(f"**{key}**: {avg:.2f}s moyenne")
    
    st.markdown("---")
    
    # Historique des dernières interactions
    st.subheader("📜 Dernières Interactions")
    
    for interaction in reversed(interactions[-10:]):
        timestamp = interaction.get('timestamp', 'N/A')
        question = interaction.get('question', 'N/A')[:80]
        response = interaction.get('response', 'N/A')[:100]
        total_time = interaction.get('latencies', {}).get('total', 0)
        
        with st.expander(f"🕐 {timestamp[:16]} — {question}..."):
            st.write(f"**Question:** {interaction.get('question', 'N/A')}")
            st.write(f"**Réponse:** {interaction.get('response', 'N/A')}")
            st.write(f"**Latence totale:** {total_time:.2f}s")
    
    # Bouton de rafraîchissement
    st.markdown("---")
    if st.button("🔄 Rafraîchir"):
        st.rerun()


if __name__ == "__main__":
    main()
