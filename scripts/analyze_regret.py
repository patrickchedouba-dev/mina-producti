#!/usr/bin/env python3
"""
Analyze Regret - CLI pour analyser le regret par institut.

Usage:
    python scripts/analyze_regret.py --institut laurence_01
    python scripts/analyze_regret.py --all --days 30
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def analyze_institut(institut_id: str, days: int):
    """Analyse le regret pour un institut."""
    from backend.agent.regret_calculator import get_regret_calculator
    from backend.agent.policy_updater import get_policy_updater
    
    print(f"\n{'='*60}")
    print(f"📊 ANALYSE REGRET - {institut_id}")
    print(f"{'='*60}\n")
    
    # 1. Insights
    calc = get_regret_calculator()
    insights = calc.get_institut_insights(institut_id, days)
    
    if "error" in insights:
        print(f"❌ Erreur: {insights['error']}")
        return
    
    if insights.get("count", 0) == 0:
        print("⚠️ Pas assez de données")
        return
    
    print(f"📅 Période: {days} derniers jours")
    print(f"📋 Décisions totales: {insights.get('total_decisions', 0)}")
    print(f"📈 Avec outcome: {insights.get('with_outcome', 0)}")
    print()
    
    print("📊 MÉTRIQUES REGRET")
    print("-" * 40)
    print(f"  Regret moyen: {insights.get('avg_regret', 0):.3f}")
    print(f"  Taux optimal: {insights.get('optimal_rate', 0):.1f}%")
    print()
    
    if insights.get("top_improvements"):
        print("🎯 TOP AMÉLIORATIONS")
        print("-" * 40)
        for path_type, count in insights["top_improvements"]:
            print(f"  • {path_type}: {count} cas")
    print()
    
    if insights.get("recommendations"):
        print("💡 RECOMMANDATIONS")
        print("-" * 40)
        for rec in insights["recommendations"]:
            print(f"  → {rec}")
    print()
    
    # 2. Suggestions de policy
    updater = get_policy_updater()
    adjustments = updater.analyze_and_suggest(institut_id, insights)
    
    if adjustments:
        print("⚙️ AJUSTEMENTS SUGGÉRÉS")
        print("-" * 40)
        for adj in adjustments:
            conf = "🟢" if adj.confidence > 0.7 else "🟡" if adj.confidence > 0.5 else "🔴"
            print(f"  {conf} {adj.parameter}: {adj.old_value} → {adj.new_value}")
            print(f"     Raison: {adj.reason}")
            print(f"     Confidence: {adj.confidence:.0%}")
            print()
    
    # 3. Policy actuelle
    policy = updater.get_active_policy(institut_id)
    print("📜 POLICY ACTIVE")
    print("-" * 40)
    print(f"  Temperature: {policy.get('temperature', 0.3)}")
    print(f"  Routing: {json.dumps(policy.get('routing', {}), indent=4)}")
    if policy.get("updated_at"):
        print(f"  Mise à jour: {policy['updated_at']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Analyse Regret Mina")
    parser.add_argument("--institut", type=str, help="ID institut à analyser")
    parser.add_argument("--all", action="store_true", help="Analyser tous les instituts")
    parser.add_argument("--days", type=int, default=30, help="Période en jours")
    parser.add_argument("--apply", action="store_true", help="Appliquer les ajustements suggérés")
    args = parser.parse_args()
    
    if args.institut:
        analyze_institut(args.institut, args.days)
        
        if args.apply:
            from backend.agent.policy_updater import get_policy_updater
            updater = get_policy_updater()
            result = updater.apply_adjustments(args.institut, auto_apply=True)
            print(f"\n✅ Ajustements appliqués: {result.get('count', 0)}")
    
    elif args.all:
        # Lister tous les instituts
        try:
            from backend.memory import get_memory_system
            memory = get_memory_system()
            
            if hasattr(memory, '_postgres') and memory._postgres:
                result = memory._postgres.fetch_all("""
                    SELECT DISTINCT institut_id FROM counterfactual_decisions
                    WHERE institut_id IS NOT NULL
                """, ())
                
                for row in result or []:
                    analyze_institut(row.get("institut_id"), args.days)
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
