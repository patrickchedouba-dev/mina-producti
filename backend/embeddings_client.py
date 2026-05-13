"""
Client pour la génération d'embeddings via Vertex AI ou Google GenAI.
Gère le batching et les retries automatiques.
"""

import logging
from typing import List, Optional
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

logger = logging.getLogger(__name__)


class EmbeddingsClient(ABC):
    """Interface abstraite pour les clients d'embeddings."""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Génère l'embedding d'un texte unique."""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Génère les embeddings d'un batch de textes."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension des vecteurs générés."""
        pass


class VertexAIEmbeddings(EmbeddingsClient):
    """
    Client d'embeddings utilisant Vertex AI.
    
    Utilise le modèle text-embedding-004 de Google.
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        Initialise le client Vertex AI.
        
        Args:
            project_id: ID du projet GCP
            location: Région Vertex AI
            model_name: Nom du modèle d'embedding
        """
        self.project_id = project_id or settings.gcs_project_id
        self.location = location or settings.vertex_ai_location
        self.model_name = model_name or settings.embedding_model
        self._model = None
        
        logger.info(
            f"VertexAI Embeddings: model={self.model_name}, "
            f"location={self.location}"
        )
    
    @property
    def model(self):
        """Accès lazy au modèle Vertex AI."""
        if self._model is None:
            from google.cloud import aiplatform
            from vertexai.language_models import TextEmbeddingModel
            
            aiplatform.init(
                project=self.project_id,
                location=self.location
            )
            self._model = TextEmbeddingModel.from_pretrained(self.model_name)
            logger.debug(f"Modèle Vertex AI chargé: {self.model_name}")
        return self._model
    
    @property
    def dimension(self) -> int:
        """Dimension des vecteurs (768 pour text-embedding-004)."""
        return settings.embedding_dimension
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def embed_text(self, text: str) -> List[float]:
        """
        Génère l'embedding d'un texte.
        
        Args:
            text: Texte à vectoriser
        
        Returns:
            Vecteur d'embedding
        """
        embeddings = self.model.get_embeddings([text])
        return embeddings[0].values
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Génère les embeddings d'un batch de textes.
        
        Args:
            texts: Liste de textes à vectoriser
        
        Returns:
            Liste de vecteurs d'embedding
        """
        if not texts:
            return []
        
        logger.debug(f"Batch embedding: {len(texts)} textes")
        embeddings = self.model.get_embeddings(texts)
        return [e.values for e in embeddings]


class GoogleGenAIEmbeddings(EmbeddingsClient):
    """
    Client d'embeddings utilisant Google Generative AI.
    
    Alternative à Vertex AI pour les cas d'usage plus simples.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialise le client Google GenAI.
        
        Args:
            model_name: Nom du modèle d'embedding
        """
        self.model_name = model_name or f"models/{settings.embedding_model}"
        self._client = None
        
        logger.info(f"Google GenAI Embeddings: model={self.model_name}")
    
    @property
    def client(self):
        """Accès lazy au client GenAI."""
        if self._client is None:
            from google import genai
            genai.configure()
            self._client = genai
            logger.debug("Client Google GenAI configuré")
        return self._client
    
    @property
    def dimension(self) -> int:
        """Dimension des vecteurs."""
        return settings.embedding_dimension
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def embed_text(self, text: str) -> List[float]:
        """
        Génère l'embedding d'un texte.
        
        Args:
            text: Texte à vectoriser
        
        Returns:
            Vecteur d'embedding
        """
        result = self.client.embed_content(
            model=self.model_name,
            content=text,
            task_type="retrieval_document"
        )
        return result["embedding"]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Génère les embeddings d'un batch de textes.
        
        Args:
            texts: Liste de textes à vectoriser
        
        Returns:
            Liste de vecteurs d'embedding
        """
        if not texts:
            return []
        
        logger.debug(f"Batch embedding GenAI: {len(texts)} textes")
        embeddings = []
        
        for text in texts:
            result = self.client.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result["embedding"])
        
        return embeddings


class BatchEmbedder:
    """
    Wrapper pour gérer le batching des embeddings.
    
    Divise automatiquement les textes en batchs de taille optimale
    pour l'API d'embeddings.
    """
    
    def __init__(
        self,
        client: EmbeddingsClient,
        batch_size: Optional[int] = None
    ):
        """
        Initialise le batch embedder.
        
        Args:
            client: Client d'embeddings à utiliser
            batch_size: Taille des batchs (défaut: config)
        """
        self.client = client
        self.batch_size = batch_size or settings.embedding_batch_size
        
        logger.info(f"BatchEmbedder initialisé: batch_size={self.batch_size}")
    
    def embed_all(
        self,
        texts: List[str],
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        Génère les embeddings pour tous les textes.
        
        Args:
            texts: Liste complète de textes
            show_progress: Afficher la progression
        
        Returns:
            Liste de tous les vecteurs d'embedding
        """
        if not texts:
            return []
        
        all_embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            if show_progress:
                logger.info(
                    f"Batch {batch_num}/{total_batches}: "
                    f"{len(batch)} textes"
                )
            
            try:
                batch_embeddings = self.client.embed_batch(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Erreur batch {batch_num}: {e}")
                # Génère des vecteurs nuls en cas d'échec
                null_vectors = [
                    [0.0] * self.client.dimension
                    for _ in batch
                ]
                all_embeddings.extend(null_vectors)
        
        logger.info(
            f"Embedding terminé: {len(all_embeddings)} vecteurs générés"
        )
        return all_embeddings


def get_embeddings_client() -> EmbeddingsClient:
    """
    Factory pour obtenir le client d'embeddings configuré.
    
    Returns:
        Client d'embeddings selon la configuration
    """
    provider = settings.embeddings_provider.lower()
    
    if provider == "vertex":
        return VertexAIEmbeddings()
    elif provider == "genai":
        return GoogleGenAIEmbeddings()
    else:
        logger.warning(
            f"Provider inconnu '{provider}', utilisation de Vertex AI"
        )
        return VertexAIEmbeddings()


def get_batch_embedder() -> BatchEmbedder:
    """Factory pour obtenir un batch embedder configuré."""
    client = get_embeddings_client()
    return BatchEmbedder(client)
