"""
Outil MCP Knowledge - Recherche RAG dans Qdrant.

Réutilise le backend/qdrant_client.py existant, ne recrée PAS le RAG.
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def search_knowledge(
    query: str,
    collection: str = "mina_documents",
    limit: int = 3,
    score_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Recherche sémantique dans la base de connaissances Body Minute.
    
    Utilise le système RAG Qdrant existant pour trouver les informations
    les plus pertinentes pour la requête.
    
    Args:
        query: Question ou requête de recherche
        collection: Collection Qdrant (bodyminute_docs, bodyminute_products)
        limit: Nombre maximum de résultats
        score_threshold: Score minimum de pertinence
        
    Returns:
        Dict avec:
        - results: Liste des résultats trouvés
        - query: Requête originale
        - collection: Collection utilisée
        - success: True si recherche réussie
    """
    logger.info(f"🔍 [MCP:knowledge] Recherche: '{query[:50]}...' dans {collection}")
    
    try:
        # Import lazy pour éviter import circulaire
        from backend.qdrant_client import get_qdrant_client
        from backend.embeddings_client import get_embeddings_client
        
        # Générer l'embedding de la requête
        embeddings_client = get_embeddings_client()
        query_vector = embeddings_client.embed_text(query)
        
        # Recherche dans Qdrant
        qdrant = get_qdrant_client()
        results = qdrant.client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold
        ).points
        
        # Formater les résultats
        formatted_results = []
        for result in results:
            formatted_results.append({
                "text": result.payload.get("text", "")[:500],
                "score": round(result.score, 3),
                "source": result.payload.get("source", ""),
                "metadata": {
                    k: v for k, v in result.payload.items()
                    if k not in ["text", "source", "vector"]
                }
            })
        
        logger.info(f"✅ [MCP:knowledge] {len(formatted_results)} résultats trouvés")
        
        return {
            "success": True,
            "query": query,
            "collection": collection,
            "results": formatted_results,
            "count": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"❌ [MCP:knowledge] Erreur: {e}")
        return {
            "success": False,
            "query": query,
            "collection": collection,
            "results": [],
            "count": 0,
            "error": str(e)
        }


# Métadonnées de l'outil pour le LLM
TOOL_METADATA = {
    "name": "search_knowledge",
    "description": "Recherche des informations dans la base de connaissances Body Minute (produits, soins, protocoles). Utilise toujours cet outil avant de répondre à une question sur les produits ou services.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "La question ou requête de recherche"
            },
            "collection": {
                "type": "string",
                "enum": ["mina_documents"],
                "description": "Collection Qdrant à chercher."
            },
            "limit": {
                "type": "integer",
                "description": "Nombre maximum de résultats (défaut: 3)",
                "default": 3
            }
        },
        "required": ["query"]
    }
}
