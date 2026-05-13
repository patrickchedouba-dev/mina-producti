#!/usr/bin/env python3
"""
Script de test de connexion à Qdrant Cloud.
Vérifie les credentials et crée une collection de test.
"""

import os
import sys

# Ajout du path pour importer le backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_connection_simple():
    """
    Test de connexion simple à Qdrant Cloud.
    Utilise uniquement les variables d'environnement.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    # Récupération des variables
    qdrant_url = os.getenv("QDRANT_URL", "")
    qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "mina_documents")
    
    print("\n" + "=" * 60)
    print("🔌 TEST CONNEXION QDRANT CLOUD")
    print("=" * 60)
    
    # Vérification configuration
    if not qdrant_url:
        print("❌ ERREUR: QDRANT_URL non défini dans .env")
        print("   Créez un compte sur https://cloud.qdrant.io")
        print("   Puis ajoutez QDRANT_URL dans votre fichier .env")
        return False
    
    if not qdrant_api_key:
        print("⚠️  ATTENTION: QDRANT_API_KEY non défini")
        print("   La connexion peut échouer sans API key")
    
    print(f"\n📡 URL: {qdrant_url[:50]}...")
    print(f"🔑 API Key: {'***' + qdrant_api_key[-4:] if qdrant_api_key else 'Non définie'}")
    print(f"📁 Collection: {collection_name}")
    
    # Test de connexion
    print("\n⏳ Test de connexion...")
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key if qdrant_api_key else None,
        )
        
        # Liste des collections
        collections = client.get_collections()
        
        print(f"\n✅ CONNEXION RÉUSSIE!")
        print(f"   Collections existantes: {len(collections.collections)}")
        
        for coll in collections.collections:
            print(f"   - {coll.name}")
        
        # Test création collection si elle n'existe pas
        existing_names = [c.name for c in collections.collections]
        
        if collection_name not in existing_names:
            print(f"\n📦 Création collection '{collection_name}'...")
            
            from qdrant_client.http.models import VectorParams, Distance
            
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=768,  # Dimension text-embedding-004
                    distance=Distance.COSINE
                )
            )
            print(f"   ✅ Collection '{collection_name}' créée!")
        else:
            print(f"\n📦 Collection '{collection_name}' existe déjà")
            
            # Afficher les stats
            info = client.get_collection(collection_name)
            print(f"   Vecteurs: {info.vectors_count}")
            print(f"   Points: {info.points_count}")
        
        print("\n" + "=" * 60)
        print("✅ QDRANT CLOUD PRÊT POUR L'INGESTION")
        print("=" * 60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR DE CONNEXION: {e}")
        print("\nVérifiez:")
        print("  1. L'URL est correcte (commence par https://)")
        print("  2. L'API Key est valide")
        print("  3. Le cluster Qdrant est actif")
        return False


def test_with_backend():
    """
    Test de connexion via le module backend.
    """
    print("\n" + "=" * 60)
    print("🔌 TEST VIA MODULE BACKEND")
    print("=" * 60)
    
    try:
        from backend.qdrant_client import get_qdrant_client
        
        client = get_qdrant_client()
        client.test_connection()
        
        # Vérifier/créer la collection
        if not client.collection_exists():
            client.create_collection(vector_size=768)
        
        info = client.get_collection_info()
        print(f"\n📊 Stats collection:")
        print(f"   Nom: {info['name']}")
        print(f"   Vecteurs: {info['vectors_count']}")
        
        print("\n✅ Backend configuré correctement!")
        return True
        
    except ImportError as e:
        print(f"\n⚠️  Dépendances manquantes: {e}")
        print("   Exécutez: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return False


if __name__ == "__main__":
    # Test simple (sans dépendances backend)
    if len(sys.argv) > 1 and sys.argv[1] == "--backend":
        success = test_with_backend()
    else:
        success = test_connection_simple()
    
    sys.exit(0 if success else 1)
