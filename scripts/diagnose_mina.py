#!/usr/bin/env python3
"""
🔍 Diagnostic Mina - Analyse des erreurs identifiées par NotebookLM

Vérifie si les informations correctes sont présentes dans Qdrant.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

# Init
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

aiplatform.init(project="bodycoachocr", location="europe-west1")
model = TextEmbeddingModel.from_pretrained("text-embedding-004")

def search(query: str, limit: int = 5):
    """Recherche dans Qdrant."""
    embedding = model.get_embeddings([query])[0].values
    results = client.query_points(
        collection_name="products_index",
        query=embedding,
        limit=limit,
        with_payload=True
    )
    return results.points

def diagnose(query: str, expected_keywords: list):
    """Diagnostique si les bons termes sont dans les sources."""
    print(f"\n{'='*60}")
    print(f"🔍 REQUÊTE: {query}")
    print(f"📋 ATTENDU: {', '.join(expected_keywords)}")
    print(f"{'='*60}")
    
    results = search(query)
    
    found_keywords = []
    for i, hit in enumerate(results, 1):
        text = hit.payload.get("text", "")
        name = hit.payload.get("product_name") or hit.payload.get("service_name") or "Info"
        score = hit.score
        
        print(f"\n--- Source #{i} (score: {score:.4f}) ---")
        print(f"📦 {name}")
        print(f"📄 {text[:300]}...")
        
        # Check keywords
        for kw in expected_keywords:
            if kw.lower() in text.lower():
                found_keywords.append(kw)
                print(f"  ✅ TROUVÉ: '{kw}'")
    
    missing = set(expected_keywords) - set(found_keywords)
    if missing:
        print(f"\n⚠️  MANQUANTS: {', '.join(missing)}")
    else:
        print(f"\n✅ Tous les mots-clés trouvés!")
    
    return found_keywords, missing

# =============================================================================
# DIAGNOSTICS DES 2 ERREURS CRITIQUES
# =============================================================================

print("\n" + "🚨"*30)
print("DIAGNOSTIC DES ERREURS CRITIQUES MINA")
print("🚨"*30)

# 1. RATU - Erreur critique (2/10)
print("\n\n" + "🔴"*20)
print("ERREUR #1: Méthode RATU (score 2/10)")
print("Mina dit: Rassurer, Argumenter, Tester, Utiliser")
print("Correct: Résultat, Avantage, Technique, Utilité")
print("🔴"*20)

diagnose(
    "méthode RATU vente argumentaire",
    ["Résultat", "Avantage", "Technique", "Utilité"]
)

# 2. Temps épilation - Erreur critique (1/10)
print("\n\n" + "🔴"*20)
print("ERREUR #2: Durée épilation demi-jambes (score 1/10)")
print("Mina dit: 30 minutes")
print("Correct: 10 minutes")
print("🔴"*20)

diagnose(
    "épilation demi-jambes durée temps minutes",
    ["10 minutes", "demi-jambes", "épilation"]
)

# 3. Bonus - Actifs Demaq'Xpress
print("\n\n" + "🟡"*20)
print("ERREUR #3: Actifs Demaq'Xpress (score 6/10)")
print("Pin: doit être 'Nettoyante efficace, Antibactérienne'")
print("🟡"*20)

diagnose(
    "Demaq'Xpress 3-en-1 STRONG actifs Pin Ginseng Houblon",
    ["Pin", "Antibactérienne", "Nettoyante", "Ginseng", "Tonifier"]
)

print("\n\n" + "="*60)
print("DIAGNOSTIC TERMINÉ")
print("="*60)
