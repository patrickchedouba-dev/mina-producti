#!/usr/bin/env python3
"""
Script pour lister les PDFs dans le bucket GCS et analyser leur structure.
"""

import os
import sys
from typing import List, Dict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def list_gcs_pdfs():
    """Liste tous les PDFs dans le bucket GCS mina-pdfs."""
    from google.cloud import storage
    
    bucket_name = "mina-pdfs"
    
    print("\n" + "=" * 80)
    print(f"📂 LISTING DES PDFs DANS gs://{bucket_name}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # Lister tous les fichiers
    blobs = list(bucket.list_blobs())
    
    # Organiser par dossier
    folders: Dict[str, List[Dict]] = {}
    
    for blob in blobs:
        if not blob.name.lower().endswith('.pdf'):
            continue
        
        parts = blob.name.split('/')
        folder = parts[0] if len(parts) > 1 else "root"
        filename = parts[-1]
        
        if folder not in folders:
            folders[folder] = []
        
        folders[folder].append({
            "name": filename,
            "path": blob.name,
            "size_kb": blob.size / 1024 if blob.size else 0,
        })
    
    # Afficher les résultats
    total_pdfs = 0
    product_folders = []
    
    print("\n📁 Structure du bucket:")
    for folder, files in sorted(folders.items()):
        is_product = any(kw in folder.upper() for kw in ["PRODUIT", "BOOK", "SKIN", "BODY"])
        marker = "🏷️" if is_product else "📋"
        
        print(f"\n{marker} {folder}/ ({len(files)} fichiers)")
        
        for f in files[:3]:  # Montrer les 3 premiers
            print(f"   └─ {f['name']} ({f['size_kb']:.1f} KB)")
        
        if len(files) > 3:
            print(f"   └─ ... et {len(files) - 3} autres fichiers")
        
        total_pdfs += len(files)
        
        if is_product:
            product_folders.append({
                "folder": folder,
                "files": files,
                "count": len(files)
            })
    
    print("\n" + "-" * 80)
    print(f"📊 RÉSUMÉ")
    print("-" * 80)
    print(f"\nTotal PDFs: {total_pdfs}")
    print(f"Dossiers identifiés: {len(folders)}")
    print(f"Dossiers produits: {len(product_folders)}")
    
    print("\n🏷️ DOSSIERS FICHES PRODUITS:")
    for pf in product_folders:
        print(f"   {pf['folder']}: {pf['count']} fichiers")
    
    print("\n" + "=" * 80)
    
    return folders, product_folders


def download_sample_pdf(folder_name: str, max_files: int = 2):
    """Télécharge des PDFs exemples pour analyse."""
    from google.cloud import storage
    import tempfile
    
    bucket_name = "mina-pdfs"
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    print(f"\n📥 Téléchargement de PDFs du dossier '{folder_name}'...")
    
    blobs = list(bucket.list_blobs(prefix=folder_name + "/"))
    pdf_blobs = [b for b in blobs if b.name.lower().endswith('.pdf')][:max_files]
    
    downloaded = []
    
    for blob in pdf_blobs:
        filename = blob.name.split('/')[-1]
        local_path = f"/tmp/{filename}"
        
        print(f"   ⬇️ {filename} ({blob.size/1024:.1f} KB)")
        blob.download_to_filename(local_path)
        
        downloaded.append({
            "gcs_path": blob.name,
            "local_path": local_path,
            "filename": filename,
            "size_kb": blob.size / 1024
        })
    
    return downloaded


def extract_text_pypdf(pdf_path: str) -> str:
    """Extraction basique avec pypdf."""
    from pypdf import PdfReader
    
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_text_document_ai(pdf_path: str, project_id: str = "bodycoachocr") -> str:
    """Extraction OCR avec Document AI."""
    from google.cloud import documentai_v1 as documentai
    
    # Lire le PDF
    with open(pdf_path, "rb") as f:
        content = f.read()
    
    # Initialiser Document AI
    client = documentai.DocumentProcessorServiceClient()
    
    # Obtenir ou créer le processeur OCR
    parent = f"projects/{project_id}/locations/eu"
    processors = list(client.list_processors(parent=parent))
    
    ocr_processor = None
    for p in processors:
        if "OCR" in p.type_.upper():
            ocr_processor = p.name
            break
    
    if not ocr_processor:
        print("   ⚠️ Pas de processeur OCR trouvé")
        return ""
    
    print(f"   🔍 OCR avec: {ocr_processor.split('/')[-1]}")
    
    # Traiter le document
    raw_document = documentai.RawDocument(
        content=content,
        mime_type="application/pdf"
    )
    
    request = documentai.ProcessRequest(
        name=ocr_processor,
        raw_document=raw_document
    )
    
    result = client.process_document(request=request)
    return result.document.text


def compare_extractions(pdf_info: Dict):
    """Compare les extractions pypdf vs Document AI."""
    pdf_path = pdf_info["local_path"]
    filename = pdf_info["filename"]
    
    print(f"\n{'='*80}")
    print(f"📄 ANALYSE: {filename}")
    print(f"{'='*80}")
    
    # Extraction pypdf
    print("\n📖 Extraction pypdf...")
    text_pypdf = extract_text_pypdf(pdf_path)
    print(f"   Longueur: {len(text_pypdf)} caractères")
    
    # Extraction Document AI
    print("\n🔍 Extraction Document AI OCR...")
    text_docai = extract_text_document_ai(pdf_path)
    print(f"   Longueur: {len(text_docai)} caractères")
    
    # Comparaison
    print("\n" + "-" * 80)
    print("📊 COMPARAISON")
    print("-" * 80)
    
    print(f"\n📖 PYPDF (premiers 1000 chars):")
    print("-" * 40)
    print(text_pypdf[:1000] if text_pypdf else "[VIDE - PDF scanné]")
    
    print(f"\n🔍 DOCUMENT AI (premiers 1000 chars):")
    print("-" * 40)
    print(text_docai[:1000] if text_docai else "[ÉCHEC OCR]")
    
    # Détection des infos structurées
    print("\n" + "-" * 80)
    print("🏷️ INFORMATIONS PRODUITS DÉTECTÉES")
    print("-" * 80)
    
    import re
    
    best_text = text_docai if len(text_docai) > len(text_pypdf) else text_pypdf
    
    # Patterns
    prices = re.findall(r'(\d+[.,]\d{2})\s*€', best_text)
    refs = re.findall(r'Ref[:\s]*([A-Z]?\d{2,4}[.]?\d*)', best_text, re.IGNORECASE)
    naturals = re.findall(r'(\d{1,3})\s*%\s*(?:d\')?(?:ingrédients\s+)?(?:d\')?(?:origine\s+)?naturel', best_text, re.IGNORECASE)
    volumes = re.findall(r'(\d+)\s*ml', best_text, re.IGNORECASE)
    
    print(f"\n   💰 Prix trouvés: {prices[:10]}")
    print(f"   🏷️ Références: {refs[:10]}")
    print(f"   🌿 % Naturel: {naturals[:10]}")
    print(f"   📦 Volumes (ml): {volumes[:10]}")
    
    return {
        "filename": filename,
        "pypdf_len": len(text_pypdf),
        "docai_len": len(text_docai),
        "prices": prices,
        "refs": refs,
        "best_extraction": "docai" if len(text_docai) > len(text_pypdf) else "pypdf",
        "text": best_text
    }


if __name__ == "__main__":
    # 1. Lister les PDFs
    folders, product_folders = list_gcs_pdfs()
    
    if product_folders:
        # 2. Télécharger des exemples du premier dossier produits
        first_product_folder = product_folders[0]["folder"]
        print(f"\n📥 Téléchargement d'exemples de '{first_product_folder}'...")
        
        samples = download_sample_pdf(first_product_folder, max_files=2)
        
        # 3. Comparer les extractions
        for sample in samples:
            compare_extractions(sample)
