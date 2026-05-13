#!/usr/bin/env python3
"""
Test des questions mixtes (protocole + produit) pour Mina.
Vérifie la détection et la génération de réponses fusionnées.
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
    from backend.collection_router import (
        analyze_question, 
        COLLECTION_PRODUCTS, 
        COLLECTION_PROTOCOLS
    )
    from backend.response_generator import (
        VoiceResponseGenerator,
        MixedAnswer,
        generate_mixed_voice_answer
    )
    
    print("\n" + "=" * 80)
    print("🔀 TEST QUESTIONS MIXTES (PROTOCOLE + PRODUIT)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    generator = VoiceResponseGenerator()
    
    # Questions mixtes à tester
    mixed_questions = [
        {
            "question": "Quel est l'objectif du Vapozone dans le Soin Longue Tenue Anti-Comédons et quel masque PRO est utilisé ?",
            "protocol_search": "Soin Longue Tenue Anti-Comédons Vapozone extraction comédons peau grasse",
            "product_search": "Masque SENSIMINE PRO C011.0 peaux grasses"
        },
        {
            "question": "Quels produits sont utilisés dans le Soin Hydratempo cabine et quels sont leurs actifs principaux ?",
            "protocol_search": "Soin Profond Hydratempo peau sèche déshydratée Sérum Masque",
            "product_search": "Masque Hydratempo PRO hydratation acide hyaluronique"
        }
    ]
    
    for i, mq in enumerate(mixed_questions, 1):
        print(f"\n{'─'*80}")
        print(f"[{i}] QUESTION MIXTE")
        print(f"❓ {mq['question']}")
        
        # Analyser la question
        qtype = analyze_question(mq['question'])
        print(f"\n📊 Analyse: product={qtype.is_product}, protocol={qtype.is_protocol}, MIXTE={qtype.is_mixed}")
        
        if qtype.is_mixed:
            print("✅ Question MIXTE détectée")
            
            # Import du filtre Qdrant
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Recherche protocole AVEC filtre is_protocol_premium=True
            print(f"\n🔍 Recherche PROTOCOLE (filtre premium): {mq['protocol_search'][:50]}...")
            proto_vector = get_embedding(mq['protocol_search'])
            
            # D'abord essayer avec le filtre premium
            proto_results = client.query_points(
                collection_name=COLLECTION_PROTOCOLS,
                query=proto_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="is_protocol_premium",
                            match=MatchValue(value=True)
                        )
                    ]
                ),
                limit=1,
                with_payload=True
            )
            
            # Si aucun résultat premium, fallback sans filtre
            used_premium_filter = True
            if not proto_results.points:
                print("   ⚠️ Aucun protocole premium trouvé, fallback recherche standard...")
                used_premium_filter = False
                proto_results = client.query_points(
                    collection_name=COLLECTION_PROTOCOLS,
                    query=proto_vector,
                    limit=1,
                    with_payload=True
                )
            else:
                print("   ✅ Protocole PREMIUM trouvé !")
            
            # Recherche produit
            print(f"🔍 Recherche PRODUIT: {mq['product_search'][:50]}...")
            prod_vector = get_embedding(mq['product_search'])
            prod_results = client.query_points(
                collection_name=COLLECTION_PRODUCTS,
                query=prod_vector,
                limit=1,
                with_payload=True
            )
            
            if proto_results.points and prod_results.points:
                proto_hit = proto_results.points[0]
                prod_hit = prod_results.points[0]
                
                # Affichage protocole
                is_protocol_premium = proto_hit.payload.get("is_protocol_premium", False)
                proto_voice = proto_hit.payload.get("voice_answer_template_protocol", "")
                
                print(f"\n📋 PROTOCOLE trouvé (score: {proto_hit.score:.3f}):")
                print(f"   ⭐ Premium: {'OUI' if is_protocol_premium else 'NON'}")
                if is_protocol_premium:
                    print(f"   📛 Nom: {proto_hit.payload.get('protocol_name', 'N/A')}")
                    print(f"   ⏱️ Durée: {proto_hit.payload.get('duration_minutes', 'N/A')} min")
                    print(f"   🎤 Template: \"{proto_voice[:80]}...\"" if proto_voice else "   🎤 Template: N/A")
                else:
                    proto_content = proto_hit.payload.get("content", proto_hit.payload.get("text", ""))[:100]
                    print(f"   {proto_content}...")
                
                # Affichage produit
                print(f"\n📦 PRODUIT trouvé (score: {prod_hit.score:.3f}):")
                print(f"   {prod_hit.payload.get('product_name', 'N/A')}")
                print(f"   Réf: {prod_hit.payload.get('product_ref', 'N/A')}")
                print(f"   Premium: {'OUI' if prod_hit.payload.get('is_premium') else 'NON'}")
                
                # Construire la réponse mixte
                mixed = MixedAnswer(
                    protocol_payload=proto_hit.payload,
                    product_payload=prod_hit.payload,
                    protocol_score=proto_hit.score,
                    product_score=prod_hit.score
                )
                
                voice_response = generator.build_mixed_voice_answer(mixed)
                
                print(f"\n🔊 RÉPONSE VOCALE MIXTE:")
                print(f"   \"{voice_response}\"")
            else:
                print("❌ Résultats incomplets")
        else:
            print("⚠️ Question non détectée comme mixte")
    
    print("\n" + "=" * 80)
    print("✅ TEST TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
