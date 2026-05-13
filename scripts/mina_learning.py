"""
Module d'apprentissage Mina.
Permet à Mina d'apprendre des corrections de l'utilisateur expert (Laurence).
"""

import os
import re
import sys
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()

# ========== IMPORTS CENTRALISÉS ==========
# Ajouter scripts/ au path pour trouver utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.qdrant_utils import get_qdrant_client
from utils.embedding_utils import get_embedding


# Patterns de détection de corrections
CORRECTION_PATTERNS = [
    r"non[,\s]+c'est faux",
    r"non[,\s]+la (vraie|bonne) réponse",
    r"tu (te trompes|as tort)",
    r"c'est (incorrect|inexact)",
    r"en fait[,\s]+c'est",
    r"la réponse (correcte|exacte) est",
    r"je te corrige",
    r"attention[,\s]+c'est",
]


def detect_correction(text: str) -> bool:
    """Détecte si le texte contient une correction de l'utilisateur."""
    text_lower = text.lower()
    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def extract_correction_content(text: str) -> str:
    """Extrait le contenu de la correction (après le pattern)."""
    text_lower = text.lower()
    for pattern in CORRECTION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            # Retourner tout ce qui suit le pattern
            return text[match.end():].strip(" ,.:")
    return text


# Alias pour rétrocompatibilité
def get_learning_client():
    """Alias vers get_qdrant_client pour rétrocompatibilité."""
    return get_qdrant_client()


def store_learning(
    original_question: str,
    wrong_answer: str,
    correction: str,
    expert_name: str = "Laurence"
) -> bool:
    """
    Stocke un apprentissage (correction) dans Qdrant.
    
    Args:
        original_question: La question qui a généré la mauvaise réponse
        wrong_answer: La réponse incorrecte de Mina
        correction: La correction apportée par l'expert
        expert_name: Nom de l'expert (pour traçabilité)
    
    Returns:
        True si stockage réussi
    """
    try:
        from qdrant_client.models import PointStruct
        
        client = get_learning_client()
        
        # Créer l'embedding basé sur la question originale
        embedding = get_embedding(original_question)
        
        # Créer le point avec les métadonnées
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "original_question": original_question,
                "wrong_answer": wrong_answer,
                "correction": correction,
                "expert_name": expert_name,
                "learned_at": datetime.now().isoformat(),
                "type": "correction"
            }
        )
        
        client.upsert(
            collection_name="mina_learnings",
            points=[point]
        )
        
        return True
        
    except Exception as e:
        print(f"Erreur stockage apprentissage: {e}")
        return False


def search_learnings(question: str, threshold: float = 0.75) -> Optional[Dict]:
    """
    Recherche si Mina a déjà appris quelque chose de pertinent pour cette question.
    
    Args:
        question: La question posée
        threshold: Score minimum pour considérer comme pertinent
    
    Returns:
        Dict avec la correction si trouvée, None sinon
    """
    try:
        client = get_learning_client()
        embedding = get_embedding(question)
        
        results = client.query_points(
            collection_name="mina_learnings",
            query=embedding,
            limit=1,
            with_payload=True
        )
        
        if results.points and results.points[0].score >= threshold:
            return {
                "original_question": results.points[0].payload.get("original_question"),
                "correction": results.points[0].payload.get("correction"),
                "expert_name": results.points[0].payload.get("expert_name"),
                "score": results.points[0].score
            }
        
        return None
        
    except Exception as e:
        print(f"Erreur recherche apprentissages: {e}")
        return None


def get_learning_stats() -> Dict:
    """Retourne les statistiques d'apprentissage."""
    try:
        client = get_learning_client()
        info = client.get_collection("mina_learnings")
        return {
            "total_learnings": info.points_count,
            "collection_exists": True
        }
    except Exception:
        return {
            "total_learnings": 0,
            "collection_exists": False
        }


# Test du module
if __name__ == "__main__":
    print("=== Test Module Apprentissage ===")
    
    # Test détection correction
    test_phrases = [
        "Non, c'est faux, la vraie réponse est les femmes enceintes",
        "Tu te trompes, c'est 15 minutes pas 10",
        "Bonjour, quelle est la durée ?",
        "En fait, c'est l'Acide Hyaluronique l'actif principal"
    ]
    
    for phrase in test_phrases:
        is_correction = detect_correction(phrase)
        print(f"'{phrase[:50]}...' -> Correction: {is_correction}")
    
    print("\n=== Stats ===")
    stats = get_learning_stats()
    print(f"Apprentissages stockés: {stats['total_learnings']}")
