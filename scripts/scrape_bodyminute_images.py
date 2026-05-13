#!/usr/bin/env python3
"""
Script pour extraire les URLs d'images depuis bodyminute.com
et enrichir le catalogue produits pour Mina.

Usage:
    pip install requests beautifulsoup4
    python scripts/scrape_bodyminute_images.py
"""

import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time

# Headers pour simuler un navigateur
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# URLs des pages à scraper
PAGES_TO_SCRAPE = [
    ("epilation", "https://www.bodyminute.com/soins/epilation/"),
    ("soins_visage", "https://www.bodyminute.com/soins/soins-visage/"),
    ("soins_corps", "https://www.bodyminute.com/soins/soins-corps/"),
    ("epilation_definitive", "https://www.bodyminute.com/soins/epilation-definitive/"),
    ("mains_pieds", "https://www.bodyminute.com/soins/soin-des-pieds/"),
    ("browlift", "https://www.bodyminute.com/soins/soins-visage/browlift/"),
    ("topcils", "https://www.bodyminute.com/soins/soins-visage/topcils/"),
]


def extract_images_from_page(url: str) -> list:
    """Extrait toutes les URLs d'images d'une page."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        images = []
        
        # Trouver toutes les balises img
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                # Normaliser l'URL
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://www.bodyminute.com' + src
                
                # Filtrer les images pertinentes (pas les icônes)
                if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    if 'logo' not in src.lower() and 'icon' not in src.lower():
                        alt = img.get('alt', '')
                        images.append({
                            'url': src,
                            'alt': alt
                        })
        
        return images
    
    except Exception as e:
        print(f"❌ Erreur pour {url}: {e}")
        return []


def main():
    """Scrape toutes les pages et sauvegarde les images."""
    print("🔍 Scraping bodyminute.com pour les images...\n")
    
    all_images = {}
    
    for category, url in PAGES_TO_SCRAPE:
        print(f"📄 {category}: {url}")
        images = extract_images_from_page(url)
        all_images[category] = images
        print(f"   → {len(images)} images trouvées")
        time.sleep(1)  # Respecter le serveur
    
    # Sauvegarder le résultat
    output_path = Path(__file__).parent.parent / "data" / "bodyminute_images.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_images, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Sauvegardé dans {output_path}")
    
    # Afficher un résumé
    total = sum(len(imgs) for imgs in all_images.values())
    print(f"📊 Total: {total} images extraites")
    
    # Afficher quelques exemples
    print("\n🖼️ Exemples d'images trouvées:")
    for category, images in all_images.items():
        if images:
            print(f"\n  [{category}]")
            for img in images[:3]:
                print(f"    - {img['alt'][:40]}... : {img['url'][:60]}...")


if __name__ == "__main__":
    main()
