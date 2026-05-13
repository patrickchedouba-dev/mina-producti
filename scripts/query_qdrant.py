#!/usr/bin/env python3
"""
Script de recherche sémantique dans Qdrant pour répondre aux questions Body Minute.
Utilise Vertex AI pour générer les embeddings des questions.
"""

import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Configuration du path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Charger .env
from dotenv import load_dotenv
load_dotenv()

# Import après configuration du path
from backend.qdrant_client import ensure_text_index

# Utilitaires centralisés (Phase 2 Refactoring)
from utils import get_qdrant_client, get_embedding


# 10 questions Body Minute
QUESTIONS = [
    {
        "id": 1,
        "question": "Quel est le prix client et la référence associée du SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ (50ml), et quel est son pourcentage d'ingrédients d'origine naturelle ?",
        "search_query": "SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ 50ml prix référence pourcentage naturel"
    },
    {
        "id": 2,
        "question": "Quelle est la différence de prix entre le Soin Corps Profond Hyper Hydratant (500ml) et le Baume Riche Corps Réparateur ++ (500ml) ?",
        "search_query": "Soin Corps Profond Hyper Hydratant Baume Riche Corps Réparateur prix 500ml 90% naturel"
    },
    {
        "id": 3,
        "question": "Quels sont les trois principes actifs majeurs de l'Huile Apaisante Après Épilation (99% naturel), et quelle est l'action spécifique de l'Huile de Soja ?",
        "search_query": "Huile Apaisante Après Épilation principes actifs Huile de Soja action"
    },
    {
        "id": 4,
        "question": "Dans la routine HOME SPA METABOLISSIME, quel est le produit spécifique utilisé à l'étape Stimuler, et combien de minutes dure cette étape ?",
        "search_query": "HOME SPA METABOLISSIME routine étape Stimuler produit minutes"
    },
    {
        "id": 5,
        "question": "Quel produit de la gamme Hydratempo contient le pourcentage d'ingrédients d'origine naturelle le plus élevé : HYA SÉRUM 3D HYDRATEMPO ou GEL HYDRATEMPO WATER BOMB ?",
        "search_query": "HYA SÉRUM 3D HYDRATEMPO GEL WATER BOMB pourcentage naturel ingrédients"
    },
    {
        "id": 6,
        "question": "Lors du soin Longue Tenue Anti-Comédons (1h), quel est le numéro de référence du masque désincrustant utilisé (Masque 2.0 SENSIMINE ou Masque 1.3 Anti-Comédons) ?",
        "search_query": "soin Longue Tenue Anti-Comédons masque désincrustant référence 2.0 SENSIMINE 1.3"
    },
    {
        "id": 7,
        "question": "Quel est le prix client du Roll-On Quartz Améthyste et pour quel bénéfice spécifique est-il recommandé ?",
        "search_query": "Roll-On Quartz Améthyste prix bénéfice apaisant purification anti-âge"
    },
    {
        "id": 8,
        "question": "La Crème SENSIMINE Ultra Apaisante coûte-t-elle plus cher ou moins cher que la Crème SENSIMINE Ultra Nourrissante ?",
        "search_query": "Crème SENSIMINE Ultra Apaisante Nourrissante prix comparaison"
    },
    {
        "id": 9,
        "question": "Quels sont les actifs principaux du GEL MOUSSE FLORAL NETTOYANT VISAGE (89% naturel), et à quelle fréquence d'utilisation est-il conseillé ?",
        "search_query": "GEL MOUSSE FLORAL NETTOYANT VISAGE actifs fréquence matin soir utilisation"
    },
    {
        "id": 10,
        "question": "Quelle est la référence client exacte et le prix du Crème Mains Skin'minute (50ml), et quel est son pourcentage d'ingrédients naturels ?",
        "search_query": "Crème Mains Skin'minute 50ml référence prix pourcentage naturel"
    }
]


# get_qdrant_client et get_embedding importés depuis utils (voir ligne 22)


def search_qdrant(client, query: str, collection_name: str = "bodyminute_docs", top_k: int = 5) -> List[Dict]:
    """
    Recherche sémantique dans Qdrant.
    
    Args:
        client: Client Qdrant
        query: Requête de recherche
        collection_name: Nom de la collection
        top_k: Nombre de résultats
    
    Returns:
        Liste des résultats avec score et payload
    """
    # --- AUTO: ENSURE QDRANT TEXT INDEX (before MatchText) ---
    try:
        ensure_text_index(client, collection_name=collection_name, field_name='text')
    except Exception:
        pass

    from qdrant_client.models import PointStruct
    from qdrant_client.http import models
    
    # Générer l'embedding de la query
    query_vector = get_embedding(query)
    
    # Recherche dans Qdrant (nouvelle API)
    # Filtre minimal: si la question parle d'une étape (ex: STIMULER), on force un match texte
    q = (query or "").lower()
    query_filter = None
    if "stimuler" in q:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="text", match=models.MatchText(text="STIMULER"))]
        )

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
        with_payload=True,
        query_filter=query_filter,
    )
    
    return [
        {
            "score": hit.score,
            "text": hit.payload.get("text") or hit.payload.get("content") or hit.payload.get("chunk", ""),
            "source": hit.payload.get("source_path") or hit.payload.get("source") or hit.payload.get("filename", "Unknown"),
            "id": str(hit.id)
        }
        for hit in results.points
    ]


def extract_answer(question: str, chunks: List[Dict]) -> str:
    """
    Extrait la réponse à partir des chunks trouvés.
    Analyse le contenu pour répondre à la question.
    """
    if not chunks:
        return "❌ Aucun chunk pertinent trouvé."
    
    # Combiner les textes des meilleurs chunks
    combined_text = "\n---\n".join([
        f"[Score: {c['score']:.3f}]\n{c['text']}"
        for c in chunks[:3]
    ])
    
    return combined_text


def run_qa_session():
    """Exécute la session de Q&A."""
    print("\n" + "=" * 80)
    print("🔍 INTERROGATION SÉMANTIQUE QDRANT - BODY MINUTE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "bodyminute_docs")
    
    # Connexion Qdrant
    print(f"\n📡 Connexion à Qdrant...")
    client = get_qdrant_client()
    # Vérifier la collection
    info = client.get_collection(collection_name)
    print(f"✅ Collection '{collection_name}': {info.points_count} vectors")
    
    print("\n" + "=" * 80)
    print("📋 RÉPONSES AUX 10 QUESTIONS")
    print("=" * 80)
    
    results = []
    
    for q in QUESTIONS:
        print(f"\n{'─' * 80}")
        print(f"❓ QUESTION {q['id']}:")
        print(f"   {q['question']}")
        print(f"\n🔎 Recherche: \"{q['search_query']}\"")
        
        try:
            # Recherche sémantique
            chunks = search_qdrant(client, q['search_query'], collection_name, top_k=5)
            
            print(f"\n📄 Top 3 chunks trouvés:")
            for i, chunk in enumerate(chunks[:3], 1):
                text_preview = chunk['text'][:300].replace('\n', ' ')
                if len(chunk['text']) > 300:
                    text_preview += "..."
                print(f"\n   [{i}] Score: {chunk['score']:.3f}")
                print(f"       {text_preview}")
            
            # Stocker le résultat
            results.append({
                "question_id": q['id'],
                "question": q['question'],
                "chunks": chunks,
                "success": True
            })
            
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            results.append({
                "question_id": q['id'],
                "question": q['question'],
                "error": str(e),
                "success": False
            })
    
    # Résumé final
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['success'])
    print(f"\n✅ Questions traitées: {success_count}/{len(QUESTIONS)}")
    
    # Calculer le score moyen
    all_scores = []
    for r in results:
        if r['success'] and r.get('chunks'):
            all_scores.append(r['chunks'][0]['score'])
    
    if all_scores:
        avg_score = sum(all_scores) / len(all_scores)
        print(f"📈 Score de pertinence moyen: {avg_score:.3f}")
    
    print("\n" + "=" * 80)
    print("✅ SESSION TERMINÉE")
    print("=" * 80 + "\n")
    
#     return results


if __name__ == "__main__":
    results = run_qa_session()
