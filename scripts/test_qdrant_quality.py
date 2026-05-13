#!/usr/bin/env python3
"""
Test de qualité des vectors Qdrant.
Analyse 20 chunks aléatoires de la collection bodyminute_docs
pour vérifier la qualité du contenu indexé.
"""

import os
import sys
import random
import re
from typing import Dict, List, Any
from datetime import datetime

# Configuration du path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_secrets_from_gcp():
    """Charge les secrets depuis Secret Manager GCP."""
    try:
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT", "bodycoachocr")
        
        secrets = {}
        secret_names = ["QDRANT_URL", "QDRANT_API_KEY"]
        
        for secret_name in secret_names:
            try:
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                secrets[secret_name] = response.payload.data.decode("UTF-8")
                print(f"✅ Secret {secret_name} chargé depuis GCP")
            except Exception as e:
                print(f"⚠️ Secret {secret_name} non trouvé: {e}")
        
        return secrets
    except ImportError:
        print("⚠️ google-cloud-secret-manager non installé, utilisation des env vars")
        return {}
    except Exception as e:
        print(f"⚠️ Erreur Secret Manager: {e}")
        return {}


def get_qdrant_credentials():
    """Récupère les credentials Qdrant (secrets GCP ou env vars)."""
    # Essayer les secrets GCP d'abord
    secrets = load_secrets_from_gcp()
    
    qdrant_url = secrets.get("QDRANT_URL") or os.getenv("QDRANT_URL", "")
    qdrant_api_key = secrets.get("QDRANT_API_KEY") or os.getenv("QDRANT_API_KEY", "")
    
    return qdrant_url, qdrant_api_key


def analyze_chunk_content(text: str) -> Dict[str, Any]:
    """
    Analyse le contenu d'un chunk pour évaluer sa qualité.
    
    Returns:
        Dict avec les métriques de qualité
    """
    analysis = {
        "length": len(text),
        "word_count": len(text.split()),
        "is_french": False,
        "has_prices": False,
        "has_products": False,
        "has_bodyminute_keywords": False,
        "quality_score": 0,
        "issues": []
    }
    
    # Détection du français (mots courants)
    french_words = ["de", "la", "le", "les", "et", "en", "un", "une", "du", "des", 
                    "pour", "avec", "sur", "par", "dans", "que", "qui", "est", "sont"]
    text_lower = text.lower()
    french_count = sum(1 for word in french_words if f" {word} " in f" {text_lower} ")
    analysis["is_french"] = french_count >= 3
    
    # Détection des prix (euros)
    price_patterns = [
        r'\d+[.,]\d{2}\s*€',
        r'\d+\s*€',
        r'\d+[.,]\d{2}\s*euros?',
        r'tarif',
        r'prix'
    ]
    for pattern in price_patterns:
        if re.search(pattern, text_lower):
            analysis["has_prices"] = True
            break
    
    # Produits et services Body Minute
    product_keywords = [
        "épilation", "cire", "vernis", "manucure", "pédicure",
        "soin", "massage", "beauté", "esthétique", "institut",
        "sourcils", "jambes", "maillot", "aisselles", "visage",
        "gel", "semi-permanent", "ongle", "nail", "lash", "cils"
    ]
    for keyword in product_keywords:
        if keyword in text_lower:
            analysis["has_products"] = True
            break
    
    # Keywords spécifiques Body Minute
    bodyminute_keywords = [
        "body minute", "bodyminute", "body'minute",
        "nail minute", "hair minute", "brow minute"
    ]
    for keyword in bodyminute_keywords:
        if keyword in text_lower:
            analysis["has_bodyminute_keywords"] = True
            break
    
    # Calcul du score de qualité (0-100)
    score = 0
    
    # Longueur appropriée (200-1000 caractères idéal)
    if 200 <= analysis["length"] <= 1000:
        score += 25
    elif 100 <= analysis["length"] < 200 or 1000 < analysis["length"] <= 1500:
        score += 15
    else:
        analysis["issues"].append(f"Longueur non optimale: {analysis['length']} chars")
    
    # Contenu français
    if analysis["is_french"]:
        score += 25
    else:
        analysis["issues"].append("Peu de contenu français détecté")
    
    # Contenu métier (prix ou produits)
    if analysis["has_prices"]:
        score += 20
    if analysis["has_products"]:
        score += 20
    if analysis["has_bodyminute_keywords"]:
        score += 10
    
    # Pénalités
    if analysis["length"] < 50:
        score -= 30
        analysis["issues"].append("Chunk trop court")
    
    # Détection de contenu garbage
    garbage_indicators = ["lorem ipsum", "undefined", "null", "NaN", "###", "---"]
    for indicator in garbage_indicators:
        if indicator in text_lower:
            score -= 20
            analysis["issues"].append(f"Contenu suspect: '{indicator}'")
    
    analysis["quality_score"] = max(0, min(100, score))
    
    return analysis


def run_quality_test():
    """Exécute le test de qualité sur les vectors Qdrant."""
    print("\n" + "=" * 70)
    print("🔍 TEST QUALITÉ VECTORS QDRANT")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Connexion Qdrant
    qdrant_url, qdrant_api_key = get_qdrant_credentials()
    
    if not qdrant_url:
        print("\n❌ ERREUR: QDRANT_URL non configuré")
        print("   Vérifiez les secrets GCP ou les variables d'environnement")
        return False
    
    print(f"\n📡 Connexion à: {qdrant_url[:50]}...")
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key if qdrant_api_key else None
        )
        
        collection_name = os.getenv("QDRANT_COLLECTION_NAME", "bodyminute_docs")
        
        # Vérifier la collection
        try:
            info = client.get_collection(collection_name)
            total_vectors = info.points_count
            print(f"\n✅ Collection '{collection_name}' trouvée")
            print(f"   📊 Total vectors: {total_vectors}")
        except Exception as e:
            print(f"\n❌ Collection '{collection_name}' non trouvée: {e}")
            return False
        
        if total_vectors == 0:
            print("\n⚠️ La collection est vide!")
            return False
        
        # Récupérer 20 points aléatoires
        sample_size = min(20, total_vectors)
        print(f"\n🎲 Récupération de {sample_size} chunks aléatoires...")
        
        # Scroll pour récupérer tous les points puis sélectionner aléatoirement
        all_points = []
        offset = None
        
        while len(all_points) < total_vectors:
            result = client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            points, offset = result
            all_points.extend(points)
            
            if offset is None:
                break
        
        # Sélection aléatoire
        sample_points = random.sample(all_points, sample_size)
        
        # Analyse de chaque chunk
        print("\n" + "-" * 70)
        print("📝 ANALYSE DES CHUNKS")
        print("-" * 70)
        
        quality_scores = []
        french_count = 0
        prices_count = 0
        products_count = 0
        bodyminute_count = 0
        
        for i, point in enumerate(sample_points, 1):
            payload = point.payload or {}
            text = payload.get("text", payload.get("content", payload.get("chunk", "")))
            source = payload.get("source", payload.get("filename", "Unknown"))
            
            if not text:
                print(f"\n⚠️ Chunk #{i}: Pas de texte trouvé dans le payload")
                print(f"   Keys disponibles: {list(payload.keys())}")
                continue
            
            analysis = analyze_chunk_content(text)
            quality_scores.append(analysis["quality_score"])
            
            if analysis["is_french"]:
                french_count += 1
            if analysis["has_prices"]:
                prices_count += 1
            if analysis["has_products"]:
                products_count += 1
            if analysis["has_bodyminute_keywords"]:
                bodyminute_count += 1
            
            # Affichage du chunk
            print(f"\n📄 Chunk #{i} (ID: {point.id})")
            print(f"   Source: {source}")
            print(f"   Longueur: {analysis['length']} chars, {analysis['word_count']} mots")
            print(f"   Score qualité: {'🟢' if analysis['quality_score'] >= 70 else '🟡' if analysis['quality_score'] >= 40 else '🔴'} {analysis['quality_score']}/100")
            
            # Indicateurs
            indicators = []
            if analysis["is_french"]:
                indicators.append("🇫🇷 Français")
            if analysis["has_prices"]:
                indicators.append("💰 Prix")
            if analysis["has_products"]:
                indicators.append("💅 Produits")
            if analysis["has_bodyminute_keywords"]:
                indicators.append("✨ Body Minute")
            
            if indicators:
                print(f"   Indicateurs: {' | '.join(indicators)}")
            
            if analysis["issues"]:
                print(f"   ⚠️ Issues: {', '.join(analysis['issues'])}")
            
            # Extrait du texte
            text_preview = text[:200].replace('\n', ' ').strip()
            if len(text) > 200:
                text_preview += "..."
            print(f"   Extrait: \"{text_preview}\"")
        
        # Rapport final
        print("\n" + "=" * 70)
        print("📊 RAPPORT DE QUALITÉ")
        print("=" * 70)
        
        if quality_scores:
            avg_score = sum(quality_scores) / len(quality_scores)
            min_score = min(quality_scores)
            max_score = max(quality_scores)
            
            print(f"\n📈 STATISTIQUES SUR {len(quality_scores)} CHUNKS:")
            print(f"   Score moyen:  {'🟢' if avg_score >= 70 else '🟡' if avg_score >= 40 else '🔴'} {avg_score:.1f}/100")
            print(f"   Score min:    {min_score}/100")
            print(f"   Score max:    {max_score}/100")
            
            print(f"\n📋 RÉPARTITION DU CONTENU:")
            print(f"   🇫🇷 Contenu français: {french_count}/{len(quality_scores)} ({100*french_count/len(quality_scores):.0f}%)")
            print(f"   💰 Contiennent des prix: {prices_count}/{len(quality_scores)} ({100*prices_count/len(quality_scores):.0f}%)")
            print(f"   💅 Contiennent des produits: {products_count}/{len(quality_scores)} ({100*products_count/len(quality_scores):.0f}%)")
            print(f"   ✨ Mentions Body Minute: {bodyminute_count}/{len(quality_scores)} ({100*bodyminute_count/len(quality_scores):.0f}%)")
            
            # Score global
            high_quality = sum(1 for s in quality_scores if s >= 70)
            medium_quality = sum(1 for s in quality_scores if 40 <= s < 70)
            low_quality = sum(1 for s in quality_scores if s < 40)
            
            print(f"\n🎯 DISTRIBUTION QUALITÉ:")
            print(f"   🟢 Excellente (>=70): {high_quality} chunks")
            print(f"   🟡 Moyenne (40-69):   {medium_quality} chunks")
            print(f"   🔴 Faible (<40):      {low_quality} chunks")
            
            # Verdict final
            print("\n" + "=" * 70)
            if avg_score >= 70:
                print("✅ VERDICT: QUALITÉ EXCELLENTE")
                print("   Les vectors sont de bonne qualité et pertinents.")
            elif avg_score >= 50:
                print("🟡 VERDICT: QUALITÉ ACCEPTABLE")
                print("   La plupart des vectors sont utilisables mais certains pourraient être améliorés.")
            else:
                print("🔴 VERDICT: QUALITÉ INSUFFISANTE")
                print("   Les vectors nécessitent une révision du pipeline d'indexation.")
            print("=" * 70 + "\n")
        
        return True
        
    except ImportError as e:
        print(f"\n❌ Dépendance manquante: {e}")
        print("   Installez: pip install qdrant-client")
        return False
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_quality_test()
    sys.exit(0 if success else 1)
