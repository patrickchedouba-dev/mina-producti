"""
Client Google Cloud Storage pour le pipeline Mina.
Gère la connexion au bucket et le listing des documents.
"""

import logging
from pathlib import Path
from typing import Iterator, Optional
from dataclasses import dataclass
from google.cloud import storage
from google.cloud.storage import Blob
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class DocumentInfo:
    """
    Informations sur un document dans GCS.
    
    Attributes:
        name: Nom complet du fichier dans le bucket
        size: Taille en bytes
        content_type: Type MIME du fichier
        bucket_name: Nom du bucket source
    """
    name: str
    size: int
    content_type: Optional[str]
    bucket_name: str
    
    @property
    def extension(self) -> str:
        """Retourne l'extension du fichier en minuscules."""
        return Path(self.name).suffix.lower()
    
    @property
    def is_supported(self) -> bool:
        """Vérifie si le type de document est supporté."""
        supported_extensions = {".pdf", ".txt", ".docx", ".doc"}
        return self.extension in supported_extensions


class GCSClient:
    """
    Client pour interagir avec Google Cloud Storage.
    
    Gère la connexion, le listing des documents et le téléchargement
    du contenu depuis le bucket configuré.
    """
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        """
        Initialise le client GCS.
        
        Args:
            bucket_name: Nom du bucket (défaut: depuis config)
            project_id: ID du projet GCP (défaut: depuis config)
        """
        self.bucket_name = bucket_name or settings.gcs_bucket_name
        self.project_id = project_id or settings.gcs_project_id
        self._client: Optional[storage.Client] = None
        self._bucket: Optional[storage.Bucket] = None
        
        logger.info(
            f"Client GCS initialisé pour bucket: {self.bucket_name}"
        )
    
    @property
    def client(self) -> storage.Client:
        """Accès lazy au client Storage."""
        if self._client is None:
            logger.debug("Création du client Google Cloud Storage")
            self._client = storage.Client(project=self.project_id)
        return self._client
    
    @property
    def bucket(self) -> storage.Bucket:
        """Accès lazy au bucket."""
        if self._bucket is None:
            logger.debug(f"Connexion au bucket: {self.bucket_name}")
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket
    
    def list_documents(
        self,
        prefix: Optional[str] = None,
        supported_only: bool = True
    ) -> Iterator[DocumentInfo]:
        """
        Liste les documents dans le bucket.
        
        Args:
            prefix: Filtre optionnel par préfixe de chemin
            supported_only: Ne retourner que les types supportés
        
        Yields:
            DocumentInfo pour chaque document trouvé
        """
        logger.info(
            f"Listing des documents (prefix={prefix}, "
            f"supported_only={supported_only})"
        )
        
        blobs: Iterator[Blob] = self.client.list_blobs(
            self.bucket_name,
            prefix=prefix
        )
        
        count = 0
        skipped = 0
        
        for blob in blobs:
            # Ignorer les "dossiers" (blobs se terminant par /)
            if blob.name.endswith("/"):
                continue
            
            doc_info = DocumentInfo(
                name=blob.name,
                size=blob.size or 0,
                content_type=blob.content_type,
                bucket_name=self.bucket_name
            )
            
            if supported_only and not doc_info.is_supported:
                skipped += 1
                logger.debug(
                    f"Document ignoré (type non supporté): {blob.name}"
                )
                continue
            
            count += 1
            yield doc_info
        
        logger.info(
            f"Listing terminé: {count} documents trouvés, "
            f"{skipped} ignorés"
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def download_as_bytes(self, document_name: str) -> bytes:
        """
        Télécharge le contenu d'un document.
        
        Args:
            document_name: Chemin complet du document dans le bucket
        
        Returns:
            Contenu du document en bytes
        
        Raises:
            google.cloud.exceptions.NotFound: Si le document n'existe pas
        """
        logger.debug(f"Téléchargement: {document_name}")
        blob = self.bucket.blob(document_name)
        content = blob.download_as_bytes()
        logger.debug(
            f"Téléchargement terminé: {len(content)} bytes"
        )
        return content
    
    def download_as_string(
        self,
        document_name: str,
        encoding: str = "utf-8"
    ) -> str:
        """
        Télécharge le contenu d'un document comme texte.
        
        Args:
            document_name: Chemin complet du document dans le bucket
            encoding: Encodage du texte
        
        Returns:
            Contenu du document en string
        """
        content = self.download_as_bytes(document_name)
        return content.decode(encoding)
    
    def get_document_count(self, prefix: Optional[str] = None) -> int:
        """
        Compte le nombre de documents dans le bucket.
        
        Args:
            prefix: Filtre optionnel par préfixe
        
        Returns:
            Nombre de documents
        """
        return sum(1 for _ in self.list_documents(prefix=prefix))
    
    def test_connection(self) -> bool:
        """
        Teste la connexion au bucket.
        
        Returns:
            True si la connexion est fonctionnelle
        
        Raises:
            Exception: Si la connexion échoue
        """
        try:
            # Tente de récupérer les métadonnées du bucket
            self.bucket.reload()
            logger.info(f"Connexion au bucket {self.bucket_name} réussie")
            return True
        except Exception as e:
            logger.error(f"Échec de connexion au bucket: {e}")
            raise


# Instance par défaut pour usage simplifié
def get_gcs_client() -> GCSClient:
    """Factory pour obtenir un client GCS configuré."""
    return GCSClient()
