"""
Routeur de collection Qdrant pour Mina.

Dirige les questions produits vers `bodyminute_products`
et les questions protocoles vers `bodyminute_docs`.
Détecte aussi les questions mixtes (produit + protocole).
"""

import logging
from typing import Set, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# === COLLECTIONS ===
COLLECTION_PRODUCTS = "bodyminute_products"
COLLECTION_PROTOCOLS = "bodyminute_docs"


# === MOTS-CLÉS PRODUITS (au moins 2 requis) ===
PRODUCT_KEYWORDS: Set[str] = {
    # Prix
    "prix", "tarif", "coût", "coûte", "€", "euro", "euros",
    # Référence
    "référence", "ref", "réf",
    # Contenance
    "ml", "contenance", "volume",
    # Composition
    "naturel", "origine naturelle", "ingrédients", "composition",
    # Yuka
    "yuka", "score yuka",
    # Actifs
    "actifs", "principes actifs", "actif",
    # Types de peau
    "type de peau", "peaux grasses", "peaux sèches", "peaux sensibles", "peaux mixtes",
    "peau grasse", "peau sèche", "peau sensible", "peau mixte", "acnéique",
    # Noms de produits
    "sérum", "crème", "gel", "mousse", "gommage", "lait", "huile", "baume",
    "démaq", "lotion", "tonique", "masque", "spray", "roll-on",
    "eau micellaire", "nettoyant", "hydratempo", "sensimine", "s-détox",
    # Mentions PRO
    "pro", "professionnel", "produit", "produits",
    # Termes de vente
    "associé", "recommandé", "utiliser", "cellulite", "anti-cellulite", "minceur"
}

# === MOTS-CLÉS PROTOCOLES ===
PROTOCOL_KEYWORDS: Set[str] = {
    # Termes de soin
    "soin", "protocole", "cure", "cabine", "traitement",
    # Équipements
    "vapozone", "haute fréquence", "électrodes",
    # Étapes
    "étapes", "étape", "durée", "minutes", "min",
    # Actions cabine
    "extraction", "modelage", "massage", "enveloppement",
    # Soins spécifiques
    "longue tenue", "anti-comédons", "silhouette", "antistress", "regard liftant"
}


# === DÉCLENCHEURS FORTS PRODUITS (1 seul suffit) ===
PRODUCT_TRIGGERS: Set[str] = {
    "référence produit",
    "prix client",
    "prix ttc",
    "pourcentage d'ingrédients",
    "% naturel",
    "% d'origine naturelle",
    "% d'ingrédients",
    "fiche produit",
    "contenance ml",
    "contenance du",
    "quel produit",
    "ce produit"
}

# === DÉCLENCHEURS FORTS PROTOCOLES (1 seul suffit) ===
PROTOCOL_TRIGGERS: Set[str] = {
    "protocole cabine",
    "soin cabine",
    "étapes du soin",
    "durée du soin",
    "comment réaliser",
    "objectif du vapozone",
    "quel masque utiliser"
}


@dataclass
class QuestionType:
    """Type de question détecté."""
    is_product: bool = False
    is_protocol: bool = False
    is_mixed: bool = False
    
    @property
    def primary_collection(self) -> str:
        """Collection principale à interroger."""
        if self.is_product and not self.is_protocol:
            return COLLECTION_PRODUCTS
        return COLLECTION_PROTOCOLS


def is_product_question(question: str) -> bool:
    """Détermine si la question concerne un produit."""
    question_lower = question.lower()
    
    # Vérifier les déclencheurs forts (1 suffit)
    for trigger in PRODUCT_TRIGGERS:
        if trigger in question_lower:
            return True
    
    # Compter les mots-clés produits (>=2 requis)
    found_keywords = [kw for kw in PRODUCT_KEYWORDS if kw in question_lower]
    return len(found_keywords) >= 2


def is_protocol_question(question: str) -> bool:
    """Détermine si la question concerne un protocole/soin."""
    question_lower = question.lower()
    
    # Vérifier les déclencheurs forts (1 suffit)
    for trigger in PROTOCOL_TRIGGERS:
        if trigger in question_lower:
            return True
    
    # Compter les mots-clés protocoles (>=2 requis)
    found_keywords = [kw for kw in PROTOCOL_KEYWORDS if kw in question_lower]
    return len(found_keywords) >= 2


def analyze_question(question: str) -> QuestionType:
    """
    Analyse une question pour déterminer son type.
    
    Args:
        question: Question en langage naturel
        
    Returns:
        QuestionType avec les flags is_product, is_protocol, is_mixed
    """
    is_product = is_product_question(question)
    is_protocol = is_protocol_question(question)
    is_mixed = is_product and is_protocol
    
    qtype = QuestionType(
        is_product=is_product,
        is_protocol=is_protocol,
        is_mixed=is_mixed
    )
    
    if is_mixed:
        logger.info("Routage: MIXTE (produit + protocole)")
    elif is_product:
        logger.info(f"Routage: PRODUIT → {COLLECTION_PRODUCTS}")
    else:
        logger.info(f"Routage: PROTOCOLE → {COLLECTION_PROTOCOLS}")
    
    return qtype


def choose_collection_for_question(question: str) -> str:
    """
    Choisit la collection Qdrant appropriée pour la question.
    
    Args:
        question: Question en langage naturel
        
    Returns:
        Nom de la collection: 'bodyminute_products' ou 'bodyminute_docs'
    """
    qtype = analyze_question(question)
    return qtype.primary_collection

