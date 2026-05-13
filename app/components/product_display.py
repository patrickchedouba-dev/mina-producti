#!/usr/bin/env python3
"""
Product Display Component v2.0 - VERSION SIMPLIFIÉE
Matching robuste + HTML propre sans bugs.
"""

import json
import unicodedata
from typing import Optional, Dict, List
from pathlib import Path

# Chemin absolu vers le fichier JSON
PRODUCTS_DB_PATH = Path(__file__).parent.parent.parent / "data" / "products_external.json"

# Cache mémoire
_PRODUCTS_CACHE = None


def _load_products():
    """Charge les produits une seule fois."""
    global _PRODUCTS_CACHE
    if _PRODUCTS_CACHE is None:
        try:
            with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                _PRODUCTS_CACHE = data.get("products", [])
        except Exception as e:
            print(f"Erreur chargement produits: {e}")
            _PRODUCTS_CACHE = []
    return _PRODUCTS_CACHE


def _normalize(text: str) -> str:
    """Normalise: minuscules + sans accents."""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower().strip()


def _find_best_match(response_text: str) -> Optional[Dict]:
    """
    Trouve LE MEILLEUR produit correspondant à la réponse.
    v2.2: Score minimum de 2 pour éviter les faux positifs.
    """
    products = _load_products()
    if not products:
        return None
    
    response_norm = _normalize(response_text)
    
    # Phase 1: Chercher nom complet exact
    for p in products:
        name_norm = _normalize(p.get('product_name', ''))
        if len(name_norm) >= 5 and name_norm in response_norm:
            return p
    
    # Phase 2: Mots-clés discriminants
    # v2.2: Liste étendue de mots trop génériques pour éviter faux positifs
    common_words = {
        'creme', 'serum', 'gel', 'huile', 'lait', 'soin', 'masque', 'eau', 
        'pour', 'avec', 'aux', 'les', 'des', 'une', 'pro', 'minute',
        'hyper', 'super', 'ultra', 'profond', 'intense', 'doux', 'leger',
        'corps', 'visage', 'peau', 'jour', 'nuit', 'matin', 'soir',
        'voici', 'sans', 'aucun', 'produit', 'reponse', 'mentionné'
    }
    
    best_match = None
    best_score = 0
    
    for p in products:
        name = p.get('product_name', '')
        name_norm = _normalize(name)
        
        # Extraire mots significatifs (>3 chars, pas communs)
        words = [w for w in name_norm.split() if len(w) > 3 and w not in common_words]
        
        # Aussi chercher les morceaux collés (hydratempo = hydra + tempo)
        compound_parts = []
        for w in words:
            if len(w) > 6:  # Mots composés
                compound_parts.extend([w[:4], w[4:]] if len(w) > 8 else [w[:3], w[3:]])
        
        all_keywords = words + [p for p in compound_parts if len(p) > 2]
        
        if not all_keywords:
            continue
        
        # Compter matches
        matches = sum(1 for w in all_keywords if w in response_norm)
        
        if matches > 0:
            score = matches  # Score absolu plutôt que ratio
            if score > best_score:
                best_score = score
                best_match = p
    
    # v2.2: Exiger score >= 2 pour éviter les faux positifs sur un seul mot
    return best_match if best_score >= 2 else None


def get_product_cards_for_response(response_text: str, max_cards: int = 1) -> Optional[str]:
    """
    Génère UNE carte pour le meilleur produit trouvé.
    Retourne du HTML simple et propre.
    """
    product = _find_best_match(response_text)
    
    if not product:
        return None
    
    name = product.get('product_name', 'Produit')
    price = product.get('price_eur', 0)
    price_str = f"{price} €" if price else ""
    img = product.get('image_url', '')
    link = product.get('product_url', '#')
    
    if not img or not img.startswith('http'):
        img = "https://via.placeholder.com/120x150?text=Produit"
    
    # HTML ULTRA SIMPLE - tout sur une ligne, pas de f-string multiligne
    html = '<div style="display:inline-flex;margin:10px 0;">'
    html += '<div style="width:150px;border:1px solid #e91e63;border-radius:10px;padding:10px;background:#fff;text-align:center;font-family:sans-serif;">'
    html += f'<img src="{img}" style="width:100px;height:120px;object-fit:contain;border-radius:5px;" />'
    html += f'<div style="margin-top:8px;font-size:13px;font-weight:600;color:#333;height:40px;overflow:hidden;">{name}</div>'
    html += f'<div style="color:#e91e63;font-weight:bold;font-size:14px;margin:5px 0;">{price_str}</div>'
    html += f'<a href="{link}" target="_blank" style="display:inline-block;background:#e91e63;color:#fff;padding:8px 16px;border-radius:20px;text-decoration:none;font-size:12px;">VOIR</a>'
    html += '</div></div>'
    
    return html


# Fonctions pour compatibilité avec imports existants
get_product_card_html = get_product_cards_for_response
normalize_text = _normalize  # Alias public pour tests


def find_product_by_name(product_name: str) -> Optional[Dict]:
    """Recherche un produit par son nom."""
    products = _load_products()
    name_norm = _normalize(product_name)
    
    for p in products:
        if _normalize(p.get("product_name", "")) == name_norm:
            return p
    
    for p in products:
        if name_norm in _normalize(p.get("product_name", "")):
            return p
    
    return None


def find_product_by_ref(ref: str) -> Optional[Dict]:
    """Recherche un produit par SKU."""
    products = _load_products()
    ref_clean = ref.upper().strip()
    for p in products:
        if p.get("product_ref", "").upper() == ref_clean:
            return p
    return None


def get_reviews_for_product(product_name: str) -> str:
    """Stub pour avis clients."""
    return f"Les avis sont disponibles sur skinminute.com"


def display_product_in_streamlit(product: Dict):
    """Affiche dans Streamlit."""
    try:
        import streamlit as st
        html = get_product_cards_for_response(product.get('product_name', ''))
        if html:
            st.markdown(html, unsafe_allow_html=True)
    except ImportError:
        pass


def load_products_db():
    """Pour compatibilité."""
    return _load_products()


# Variable pour compatibilité
PRODUCTS_DB = []
