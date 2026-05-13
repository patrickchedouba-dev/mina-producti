#!/usr/bin/env python3
"""
Tests de régression automatisés pour Mina Bêta V2.
35 questions validées pour garantir une bêta "zéro faute".
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


# === 35 QUESTIONS DE RÉGRESSION ===

REGRESSION_TESTS = [
    # === PRODUITS PREMIUM (15 tests) ===
    {
        "id": "PROD-01",
        "question": "Quel est le prix du SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ ?",
        "expected_type": "product",
        "expected_ref": "V012.0",
        "must_be_premium": True,
        "min_score": 0.6
    },
    {
        "id": "PROD-02",
        "question": "Quels sont les actifs du Masque Sensimine Pro ?",
        "expected_type": "product",
        "expected_ref": "C011.0",
        "must_be_premium": True,
        "min_score": 0.6
    },
    {
        "id": "PROD-03",
        "question": "À quoi sert la HYA Crème 24H Hydratempo ?",
        "expected_type": "product",
        "expected_ref": "V013.0",
        "must_be_premium": True,
        "min_score": 0.6
    },
    {
        "id": "PROD-04",
        "question": "Prix de la Crème Metabolic Collagen Pro ?",
        "expected_type": "product",
        "expected_ref": "V019.0",
        "must_be_premium": True,
        "min_score": 0.6
    },
    {
        "id": "PROD-05",
        "question": "Quel produit pour les jambes lourdes ?",
        "expected_type": "product",
        "expected_ref": "V038.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-06",
        "question": "Démaquillant express recommandé ?",
        "expected_type": "product",
        "expected_ref": "V005.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-07",
        "question": "Gommage visage utilisé en cabine ?",
        "expected_type": "product",
        "expected_ref": "V001.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-08",
        "question": "Huile de massage pour épilation ?",
        "expected_type": "product",
        "expected_ref": "V055.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-09",
        "question": "Produit contre les poils incarnés ?",
        "expected_type": "product",
        "expected_ref": "V063.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-10",
        "question": "Sérum anti-cellulite zones rebelles ?",
        "expected_type": "product",
        "expected_ref": "V037.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-11",
        "question": "Baume de massage professionnel cabine ?",
        "expected_type": "product",
        "expected_ref": "V036.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-12",
        "question": "Crème nuit Rose Alpine ?",
        "expected_type": "product",
        "expected_ref": "V028.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-13",
        "question": "Elixir Cell Flash pour teint terne ?",
        "expected_type": "product",
        "expected_ref": "V026.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-14",
        "question": "Shampoo pour cheveux secs ?",
        "expected_type": "product",
        "expected_ref": "V049.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROD-15",
        "question": "Tonique 3 fleurs après démaquillage ?",
        "expected_type": "product",
        "expected_ref": "V004.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    
    # === PROTOCOLES PREMIUM (10 tests) ===
    {
        "id": "PROTO-01",
        "question": "Quelle est la durée du Soin Hydratempo ?",
        "expected_type": "protocol",
        "expected_name": "SOIN PROFOND HYDRATEMPO",
        "must_be_premium": True,
        "min_score": 0.6
    },
    {
        "id": "PROTO-02",
        "question": "Étapes du Soin Longue Tenue Anti-Comédons ?",
        "expected_type": "protocol",
        "expected_name": "SOIN LONGUE TENUE ANTI-COMÉDONS",
        "must_be_premium": True,
        "min_score": 0.6
    },
    {
        "id": "PROTO-03",
        "question": "Comment fonctionne la Cure Silhouette ?",
        "expected_type": "protocol",
        "expected_name": "CURE SILHOUETTE",
        "must_be_premium": True,
        "min_score": 0.6
    },
    {
        "id": "PROTO-04",
        "question": "Soin pour peaux sensibles en cabine ?",
        "expected_type": "protocol",
        "expected_name": "SOIN PROFOND SENSIMINE",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROTO-05",
        "question": "Protocole S-Détox pour peau grasse ?",
        "expected_type": "protocol",
        "expected_name": "SOIN PROFOND S-DÉTOX",
        "must_be_premium": True,
        "min_score": 0.6
    },
    {
        "id": "PROTO-06",
        "question": "Soin anti-âge Metabolissime ?",
        "expected_type": "protocol",
        "expected_name": "SOIN METABOLISSIME ÉCLAT",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROTO-07",
        "question": "Soin express pour éclat rapide ?",
        "expected_type": "protocol",
        "expected_name": "SOIN EXPRESS ÉCLAT",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROTO-08",
        "question": "Gommage corps complet en cabine ?",
        "expected_type": "protocol",
        "expected_name": "GOMMAGE CORPS COMPLET",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROTO-09",
        "question": "Soin relaxant antistress ?",
        "expected_type": "protocol",
        "expected_name": "SOIN ANTISTRESS",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "PROTO-10",
        "question": "Soin jambes légères drainant ?",
        "expected_type": "protocol",
        "expected_name": "SOIN JAMBES LÉGÈRES",
        "must_be_premium": True,
        "min_score": 0.5
    },
    
    # === QUESTIONS MIXTES (5 tests) ===
    {
        "id": "MIX-01",
        "question": "Quel masque PRO dans le Soin Anti-Comédons avec Vapozone ?",
        "expected_type": "mixed",
        "expected_protocol": "SOIN LONGUE TENUE ANTI-COMÉDONS",
        "expected_product_ref": "C011.0",
        "must_be_premium": True,
        "min_score": 0.5
    },
    {
        "id": "MIX-02",
        "question": "Quels produits dans le Soin Hydratempo cabine ?",
        "expected_type": "mixed",
        "expected_protocol": "SOIN PROFOND HYDRATEMPO",
        "min_score": 0.5
    },
    {
        "id": "MIX-03",
        "question": "Sérum et masque utilisés dans le Soin Sensimine ?",
        "expected_type": "mixed",
        "expected_protocol": "SOIN PROFOND SENSIMINE",
        "min_score": 0.5
    },
    {
        "id": "MIX-04",
        "question": "Protocole et produits pour peau grasse acnéique ?",
        "expected_type": "mixed",
        "min_score": 0.5
    },
    {
        "id": "MIX-05",
        "question": "Soin minceur et sérum anti-cellulite associé ?",
        "expected_type": "mixed",
        "expected_protocol": "CURE SILHOUETTE",
        "min_score": 0.5
    },
    
    # === HORS SCOPE (5 tests - doivent fallback proprement) ===
    {
        "id": "OOS-01",
        "question": "Quels sont les horaires d'ouverture ?",
        "expected_type": "out_of_scope",
        "should_safe_mode": True,
        "min_score": 0.3
    },
    {
        "id": "OOS-02",
        "question": "Comment prendre rendez-vous ?",
        "expected_type": "out_of_scope",
        "should_safe_mode": True,
        "min_score": 0.3
    },
    {
        "id": "OOS-03",
        "question": "Où est situé l'institut le plus proche ?",
        "expected_type": "out_of_scope",
        "should_safe_mode": True,
        "min_score": 0.3
    },
    {
        "id": "OOS-04",
        "question": "Recette de gâteau au chocolat ?",
        "expected_type": "out_of_scope",
        "should_safe_mode": True,
        "min_score": 0.2
    },
    {
        "id": "OOS-05",
        "question": "Quelle est la météo aujourd'hui ?",
        "expected_type": "out_of_scope",
        "should_safe_mode": True,
        "min_score": 0.2
    }
]


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


def run_single_test(client, test: Dict) -> Tuple[bool, str]:
    """Exécute un test unique et retourne (succès, message)."""
    from backend.collection_router import analyze_question, COLLECTION_PRODUCTS, COLLECTION_PROTOCOLS
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    question = test["question"]
    expected_type = test["expected_type"]
    min_score = test.get("min_score", 0.5)
    
    try:
        query_vector = get_embedding(question)
        
        if expected_type == "product":
            results = client.query_points(
                collection_name=COLLECTION_PRODUCTS,
                query=query_vector,
                limit=1,
                with_payload=True
            )
            
            if not results.points:
                return False, "Aucun résultat"
            
            hit = results.points[0]
            actual_ref = hit.payload.get("product_ref", "")
            is_premium = hit.payload.get("is_premium", False)
            
            if hit.score < min_score:
                return False, f"Score trop bas: {hit.score:.3f}"
            
            if test.get("must_be_premium") and not is_premium:
                return False, f"Non premium (ref: {actual_ref})"
            
            if test.get("expected_ref") and actual_ref != test["expected_ref"]:
                return False, f"Mauvaise ref: {actual_ref} (attendu: {test['expected_ref']})"
            
            return True, f"OK (score: {hit.score:.3f}, ref: {actual_ref})"
        
        elif expected_type == "protocol":
            results = client.query_points(
                collection_name=COLLECTION_PROTOCOLS,
                query=query_vector,
                query_filter=Filter(
                    must=[FieldCondition(key="is_protocol_premium", match=MatchValue(value=True))]
                ),
                limit=1,
                with_payload=True
            )
            
            if not results.points:
                return False, "Aucun protocole premium"
            
            hit = results.points[0]
            actual_name = hit.payload.get("protocol_name", "")
            
            if hit.score < min_score:
                return False, f"Score trop bas: {hit.score:.3f}"
            
            if test.get("expected_name") and actual_name != test["expected_name"]:
                return False, f"Mauvais protocole: {actual_name}"
            
            return True, f"OK (score: {hit.score:.3f}, proto: {actual_name})"
        
        elif expected_type == "mixed":
            qtype = analyze_question(question)
            if not qtype.is_mixed:
                return False, "Non détecté comme mixte"
            
            # Recherche protocole
            proto_results = client.query_points(
                collection_name=COLLECTION_PROTOCOLS,
                query=query_vector,
                query_filter=Filter(
                    must=[FieldCondition(key="is_protocol_premium", match=MatchValue(value=True))]
                ),
                limit=1,
                with_payload=True
            )
            
            if proto_results.points:
                proto_name = proto_results.points[0].payload.get("protocol_name", "")
                proto_score = proto_results.points[0].score
                
                if test.get("expected_protocol") and proto_name != test["expected_protocol"]:
                    return False, f"Mauvais protocole: {proto_name}"
                
                return True, f"OK mixte (proto: {proto_name}, score: {proto_score:.3f})"
            
            return False, "Pas de protocole premium trouvé"
        
        elif expected_type == "out_of_scope":
            # Pour hors scope, on vérifie juste que ça ne crash pas
            results = client.query_points(
                collection_name=COLLECTION_PRODUCTS,
                query=query_vector,
                limit=1,
                with_payload=True
            )
            
            if results.points and results.points[0].score > 0.6:
                return False, f"Score trop haut pour OOS: {results.points[0].score:.3f}"
            
            return True, f"OK (low score ou safe mode)"
        
        return False, "Type de test inconnu"
        
    except Exception as e:
        return False, f"ERREUR: {str(e)}"


def run_regression_tests():
    """Exécute tous les tests de régression."""
    print("\n" + "=" * 80)
    print("🧪 TESTS DE RÉGRESSION MINA BÊTA V2")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    categories = {
        "PROD": "📦 PRODUITS",
        "PROTO": "🏥 PROTOCOLES",
        "MIX": "🔀 MIXTES",
        "OOS": "❓ HORS SCOPE"
    }
    
    current_cat = None
    
    for test in REGRESSION_TESTS:
        test_id = test["id"]
        cat = test_id.split("-")[0]
        
        if cat != current_cat:
            current_cat = cat
            print(f"\n{'-'*60}")
            print(f"{categories.get(cat, cat)}")
            print(f"{'-'*60}")
        
        success, message = run_single_test(client, test)
        
        if success:
            results["passed"] += 1
            status = "✅"
        else:
            results["failed"] += 1
            results["errors"].append({"id": test_id, "message": message})
            status = "❌"
        
        # Affichage condensé
        q_short = test["question"][:45] + "..." if len(test["question"]) > 45 else test["question"]
        print(f"  {status} [{test_id}] {q_short}")
        if not success:
            print(f"      → {message}")
    
    # Rapport final
    total = results["passed"] + results["failed"]
    pct = (results["passed"] / total * 100) if total > 0 else 0
    
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    print(f"\n  ✅ Passés: {results['passed']}/{total} ({pct:.1f}%)")
    print(f"  ❌ Échoués: {results['failed']}/{total}")
    
    if results["errors"]:
        print("\n  📋 Détail des échecs:")
        for err in results["errors"]:
            print(f"     • [{err['id']}] {err['message']}")
    
    # Verdict
    print("\n" + "-" * 60)
    if pct >= 95:
        print("  🎯 VERDICT: BÊTA PRÊTE POUR DÉMO")
    elif pct >= 85:
        print("  ⚠️ VERDICT: CORRECTIONS MINEURES NÉCESSAIRES")
    else:
        print("  ❌ VERDICT: CORRECTIONS MAJEURES REQUISES")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    run_regression_tests()
