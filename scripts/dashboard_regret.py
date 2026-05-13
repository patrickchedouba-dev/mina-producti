#!/usr/bin/env python3
"""
Dashboard Regret-Zero - Visualisation temps réel.

Usage:
    streamlit run scripts/dashboard_regret.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta


def load_decisions(institut_id: str = None, days: int = 30):
    """Charge les décisions depuis PostgreSQL."""
    try:
        from backend.memory import get_memory_system
        memory = get_memory_system()
        
        if not hasattr(memory, '_postgres') or not memory._postgres:
            return []
        
        query = """
            SELECT * FROM counterfactual_decisions
            WHERE timestamp > NOW() - INTERVAL '%s days'
        """
        params = [days]
        
        if institut_id:
            query += " AND institut_id = %s"
            params.append(institut_id)
        
        query += " ORDER BY timestamp DESC LIMIT 500"
        
        result = memory._postgres.fetch_all(query, params)
        return [dict(row) for row in result] if result else []
    except Exception as e:
        st.warning(f"⚠️ Erreur chargement: {e}")
        return []


def main():
    st.set_page_config(
        page_title="Mina Regret-Zero Dashboard",
        page_icon="🧠",
        layout="wide"
    )
    
    st.title("🧠 Mina Regret-Zero Dashboard")
    st.markdown("---")
    
    # Sidebar - Filters
    with st.sidebar:
        st.header("🔍 Filtres")
        institut_id = st.text_input("Institut ID", value="laurence_01")
        days = st.slider("Période (jours)", 7, 90, 30)
        
        st.markdown("---")
        st.header("⚙️ Actions")
        
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Load data
    decisions = load_decisions(institut_id, days)
    
    if not decisions:
        st.info("📋 Aucune donnée disponible. Activez le shadow mode pour collecter des données.")
        
        st.code("""
# Dans .env
MINA_COUNTERFACTUAL_ENABLED=true
        """)
        return
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(decisions)
    with_outcome = sum(1 for d in decisions if d.get("outcome_7d"))
    regrets = [d.get("regret_score", 0) for d in decisions if d.get("regret_score") is not None]
    avg_regret = sum(regrets) / len(regrets) if regrets else 0
    optimal_rate = sum(1 for r in regrets if r <= 0) / len(regrets) * 100 if regrets else 0
    
    col1.metric("📋 Décisions", total)
    col2.metric("📊 Avec Outcome", with_outcome)
    col3.metric("📉 Regret Moyen", f"{avg_regret:.3f}")
    col4.metric("✅ Taux Optimal", f"{optimal_rate:.1f}%")
    
    st.markdown("---")
    
    # Charts
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📈 Évolution Regret")
        
        # Group by day
        regret_by_day = {}
        for d in decisions:
            if d.get("regret_score") is not None:
                date = d.get("timestamp", "")[:10]
                if date:
                    if date not in regret_by_day:
                        regret_by_day[date] = []
                    regret_by_day[date].append(d["regret_score"])
        
        if regret_by_day:
            chart_data = {
                "Date": list(regret_by_day.keys()),
                "Regret Moyen": [sum(v)/len(v) for v in regret_by_day.values()]
            }
            df = pd.DataFrame(chart_data)
            st.line_chart(df.set_index("Date"))
        else:
            st.info("Pas assez de données pour le graphique")
    
    with col_right:
        st.subheader("🎯 Shadow Paths Distribution")
        
        path_counts = {"cheaper": 0, "premium": 0, "minimal": 0, "safe": 0}
        for d in decisions:
            shadows = json.loads(d.get("shadow_paths", "[]")) if d.get("shadow_paths") else []
            for s in shadows:
                ptype = s.get("path_type", "")
                if ptype in path_counts:
                    path_counts[ptype] += 1
        
        df = pd.DataFrame(list(path_counts.items()), columns=["Path Type", "Count"])
        st.bar_chart(df.set_index("Path Type"))
    
    st.markdown("---")
    
    # Insights
    st.subheader("💡 Insights")
    
    try:
        from backend.agent.regret_calculator import get_regret_calculator
        calc = get_regret_calculator()
        insights = calc.get_institut_insights(institut_id, days)
        
        if insights.get("recommendations"):
            for rec in insights["recommendations"]:
                st.success(f"💡 {rec}")
        
        if insights.get("top_improvements"):
            st.markdown("**Top améliorations suggérées:**")
            for ptype, count in insights["top_improvements"]:
                st.markdown(f"- **{ptype}**: {count} cas où cette alternative aurait été meilleure")
    except Exception as e:
        st.warning(f"Insights non disponibles: {e}")
    
    st.markdown("---")
    
    # Recent decisions table
    st.subheader("📋 Décisions Récentes")
    
    table_data = []
    for d in decisions[:20]:
        table_data.append({
            "Date": d.get("timestamp", "")[:16],
            "Input": d.get("user_input", "")[:50] + "...",
            "Regret": f"{d.get('regret_score', 'N/A')}",
            "Outcome 7d": "✅" if d.get("outcome_7d") else "⏳",
            "Outcome 30d": "✅" if d.get("outcome_30d") else "⏳"
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
    
    # Policy section
    st.markdown("---")
    st.subheader("📜 Policy Active")
    
    try:
        from backend.agent.policy_updater import get_policy_updater
        updater = get_policy_updater()
        policy = updater.get_active_policy(institut_id)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Temperature LLM", policy.get("temperature", 0.3))
        
        with col2:
            routing = policy.get("routing", {})
            st.json(routing)
        
        if policy.get("updated_at"):
            st.caption(f"Dernière mise à jour: {policy['updated_at']}")
    except Exception as e:
        st.info(f"Policy par défaut (aucun ajustement)")


if __name__ == "__main__":
    main()
