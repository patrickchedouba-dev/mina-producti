"""
Safe Mode pour Mina V2.
Réponses de secours professionnelles quand le score est insuffisant.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Réponses de secours élégantes par catégorie
SAFE_RESPONSES = {
    "default": (
        "Je vous invite à consulter votre guide produits ou à contacter "
        "votre formatrice pour cette question précise. "
        "Puis-je vous aider sur un autre sujet ?"
    ),
    "product": (
        "Je n'ai pas trouvé d'information précise sur ce produit. "
        "Consultez votre catalogue produits ou demandez à votre formatrice. "
        "Souhaitez-vous des informations sur un autre produit ?"
    ),
    "protocol": (
        "Pour les détails de ce protocole, je vous recommande de consulter "
        "votre guide de formation cabine. "
        "Puis-je vous aider sur un autre soin ?"
    ),
    "price": (
        "Les tarifs peuvent varier selon votre institut. "
        "Vérifiez sur votre grille tarifaire ou consultez votre responsable. "
        "Autre question ?"
    ),
    "unknown": (
        "Cette question dépasse mon domaine d'expertise actuel. "
        "Je vous suggère de contacter votre équipe formation. "
        "Puis-je vous aider autrement ?"
    )
}


def get_safe_response(
    category: str = "default",
    question: Optional[str] = None
) -> str:
    """
    Retourne une réponse de secours professionnelle.
    
    Args:
        category: Type de question (default, product, protocol, price, unknown)
        question: Question originale (pour logging)
        
    Returns:
        Message de secours élégant
    """
    response = SAFE_RESPONSES.get(category, SAFE_RESPONSES["default"])
    
    if question:
        logger.info(f"Safe mode activé pour: '{question[:50]}...' → catégorie: {category}")
    else:
        logger.info(f"Safe mode activé → catégorie: {category}")
    
    return response


def detect_question_category(question: str) -> str:
    """
    Détecte la catégorie d'une question pour choisir la bonne réponse safe.
    
    Args:
        question: Question de l'utilisateur
        
    Returns:
        Catégorie détectée
    """
    question_lower = question.lower()
    
    # Prix
    if any(kw in question_lower for kw in ["prix", "tarif", "coût", "combien", "euros", "€"]):
        return "price"
    
    # Protocole
    if any(kw in question_lower for kw in ["protocole", "soin", "étapes", "durée", "cabine"]):
        return "protocol"
    
    # Produit
    if any(kw in question_lower for kw in ["produit", "crème", "sérum", "masque", "actif"]):
        return "product"
    
    return "default"


def should_trigger_safe_mode(
    score: float,
    min_score: float = 0.5,
    has_premium: bool = False
) -> bool:
    """
    Détermine si le safe mode doit être déclenché.
    
    Args:
        score: Score de similarité
        min_score: Seuil minimum
        has_premium: Résultat premium disponible
        
    Returns:
        True si safe mode doit être activé
    """
    # Score trop bas
    if score < min_score:
        logger.warning(f"Safe mode trigger: score {score:.3f} < {min_score}")
        return True
    
    # Score moyen sans premium
    if score < 0.6 and not has_premium:
        logger.warning(f"Safe mode trigger: score moyen {score:.3f} sans premium")
        return True
    
    return False


class SafeModeHandler:
    """Gestionnaire du safe mode avec statistiques."""
    
    def __init__(self):
        self.trigger_count = 0
        self.category_stats = {cat: 0 for cat in SAFE_RESPONSES.keys()}
    
    def handle(
        self,
        question: str,
        score: float,
        min_score: float = 0.5,
        has_premium: bool = False
    ) -> Optional[str]:
        """
        Gère une question potentiellement problématique.
        
        Returns:
            Réponse safe si nécessaire, None sinon
        """
        if not should_trigger_safe_mode(score, min_score, has_premium):
            return None
        
        self.trigger_count += 1
        category = detect_question_category(question)
        self.category_stats[category] += 1
        
        return get_safe_response(category, question)
    
    def get_stats(self) -> dict:
        """Retourne les statistiques du safe mode."""
        return {
            "trigger_count": self.trigger_count,
            "by_category": self.category_stats
        }


# Instance singleton
_handler = None


def get_safe_handler() -> SafeModeHandler:
    """Retourne l'instance singleton du handler."""
    global _handler
    if _handler is None:
        _handler = SafeModeHandler()
    return _handler
