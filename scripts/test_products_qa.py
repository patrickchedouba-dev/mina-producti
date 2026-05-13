#!/usr/bin/env python3
"""
Test des 10 questions sur la nouvelle collection bodyminute_products.
"""

import os
import sys
from typing import List, Dict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


QUESTIONS = [
    {
        "id": 1,
        "question": "Quel est le prix et la référence du SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ ?",
        "search": "SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ prix référence"
    },
    {
        "id": 2,
        "question": "Différence de prix Soin Corps Profond Hyper Hydratant vs Baume Riche Corps ?",
        "search": "Soin Corps Profond Hyper Hydratant Baume Riche Corps prix"
    },
    {
        "id": 3,
        "question": "Actifs de l'Huile Apaisante Après Épilation et action Huile de Soja ?",
        "search": "Huile Apaisante Après Épilation principes actifs Huile Soja"
    },
    {
        "id": 4,
        "question": "Routine HOME SPA METABOLISSIME - étape Stimuler ?",
        "search": "HOME SPA METABOLISSIME Stimuler produit"
    },
    {
        "id": 5,
        "question": "HYA SÉRUM 3D HYDRATEMPO vs GEL WATER BOMB - % naturel ?",
        "search": "HYA SÉRUM HYDRATEMPO GEL WATER BOMB pourcentage naturel"
    },
    {
        "id": 6,
        "question": "Soin Longue Tenue Anti-Comédons - référence masque ?",
        "search": "Longue Tenue Anti-Comédons masque référence"
    },
    {
        "id": 7,
        "question": "Prix Roll-On Quartz Améthyste et bénéfice ?",
        "search": "Roll-On Quartz Améthyste prix bénéfice"
    },
    {
        "id": 8,
        "question": "Crème SENSIMINE Ultra Apaisante vs Nourrissante ?",
        "search": "Crème SENSIMINE Ultra Apaisante Nourrissante prix"
    },
    {
        "id": 9,
        "question": "GEL MOUSSE FLORAL NETTOYANT - actifs et fréquence ?",
        "search": "GEL MOUSSE FLORAL NETTOYANT VISAGE actifs fréquence"
    },
    {
        "id": 10,
        "question": "Crème Mains Skin'minute - référence et prix ?",
        "search": "Crème Mains Skin'minute 50ml référence prix"
    }
]


def get_embedding(text: str) -> List[float]:
    """Génère l'embedding avec Vertex AI."""
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    
    project_id = os.getenv("GCS_PROJECT_ID", "bodycoachocr")
    location = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
    
    aiplatform.init(project=project_id, location=location)
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    embeddings = model.get_embeddings([text])
    return embeddings[0].values


def search_products(query: str, collection: str = "bodyminute_products", top_k: int = 3) -> List[Dict]:
    """Recherche dans la collection produits."""
    from qdrant_client import QdrantClient
    
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    # Vérifier si la collection existe
    try:
        info = client.get_collection(collection)
        if info.points_count == 0:
            return []
    except:
        return []
    
    query_vector = get_embedding(query)
    
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=top_k,
        with_payload=True
    )
    
    return [
        {
            "score": hit.score,
            "product_name": hit.payload.get("product_name", ""),
            "product_ref": hit.payload.get("product_ref", ""),
            "price_eur": hit.payload.get("price_eur", 0),
            "natural_pct": hit.payload.get("natural_origin_pct"),
            "actives": hit.payload.get("key_actives", []),
            "text": hit.payload.get("text", ""),
        }
        for hit in results.points
    ]


def main():
    """Test des 10 questions."""
    print("\n" + "=" * 80)
    print("🔍 TEST 10 QUESTIONS - COLLECTION bodyminute_products")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    scores = []
    found = 0
    not_found = 0
    
    for q in QUESTIONS:
        print(f"\n{'─' * 80}")
        print(f"❓ Q{q['id']}: {q['question']}")
        print(f"🔎 Recherche: {q['search']}")
        
        try:
            results = search_products(q['search'])
            
            if results:
                best = results[0]
                scores.append(best['score'])
                
                print(f"\n📦 RÉPONSE (score: {best['score']:.3f}):")
                print(f"   Produit: {best['product_name']}")
                print(f"   Référence: {best['product_ref']}")
                print(f"   Prix: {best['price_eur']}€")
                print(f"   % Naturel: {best['natural_pct']}")
                print(f"   Actifs: {best['actives'][:3]}")
                
                # Évaluer la pertinence
                if best['score'] >= 0.6:
                    print(f"   ✅ Pertinent")
                    found += 1
                else:
                    print(f"   ⚠️ Faible pertinence")
                    not_found += 1
            else:
                print(f"\n❌ Aucun résultat")
                not_found += 1
                
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            not_found += 1
    
    # Résumé
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    
    avg_score = sum(scores) / len(scores) if scores else 0
    
    print(f"\nQuestions traitées: {len(QUESTIONS)}")
    print(f"Réponses pertinentes: {found} ({'🟢' if found >= 7 else '🟡' if found >= 5 else '🔴'})")
    print(f"Non trouvées / faible: {not_found}")
    print(f"Score moyen: {avg_score:.3f}")
    
    if avg_score >= 0.6:
        print("\n✅ VERDICT: Bonne qualité de recherche")
    elif avg_score >= 0.4:
        print("\n🟡 VERDICT: Qualité acceptable, indexation à compléter")
    else:
        print("\n🔴 VERDICT: Insuffisant, plus de données nécessaires")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
