#!/usr/bin/env python3
"""
Pipeline complet d'extraction et indexation des fiches produits Body Minute.

1. Télécharge les PDFs depuis GCS (dossiers PRODUITS_SKINMINUTE_*)
2. OCR avec Google Cloud Vision
3. Extraction structurée des produits
4. Création collection bodyminute_products dans Qdrant
5. Vectorisation et indexation
"""

import os
import sys
import re
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


@dataclass
class ProductCard:
    """Fiche produit Body Minute structurée."""
    product_name: str
    product_ref: str = ""
    price_eur: float = 0.0
    volume_ml: Optional[int] = None
    natural_origin_pct: Optional[int] = None
    skin_type_or_indication: str = ""
    key_actives: List[str] = field(default_factory=list)
    short_description: str = ""
    brand: str = "Body Minute"
    yuka_score: Optional[int] = None
    source_file: str = ""
    page_number: int = 0
    
    def to_text(self) -> str:
        """Génère un texte structuré pour la vectorisation."""
        parts = [self.product_name]
        
        if self.product_ref:
            parts.append(f"Référence: {self.product_ref}")
        
        if self.price_eur > 0:
            parts.append(f"Prix: {self.price_eur:.2f}€")
        
        if self.volume_ml:
            parts.append(f"Contenance: {self.volume_ml}ml")
        
        if self.natural_origin_pct:
            parts.append(f"{self.natural_origin_pct}% d'ingrédients d'origine naturelle")
        
        if self.skin_type_or_indication:
            parts.append(f"Indication: {self.skin_type_or_indication}")
        
        if self.key_actives:
            parts.append(f"Principes actifs: {', '.join(self.key_actives[:5])}")
        
        if self.yuka_score:
            parts.append(f"Score Yuka: {self.yuka_score}/100")
        
        if self.short_description:
            parts.append(self.short_description)
        
        return ". ".join(parts)
    
    def to_payload(self) -> Dict:
        """Génère le payload pour Qdrant."""
        return {
            "doc_type": "product_card",
            "brand": self.brand,
            "product_name": self.product_name,
            "product_ref": self.product_ref,
            "price_eur": self.price_eur,
            "volume_ml": self.volume_ml,
            "natural_origin_pct": self.natural_origin_pct,
            "skin_type_or_indication": self.skin_type_or_indication,
            "key_actives": self.key_actives,
            "yuka_score": self.yuka_score,
            "text": self.to_text(),
            "source_file": self.source_file,
            "page_number": self.page_number,
        }


class ProductExtractor:
    """Extracteur de fiches produits depuis le texte OCR."""
    
    def __init__(self):
        # Patterns améliorés basés sur l'OCR réel
        self.patterns = {
            "price": re.compile(r'(\d+[.,]\d{2})\s*€'),
            "reference": re.compile(r'Ref\s*\.?\s*([A-Z]?\d{2,4}[.]?\d*)', re.IGNORECASE),
            # Pattern pour capturer: 89%\nD'ingrédients d'origine naturelle
            "natural_pct": re.compile(r'(\d{1,3})\s*%\s*\n?\s*[Dd]\'?ingrédients', re.IGNORECASE),
            "volume_ml": re.compile(r'(\d+)\s*ml', re.IGNORECASE),
            "yuka": re.compile(r'Yuka\s*[:\s]*(\d+)', re.IGNORECASE),
        }
        
        # Noms de produits connus pour validation
        self.product_keywords = [
            "gel mousse", "démaq", "demaq", "lotion", "crème", "creme", "sérum", "serum",
            "eau micellaire", "lait", "huile", "baume", "toniq", "masque", "gommage",
            "spray", "contour des yeux", "anti-", "hydra", "sensimine"
        ]
        
        # Types de peau
        self.skin_types = {
            "toutes peaux": "Toutes peaux",
            "tous types de peau": "Toutes peaux",
            "peaux grasses": "Peaux grasses",
            "peaux mixtes": "Peaux mixtes",
            "peaux sèches": "Peaux sèches",
            "peaux sensibles": "Peaux sensibles",
            "anti-acné": "Anti-acné",
            "anti-âge": "Anti-âge",
            "hydratant": "Hydratation",
        }
    
    def extract_from_page(self, page_text: str, source_file: str, page_num: int) -> List[ProductCard]:
        """Extrait les produits d'une page OCR."""
        products = []
        
        # Trouver les références
        refs = list(self.patterns["reference"].finditer(page_text))
        
        if not refs:
            return products
        
        # Pour chaque référence, extraire le produit associé
        for i, ref_match in enumerate(refs):
            # Prendre le contexte: du début de la page (ou ref précédente) jusqu'à cette ref
            start = refs[i-1].end() if i > 0 else 0
            end = ref_match.end()
            product_block = page_text[start:end]
            
            product = self._parse_product_block(product_block, ref_match.group(1), source_file, page_num)
            
            if product:
                products.append(product)
        
        return products
    
    def _parse_product_block(self, block: str, ref: str, source_file: str, page_num: int) -> Optional[ProductCard]:
        """Parse un bloc de texte pour créer une fiche produit."""
        
        # Extraire le nom du produit (première ligne significative)
        lines = block.strip().split('\n')
        product_name = self._extract_product_name(lines)
        
        if not product_name:
            return None
        
        product = ProductCard(
            product_name=product_name,
            product_ref=ref,
            source_file=source_file,
            page_number=page_num,
        )
        
        # Prix
        price_match = self.patterns["price"].search(block)
        if price_match:
            product.price_eur = float(price_match.group(1).replace(",", "."))
        
        # % naturel
        natural_match = self.patterns["natural_pct"].search(block)
        if natural_match:
            product.natural_origin_pct = int(natural_match.group(1))
        
        # Volume
        volume_match = self.patterns["volume_ml"].search(block)
        if volume_match:
            product.volume_ml = int(volume_match.group(1))
        
        # Yuka
        yuka_match = self.patterns["yuka"].search(block)
        if yuka_match:
            product.yuka_score = int(yuka_match.group(1))
        
        # Type de peau
        block_lower = block.lower()
        for pattern, label in self.skin_types.items():
            if pattern in block_lower:
                product.skin_type_or_indication = label
                break
        
        # Actifs (rechercher dans la section PRINCIPES ACTIFS)
        product.key_actives = self._extract_actives(block)
        
        return product
    
    def _extract_product_name(self, lines: List[str]) -> str:
        """Extrait le nom du produit des premières lignes."""
        name_parts = []
        
        for line in lines[:5]:
            line = line.strip()
            
            # Ignorer les lignes courtes ou de marque
            if len(line) < 3:
                continue
            if line.upper() in ["SKIN", "MINUTE", "SWITZERLAND", "BODY", "BEAUTY"]:
                continue
            if "J'AIME MA PEAU" in line:
                continue
            
            # Garder les lignes en majuscules (titres de produits)
            if line.isupper() or (len(line) > 5 and line[0].isupper()):
                name_parts.append(line)
                if len(' '.join(name_parts)) > 30:
                    break
        
        return ' '.join(name_parts[:2]).strip()[:80] if name_parts else ""
    
    def _extract_actives(self, block: str) -> List[str]:
        """Extrait les principes actifs du bloc."""
        actives = []
        
        # Chercher la section PRINCIPES ACTIFS
        if "PRINCIPES ACTIFS" in block.upper():
            # Prendre le texte après PRINCIPES ACTIFS
            idx = block.upper().find("PRINCIPES ACTIFS")
            actives_section = block[idx:idx+500]
            
            # Pattern: NOM_ACTIF → Action
            active_pattern = re.compile(r'([A-ZÉÈÀÙ][A-ZÉÈÀÙ\'\s]+)\s*→', re.IGNORECASE)
            matches = active_pattern.findall(actives_section)
            
            for match in matches[:5]:
                active = match.strip()
                if len(active) > 2 and active.upper() not in ["ACTIONS"]:
                    actives.append(active.title())
        
        return actives


def pdf_to_images(pdf_path: str, max_pages: int = 50) -> List[bytes]:
    """Convertit les pages PDF en images avec PyMuPDF."""
    import fitz
    
    doc = fitz.open(pdf_path)
    total_pages = min(len(doc), max_pages)
    
    image_bytes = []
    for i in range(total_pages):
        page = doc[i]
        mat = fitz.Matrix(150/72, 150/72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        image_bytes.append(img_bytes)
    
    doc.close()
    return image_bytes


def ocr_page(image_bytes: bytes) -> str:
    """OCR d'une page avec Google Cloud Vision."""
    from google.cloud import vision
    
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    
    response = client.document_text_detection(image=image)
    
    if response.error.message:
        raise Exception(response.error.message)
    
    return response.full_text_annotation.text if response.full_text_annotation else ""


def get_embedding(text: str) -> List[float]:
    """Génère l'embedding avec Vertex AI."""
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    
    project_id = os.getenv("GCS_PROJECT_ID", "bodycoachocr")
    location = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
    
    aiplatform.init(project=project_id, location=location)
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    embeddings = model.get_embeddings([text])
    return embeddings[0].values


def run_pipeline(max_pdfs: int = 5, max_pages_per_pdf: int = 20):
    """Exécute le pipeline complet."""
    from google.cloud import storage
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    
    print("\n" + "=" * 80)
    print("🚀 PIPELINE EXTRACTION FICHES PRODUITS BODY MINUTE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Configuration
    bucket_name = "mina-pdfs"
    target_folders = ["PRODUITS_SKINMINUTE_VISAGE", "PRODUITS_SKINMINUTE_CORPS"]
    target_collection = "bodyminute_products"
    
    # Clients
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    qdrant = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    extractor = ProductExtractor()
    
    # ÉTAPE 1: Lister les PDFs
    print(f"\n📂 [1/5] Recherche des PDFs produits dans gs://{bucket_name}...")
    
    pdf_files = []
    for folder in target_folders:
        blobs = bucket.list_blobs(prefix=folder + "/")
        for blob in blobs:
            if blob.name.lower().endswith('.pdf'):
                pdf_files.append(blob.name)
    
    print(f"   ✅ {len(pdf_files)} PDFs trouvés")
    for f in pdf_files[:5]:
        print(f"      - {f}")
    if len(pdf_files) > 5:
        print(f"      ... et {len(pdf_files) - 5} autres")
    
    # Limiter pour le test
    pdf_files = pdf_files[:max_pdfs]
    print(f"\n   📋 Traitement limité à {len(pdf_files)} PDFs")
    
    # ÉTAPE 2: Extraire les produits
    print(f"\n🔍 [2/5] Extraction OCR et parsing...")
    
    all_products: List[ProductCard] = []
    
    for pdf_idx, pdf_path in enumerate(pdf_files, 1):
        filename = pdf_path.split('/')[-1]
        print(f"\n   [{pdf_idx}/{len(pdf_files)}] {filename}")
        
        # Télécharger le PDF
        local_path = f"/tmp/{filename}"
        blob = bucket.blob(pdf_path)
        blob.download_to_filename(local_path)
        print(f"      ⬇️ Téléchargé ({os.path.getsize(local_path)//1024//1024} Mo)")
        
        # Convertir en images
        images = pdf_to_images(local_path, max_pages=max_pages_per_pdf)
        print(f"      📄 {len(images)} pages")
        
        # OCR + Extraction par page
        for page_num, img_bytes in enumerate(images, 1):
            try:
                text = ocr_page(img_bytes)
                products = extractor.extract_from_page(text, filename, page_num)
                all_products.extend(products)
                
                if products:
                    print(f"      Page {page_num}: {len(products)} produit(s)")
                    
            except Exception as e:
                print(f"      ⚠️ Page {page_num}: Erreur OCR - {e}")
        
        # Nettoyer
        os.remove(local_path)
    
    print(f"\n   ✅ Total: {len(all_products)} produits extraits")
    
    # ÉTAPE 3: Dédupliquer
    print(f"\n🔄 [3/5] Déduplication par référence...")
    
    seen_refs = set()
    unique_products = []
    
    for product in all_products:
        if product.product_ref and product.product_ref not in seen_refs:
            seen_refs.add(product.product_ref)
            unique_products.append(product)
        elif not product.product_ref:
            # Garder les produits sans ref si nom unique
            unique_products.append(product)
    
    print(f"   ✅ {len(unique_products)} produits uniques")
    
    # ÉTAPE 4: Créer la collection Qdrant
    print(f"\n📦 [4/5] Création collection '{target_collection}'...")
    
    try:
        qdrant.delete_collection(target_collection)
        print(f"   ⚠️ Collection existante supprimée")
    except:
        pass
    
    qdrant.create_collection(
        collection_name=target_collection,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE
        )
    )
    print(f"   ✅ Collection créée")
    
    # ÉTAPE 5: Vectoriser et indexer
    print(f"\n🔄 [5/5] Vectorisation et indexation...")
    
    batch_size = 10
    points = []
    
    for i, product in enumerate(unique_products, 1):
        print(f"\r   Traitement: {i}/{len(unique_products)}", end="", flush=True)
        
        try:
            product_text = product.to_text()
            embedding = get_embedding(product_text)
            
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=product.to_payload()
            )
            points.append(point)
            
            if len(points) >= batch_size:
                qdrant.upsert(collection_name=target_collection, points=points)
                points = []
                
        except Exception as e:
            print(f"\n   ⚠️ Erreur '{product.product_name}': {e}")
    
    # Insérer le reste
    if points:
        qdrant.upsert(collection_name=target_collection, points=points)
    
    print(f"\n   ✅ {len(unique_products)} produits indexés")
    
    # Résumé
    info = qdrant.get_collection(target_collection)
    
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    print(f"\n✅ Collection '{target_collection}': {info.points_count} vecteurs")
    
    print("\n📋 Exemples de produits indexés:")
    samples = qdrant.scroll(collection_name=target_collection, limit=5, with_payload=True)[0]
    
    for i, point in enumerate(samples, 1):
        p = point.payload
        print(f"\n   [{i}] {p.get('product_name', 'N/A')}")
        print(f"       Ref: {p.get('product_ref')} | Prix: {p.get('price_eur')}€ | {p.get('natural_origin_pct', '?')}% naturel")
        print(f"       Actifs: {p.get('key_actives', [])[:3]}")
    
    print("\n" + "=" * 80)
    
    return unique_products


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pdfs", type=int, default=3, help="Nombre max de PDFs")
    parser.add_argument("--max-pages", type=int, default=10, help="Pages max par PDF")
    args = parser.parse_args()
    
    products = run_pipeline(max_pdfs=args.max_pdfs, max_pages_per_pdf=args.max_pages)
