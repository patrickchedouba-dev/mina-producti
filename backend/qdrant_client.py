"""
Client Qdrant pour le stockage et la recherche de vecteurs.
Gère la création de collection, l'upsert et la recherche sémantique.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from qdrant_client import QdrantClient as Qdrant
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .chunking import TextChunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """
    Résultat d'une recherche sémantique.
    
    Attributes:
        id: ID du point dans Qdrant
        score: Score de similarité
        content: Contenu du chunk
        metadata: Métadonnées complètes
    """
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class QdrantVectorClient:
    """
    Client pour interagir avec Qdrant (local ou cloud).
    
    Supporte deux modes de connexion:
    - Qdrant Cloud: via URL complète + API key
    - Local: via host + port
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        """
        Initialise le client Qdrant.
        
        Args:
            url: URL complète Qdrant Cloud (prioritaire)
            host: Hôte du serveur Qdrant local
            port: Port du serveur Qdrant local
            api_key: Clé API (requis pour cloud)
            collection_name: Nom de la collection
        """
        self.url = url or settings.qdrant_url or None
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.api_key = api_key or settings.qdrant_api_key or None
        self.collection_name = collection_name or settings.qdrant_collection_name
        self._client: Optional[Qdrant] = None
        
        # Déterminer le mode de connexion
        self.is_cloud = bool(self.url)
        
        if self.is_cloud:
            logger.info(
                f"QdrantClient configuré: CLOUD → {self.url[:50]}..., "
                f"collection={self.collection_name}"
            )
        else:
            logger.info(
                f"QdrantClient configuré: LOCAL → {self.host}:{self.port}, "
                f"collection={self.collection_name}"
            )
    
    @property
    def client(self) -> Qdrant:
        """Accès lazy au client Qdrant."""
        if self._client is None:
            if self.is_cloud:
                # Connexion Qdrant Cloud via URL
                logger.debug(f"Connexion Qdrant Cloud: {self.url}")
                self._client = Qdrant(
                    url=self.url,
                    api_key=self.api_key,
                )
            else:
                # Connexion locale via host/port
                logger.debug(f"Connexion Qdrant local: {self.host}:{self.port}")
                self._client = Qdrant(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key if self.api_key else None,
                )
        return self._client
    
    def test_connection(self) -> bool:
        """
        Teste la connexion à Qdrant.
        
        Returns:
            True si la connexion est fonctionnelle
        """
        try:
            collections = self.client.get_collections()
            logger.info(
                f"Connexion Qdrant OK - "
                f"{len(collections.collections)} collections"
            )
            return True
        except Exception as e:
            logger.error(f"Échec connexion Qdrant: {e}")
            raise
    
    def collection_exists(self) -> bool:
        """Vérifie si la collection existe."""
        try:
            collections = self.client.get_collections()
            exists = any(
                c.name == self.collection_name
                for c in collections.collections
            )
            logger.debug(f"Collection {self.collection_name} existe: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Erreur vérification collection: {e}")
            return False
    
    def create_collection(
        self,
        vector_size: int = 768,
        force_recreate: bool = False
    ) -> bool:
        """
        Crée la collection Qdrant.
        
        Args:
            vector_size: Dimension des vecteurs
            force_recreate: Supprimer et recréer si existe
        
        Returns:
            True si la collection a été créée
        """
        if self.collection_exists():
            if force_recreate:
                logger.warning(
                    f"Suppression collection existante: {self.collection_name}"
                )
                self.client.delete_collection(self.collection_name)
            else:
                logger.info(
                    f"Collection {self.collection_name} existe déjà"
                )
                return False
        
        logger.info(
            f"Création collection {self.collection_name} "
            f"(dimension={vector_size})"
        )
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        
        # Création des index pour les métadonnées
        self._create_payload_indexes()
        
        logger.info(f"Collection {self.collection_name} créée avec succès")
        return True
    
    def _create_payload_indexes(self):
        """Crée les index sur les champs de payload."""
        indexed_fields = [
            ("source_path", "keyword"),
            ("doc_type", "keyword"),
            ("chunk_index", "integer"),
        ]
        
        for field_name, field_type in indexed_fields:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                logger.debug(f"Index créé: {field_name} ({field_type})")
            except Exception as e:
                logger.warning(f"Index {field_name} existe peut-être déjà: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upsert_chunks(
        self,
        chunks: List[TextChunk],
        embeddings: List[List[float]]
    ) -> int:
        """
        Insère ou met à jour des chunks dans Qdrant.
        
        Args:
            chunks: Liste de chunks à insérer
            embeddings: Vecteurs correspondants
        
        Returns:
            Nombre de points insérés
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )
        
        if not chunks:
            return 0
        
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=chunk.to_metadata()
            )
            points.append(point)
        
        logger.debug(f"Upsert de {len(points)} points")
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"{len(points)} points insérés dans Qdrant")
        return len(points)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Recherche sémantique dans la collection.
        
        Args:
            query_vector: Vecteur de recherche
            limit: Nombre max de résultats
            filter_conditions: Filtres optionnels
            collection_name: Nom de la collection (override le défaut)
        
        Returns:
            Liste de résultats triés par similarité (liste vide si erreur)
        """
        try:
            # Utiliser la collection spécifiée ou celle par défaut
            target_collection = collection_name or self.collection_name
            
            # Construction du filtre
            query_filter = None
            if filter_conditions:
                must_conditions = []
                for key, value in filter_conditions.items():
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                query_filter = Filter(must=must_conditions)
            
            logger.debug(
                f"Recherche: collection={target_collection}, limit={limit}, filter={filter_conditions}"
            )
            
            results = self.client.search(
                collection_name=target_collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                with_payload=True
            )
            
            search_results = []
            for hit in results:
                search_results.append(
                    SearchResult(
                        id=str(hit.id),
                        score=hit.score,
                        content=hit.payload.get("text", ""),
                        metadata=hit.payload
                    )
                )
            
            logger.info(f"Recherche terminée: {len(search_results)} résultats")
            return search_results
        
        except Exception as e:
            logger.error(f"Erreur recherche Qdrant après 3 tentatives: {e}")
            return []  # Fallback: liste vide pour éviter le crash
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur la collection.
        
        Returns:
            Dictionnaire avec les stats de la collection
        """
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
            "vector_size": info.config.params.vectors.size,
        }
    
    def delete_by_source(self, source_path: str) -> int:
        """
        Supprime tous les chunks d'un document source.
        
        Args:
            source_path: Chemin du document source
        
        Returns:
            Nombre de points supprimés (estimé)
        """
        logger.info(f"Suppression des chunks de: {source_path}")
        
        # Compte avant suppression
        count_before = self.get_collection_info()["points_count"]
        
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_path",
                            match=MatchValue(value=source_path)
                        )
                    ]
                )
            )
        )
        
        # Compte après suppression
        count_after = self.get_collection_info()["points_count"]
        deleted = count_before - count_after
        
        logger.info(f"{deleted} points supprimés")
        return deleted


def get_qdrant_client() -> QdrantVectorClient:
    """Factory pour obtenir un client Qdrant configuré."""
    return QdrantVectorClient()

# --- AUTO PATCH: QDRANT TEXT INDEX HELPER ---
def ensure_text_index(client, collection_name: str, field_name: str = "text") -> bool:
    """
    Ensure a Qdrant full-text payload index exists for `field_name`.
    Returns True if created, False if already existed or could not be created.
    """
    try:
        from qdrant_client import models
    except Exception:
        return False

    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=models.TextIndexParams(
                type=models.TextIndexType.TEXT,
                tokenizer=models.TokenizerType.WORD,
                lowercase=True,
            ),
        )
        return True
    except Exception as e:
        msg = str(e)
        # "already exists" varies by versions; keep broad and non-fatal
        if "already exists" in msg.lower() or "exists" in msg.lower():
            return False
        return False
