#!/usr/bin/env python3
"""
Re-vectorisation des protocoles premium dans bodyminute_docs.
Génère de nouveaux embeddings basés sur les champs enrichis.
"""

import os
import sys
from typing import Dict, List, Any
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


def get_embedding(text: str) -> List[float]:
    """Génère un embedding avec Vertex AI text-embedding-004."""
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    
    project_id = os.getenv("GCS_PROJECT_ID", "bodycoachocr")
    location = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
    
    aiplatform.init(project=project_id, location=location)
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    embeddings = model.get_embeddings([text])
    return embeddings[0].values


def build_indexation_text(payload: Dict[str, Any]) -> str:
    """
    Construit un texte d'indexation propre à partir des champs enrichis.
    Ce texte sera vectorisé pour améliorer la recherche sémantique.
    """
    parts = []
    
    # Nom du protocole
    protocol_name = payload.get("protocol_name", "")
    if protocol_name:
        parts.append(f"Nom du soin : {protocol_name}")
    
    # Peau ciblée
    skin_need = payload.get("skin_need", "")
    if skin_need:
        parts.append(f"Peau ciblée : {skin_need}")
    
    # Durée
    duration = payload.get("duration_minutes")
    if duration:
        parts.append(f"Durée : {duration} minutes")
    
    # Résumé du protocole
    summary = payload.get("protocol_summary", "")
    if summary:
        parts.append(f"Description : {summary}")
    
    # Étapes clés
    key_steps = payload.get("key_steps", [])
    if key_steps:
        steps_text = " ; ".join(key_steps)
        parts.append(f"Étapes clés : {steps_text}")
    
    # Produits principaux
    main_products = payload.get("main_products", [])
    if main_products:
        products_text = ", ".join([
            p.get("name", "") for p in main_products if isinstance(p, dict) and p.get("name")
        ])
        if products_text:
            parts.append(f"Produits utilisés : {products_text}")
    
    return " | ".join(parts)


def get_premium_protocols(client) -> List[Dict]:
    """Récupère tous les protocoles premium de bodyminute_docs."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    all_premium = []
    offset = None
    
    while True:
        results, next_offset = client.scroll(
            collection_name="bodyminute_docs",
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="is_protocol_premium",
                        match=MatchValue(value=True)
                    )
                ]
            ),
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )
        
        all_premium.extend(results)
        
        if next_offset is None:
            break
        offset = next_offset
    
    return all_premium


def update_vector(client, point_id, new_vector: List[float]):
    """Met à jour le vecteur d'un point sans toucher au payload."""
    from qdrant_client.models import PointVectors
    
    client.update_vectors(
        collection_name="bodyminute_docs",
        points=[
            PointVectors(
                id=point_id,
                vector=new_vector
            )
        ]
    )


def run_revectorization():
    """Exécute la re-vectorisation des protocoles premium."""
    print("\n" + "=" * 80)
    print("🔄 RE-VECTORISATION PROTOCOLES PREMIUM")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    
    # Récupérer les protocoles premium
    print("\n📋 Récupération des protocoles premium...")
    premium_points = get_premium_protocols(client)
    print(f"   Trouvés: {len(premium_points)} points is_protocol_premium=true")
    
    if not premium_points:
        print("❌ Aucun protocole premium trouvé")
        return
    
    # Grouper par protocole pour affichage
    protocols_seen = set()
    revectorized_count = 0
    
    print("\n" + "-" * 80)
    print("🔄 RE-VECTORISATION EN COURS")
    print("-" * 80)
    
    for i, point in enumerate(premium_points, 1):
        protocol_name = point.payload.get("protocol_name", "Unknown")
        
        # Afficher une fois par protocole
        if protocol_name not in protocols_seen:
            protocols_seen.add(protocol_name)
            print(f"\n🏥 {protocol_name}")
        
        # Construire le texte d'indexation
        indexation_text = build_indexation_text(point.payload)
        
        if not indexation_text:
            print(f"   ⚠️ Point {point.id}: texte vide, ignoré")
            continue
        
        # Générer le nouvel embedding
        try:
            new_vector = get_embedding(indexation_text)
            
            # Mettre à jour le vecteur
            update_vector(client, point.id, new_vector)
            revectorized_count += 1
            
            print(f"   ✅ Point {point.id} re-vectorisé")
            
        except Exception as e:
            print(f"   ❌ Point {point.id}: erreur - {e}")
    
    # Rapport final
    print("\n" + "=" * 80)
    print("📊 RAPPORT FINAL")
    print("=" * 80)
    
    print(f"\n✅ Protocoles premium re-vectorisés: {revectorized_count}/{len(premium_points)}")
    print(f"📋 Protocoles distincts: {len(protocols_seen)}")
    
    for proto in sorted(protocols_seen):
        print(f"   • {proto}")
    
    print("\n💡 Exécutez maintenant test_mixed_question.py pour vérifier les matches")
    print("=" * 80)
    
    return revectorized_count


if __name__ == "__main__":
    run_revectorization()
