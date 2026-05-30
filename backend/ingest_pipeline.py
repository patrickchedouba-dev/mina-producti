"""
Pipeline principal d'ingestion des documents Body Minute.
Orchestre le flux GCS → Extraction → Chunking → Embeddings → Qdrant.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field

from .config import settings, setup_logging
from .gcs_client import GCSClient, DocumentInfo, get_gcs_client
from .text_extraction import TextExtractor, get_text_extractor
from .chunking import TextChunker, TextChunk, get_chunker
from .embeddings_client import BatchEmbedder, get_batch_embedder
from .qdrant_client import QdrantVectorClient, get_qdrant_client

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """
    Statistiques d'une session d'ingestion.
    
    Attributes:
        start_time: Heure de début
        end_time: Heure de fin
        documents_processed: Nombre de documents traités
        documents_failed: Nombre de documents en échec
        chunks_created: Nombre total de chunks
        vectors_inserted: Nombre de vecteurs insérés
        errors: Liste des erreurs rencontrées
    """
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    documents_processed: int = 0
    documents_failed: int = 0
    chunks_created: int = 0
    vectors_inserted: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Durée totale en secondes."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Taux de réussite en pourcentage."""
        total = self.documents_processed + self.documents_failed
        if total == 0:
            return 0.0
        return (self.documents_processed / total) * 100
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour le logging."""
        return {
            "duration_seconds": round(self.duration_seconds, 2),
            "documents_processed": self.documents_processed,
            "documents_failed": self.documents_failed,
            "chunks_created": self.chunks_created,
            "vectors_inserted": self.vectors_inserted,
            "success_rate": f"{self.success_rate:.1f}%",
            "errors_count": len(self.errors),
        }


class IngestionPipeline:
    """
    Pipeline complet d'ingestion des documents.
    
    Orchestre toutes les étapes depuis GCS jusqu'à Qdrant.
    """
    
    def __init__(
        self,
        gcs_client: Optional[GCSClient] = None,
        extractor: Optional[TextExtractor] = None,
        chunker: Optional[TextChunker] = None,
        embedder: Optional[BatchEmbedder] = None,
        qdrant_client: Optional[QdrantVectorClient] = None
    ):
        """
        Initialise le pipeline avec les composants.
        
        Args:
            gcs_client: Client GCS (défaut: nouveau)
            extractor: Extracteur de texte (défaut: nouveau)
            chunker: Chunker (défaut: nouveau)
            embedder: Embedder avec batching (défaut: nouveau)
            qdrant_client: Client Qdrant (défaut: nouveau)
        """
        self.gcs = gcs_client or get_gcs_client()
        self.extractor = extractor or get_text_extractor()
        self.chunker = chunker or get_chunker()
        self.embedder = embedder or get_batch_embedder()
        self.qdrant = qdrant_client or get_qdrant_client()
        
        logger.info("Pipeline d'ingestion initialisé")
    
    def setup(self, force_recreate_collection: bool = False) -> bool:
        """
        Configure le pipeline (connexions, collection).
        
        Args:
            force_recreate_collection: Recréer la collection si existe
        
        Returns:
            True si setup réussi
        """
        logger.info("=== SETUP DU PIPELINE ===")
        
        # Test connexion Qdrant
        try:
            self.qdrant.test_connection()
        except Exception as e:
            logger.error(f"Connexion Qdrant impossible: {e}")
            return False
        
        # Création/vérification collection
        self.qdrant.create_collection(
            vector_size=settings.embedding_dimension,
            force_recreate=force_recreate_collection
        )
        
        logger.info("Setup terminé avec succès")
        return True
    
    def process_document(
        self,
        doc_info: DocumentInfo,
        stats: IngestionStats
    ) -> List[TextChunk]:
        """
        Traite un document unique.
        
        Args:
            doc_info: Informations sur le document
            stats: Stats à mettre à jour
        
        Returns:
            Liste des chunks créés
        """
        logger.info(f"Traitement: {doc_info.name}")
        
        try:
            # 1. Téléchargement (ignoré pour PDFs — Document AI lit directement depuis GCS)
            import os
            if os.path.splitext(doc_info.name)[1].lower() == ".pdf":
                logger.debug(f"PDF: lecture directe GCS sans téléchargement")
                gcs_uri = f"gs://mina-pdfs/{doc_info.name}"
                extraction = self.extractor.extract_from_uri(gcs_uri, doc_info.name)
            else:
                content = self.gcs.download_as_bytes(doc_info.name)
                logger.debug(f"Téléchargé: {len(content)} bytes")
                extraction = self.extractor.extract(content, doc_info.name)
            if not extraction.success:
                raise ValueError(f"Extraction échouée: {extraction.error_message}")
            
            if not extraction.text.strip():
                logger.warning(f"Document vide après extraction: {doc_info.name}")
                stats.documents_processed += 1
                return []
            
            # 3. Découpage en chunks
            chunks = self.chunker.chunk_text(
                text=extraction.text,
                source_path=doc_info.name,
                doc_type=doc_info.extension.lstrip(".")
            )
            
            stats.documents_processed += 1
            stats.chunks_created += len(chunks)
            
            logger.info(
                f"Document traité: {len(chunks)} chunks créés"
            )
            return chunks
            
        except Exception as e:
            logger.error(f"Erreur traitement {doc_info.name}: {e}")
            stats.documents_failed += 1
            stats.errors.append(f"{doc_info.name}: {str(e)}")
            return []
    
    def run(
        self,
        prefix: Optional[str] = None,
        limit: Optional[int] = None,
        force_recreate: bool = False
    ) -> IngestionStats:
        """
        Exécute le pipeline complet d'ingestion.
        
        Args:
            prefix: Filtre optionnel par préfixe GCS
            limit: Limite du nombre de documents (pour tests)
            force_recreate: Recréer la collection Qdrant
        
        Returns:
            Statistiques d'ingestion
        """
        stats = IngestionStats()
        
        logger.info("=" * 60)
        logger.info("DÉMARRAGE PIPELINE D'INGESTION MINA")
        logger.info("=" * 60)
        
        # Setup
        if not self.setup(force_recreate_collection=force_recreate):
            logger.error("Setup échoué, arrêt du pipeline")
            stats.end_time = datetime.now()
            return stats
        
        # Collecte des documents
        logger.info("Récupération de la liste des documents...")
        documents = list(self.gcs.list_documents(prefix=prefix))
        
        if limit:
            documents = documents[:limit]
            logger.info(f"Limite appliquée: {limit} documents")
        
        total_docs = len(documents)
        logger.info(f"Documents à traiter: {total_docs}")
        
        # Traitement par batch
        all_chunks: List[TextChunk] = []
        
        for i, doc_info in enumerate(documents, 1):
            logger.info(f"[{i}/{total_docs}] {doc_info.name}")
            chunks = self.process_document(doc_info, stats)
            all_chunks.extend(chunks)
            
            # Upsert par batch quand on a assez de chunks
            if len(all_chunks) >= settings.embedding_batch_size:
                self._embed_and_store(all_chunks, stats)
                all_chunks = []
        
        # Traitement des chunks restants
        if all_chunks:
            self._embed_and_store(all_chunks, stats)
        
        # Finalisation
        stats.end_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("PIPELINE TERMINÉ")
        logger.info(f"Statistiques: {stats.to_dict()}")
        logger.info("=" * 60)
        
        return stats
    
    def _embed_and_store(
        self,
        chunks: List[TextChunk],
        stats: IngestionStats
    ):
        """
        Génère les embeddings et stocke dans Qdrant.
        
        Args:
            chunks: Chunks à traiter
            stats: Stats à mettre à jour
        """
        if not chunks:
            return
        
        logger.info(f"Génération embeddings pour {len(chunks)} chunks...")
        
        try:
            # Génération des embeddings
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedder.embed_all(texts, show_progress=True)
            
            # Stockage dans Qdrant
            inserted = self.qdrant.upsert_chunks(chunks, embeddings)
            stats.vectors_inserted += inserted
            
        except Exception as e:
            logger.error(f"Erreur embed/store: {e}")
            stats.errors.append(f"Batch embed/store: {str(e)}")


def main():
    """Point d'entrée du script d'ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Pipeline d'ingestion Mina - Body Minute"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Préfixe GCS pour filtrer les documents"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite du nombre de documents à traiter"
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Recréer la collection Qdrant"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activer le mode debug"
    )
    
    args = parser.parse_args()
    
    # Configuration du logging
    log_level = "DEBUG" if args.debug else settings.log_level
    setup_logging(log_level)
    
    # Exécution du pipeline
    pipeline = IngestionPipeline()
    stats = pipeline.run(
        prefix=args.prefix,
        limit=args.limit,
        force_recreate=args.force_recreate
    )
    
    # Code de sortie basé sur le succès
    if stats.documents_failed > 0 and stats.documents_processed == 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
