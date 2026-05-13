#!/usr/bin/env python3
"""
CLI A/B Testing - Gestion des expériences.

Usage:
    python scripts/ab_test_cli.py create --institut laurence_01 --name "Test Budget"
    python scripts/ab_test_cli.py list --institut laurence_01
    python scripts/ab_test_cli.py results --id exp_xxxx
    python scripts/ab_test_cli.py complete --id exp_xxxx
"""

import os
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_experiment(args):
    """Crée une nouvelle expérience."""
    from backend.agent.ab_testing import get_ab_manager, Variant
    
    manager = get_ab_manager()
    
    # Variants par défaut: Control (real) 50% / Treatment (from args) 50%
    treatment_type = args.treatment or "cheaper"
    
    variants = [
        Variant(
            name="control",
            description="Chemin réel (baseline)",
            path_type="real",
            traffic_percent=50
        ),
        Variant(
            name="treatment",
            description=f"Alternative: {treatment_type}",
            path_type=treatment_type,
            traffic_percent=50
        )
    ]
    
    experiment = manager.create_experiment(
        name=args.name,
        institut_id=args.institut,
        variants=variants,
        description=args.description or "",
        target_sample_size=args.sample_size
    )
    
    print(f"\n✅ Expérience créée: {experiment.experiment_id}")
    print(f"   Nom: {experiment.name}")
    print(f"   Institut: {experiment.institut_id}")
    print(f"   Variants: {len(experiment.variants)}")
    print(f"   Target: {experiment.target_sample_size} samples")
    print()


def list_experiments(args):
    """Liste les expériences."""
    from backend.agent.ab_testing import get_ab_manager
    
    manager = get_ab_manager()
    manager._ensure_db()
    
    if not manager._postgres:
        print("❌ PostgreSQL non connecté")
        return
    
    query = "SELECT * FROM ab_experiments"
    params = []
    
    if args.institut:
        query += " WHERE institut_id = %s"
        params.append(args.institut)
    
    query += " ORDER BY created_at DESC LIMIT 20"
    
    results = manager._postgres.fetch_all(query, params)
    
    if not results:
        print("📋 Aucune expérience")
        return
    
    print("\n📋 EXPÉRIENCES A/B")
    print("=" * 70)
    
    for row in results:
        status_icon = "🟢" if row["status"] == "running" else "⚪"
        print(f"\n{status_icon} {row['experiment_id']}")
        print(f"   Nom: {row['name']}")
        print(f"   Institut: {row['institut_id']}")
        print(f"   Status: {row['status']}")
    
    print()


def show_results(args):
    """Affiche les résultats d'une expérience."""
    from backend.agent.ab_testing import get_ab_manager
    
    manager = get_ab_manager()
    results = manager.get_experiment_results(args.id)
    
    if "error" in results:
        print(f"❌ {results['error']}")
        return
    
    print(f"\n📊 RÉSULTATS: {results['name']}")
    print("=" * 60)
    print(f"Status: {results['status']}")
    print(f"Impressions: {results['total_impressions']}")
    print(f"Significatif: {'✅' if results['is_significant'] else '⏳'}")
    print()
    
    print("VARIANTS:")
    for v in results["variants"]:
        print(f"\n  [{v['name']}] ({v['path_type']})")
        print(f"    Traffic: {v['traffic_percent']}%")
        print(f"    Impressions: {v['impressions']}")
        print(f"    Conversions: {v['conversions']}")
        print(f"    Taux: {v['conversion_rate']:.2f}%")
    
    if results.get("winner"):
        print(f"\n🏆 GAGNANT: {results['winner']}")
    
    if results.get("improvement"):
        print(f"📈 Amélioration: {results['improvement']:+.1f}%")
    
    if results.get("recommendation"):
        print(f"\n💡 {results['recommendation']}")
    
    print()


def complete_experiment(args):
    """Termine une expérience."""
    from backend.agent.ab_testing import get_ab_manager
    
    manager = get_ab_manager()
    results = manager.complete_experiment(args.id)
    
    if "error" in results:
        print(f"❌ {results['error']}")
        return
    
    print(f"✅ Expérience terminée: {args.id}")
    
    if results.get("winner"):
        print(f"🏆 Gagnant: {results['winner']}")
        print(f"💡 {results.get('recommendation', '')}")


def main():
    parser = argparse.ArgumentParser(description="A/B Testing CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Create
    create_p = subparsers.add_parser("create", help="Créer une expérience")
    create_p.add_argument("--institut", required=True, help="ID institut")
    create_p.add_argument("--name", required=True, help="Nom expérience")
    create_p.add_argument("--treatment", default="cheaper", help="Type treatment (cheaper/premium/minimal/safe)")
    create_p.add_argument("--description", help="Description")
    create_p.add_argument("--sample-size", type=int, default=1000, help="Taille échantillon cible")
    
    # List
    list_p = subparsers.add_parser("list", help="Lister les expériences")
    list_p.add_argument("--institut", help="Filtrer par institut")
    
    # Results
    results_p = subparsers.add_parser("results", help="Afficher résultats")
    results_p.add_argument("--id", required=True, help="ID expérience")
    
    # Complete
    complete_p = subparsers.add_parser("complete", help="Terminer expérience")
    complete_p.add_argument("--id", required=True, help="ID expérience")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_experiment(args)
    elif args.command == "list":
        list_experiments(args)
    elif args.command == "results":
        show_results(args)
    elif args.command == "complete":
        complete_experiment(args)


if __name__ == "__main__":
    main()
