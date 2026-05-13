"""
Package backend pour le pipeline de vectorisation Mina.

Ce package contient tous les modules nécessaires pour:
- Connexion à Google Cloud Storage
- Extraction de texte depuis PDF/TXT/DOCX
- Découpage en chunks avec chevauchement
- Génération d'embeddings via Vertex AI ou Google GenAI
- Stockage et recherche dans Qdrant
"""

from .config import settings, setup_logging
from .gcs_client import GCSClient, DocumentInfo, get_gcs_client
from .text_extraction import TextExtractor, ExtractionResult, get_text_extractor
from .chunking import TextChunker, TextChunk, get_chunker
from .embeddings_client import (
    EmbeddingsClient,
    VertexAIEmbeddings,
    GoogleGenAIEmbeddings,
    BatchEmbedder,
    get_embeddings_client,
    get_batch_embedder,
)
from .qdrant_client import (
    QdrantVectorClient,
    SearchResult,
    get_qdrant_client,
)
from .ingest_pipeline import IngestionPipeline, IngestionStats
from .conversation_state import (
    StateType,
    ConversationState,
    detect_state,
    detect_hesitation_patterns,
)
from .conversation_rules import (
    ConversationRule,
    CONVERSATION_CODE,
    get_rule_for_state,
    apply_rule,
    transform_response_with_state,
)
from .tension_analyzer import (
    TensionLevel,
    TensionAnalysis,
    get_tension_level,
    analyze_tension_from_text,
)

__all__ = [
    # Config
    "settings",
    "setup_logging",
    # GCS
    "GCSClient",
    "DocumentInfo",
    "get_gcs_client",
    # Text Extraction
    "TextExtractor",
    "ExtractionResult",
    "get_text_extractor",
    # Chunking
    "TextChunker",
    "TextChunk",
    "get_chunker",
    # Embeddings
    "EmbeddingsClient",
    "VertexAIEmbeddings",
    "GoogleGenAIEmbeddings",
    "BatchEmbedder",
    "get_embeddings_client",
    "get_batch_embedder",
    # Qdrant
    "QdrantVectorClient",
    "SearchResult",
    "get_qdrant_client",
    # Pipeline
    "IngestionPipeline",
    "IngestionStats",
    # Conversation State (Code de la Conversation)
    "StateType",
    "ConversationState",
    "detect_state",
    "detect_hesitation_patterns",
    "ConversationRule",
    "CONVERSATION_CODE",
    "get_rule_for_state",
    "apply_rule",
    "transform_response_with_state",
    # Tension Vocale
    "TensionLevel",
    "TensionAnalysis",
    "get_tension_level",
    "analyze_tension_from_text",
]

__version__ = "0.1.0"
