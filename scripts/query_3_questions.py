#!/usr/bin/env python3
"""
Interrogation Qdrant : 3 questions précises avec données brutes.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )


def get_embedding(text: str):
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    
    project_id = os.getenv("GCS_PROJECT_ID", "bodycoachocr")
    location = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
    
    aiplatform.init(project=project_id, location=location)
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    embeddings = model.get_embeddings([text])
    return embeddings[0].values


def query_qdrant(question: str, client):
    """Interroge Qdrant avec routage automatique."""
    from backend.collection_router import choose_collection_for_question
    
    collection = choose_collection_for_question(question)
    query_vector = get_embedding(question)
    
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=5,
        with_payload=True
    )
    
    return collection, results.points


def display_results(question_num, question, collection, results):
    """Affiche les résultats bruts."""
    print(f"\n{'='*80}")
    print(f"❓ QUESTION {question_num}")
    print(f"{'='*80}")
    print(f"\n📝 {question}")
    print(f"\n📦 Collection utilisée: {collection}")
    print(f"\n🔍 Résultats ({len(results)}):")
    print("-" * 80)
    
    for i, hit in enumerate(results[:3], 1):
        print(f"\n[{i}] Score: {hit.score:.4f}")
        payload = hit.payload
        
        # Afficher tous les champs du payload
        for key, value in payload.items():
            if key == "text" and len(str(value)) > 300:
                value = str(value)[:300] + "..."
            elif key == "content" and len(str(value)) > 300:
                value = str(value)[:300] + "..."
            print(f"    {key}: {value}")


def main():
    print("\n" + "=" * 80)
    print("🔍 INTERROGATION QDRANT - 3 QUESTIONS PRÉCISES")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    
    questions = [
        "Gommage Corps Exfoliant Intense V030.0 principes actifs Eau d'Hamamélis action prix client",
        "Soin Longue Tenue Anti-Comédons protocole Vapozone Masque référence PRO peau grasse",
        "Crème SENSIMINE Ultra Nourrissante V018.0 actifs 97% naturel type de peau Ultra Apaisante"
    ]
    
    for i, question in enumerate(questions, 1):
        collection, results = query_qdrant(question, client)
        display_results(i, question, collection, results)
    
    print("\n" + "=" * 80)
    print("✅ INTERROGATION TERMINÉE")
    print("=" * 80)


if __name__ == "__main__":
    main()
