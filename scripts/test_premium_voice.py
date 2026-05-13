#!/usr/bin/env python3
"""
Test des réponses vocales premium pour Mina.
Vérifie que voice_answer_template est utilisé en priorité.
"""

import os
import sys
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


def main():
    from backend.collection_router import choose_collection_for_question
    from backend.response_generator import VoiceResponseGenerator
    
    print("\n" + "=" * 80)
    print("🎤 TEST RÉPONSES VOCALES PREMIUM - MINA")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    generator = VoiceResponseGenerator()
    
    # 3 questions de test
    questions = [
        {
            "question": "Quel est le prix du SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ ?",
            "type": "PRODUIT PREMIUM"
        },
        {
            "question": "Quels sont les actifs de la Crème SENSIMINE Ultra Nourrissante ?",
            "type": "PRODUIT PREMIUM"
        },
        {
            "question": "Quel est le protocole de la Cure Silhouette ?",
            "type": "PROTOCOLE"
        }
    ]
    
    for i, q in enumerate(questions, 1):
        print(f"\n{'─'*80}")
        print(f"[{i}] {q['type']}")
        print(f"❓ Question: {q['question']}")
        
        # Routage
        collection = choose_collection_for_question(q['question'])
        print(f"📂 Collection: {collection}")
        
        # Recherche
        query_vector = get_embedding(q['question'])
        results = client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=1,
            with_payload=True
        )
        
        if results.points:
            hit = results.points[0]
            payload = hit.payload
            
            print(f"📊 Score: {hit.score:.3f}")
            print(f"📦 Produit: {payload.get('product_name', payload.get('content', '')[:50])}")
            
            # Vérifier si premium
            is_premium = payload.get("is_premium", False)
            has_template = bool(payload.get("voice_answer_template"))
            
            print(f"⭐ Premium: {'OUI' if is_premium else 'NON'}")
            print(f"🎤 Template vocal: {'OUI' if has_template else 'NON'}")
            
            # Générer la réponse vocale
            voice_response = generator.generate_voice_response(payload)
            
            print(f"\n🔊 RÉPONSE VOCALE MINA:")
            print(f"   \"{voice_response}\"")
            
        else:
            print("❌ Aucun résultat")
    
    print("\n" + "=" * 80)
    print("✅ TEST TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
