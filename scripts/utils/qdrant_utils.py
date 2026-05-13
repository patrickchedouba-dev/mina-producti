#!/usr/bin/env python3
"""
Utilitaires centralisés pour Qdrant.
Point d'accès unique pour tous les scripts du projet Mina.
"""

import os
import sys
from typing import Optional

# Ajouter le backend au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient


def get_qdrant_client() -> QdrantClient:
    """
    Retourne un client Qdrant configuré via les variables d'environnement.
    
    Environnement requis:
        - QDRANT_URL: URL du serveur Qdrant Cloud
        - QDRANT_API_KEY: Clé API Qdrant
    
    Returns:
        QdrantClient connecté et prêt à l'emploi
    """
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    
    if not url or not api_key:
        raise ValueError(
            "Variables QDRANT_URL et QDRANT_API_KEY requises. "
            "Vérifiez votre fichier .env"
        )
    
    return QdrantClient(url=url, api_key=api_key)


def get_collection_name() -> str:
    """Retourne le nom de la collection Qdrant par défaut."""
    return os.getenv("QDRANT_COLLECTION_NAME", "bodyminute_docs")


# Alias pour compatibilité
COLLECTION_PRODUCTS = get_collection_name()
