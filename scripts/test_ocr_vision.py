#!/usr/bin/env python3
"""
Test OCR avec Google Cloud Vision API sur un PDF de fiches produits.
Alternative à Document AI qui nécessite une activation séparée.
"""

import os
import sys
import re
from typing import Dict, List
from datetime import datetime
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def pdf_to_images(pdf_path: str, max_pages: int = 5) -> List[bytes]:
    """Convertit les pages PDF en images pour l'OCR avec PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        
        print(f"📄 Conversion PDF → Images avec PyMuPDF (max {max_pages} pages)...")
        
        doc = fitz.open(pdf_path)
        total_pages = min(len(doc), max_pages)
        
        print(f"   PDF: {len(doc)} pages, traitant {total_pages}")
        
        image_bytes = []
        for i in range(total_pages):
            page = doc[i]
            # Render à 150 DPI
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            image_bytes.append(img_bytes)
            print(f"   Page {i+1}: {len(img_bytes)//1024} KB")
        
        doc.close()
        print(f"   ✅ {len(image_bytes)} pages converties")
        
        return image_bytes
        
    except ImportError:
        print("❌ PyMuPDF non installé")
        print("   Installez: pip install PyMuPDF")
        return []
    except Exception as e:
        print(f"❌ Erreur conversion: {e}")
        return []


def ocr_with_vision(image_bytes: bytes) -> str:
    """OCR d'une image avec Google Cloud Vision."""
    from google.cloud import vision
    
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    
    response = client.document_text_detection(image=image)
    
    if response.error.message:
        raise Exception(response.error.message)
    
    return response.full_text_annotation.text if response.full_text_annotation else ""


def extract_products_from_text(text: str) -> List[Dict]:
    """Extrait les produits structurés du texte OCR."""
    products = []
    
    patterns = {
        "price": re.compile(r'(\d+[.,]\d{2})\s*€'),
        "reference": re.compile(r'Ref[:\s]*([A-Z]?\d{2,4}[.]?\d*)', re.IGNORECASE),
        "natural_pct": re.compile(r'(\d{1,3})\s*%\s*(?:d\')?(?:ingrédients\s+)?(?:d\')?(?:origine\s+)?naturel', re.IGNORECASE),
        "volume_ml": re.compile(r'(\d+)\s*ml', re.IGNORECASE),
        "yuka": re.compile(r'Yuka\s*[:\s]*(\d+)/100', re.IGNORECASE),
    }
    
    # Chercher les références produits
    ref_matches = list(patterns["reference"].finditer(text))
    
    for match in ref_matches:
        start = max(0, match.start() - 400)
        end = min(len(text), match.end() + 100)
        block = text[start:end]
        
        product = {
            "product_ref": match.group(1),
            "price_eur": None,
            "natural_pct": None,
            "volume_ml": None,
            "yuka_score": None,
            "raw_block": block[:200].replace('\n', ' ')
        }
        
        # Prix
        prices = patterns["price"].findall(text[start:match.start()])
        if prices:
            product["price_eur"] = float(prices[-1].replace(",", "."))
        
        # % naturel
        natural = patterns["natural_pct"].search(block)
        if natural:
            product["natural_pct"] = int(natural.group(1))
        
        # Volume
        volume = patterns["volume_ml"].search(block)
        if volume:
            product["volume_ml"] = int(volume.group(1))
        
        # Yuka
        yuka = patterns["yuka"].search(block)
        if yuka:
            product["yuka_score"] = int(yuka.group(1))
        
        products.append(product)
    
    return products


def main():
    """Test OCR Vision sur un PDF de fiches produits."""
    print("\n" + "=" * 80)
    print("🧪 TEST OCR VISION - FICHES PRODUITS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    pdf_path = "/tmp/1-5_VISAGE.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Fichier non trouvé: {pdf_path}")
        print("   Téléchargez d'abord avec test_ocr_product.py")
        return
    
    # Étape 1: Convertir PDF en images
    print("\n" + "-" * 80)
    print("📄 CONVERSION PDF → IMAGES")
    print("-" * 80)
    
    images = pdf_to_images(pdf_path, max_pages=5)
    
    if not images:
        print("❌ Échec conversion PDF")
        return
    
    # Étape 2: OCR avec Vision
    print("\n" + "-" * 80)
    print("🔍 OCR GOOGLE CLOUD VISION")
    print("-" * 80)
    
    all_text = ""
    for i, img_bytes in enumerate(images, 1):
        print(f"\n📸 Page {i}...")
        try:
            text = ocr_with_vision(img_bytes)
            all_text += f"\n--- PAGE {i} ---\n{text}"
            print(f"   ✅ {len(text)} caractères extraits")
            
            # Aperçu
            preview = text[:300].replace('\n', ' ')
            print(f"   Aperçu: {preview}...")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    print(f"\n📊 Total OCR: {len(all_text)} caractères")
    
    # Étape 3: Extraction des produits
    print("\n" + "-" * 80)
    print("🏷️ EXTRACTION STRUCTURÉE DES PRODUITS")
    print("-" * 80)
    
    products = extract_products_from_text(all_text)
    
    print(f"\n✅ {len(products)} produits détectés\n")
    
    for i, p in enumerate(products[:10], 1):
        print(f"[{i}] Ref: {p['product_ref']}")
        print(f"    Prix: {p['price_eur']}€ | {p['natural_pct']}% naturel | {p['volume_ml']}ml | Yuka: {p['yuka_score']}")
        print(f"    Block: {p['raw_block'][:100]}...")
        print()
    
    # Résumé
    print("=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    
    with_price = sum(1 for p in products if p['price_eur'])
    with_natural = sum(1 for p in products if p['natural_pct'])
    
    print(f"\nPages OCR: {len(images)}")
    print(f"Caractères extraits: {len(all_text)}")
    print(f"Produits trouvés: {len(products)}")
    print(f"   - Avec prix: {with_price}/{len(products)}")
    print(f"   - Avec % naturel: {with_natural}/{len(products)}")
    
    # Sauvegarder le texte OCR pour analyse
    with open("/tmp/ocr_output.txt", "w") as f:
        f.write(all_text)
    print(f"\n📝 Texte OCR sauvegardé: /tmp/ocr_output.txt")
    
    return products


if __name__ == "__main__":
    products = main()
