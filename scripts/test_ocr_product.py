#!/usr/bin/env python3
"""
Test d'extraction OCR sur un fichier de fiches produits.
Compare pypdf vs Document AI.
"""

import os
import sys
import re
from typing import Dict, List
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def download_pdf(gcs_path: str, local_path: str):
    """Télécharge un PDF depuis GCS."""
    from google.cloud import storage
    
    bucket_name = "mina-pdfs"
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    
    # Recharger pour avoir la taille
    blob.reload()
    size_mb = blob.size / 1024 / 1024 if blob.size else 0
    
    print(f"⬇️ Téléchargement: {gcs_path} ({size_mb:.1f} Mo)")
    blob.download_to_filename(local_path)
    print(f"✅ Sauvegardé: {local_path}")


def extract_with_pypdf(pdf_path: str) -> str:
    """Extraction avec pypdf."""
    from pypdf import PdfReader
    
    reader = PdfReader(pdf_path)
    text = ""
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        text += f"\n--- PAGE {i+1} ---\n{page_text}"
    return text


def extract_with_document_ai(pdf_path: str, project_id: str = "bodycoachocr") -> str:
    """Extraction OCR avec Document AI."""
    from google.cloud import documentai_v1 as documentai
    
    print("🔍 Initialisation Document AI...")
    
    with open(pdf_path, "rb") as f:
        content = f.read()
    
    client = documentai.DocumentProcessorServiceClient()
    
    # Trouver le processeur OCR
    parent = f"projects/{project_id}/locations/eu"
    processors = list(client.list_processors(parent=parent))
    
    ocr_processor = None
    for p in processors:
        if "OCR" in p.type_.upper():
            ocr_processor = p.name
            print(f"   Processeur: {p.display_name}")
            break
    
    if not ocr_processor:
        print("❌ Pas de processeur OCR")
        return ""
    
    # Traiter le document
    print(f"🔄 OCR en cours ({len(content)/1024/1024:.1f} Mo)...")
    
    raw_document = documentai.RawDocument(
        content=content,
        mime_type="application/pdf"
    )
    
    request = documentai.ProcessRequest(
        name=ocr_processor,
        raw_document=raw_document
    )
    
    result = client.process_document(request=request)
    print(f"✅ OCR terminé: {len(result.document.text)} chars")
    
    return result.document.text


def extract_products_from_text(text: str) -> List[Dict]:
    """Extrait les produits structurés du texte."""
    products = []
    
    # Patterns
    patterns = {
        "price": re.compile(r'(\d+[.,]\d{2})\s*€'),
        "reference": re.compile(r'Ref[:\s]*([A-Z]?\d{2,4}[.]?\d*)', re.IGNORECASE),
        "natural_pct": re.compile(r'(\d{1,3})\s*%\s*(?:d\')?(?:ingrédients\s+)?(?:d\')?(?:origine\s+)?naturel', re.IGNORECASE),
        "volume_ml": re.compile(r'(\d+)\s*ml', re.IGNORECASE),
        "yuka": re.compile(r'Yuka\s*[:\s]*(\d+)/100', re.IGNORECASE),
    }
    
    # Chercher les blocs avec Ref:
    ref_matches = list(patterns["reference"].finditer(text))
    
    for i, match in enumerate(ref_matches):
        # Prendre le contexte autour de la référence
        start = max(0, match.start() - 300)
        end = min(len(text), match.end() + 100)
        block = text[start:end]
        
        product = {
            "product_ref": match.group(1),
            "price_eur": None,
            "natural_pct": None,
            "volume_ml": None,
            "yuka_score": None,
            "raw_block": block[:200]
        }
        
        # Extraire le prix le plus proche avant la référence
        prices_before = patterns["price"].findall(text[start:match.start()])
        if prices_before:
            product["price_eur"] = float(prices_before[-1].replace(",", "."))
        
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
    """Test d'extraction sur un fichier de fiches produits."""
    print("\n" + "=" * 80)
    print("🧪 TEST EXTRACTION FICHES PRODUITS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Fichier cible: le plus petit fichier de fiches produits visage
    gcs_path = "PRODUITS_SKINMINUTE_VISAGE/1-5_VISAGE.pdf"
    local_path = "/tmp/1-5_VISAGE.pdf"
    
    # Télécharger si nécessaire
    if not os.path.exists(local_path):
        download_pdf(gcs_path, local_path)
    else:
        print(f"📁 Fichier déjà présent: {local_path}")
    
    # ÉTAPE 1: Extraction pypdf
    print("\n" + "-" * 80)
    print("📖 EXTRACTION PYPDF")
    print("-" * 80)
    
    text_pypdf = extract_with_pypdf(local_path)
    print(f"Longueur: {len(text_pypdf)} chars")
    
    if len(text_pypdf) < 100:
        print("⚠️ PDF probablement scanné (texte vide)")
    else:
        print(f"\n📄 Extrait (500 premiers chars):\n{text_pypdf[:500]}")
    
    # ÉTAPE 2: Extraction Document AI
    print("\n" + "-" * 80)
    print("🔍 EXTRACTION DOCUMENT AI OCR")
    print("-" * 80)
    
    text_docai = extract_with_document_ai(local_path)
    
    if text_docai:
        print(f"\n📄 Extrait (1000 premiers chars):\n{text_docai[:1000]}")
    
    # ÉTAPE 3: Extraction des produits
    best_text = text_docai if len(text_docai) > len(text_pypdf) else text_pypdf
    
    print("\n" + "-" * 80)
    print("🏷️ EXTRACTION STRUCTURÉE DES PRODUITS")
    print("-" * 80)
    
    products = extract_products_from_text(best_text)
    
    print(f"\n✅ {len(products)} produits détectés\n")
    
    for i, p in enumerate(products[:10], 1):
        print(f"[{i}] Ref: {p['product_ref']}")
        print(f"    Prix: {p['price_eur']}€ | {p['natural_pct']}% naturel | Volume: {p['volume_ml']}ml | Yuka: {p['yuka_score']}")
        print(f"    Block: {p['raw_block'][:100]}...")
        print()
    
    print("=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    print(f"\nMeilleure extraction: {'Document AI' if len(text_docai) > len(text_pypdf) else 'pypdf'}")
    print(f"Caractères extraits: {len(best_text)}")
    print(f"Produits structurés: {len(products)}")
    
    # Statistiques
    with_price = sum(1 for p in products if p['price_eur'])
    with_natural = sum(1 for p in products if p['natural_pct'])
    
    print(f"   - Avec prix: {with_price}/{len(products)}")
    print(f"   - Avec % naturel: {with_natural}/{len(products)}")
    
    return products


if __name__ == "__main__":
    products = main()
