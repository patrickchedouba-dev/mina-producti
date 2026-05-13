#!/usr/bin/env python3
"""
Scraper Shopify pour récupérer les données produits Skinminute.
Génère un fichier JSON avec images HD et métadonnées.
"""

import json
import requests
import os
from datetime import datetime
from typing import List, Dict, Any

# Configuration
SHOPIFY_PRODUCTS_URL = "https://skinminute.com/products.json"
OUTPUT_FILE = "/home/jupyter/mina_fichiers/mina-bêta/data/products_external.json"


def fetch_shopify_products(limit: int = 250) -> List[Dict]:
    """Récupère les produits via l'API Shopify publique."""
    products = []
    page = 1
    
    while True:
        url = f"{SHOPIFY_PRODUCTS_URL}?limit={limit}&page={page}"
        print(f"📥 Fetching page {page}...")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("products"):
                break
                
            products.extend(data["products"])
            
            if len(data["products"]) < limit:
                break
                
            page += 1
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            break
    
    print(f"✅ {len(products)} produits récupérés")
    return products


def transform_product(product: Dict) -> Dict[str, Any]:
    """Transforme un produit Shopify en format Mina simplifié."""
    
    # Extraire la première image HD
    image_url = ""
    if product.get("images") and len(product["images"]) > 0:
        image_url = product["images"][0].get("src", "")
    
    # Extraire le SKU et le prix du premier variant
    sku = ""
    price = 0.0
    if product.get("variants") and len(product["variants"]) > 0:
        variant = product["variants"][0]
        sku = variant.get("sku", "")
        try:
            price = float(variant.get("price", 0))
        except:
            price = 0.0
    
    # Nettoyer la description HTML
    description = product.get("body_html", "")
    # Nettoyage basique du HTML
    import re
    description_clean = re.sub(r'<[^>]+>', '', description)
    description_clean = re.sub(r'\s+', ' ', description_clean).strip()[:500]
    
    # Construire l'URL produit
    handle = product.get("handle", "")
    product_url = f"https://skinminute.com/products/{handle}" if handle else ""
    
    return {
        "product_id": product.get("id"),
        "product_name": product.get("title", ""),
        "product_ref": sku,
        "product_url": product_url,
        "image_url": image_url,
        "price_eur": price,
        "product_type": product.get("product_type", ""),
        "vendor": product.get("vendor", ""),
        "tags": product.get("tags", []),
        "description": description_clean,
        "reviews": []  # Placeholder pour avis clients (nécessite scraping supplémentaire)
    }


def create_products_json():
    """Crée le fichier JSON des produits."""
    print(f"\n{'='*60}")
    print("🛒 SCRAPING SKINMINUTE.COM - DONNÉES PRODUITS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Récupérer les produits
    raw_products = fetch_shopify_products()
    
    # Transformer
    products = [transform_product(p) for p in raw_products]
    
    # Structure de sortie
    output = {
        "metadata": {
            "source": "https://skinminute.com",
            "scraped_at": datetime.now().isoformat(),
            "total_products": len(products),
            "note": "Données publiques Shopify API - Usage interne Mina"
        },
        "products": products
    }
    
    # Sauvegarder
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Fichier généré: {OUTPUT_FILE}")
    print(f"📊 {len(products)} produits avec images HD")
    
    # Afficher quelques exemples
    print(f"\n{'='*60}")
    print("📋 EXEMPLES DE PRODUITS")
    print(f"{'='*60}")
    
    for p in products[:3]:
        print(f"\n🔹 {p['product_name']}")
        print(f"   Réf: {p['product_ref']} | Prix: {p['price_eur']}€")
        print(f"   Image: {p['image_url'][:60]}...")
        print(f"   URL: {p['product_url']}")
    
    return output


if __name__ == "__main__":
    create_products_json()
