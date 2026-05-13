"""
Configuration centralisée pour le pipeline de vectorisation Mina.
Charge toutes les variables d'environnement et fournit des valeurs par défaut.
"""

import os
import logging
from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()


class Settings(BaseSettings):
    """
    Configuration globale du pipeline.
    Toutes les valeurs sensibles proviennent des variables d'environnement.
    """
    
    # --- Google Cloud Storage ---
    gcs_bucket_name: str = Field(
        default="bodyminute-docs-storage",
        description="Nom du bucket GCS contenant les documents"
    )
    gcs_project_id: str = Field(
        default="",
        description="ID du projet Google Cloud"
    )
    google_application_credentials: str = Field(
        default="",
        description="Chemin vers le fichier de credentials GCP"
    )
    
    # --- Qdrant Vector Database ---
    # Pour Qdrant Cloud: utiliser QDRANT_URL (ex: https://xxx.cloud.qdrant.io)
    # Pour local: utiliser QDRANT_HOST + QDRANT_PORT
    qdrant_url: str = Field(
        default="",
        description="URL complète Qdrant Cloud (prioritaire sur host/port)"
    )
    qdrant_host: str = Field(
        default="localhost",
        description="Hôte du serveur Qdrant (ignoré si qdrant_url défini)"
    )
    qdrant_port: int = Field(
        default=6333,
        description="Port du serveur Qdrant (ignoré si qdrant_url défini)"
    )
    qdrant_api_key: str = Field(
        default="",
        description="Clé API Qdrant (requis pour Qdrant Cloud)"
    )
    qdrant_collection_name: str = Field(
        default="mina_documents",
        description="Nom de la collection Qdrant"
    )
    
    @property
    def is_qdrant_cloud(self) -> bool:
        """Vérifie si on utilise Qdrant Cloud."""
        return bool(self.qdrant_url)
    
    # --- Embeddings Configuration ---
    embeddings_provider: Literal["vertex", "genai"] = Field(
        default="vertex",
        description="Provider d'embeddings: 'vertex' ou 'genai'"
    )
    vertex_ai_location: str = Field(
        default="europe-west1",
        description="Région Vertex AI"
    )
    embedding_model: str = Field(
        default="text-embedding-004",
        description="Modèle d'embedding à utiliser"
    )
    embedding_dimension: int = Field(
        default=768,
        description="Dimension des vecteurs d'embedding"
    )
    
    # --- Chunking Parameters ---
    chunk_size: int = Field(
        default=800,
        description="Taille maximale d'un chunk en caractères"
    )
    chunk_overlap: int = Field(
        default=150,
        description="Chevauchement entre chunks en caractères"
    )
    
    # --- Pipeline Settings ---
    embedding_batch_size: int = Field(
        default=100,
        description="Taille des batchs pour les embeddings"
    )
    max_retries: int = Field(
        default=3,
        description="Nombre maximum de tentatives en cas d'erreur"
    )
    log_level: str = Field(
        default="INFO",
        description="Niveau de logging"
    )
    
    # --- Google API (Gemini, etc.) ---
    google_api_key: str = Field(
        default="",
        description="Clé API Google pour Gemini et autres services"
    )
    
    # --- Redis (Short-term Memory) ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL Redis pour cache sessions (mémoire court terme)"
    )
    
    # --- PostgreSQL (Long-term Memory) ---
    postgres_url: str = Field(
        default="postgresql://mina:mina@localhost:5432/mina",
        description="URL PostgreSQL pour historique et profils clients"
    )
    
    # Pydantic V2 configuration
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore les variables d'environnement non définies
    }


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure le logging pour le pipeline.
    
    Args:
        level: Niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Logger configuré pour le module appelant
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger(__name__)


# Instance globale de configuration
settings = Settings()

# Configuration du logging au chargement du module
logger = setup_logging(settings.log_level)
