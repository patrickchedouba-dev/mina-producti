"""
Module de découpage (chunking) de texte pour la vectorisation.
Implémente un découpage par caractères avec chevauchement.
"""

import logging
from typing import List
from dataclasses import dataclass, field
from datetime import datetime

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """
    Représente un chunk de texte avec ses métadonnées.
    
    Attributes:
        content: Contenu textuel du chunk
        chunk_index: Index du chunk dans le document source
        source_path: Chemin du document source
        doc_type: Type de document (pdf, txt, docx)
        start_char: Position de départ dans le document original
        end_char: Position de fin dans le document original
        ingestion_date: Date d'ingestion
    """
    content: str
    chunk_index: int
    source_path: str
    doc_type: str
    start_char: int = 0
    end_char: int = 0
    ingestion_date: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    
    def to_metadata(self) -> dict:
        """
        Convertit les métadonnées en dictionnaire pour Qdrant.
        
        Le champ 'text' est le champ principal pour le RAG.
        Le champ 'content' est conservé pour compatibilité.
        
        Returns:
            Dictionnaire des métadonnées
        """
        return {
            "text": self.content,           # Champ principal pour la recherche RAG
            "content": self.content,        # Compatibilité avec ancien code
            "chunk_index": self.chunk_index,
            "source_path": self.source_path,
            "doc_type": self.doc_type,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "ingestion_date": self.ingestion_date,
        }
    
    def __len__(self) -> int:
        """Retourne la longueur du contenu."""
        return len(self.content)


class TextChunker:
    """
    Découpe le texte en chunks avec chevauchement.
    
    Utilise un découpage par caractères avec gestion intelligente
    des séparateurs naturels (phrases, paragraphes).
    """
    
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None
    ):
        """
        Initialise le chunker.
        
        Args:
            chunk_size: Taille max d'un chunk (défaut: config)
            chunk_overlap: Chevauchement entre chunks (défaut: config)
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        # Séparateurs par ordre de préférence
        self.separators = [
            "\n\n",   # Paragraphes
            "\n",     # Lignes
            ". ",     # Phrases
            "! ",     # Exclamations
            "? ",     # Questions
            "; ",     # Points-virgules
            ", ",     # Virgules
            " ",      # Espaces
        ]
        
        logger.info(
            f"TextChunker initialisé: size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}"
        )
    
    def chunk_text(
        self,
        text: str,
        source_path: str,
        doc_type: str
    ) -> List[TextChunk]:
        """
        Découpe un texte en chunks.
        
        Args:
            text: Texte à découper
            source_path: Chemin du document source
            doc_type: Type de document
        
        Returns:
            Liste de TextChunk
        """
        if not text or not text.strip():
            logger.warning(f"Texte vide pour: {source_path}")
            return []
        
        chunks = []
        current_pos = 0
        chunk_index = 0
        text_length = len(text)
        
        logger.debug(
            f"Début chunking: {source_path} ({text_length} caractères)"
        )
        
        while current_pos < text_length:
            # Calcul de la fin du chunk
            end_pos = min(current_pos + self.chunk_size, text_length)
            
            # Si on n'est pas à la fin, chercher un bon point de coupure
            if end_pos < text_length:
                end_pos = self._find_best_split(text, current_pos, end_pos)
            
            # Extraction du chunk
            chunk_text = text[current_pos:end_pos].strip()
            
            if chunk_text:
                chunk = TextChunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    source_path=source_path,
                    doc_type=doc_type,
                    start_char=current_pos,
                    end_char=end_pos
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Avance avec chevauchement
            if end_pos >= text_length:
                break
            
            current_pos = end_pos - self.chunk_overlap
            # Évite de rester bloqué
            if current_pos <= chunks[-1].start_char if chunks else 0:
                current_pos = end_pos
        
        logger.info(
            f"Chunking terminé: {source_path} -> {len(chunks)} chunks"
        )
        
        return chunks
    
    def _find_best_split(
        self,
        text: str,
        start: int,
        end: int
    ) -> int:
        """
        Trouve le meilleur point de coupure dans une plage.
        
        Cherche le séparateur le plus approprié près de la fin
        de la plage pour éviter de couper au milieu d'un mot
        ou d'une phrase.
        
        Args:
            text: Texte complet
            start: Position de départ
            end: Position de fin souhaitée
        
        Returns:
            Position de coupure optimale
        """
        # Zone de recherche (dernier quart du chunk)
        search_start = start + (end - start) * 3 // 4
        chunk = text[search_start:end]
        
        # Cherche le dernier séparateur dans la zone
        for separator in self.separators:
            last_pos = chunk.rfind(separator)
            if last_pos != -1:
                # Position dans le texte complet
                split_pos = search_start + last_pos + len(separator)
                logger.debug(
                    f"Coupure trouvée avec '{repr(separator)}' à {split_pos}"
                )
                return split_pos
        
        # Aucun séparateur trouvé, coupe à end
        return end
    
    def estimate_chunks(self, text_length: int) -> int:
        """
        Estime le nombre de chunks pour une longueur de texte.
        
        Args:
            text_length: Longueur du texte en caractères
        
        Returns:
            Estimation du nombre de chunks
        """
        if text_length <= self.chunk_size:
            return 1
        
        effective_size = self.chunk_size - self.chunk_overlap
        return (text_length - self.chunk_overlap) // effective_size + 1


# Instance par défaut
def get_chunker() -> TextChunker:
    """Factory pour obtenir un chunker configuré."""
    return TextChunker()
