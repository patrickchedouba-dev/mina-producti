#!/usr/bin/env python3
"""
Script de validation des modes dégradés (fallbacks).
Vérifie que Mina peut fonctionner même sans certains services.

Usage:
    python scripts/validate_fallbacks.py
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"🔍 {title}")
    print("=" * 60)

def test_google_genai():
    """Test du mode Google Generative AI."""
    print_header("TEST 1: Google Generative AI (Embeddings)")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY non défini")
        return False
    
    try:
        from google import genai
        genai.configure(api_key=api_key)
        
        result = genai.embed_content(
            model="models/embedding-001",
            content="Test Body Minute",
            task_type="retrieval_document"
        )
        
        embedding = result['embedding']
        print(f"✅ Google GenAI OK - Dimensions: {len(embedding)}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Google GenAI: {e}")
        return False

def test_gemini_llm():
    """Test du LLM Gemini."""
    print_header("TEST 2: Gemini LLM (Génération)")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY non défini")
        return False
    
    try:
        from google import genai
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Dis 'OK' en un mot.")
        
        print(f"✅ Gemini LLM OK - Réponse: {response.text[:50]}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Gemini: {e}")
        return False

def test_qdrant():
    """Test de la connexion Qdrant."""
    print_header("TEST 3: Qdrant Cloud (Vector DB)")
    
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    
    if not url:
        print("❌ QDRANT_URL non défini")
        return False
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(url=url, api_key=api_key)
        collections = client.get_collections()
        
        print(f"✅ Qdrant OK - Collections: {len(collections.collections)}")
        for c in collections.collections:
            print(f"   - {c.name}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Qdrant: {e}")
        return False

def test_products_json():
    """Test du fichier produits."""
    print_header("TEST 4: Fichier Produits (data/products_external.json)")
    
    path = "data/products_external.json"
    if not os.path.exists(path):
        print(f"❌ Fichier {path} non trouvé")
        return False
    
    try:
        import json
        with open(path, 'r') as f:
            data = json.load(f)
        
        products = data.get('products', [])
        print(f"✅ Fichier OK - {len(products)} produits")
        
        # Vérifier les URLs images
        valid_imgs = sum(1 for p in products if p.get('image_url', '').startswith('http'))
        print(f"   - Images valides: {valid_imgs}/{len(products)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lecture JSON: {e}")
        return False

def test_local_fallback():
    """Test du mode local (SentenceTransformers)."""
    print_header("TEST 5: Mode Local (SentenceTransformers)")
    
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        embedding = model.encode(["Test local"])[0]
        print(f"✅ Mode Local OK - Dimensions: {len(embedding)}")
        print(f"⚠️  ATTENTION: 384D != 768D (incompatible avec index Qdrant actuel)")
        return True
        
    except ImportError:
        print("❌ sentence-transformers non installé")
        print("   Pour installer: pip install sentence-transformers")
        return False
    except Exception as e:
        print(f"❌ Erreur mode local: {e}")
        return False

def main():
    """Exécute tous les tests de validation."""
    print("\n" + "=" * 60)
    print("🚀 VALIDATION DES FALLBACKS - MINA BODY TOUCH")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Charger .env
    from dotenv import load_dotenv
    load_dotenv()
    
    results = {
        "Google GenAI": test_google_genai(),
        "Gemini LLM": test_gemini_llm(),
        "Qdrant Cloud": test_qdrant(),
        "Products JSON": test_products_json(),
        "Local Fallback": test_local_fallback(),
    }
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    
    for name, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"{status} {name}")
    
    passed = sum(results.values())
    total = len(results)
    
    print("\n" + "-" * 60)
    print(f"Score: {passed}/{total} ({100*passed//total}%)")
    
    if passed == total:
        print("🎉 TOUS LES SERVICES OPÉRATIONNELS")
    elif passed >= 3:
        print("⚠️  FONCTIONNEMENT DÉGRADÉ POSSIBLE")
    else:
        print("🔴 SERVICES CRITIQUES MANQUANTS")
    
    print("=" * 60 + "\n")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
