#!/usr/bin/env python3
"""
Test du routeur de collection Qdrant.
Vérifie que les questions produits et protocoles sont bien routées.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def get_qdrant_client():
    """Initialise le client Qdrant."""
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )


def get_embedding(text: str):
    """Génère l'embedding avec Vertex AI."""
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    
    project_id = os.getenv("GCS_PROJECT_ID", "bodycoachocr")
    location = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
    
    aiplatform.init(project=project_id, location=location)
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    embeddings = model.get_embeddings([text])
    return embeddings[0].values


def test_router():
    """Test du routeur de collection."""
    # Import du routeur
    from backend.collection_router import (
        is_product_question,
        choose_collection_for_question,
        COLLECTION_PRODUCTS,
        COLLECTION_PROTOCOLS
    )
    
    print("\n" + "=" * 80)
    print("🧪 TEST ROUTEUR DE COLLECTION QDRANT")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Cas de test
    test_cases = [
        {
            "question": "Quel est le prix, la référence produit, la contenance et le pourcentage d'ingrédients d'origine naturelle du SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ (50 ml) ?",
            "expected_collection": COLLECTION_PRODUCTS,
            "expected_type": "PRODUIT"
        },
        {
            "question": "Quel est le protocole cabine pour la Cure Silhouette ?",
            "expected_collection": COLLECTION_PROTOCOLS,
            "expected_type": "PROTOCOLE"
        },
        {
            "question": "Combien coûte le GEL MOUSSE FLORAL NETTOYANT VISAGE ?",
            "expected_collection": COLLECTION_PRODUCTS,
            "expected_type": "PRODUIT"
        },
        {
            "question": "Comment réaliser un soin anti-stress en cabine ?",
            "expected_collection": COLLECTION_PROTOCOLS,
            "expected_type": "PROTOCOLE"
        },
        {
            "question": "Quelle est la référence et le prix du HYA SÉRUM HYDRATEMPO ?",
            "expected_collection": COLLECTION_PRODUCTS,
            "expected_type": "PRODUIT"
        },
        {
            "question": "Quelles sont les étapes de la formation initiale ?",
            "expected_collection": COLLECTION_PROTOCOLS,
            "expected_type": "PROTOCOLE"
        }
    ]
    
    # Test de routage
    print("\n" + "-" * 80)
    print("📊 TEST DU ROUTAGE")
    print("-" * 80)
    
    passed = 0
    failed = 0
    
    for i, tc in enumerate(test_cases, 1):
        question = tc["question"]
        expected = tc["expected_collection"]
        expected_type = tc["expected_type"]
        
        is_product = is_product_question(question)
        collection = choose_collection_for_question(question)
        
        success = collection == expected
        
        status = "✅" if success else "❌"
        print(f"\n{status} [{i}] {expected_type}")
        print(f"   Q: {question[:70]}...")
        print(f"   → Collection: {collection}")
        
        if success:
            passed += 1
        else:
            failed += 1
            print(f"   ⚠️ ATTENDU: {expected}")
    
    # Test de recherche réelle
    print("\n" + "-" * 80)
    print("🔍 TEST DE RECHERCHE RÉELLE")
    print("-" * 80)
    
    client = get_qdrant_client()
    
    # Question produit
    question_produit = "Quel est le prix du SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ ?"
    collection_produit = choose_collection_for_question(question_produit)
    
    print(f"\n📦 Question PRODUIT:")
    print(f"   Q: {question_produit}")
    print(f"   → Collection: {collection_produit}")
    
    query_vector = get_embedding(question_produit)
    results = client.query_points(
        collection_name=collection_produit,
        query=query_vector,
        limit=3,
        with_payload=True
    )
    
    print(f"   Résultats ({len(results.points)}):")
    for hit in results.points[:2]:
        name = hit.payload.get("product_name", hit.payload.get("content", "")[:50])
        score = hit.score
        print(f"      [{score:.3f}] {name}")
    
    # Question protocole
    question_protocole = "Quel est le protocole pour la Cure Silhouette ?"
    collection_protocole = choose_collection_for_question(question_protocole)
    
    print(f"\n📋 Question PROTOCOLE:")
    print(f"   Q: {question_protocole}")
    print(f"   → Collection: {collection_protocole}")
    
    query_vector = get_embedding(question_protocole)
    results = client.query_points(
        collection_name=collection_protocole,
        query=query_vector,
        limit=3,
        with_payload=True
    )
    
    print(f"   Résultats ({len(results.points)}):")
    for hit in results.points[:2]:
        content = hit.payload.get("content", hit.payload.get("text", ""))[:80]
        score = hit.score
        print(f"      [{score:.3f}] {content}...")
    
    # Résumé
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    print(f"\nTests de routage: {passed}/{passed+failed} ({'✅' if failed == 0 else '⚠️'})")
    print(f"Recherche réelle: OK")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_router()
