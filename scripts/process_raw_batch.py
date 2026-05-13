#!/usr/bin/env python3
"""
Pipeline d'Ingestion Intelligent - Body Minute.

Scanne tous les PDFs GCS, extrait les données via LLM (Gemini),
classifie et indexe automatiquement selon le score de confiance.

Usage:
    python scripts/process_raw_batch.py
    python scripts/process_raw_batch.py --max-docs 5         # Limiter le nombre de docs
    python scripts/process_raw_batch.py --skip-indexed       # Ignorer les déjà indexés
    python scripts/process_raw_batch.py --dry-run            # Test sans indexation
"""

import os
import sys

# IMPORTANT: Charger dotenv AVANT tout autre import qui utilise des variables d'env
from pathlib import Path
from dotenv import load_dotenv

# Charger explicitement le .env depuis la racine du projet
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Debug: vérifier que GOOGLE_API_KEY est chargée
_api_key = os.getenv("GOOGLE_API_KEY")
if _api_key:
    print(f"✅ GOOGLE_API_KEY détectée ({len(_api_key)} caractères)")
else:
    print("⚠️ GOOGLE_API_KEY non trouvée dans .env - L'extraction LLM ne fonctionnera pas")

import json
import uuid
import argparse
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
import io

sys.path.insert(0, str(project_root))


# =============================================================================
# CONFIGURATION
# =============================================================================

BUCKET_NAME = "mina-pdfs"
COLLECTION_NAME = "products_index"
CONFIDENCE_THRESHOLD = 0.8  # Seuil pour indexation automatique

# Dossiers à scanner dans GCS
TARGET_FOLDERS = [
    "PRODUITS_SKINMINUTE_VISAGE",
    "PRODUITS_SKINMINUTE_CORPS",
    "PROTOCOLS",
    "FORMATIONS",
    "SERVICES",
]

# Schéma JSON pour l'extraction LLM
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {
            "type": "string",
            "enum": ["product", "service", "protocol", "training", "other"],
            "description": "Type de document détecté"
        },
        "name": {
            "type": "string",
            "description": "Nom du produit/service/protocole"
        },
        "reference": {
            "type": "string",
            "description": "Référence (ex: V063.0, C011.0)"
        },
        "price_eur": {
            "type": "number",
            "description": "Prix en euros"
        },
        "natural_origin_pct": {
            "type": "integer",
            "description": "Pourcentage d'ingrédients naturels"
        },
        "key_actives": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Liste des principes actifs"
        },
        "skin_type": {
            "type": "string",
            "description": "Type de peau ou indication"
        },
        "usage_advice": {
            "type": "string",
            "description": "Conseil d'utilisation"
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step": {"type": "integer"},
                    "name": {"type": "string"},
                    "action": {"type": "string"},
                    "duration_minutes": {"type": "integer"}
                }
            },
            "description": "Étapes pour les protocoles/services"
        },
        "duration_minutes": {
            "type": "integer",
            "description": "Durée totale en minutes"
        },
        "volume_ml": {
            "type": "integer",
            "description": "Contenance en ml"
        },
        "confidence": {
            "type": "number",
            "description": "Score de confiance de l'extraction (0-1)"
        },
        "extraction_notes": {
            "type": "string",
            "description": "Notes sur la qualité de l'extraction"
        }
    },
    "required": ["doc_type", "name", "confidence"]
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExtractionResult:
    """Résultat d'extraction d'un document."""
    source_file: str
    doc_type: str
    name: str
    confidence: float
    data: Dict[str, Any]
    raw_text: str = ""  # Texte OCR brut pour indexation
    extraction_notes: str = ""
    indexed: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BatchStats:
    """Statistiques du batch."""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    docs_scanned: int = 0
    docs_processed: int = 0
    docs_indexed: int = 0
    docs_review_needed: int = 0
    docs_failed: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "docs_scanned": self.docs_scanned,
            "docs_processed": self.docs_processed,
            "docs_indexed": self.docs_indexed,
            "docs_review_needed": self.docs_review_needed,
            "docs_failed": self.docs_failed,
            "success_rate": f"{(self.docs_indexed / self.docs_processed * 100):.1f}%" if self.docs_processed > 0 else "0%"
        }


# =============================================================================
# GCS & OCR FUNCTIONS
# =============================================================================

def get_gcs_client():
    """Initialise le client Google Cloud Storage."""
    from google.cloud import storage
    project_id = os.getenv("GCS_PROJECT_ID", "bodycoachocr")
    return storage.Client(project=project_id)


def list_all_pdfs() -> List[str]:
    """Liste TOUS les PDFs du bucket GCS (tous les dossiers)."""
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    
    print(f"   🔍 Scan complet du bucket gs://{BUCKET_NAME}...")
    
    # Lister TOUS les blobs du bucket (pas de filtre par dossier)
    all_pdfs = []
    folders_found = set()
    
    try:
        blobs = bucket.list_blobs()
        for blob in blobs:
            if blob.name.lower().endswith('.pdf'):
                all_pdfs.append(blob.name)
                # Extraire le dossier racine
                if '/' in blob.name:
                    folders_found.add(blob.name.split('/')[0])
        
        print(f"   📁 Dossiers trouvés: {len(folders_found)}")
        for folder in sorted(folders_found):
            count = len([p for p in all_pdfs if p.startswith(folder + '/')])
            print(f"      - {folder}: {count} PDFs")
            
    except Exception as e:
        print(f"   ⚠️ Erreur listage bucket: {e}")
    
    return all_pdfs


def download_pdf(blob_name: str) -> bytes:
    """Télécharge un PDF depuis GCS."""
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes()


def pdf_to_images(pdf_bytes: bytes, max_pages: int = 10) -> List[bytes]:
    """Convertit les pages PDF en images."""
    import fitz  # PyMuPDF
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = min(len(doc), max_pages)
    
    images = []
    for i in range(total_pages):
        page = doc[i]
        mat = fitz.Matrix(150/72, 150/72)  # 150 DPI
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("png"))
    
    doc.close()
    return images


def ocr_image(image_bytes: bytes) -> str:
    """OCR d'une image avec Google Cloud Vision."""
    from google.cloud import vision
    
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    
    response = client.document_text_detection(image=image)
    
    if response.error.message:
        raise Exception(response.error.message)
    
    return response.full_text_annotation.text if response.full_text_annotation else ""


def extract_text_from_pdf(blob_name: str) -> str:
    """Extrait le texte d'un PDF via OCR."""
    pdf_bytes = download_pdf(blob_name)
    images = pdf_to_images(pdf_bytes, max_pages=30)  # Augmenté pour capturer tout le contenu
    
    all_text = []
    for img_bytes in images:
        try:
            text = ocr_image(img_bytes)
            if text:
                all_text.append(text)
        except Exception as e:
            print(f"      ⚠️ OCR erreur: {e}")
    
    return "\n\n---PAGE---\n\n".join(all_text)


# =============================================================================
# LLM EXTRACTION
# =============================================================================

def get_gemini_model():
    """Initialise le modèle Gemini."""
    from google import genai
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY non configurée")
    
    genai.configure(api_key=api_key)
    # Utiliser gemini-2.0-flash (modèle stable et rapide)
    return genai.GenerativeModel("gemini-2.0-flash")


def extract_with_llm(text: str, source_file: str) -> Optional[ExtractionResult]:
    """Extrait les données structurées avec Gemini."""
    
    if not text.strip():
        return None
    
    # Conserver le texte OCR brut (limité à 30K pour l'embedding)
    raw_text_for_index = text[:100000]  # FULL MEMORY: garder jusqu'à 100K caractères
    
    model = get_gemini_model()
    
    prompt = f"""Tu es un expert en extraction de données Body Minute.
Analyse le texte OCR suivant et extrais les informations structurées.

**Source:** {source_file}

**Texte OCR:**
{text[:8000]}  # Limiter la longueur

**Instructions:**
1. Détermine le TYPE de document (product, service, protocol, training, other)
2. Extrais toutes les informations disponibles
3. Attribue un score de CONFIANCE de 0 à 1:
   - 1.0 = Données complètes et claires
   - 0.8 = Données principales présentes
   - 0.5 = Données partielles
   - 0.2 = Très peu d'informations exploitables

**Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après:**

```json
{{
  "doc_type": "product|service|protocol|training|other",
  "name": "Nom du produit/service",
  "reference": "V0XX.0 ou null",
  "price_eur": 0.00,
  "natural_origin_pct": 0,
  "key_actives": ["Actif 1", "Actif 2"],
  "skin_type": "Type de peau ou indication",
  "usage_advice": "Conseil d'utilisation",
  "steps": [
    {{"step": 1, "name": "Étape", "action": "Description"}}
  ],
  "duration_minutes": 0,
  "volume_ml": 0,
  "confidence": 0.85,
  "extraction_notes": "Notes sur l'extraction"
}}
```
"""
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extraire le JSON de la réponse
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        data = json.loads(response_text)
        
        # Si le LLM retourne un tableau (plusieurs produits), prendre le premier
        if isinstance(data, list):
            if len(data) > 0:
                data = data[0]
            else:
                data = {}
        
        return ExtractionResult(
            source_file=source_file,
            doc_type=data.get("doc_type", "other"),
            name=data.get("name", "Inconnu"),
            confidence=float(data.get("confidence", 0.5)),
            data=data,
            raw_text=raw_text_for_index,  # Stocker le texte OCR
            extraction_notes=data.get("extraction_notes", "")
        )
        
    except json.JSONDecodeError as e:
        print(f"      ⚠️ JSON invalide: {e}")
        return ExtractionResult(
            source_file=source_file,
            doc_type="other",
            name="Extraction échouée",
            confidence=0.0,
            data={},
            raw_text=raw_text_for_index,
            extraction_notes=f"Erreur JSON: {e}"
        )
    except Exception as e:
        print(f"      ⚠️ Erreur LLM: {e}")
        return None


# =============================================================================
# INDEXATION
# =============================================================================

def get_qdrant_client():
    """Initialise le client Qdrant."""
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )


def get_embedding(text: str) -> List[float]:
    """Génère l'embedding."""
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    
    project_id = os.getenv("GCS_PROJECT_ID", "bodycoachocr")
    location = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
    
    aiplatform.init(project=project_id, location=location)
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    embeddings = model.get_embeddings([text])
    return embeddings[0].values


def build_text_for_indexing(extraction: ExtractionResult) -> str:
    """Construit le texte pour l'indexation."""
    data = extraction.data
    parts = []
    
    parts.append(f"Type: {extraction.doc_type}")
    parts.append(f"Nom: {extraction.name}")
    
    if data.get("reference"):
        parts.append(f"Référence: {data['reference']}")
    
    if data.get("price_eur"):
        parts.append(f"Prix: {data['price_eur']}€")
    
    if data.get("natural_origin_pct"):
        parts.append(f"{data['natural_origin_pct']}% d'origine naturelle")
    
    if data.get("key_actives"):
        parts.append(f"Actifs: {', '.join(data['key_actives'])}")
    
    if data.get("skin_type"):
        parts.append(f"Indication: {data['skin_type']}")
    
    if data.get("usage_advice"):
        parts.append(f"Conseil: {data['usage_advice']}")
    
    if data.get("steps"):
        steps_text = []
        for step in data["steps"]:
            steps_text.append(f"Étape {step.get('step', '?')}: {step.get('name', '')} - {step.get('action', '')}")
        parts.append("Étapes: " + " | ".join(steps_text))
    
    if data.get("duration_minutes"):
        parts.append(f"Durée: {data['duration_minutes']} minutes")
    
    return ". ".join(parts)


def index_extraction(extraction: ExtractionResult, dry_run: bool = False) -> bool:
    """Indexe une extraction dans Qdrant."""
    from qdrant_client.models import PointStruct
    
    if dry_run:
        print(f"      [DRY-RUN] Indexation simulée: {extraction.name}")
        return True
    
    try:
        # Utiliser le texte OCR brut pour l'embedding (meilleure recherche)
        # Limité à 8000 chars pour l'embedding
        text_for_embedding = extraction.raw_text[:8000] if extraction.raw_text else build_text_for_indexing(extraction)
        embedding = get_embedding(text_for_embedding)
        
        payload = {
            "doc_type": extraction.doc_type,
            "text": extraction.raw_text[:100000],  # FULL MEMORY: stocker jusqu'à 100K caractères
            "text_summary": build_text_for_indexing(extraction),  # Résumé structuré
            "source_file": extraction.source_file,
            "confidence": extraction.confidence,
            "extraction_notes": extraction.extraction_notes,
            **extraction.data
        }
        
        # Nettoyer les clés None
        payload = {k: v for k, v in payload.items() if v is not None}
        
        client = get_qdrant_client()
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )]
        )
        
        return True
        
    except Exception as e:
        print(f"      ⚠️ Erreur indexation: {e}")
        return False


# =============================================================================
# REVIEW LOG
# =============================================================================

def write_review_log(extractions: List[ExtractionResult], output_file: str):
    """Écrit les extractions à faible confiance dans un fichier de review."""
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Documents à revoir - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"# Seuil de confiance: {CONFIDENCE_THRESHOLD}\n")
        f.write("=" * 80 + "\n\n")
        
        for ext in extractions:
            f.write(f"## {ext.name}\n")
            f.write(f"- **Source:** {ext.source_file}\n")
            f.write(f"- **Type:** {ext.doc_type}\n")
            f.write(f"- **Confiance:** {ext.confidence:.2f}\n")
            f.write(f"- **Notes:** {ext.extraction_notes}\n\n")
            
            f.write("**Données extraites:**\n```json\n")
            f.write(json.dumps(ext.data, indent=2, ensure_ascii=False))
            f.write("\n```\n\n")
            f.write("-" * 40 + "\n\n")
    
    print(f"📝 Log de review écrit: {output_file}")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_batch_processing(
    max_docs: Optional[int] = None,
    skip_indexed: bool = False,
    dry_run: bool = False
):
    """Exécute le traitement batch complet."""
    
    print("\n" + "=" * 80)
    print("🚀 PIPELINE D'INGESTION INTELLIGENT")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    stats = BatchStats()
    high_confidence: List[ExtractionResult] = []
    low_confidence: List[ExtractionResult] = []
    
    # 1. Lister les PDFs
    print(f"\n📂 [1/5] Scan du bucket gs://{BUCKET_NAME}...")
    all_pdfs = list_all_pdfs()
    stats.docs_scanned = len(all_pdfs)
    
    print(f"   ✅ {len(all_pdfs)} PDFs trouvés")
    
    if max_docs:
        all_pdfs = all_pdfs[:max_docs]
        print(f"   📋 Limité à {len(all_pdfs)} documents")
    
    # 2. Vérifier les documents déjà indexés
    if skip_indexed:
        print(f"\n🔍 [2/5] Vérification des documents déjà indexés...")
        client = get_qdrant_client()
        # TODO: implémenter la vérification via scroll
        print(f"   ⚠️ Skip non implémenté pour l'instant")
    else:
        print(f"\n⏭️ [2/5] Pas de skip - tous les documents seront traités")
    
    # 3. Traitement des documents
    print(f"\n🔄 [3/5] Extraction LLM de {len(all_pdfs)} documents...")
    
    for i, pdf_path in enumerate(all_pdfs, 1):
        filename = pdf_path.split("/")[-1]
        print(f"\n   [{i}/{len(all_pdfs)}] {filename}")
        
        try:
            # OCR
            print(f"      📄 OCR en cours...")
            text = extract_text_from_pdf(pdf_path)
            
            if not text.strip():
                print(f"      ⚠️ Texte vide après OCR")
                stats.docs_failed += 1
                continue
            
            print(f"      ✅ {len(text)} caractères extraits")
            
            # Extraction LLM
            print(f"      🤖 Extraction LLM...")
            extraction = extract_with_llm(text, pdf_path)
            
            if not extraction:
                print(f"      ❌ Extraction échouée")
                stats.docs_failed += 1
                continue
            
            stats.docs_processed += 1
            
            print(f"      📊 Type: {extraction.doc_type} | Nom: {extraction.name[:40]}")
            print(f"      🎯 Confiance: {extraction.confidence:.2f}")
            
            # Classification par confiance
            if extraction.confidence >= CONFIDENCE_THRESHOLD:
                high_confidence.append(extraction)
                print(f"      ✅ → Indexation automatique")
            else:
                low_confidence.append(extraction)
                print(f"      📝 → Review nécessaire")
            
        except Exception as e:
            print(f"      ❌ Erreur: {e}")
            stats.docs_failed += 1
            stats.errors.append(f"{pdf_path}: {str(e)}")
    
    # 4. Indexation des documents à haute confiance
    print(f"\n📥 [4/5] Indexation des {len(high_confidence)} documents haute confiance...")
    
    for ext in high_confidence:
        success = index_extraction(ext, dry_run=dry_run)
        if success:
            ext.indexed = True
            stats.docs_indexed += 1
    
    stats.docs_review_needed = len(low_confidence)
    
    # 5. Écriture du log de review
    print(f"\n📝 [5/5] Génération du log de review...")
    
    if low_confidence:
        review_file = f"reports/review_needed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        os.makedirs("reports", exist_ok=True)
        write_review_log(low_confidence, review_file)
    else:
        print(f"   ✅ Aucun document à revoir")
    
    # Résumé
    stats.end_time = datetime.now()
    
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DU TRAITEMENT")
    print("=" * 80)
    print(f"\n✅ Documents scannés: {stats.docs_scanned}")
    print(f"✅ Documents traités: {stats.docs_processed}")
    print(f"✅ Documents indexés (confiance > {CONFIDENCE_THRESHOLD}): {stats.docs_indexed}")
    print(f"📝 Documents à revoir (confiance < {CONFIDENCE_THRESHOLD}): {stats.docs_review_needed}")
    print(f"❌ Documents échoués: {stats.docs_failed}")
    print(f"⏱️ Durée totale: {stats.to_dict()['duration_seconds']:.1f} secondes")
    
    if dry_run:
        print(f"\n⚠️ MODE DRY-RUN: Aucune donnée n'a été réellement indexée")
    
    # Vérification finale
    if not dry_run:
        try:
            client = get_qdrant_client()
            info = client.get_collection(COLLECTION_NAME)
            print(f"\n📦 Collection '{COLLECTION_NAME}': {info.points_count} vecteurs totaux")
        except Exception as e:
            print(f"\n⚠️ Erreur vérification collection: {e}")
    
    print("\n" + "=" * 80)
    print("✅ PIPELINE TERMINÉ")
    print("=" * 80 + "\n")
    
    return stats


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline d'ingestion intelligent Body Minute")
    parser.add_argument("--max-docs", type=int, default=None, help="Nombre max de documents à traiter")
    parser.add_argument("--skip-indexed", action="store_true", help="Ignorer les documents déjà indexés")
    parser.add_argument("--dry-run", action="store_true", help="Simuler sans indexer réellement")
    
    args = parser.parse_args()
    
    stats = run_batch_processing(
        max_docs=args.max_docs,
        skip_indexed=args.skip_indexed,
        dry_run=args.dry_run
    )
