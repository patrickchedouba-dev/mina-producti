#!/usr/bin/env python3
"""
Analyse des chunks existants dans Qdrant pour identifier les fiches produits.
"""

import os
import sys
import re
from collections import Counter
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def get_qdrant_client():
    """Initialise le client Qdrant."""
    from qdrant_client import QdrantClient
    
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    return QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key if qdrant_api_key else None
    )


def analyze_chunks():
    """Analyse les chunks existants pour identifier les fiches produits."""
    print("\n" + "=" * 80)
    print("🔍 ANALYSE DES CHUNKS QDRANT - IDENTIFICATION FICHES PRODUITS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "bodyminute_docs")
    client = get_qdrant_client()
    
    # Récupérer tous les chunks
    print(f"\n📦 Récupération de tous les chunks de '{collection_name}'...")
    
    all_points = []
    offset = None
    
    while True:
        result = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        points, offset = result
        all_points.extend(points)
        
        if offset is None:
            break
    
    print(f"✅ {len(all_points)} chunks récupérés")
    
    # Patterns de détection des fiches produits
    product_patterns = {
        "price": re.compile(r'(\d+[.,]\d{2})\s*€', re.IGNORECASE),
        "reference": re.compile(r'Ref\s*[:\s]?\s*([A-Z][0-9]{3}[.]?[0-9]*)', re.IGNORECASE),
        "natural_pct": re.compile(r'(\d{1,3})\s*%\s*(?:d\'origine\s+)?naturel', re.IGNORECASE),
        "volume_ml": re.compile(r'(\d+)\s*ml', re.IGNORECASE),
        "yuka_score": re.compile(r'Yuka\s*[:\s]?\s*(\d+)/100', re.IGNORECASE),
    }
    
    # Keywords de produits vs protocoles
    product_keywords = [
        "sérum", "crème", "gel", "huile", "lotion", "baume", "masque", "spray",
        "mousse", "eau micellaire", "gommage", "vernis", "roll-on"
    ]
    
    protocol_keywords = [
        "consommables", "matériel", "protocole", "étape", "min ", 
        "bandeau", "coton", "serviette jetable", "coupelle"
    ]
    
    # Classification des chunks
    product_chunks = []
    protocol_chunks = []
    mixed_chunks = []
    other_chunks = []
    
    for point in all_points:
        payload = point.payload or {}
        text = payload.get("text", payload.get("content", payload.get("chunk", "")))
        text_lower = text.lower()
        
        # Détection des éléments
        has_price = bool(product_patterns["price"].search(text))
        has_ref = bool(product_patterns["reference"].search(text))
        has_natural_pct = bool(product_patterns["natural_pct"].search(text))
        has_volume = bool(product_patterns["volume_ml"].search(text))
        
        product_keyword_count = sum(1 for kw in product_keywords if kw in text_lower)
        protocol_keyword_count = sum(1 for kw in protocol_keywords if kw in text_lower)
        
        # Score de "fiche produit"
        product_score = 0
        if has_price: product_score += 3
        if has_ref: product_score += 3
        if has_natural_pct: product_score += 2
        if has_volume: product_score += 1
        product_score += product_keyword_count
        
        # Score de "protocole"
        protocol_score = protocol_keyword_count * 2
        
        chunk_info = {
            "id": str(point.id),
            "text": text,
            "has_price": has_price,
            "has_ref": has_ref,
            "has_natural_pct": has_natural_pct,
            "has_volume": has_volume,
            "product_score": product_score,
            "protocol_score": protocol_score,
            "prices_found": product_patterns["price"].findall(text),
            "refs_found": product_patterns["reference"].findall(text),
        }
        
        # Classification
        if product_score >= 5 and product_score > protocol_score:
            product_chunks.append(chunk_info)
        elif protocol_score >= 4 and protocol_score > product_score:
            protocol_chunks.append(chunk_info)
        elif product_score >= 3 or has_price:
            mixed_chunks.append(chunk_info)
        else:
            other_chunks.append(chunk_info)
    
    # Rapport
    print("\n" + "-" * 80)
    print("📊 CLASSIFICATION DES CHUNKS")
    print("-" * 80)
    
    print(f"\n🏷️ Fiches produits potentielles: {len(product_chunks)}")
    print(f"📋 Protocoles de soins: {len(protocol_chunks)}")
    print(f"🔀 Mixtes (produits+protocoles): {len(mixed_chunks)}")
    print(f"❓ Autres: {len(other_chunks)}")
    
    # Exemples de fiches produits
    print("\n" + "-" * 80)
    print("📄 EXEMPLES DE CHUNKS FICHES PRODUITS (top 5)")
    print("-" * 80)
    
    # Trier par score produit
    product_chunks.sort(key=lambda x: x["product_score"], reverse=True)
    
    for i, chunk in enumerate(product_chunks[:5], 1):
        print(f"\n[{i}] Score: {chunk['product_score']} | Prix: {chunk['prices_found']} | Refs: {chunk['refs_found']}")
        text_preview = chunk['text'][:500].replace('\n', ' ')
        print(f"    {text_preview}...")
    
    # Produits détectés avec prix et référence
    print("\n" + "-" * 80)
    print("💰 PRODUITS AVEC PRIX ET RÉFÉRENCE DÉTECTÉS")
    print("-" * 80)
    
    products_with_price_ref = [c for c in product_chunks if c["has_price"] and c["has_ref"]]
    print(f"\n✅ {len(products_with_price_ref)} chunks avec PRIX + RÉFÉRENCE")
    
    # Recherche des produits spécifiques demandés
    print("\n" + "-" * 80)
    print("🔎 RECHERCHE DES PRODUITS SPÉCIFIQUES")
    print("-" * 80)
    
    target_products = [
        "S-DÉTOX",
        "SÉRUM S-DÉTOX",
        "SPRAY ANTI-ACNÉ",
        "HYDRATEMPO",
        "WATER BOMB",
        "SENSIMINE",
        "Roll-On Quartz",
        "Crème Mains",
        "GEL MOUSSE FLORAL",
        "Huile Apaisante"
    ]
    
    for product in target_products:
        found = [c for c in all_points if product.lower() in (c.payload.get("text", "") or "").lower()]
        if found:
            print(f"\n✅ '{product}' trouvé dans {len(found)} chunk(s)")
            # Afficher un extrait
            sample = found[0].payload.get("text", "")[:200]
            print(f"   Extrait: {sample}...")
        else:
            print(f"\n❌ '{product}' NON TROUVÉ")
    
    print("\n" + "=" * 80)
    print("📋 RÉSUMÉ")
    print("=" * 80)
    print(f"\nTotal chunks: {len(all_points)}")
    print(f"Fiches produits identifiées: {len(product_chunks)} ({100*len(product_chunks)/len(all_points):.1f}%)")
    print(f"Avec prix ET référence: {len(products_with_price_ref)}")
    print("\n" + "=" * 80)
    
    return {
        "total": len(all_points),
        "product_chunks": product_chunks,
        "protocol_chunks": protocol_chunks,
        "mixed_chunks": mixed_chunks
    }


if __name__ == "__main__":
    analyze_chunks()
