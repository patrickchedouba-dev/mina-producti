#!/usr/bin/env python3
"""
Analyse des interactions Mina V1.5
Génère statistiques de performance et concision

Usage:
    python scripts/analyze_benchmark.py
"""

import json
import statistics
from pathlib import Path

def analyze_benchmark():
    """Analyse fichier benchmark et affiche stats."""
    
    filepath = Path("/home/jupyter/mina_fichiers/mina-bêta/logs/benchmark_interactions.jsonl")
    
    if not filepath.exists():
        print(f"❌ Fichier {filepath} introuvable")
        print("   Lance quelques interactions avec Mina d'abord.")
        return
    
    interactions = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                interactions.append(json.loads(line))
    
    if not interactions:
        print("❌ Aucune interaction trouvée")
        return
    
    # Extraire métriques
    totals = [i['latencies']['total'] for i in interactions]
    stts = [i['latencies']['stt'] for i in interactions]
    rags = [i['latencies']['rag'] for i in interactions]
    llms = [i['latencies']['llm'] for i in interactions]
    ttss = [i['latencies']['tts'] for i in interactions]
    words = [i['word_count'] for i in interactions]
    
    # Afficher stats
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          ANALYSE BENCHMARK MINA V1.5                         ║
║          {len(interactions):3d} interactions analysées                        ║
╚══════════════════════════════════════════════════════════════╝

⏱️  LATENCES (secondes):
    ┌─────────────┬──────────┬──────────┬──────────┐
    │ Composant   │ Moyenne  │ Min      │ Max      │
    ├─────────────┼──────────┼──────────┼──────────┤
    │ STT         │ {statistics.mean(stts):8.2f} │ {min(stts):8.2f} │ {max(stts):8.2f} │
    │ RAG         │ {statistics.mean(rags):8.2f} │ {min(rags):8.2f} │ {max(rags):8.2f} │
    │ LLM         │ {statistics.mean(llms):8.2f} │ {min(llms):8.2f} │ {max(llms):8.2f} │
    │ TTS         │ {statistics.mean(ttss):8.2f} │ {min(ttss):8.2f} │ {max(ttss):8.2f} │
    │ TOTAL       │ {statistics.mean(totals):8.2f} │ {min(totals):8.2f} │ {max(totals):8.2f} │
    └─────────────┴──────────┴──────────┴──────────┘

📏 CONCISION:
    Mots par réponse (moyenne): {statistics.mean(words):.1f}
    Mots par réponse (médiane): {statistics.median(words):.1f}
    
    Réponses ≤30 mots: {sum(1 for w in words if w <= 30)/len(words)*100:.1f}%
    Réponses ≤40 mots: {sum(1 for w in words if w <= 40)/len(words)*100:.1f}%
    Réponses >40 mots: {sum(1 for w in words if w > 40)/len(words)*100:.1f}%

🎯 OBJECTIFS V1.5:
    Latence <5s:  {sum(1 for t in totals if t < 5)/len(totals)*100:5.1f}% {'✅' if sum(1 for t in totals if t < 5)/len(totals) > 0.5 else '❌'}
    Latence <6s:  {sum(1 for t in totals if t < 6)/len(totals)*100:5.1f}% {'✅' if sum(1 for t in totals if t < 6)/len(totals) > 0.7 else '⚠️'}
    Latence <7s:  {sum(1 for t in totals if t < 7)/len(totals)*100:5.1f}%
    
    Concision OK: {sum(1 for w in words if w <= 40)/len(words)*100:5.1f}% {'✅' if sum(1 for w in words if w <= 40)/len(words) > 0.8 else '❌'}
""")
    
    # Identifier goulot
    components = [
        ('STT', statistics.mean(stts)),
        ('RAG', statistics.mean(rags)),
        ('LLM', statistics.mean(llms)),
        ('TTS', statistics.mean(ttss))
    ]
    slowest = max(components, key=lambda x: x[1])
    print(f"📊 GOULOT D'ÉTRANGLEMENT: {slowest[0]} ({slowest[1]:.2f}s)")
    
    # Top 3 réponses les plus longues
    print(f"\n🔍 QUESTIONS AVEC RÉPONSES LES PLUS LONGUES:")
    longest = sorted(interactions, key=lambda x: x['word_count'], reverse=True)[:3]
    for i, interaction in enumerate(longest, 1):
        q = interaction['question'][:40] + "..." if len(interaction['question']) > 40 else interaction['question']
        print(f"    {i}. {interaction['word_count']} mots - Q: \"{q}\"")
    
    # Top 3 réponses les plus rapides
    print(f"\n⚡ INTERACTIONS LES PLUS RAPIDES:")
    fastest = sorted(interactions, key=lambda x: x['latencies']['total'])[:3]
    for i, interaction in enumerate(fastest, 1):
        q = interaction['question'][:40] + "..." if len(interaction['question']) > 40 else interaction['question']
        print(f"    {i}. {interaction['latencies']['total']:.2f}s - Q: \"{q}\"")
    
    print("\n" + "="*66)


if __name__ == "__main__":
    analyze_benchmark()
