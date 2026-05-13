#!/usr/bin/env python3
"""
Pipeline d'extraction et indexation des fiches produits Body Minute.
Extrait les produits des chunks existants et crée une collection Qdrant dédiée.
"""

import os
import sys
import re
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


@dataclass
class ProductCard:
    """Structure d'une fiche produit Body Minute."""
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
    source_chunk_id: str = ""
    
    def to_text(self) -> str:
        """Génère un texte structuré pour le vectorisation (250-400 chars)."""
        parts = [f"{self.product_name}"]
        
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
            parts.append(f"Actifs: {', '.join(self.key_actives[:5])}")
        
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
            "source_chunk_id": self.source_chunk_id,
        }


class ProductExtractor:
    """Extracteur de fiches produits depuis les chunks Qdrant."""
    
    def __init__(self):
        self.patterns = {
            "price": re.compile(r'(\d+[.,]\d{2})\s*€', re.IGNORECASE),
            "reference": re.compile(r'Ref[:\s]*([A-Z]?\d{2,4}[.]?\d*)', re.IGNORECASE),
            "natural_pct": re.compile(r'(\d{1,3})\s*%\s*(?:d\'(?:ingrédients\s+)?origine\s+)?naturel', re.IGNORECASE),
            "volume_ml": re.compile(r'(\d+)\s*ml', re.IGNORECASE),
            "yuka_score": re.compile(r'Yuka\s*[:\s]*(\d+)/100', re.IGNORECASE),
        }
        
        # Patterns pour détecter les noms de produits
        self.product_name_patterns = [
            # Format: NOM PRODUIT suivi de pourcentage ou prix
            re.compile(r'([A-ZÉÈÀÙ][A-ZÉÈÀÙ\'\s\-]+(?:MINUTE|SKIN|BODY|BEAUTY|HYA)?[A-ZÉÈÀÙ\'\s\-]+)(?:\s*D\'ingrédients|\s*\d+\s*%|\s*\d+[.,]\d{2}\s*€)', re.IGNORECASE),
            # Format avec brand: SKIN minute NOM
            re.compile(r'(?:SKIN|BODY|BEAUTY|NAIL|HAIR)\s*\'?minute\s+([A-ZÉÈÀÙ][A-ZÉÈÀÙ\'\s\-0-9]+)', re.IGNORECASE),
        ]
        
        # Actifs connus
        self.known_actives = [
            "Acide Hyaluronique", "Vitamine C", "Vitamine E", "Aloe Vera",
            "Collagène", "Rétinol", "Niacinamide", "Glycérine",
            "Huile de Coco", "Huile de Jojoba", "Huile d'Argan", "Huile de Soja",
            "Beurre de Karité", "Extrait de Thé Vert", "Extrait de Rose",
            "Clarimatt", "Menthol", "Saule Noir", "Zinc", "Soufre",
            "Acide Salicylique", "AHA", "BHA", "Acide Lactique",
            "Eau Micellaire", "Charbon", "Argile", "Calendula",
        ]
        
        # Indications de peau
        self.skin_indications = [
            ("peaux mixtes", "Peaux mixtes"),
            ("peaux grasses", "Peaux grasses"),
            ("peaux sèches", "Peaux sèches"),
            ("peaux sensibles", "Peaux sensibles"),
            ("peaux matures", "Peaux matures"),
            ("anti-âge", "Anti-âge"),
            ("anti-acné", "Anti-acné"),
            ("anti-rides", "Anti-rides"),
            ("hydratant", "Hydratation"),
            ("nourrissant", "Nutrition"),
            ("apaisant", "Apaisant"),
            ("purifiant", "Purifiant"),
            ("éclat", "Éclat"),
        ]
    
    def extract_products_from_chunk(self, text: str, chunk_id: str) -> List[ProductCard]:
        """
        Extrait les produits d'un chunk de texte.
        Un chunk peut contenir plusieurs produits.
        """
        products = []
        
        # Trouver tous les prix et références
        prices = self.patterns["price"].findall(text)
        refs = self.patterns["reference"].findall(text)
        natural_pcts = self.patterns["natural_pct"].findall(text)
        volumes = self.patterns["volume_ml"].findall(text)
        yuka_scores = self.patterns["yuka_score"].findall(text)
        
        # Si pas de prix ET pas de référence, ignorer
        if not prices and not refs:
            return []
        
        # Stratégie: découper le texte autour des références
        # Les produits sont souvent structurés: NOM ... % naturel ... PRIX ... Ref: XXX
        
        # Essayer de trouver des blocs produits
        ref_positions = [(m.start(), m.group(1)) for m in self.patterns["reference"].finditer(text)]
        
        if ref_positions:
            # Découper autour des références
            for i, (pos, ref) in enumerate(ref_positions):
                # Prendre le texte avant cette référence (jusqu'à la ref précédente)
                start = ref_positions[i-1][0] + 20 if i > 0 else 0
                product_block = text[start:pos+20]
                
                product = self._parse_product_block(product_block, ref, chunk_id)
                if product and product.product_name:
                    products.append(product)
        else:
            # Pas de référence claire, essayer d'extraire un seul produit
            product = self._parse_product_block(text, "", chunk_id)
            if product and product.product_name:
                products.append(product)
        
        return products
    
    def _parse_product_block(self, block: str, ref: str, chunk_id: str) -> Optional[ProductCard]:
        """Parse un bloc de texte pour extraire un produit."""
        
        # Extraire le nom du produit
        product_name = self._extract_product_name(block)
        if not product_name or len(product_name) < 3:
            return None
        
        # Créer la fiche produit
        product = ProductCard(
            product_name=product_name,
            product_ref=ref or self._extract_first_match(self.patterns["reference"], block, ""),
            source_chunk_id=chunk_id,
        )
        
        # Extraire le prix
        price_match = self.patterns["price"].search(block)
        if price_match:
            product.price_eur = float(price_match.group(1).replace(",", "."))
        
        # Extraire le volume
        volume_match = self.patterns["volume_ml"].search(block)
        if volume_match:
            product.volume_ml = int(volume_match.group(1))
        
        # Extraire le pourcentage naturel
        natural_match = self.patterns["natural_pct"].search(block)
        if natural_match:
            product.natural_origin_pct = int(natural_match.group(1))
        
        # Extraire le score Yuka
        yuka_match = self.patterns["yuka_score"].search(block)
        if yuka_match:
            product.yuka_score = int(yuka_match.group(1))
        
        # Extraire les actifs
        product.key_actives = self._extract_actives(block)
        
        # Extraire l'indication de peau
        product.skin_type_or_indication = self._extract_skin_indication(block)
        
        return product
    
    def _extract_product_name(self, block: str) -> str:
        """Extrait le nom du produit du bloc."""
        # Nettoyer le bloc
        block_clean = block.replace('\n', ' ').strip()
        
        # Chercher des patterns connus
        for pattern in self.product_name_patterns:
            match = pattern.search(block_clean)
            if match:
                name = match.group(1).strip()
                # Nettoyer le nom
                name = re.sub(r'\s+', ' ', name)
                name = name.strip(' -\'')
                if len(name) > 5:
                    return name[:80]  # Limiter la longueur
        
        # Fallback: prendre les premiers mots en majuscules
        words = block_clean.split()
        name_parts = []
        for word in words[:10]:
            if word.isupper() or (len(word) > 2 and word[0].isupper()):
                name_parts.append(word)
                if len(name_parts) >= 5:
                    break
            elif name_parts:
                # Arrêter quand on rencontre un mot en minuscule après avoir commencé
                break
        
        if name_parts:
            return ' '.join(name_parts)[:80]
        
        return ""
    
    def _extract_actives(self, block: str) -> List[str]:
        """Extrait les actifs du bloc."""
        actives = []
        block_lower = block.lower()
        
        for active in self.known_actives:
            if active.lower() in block_lower:
                actives.append(active)
        
        return actives[:5]  # Limiter à 5 actifs
    
    def _extract_skin_indication(self, block: str) -> str:
        """Extrait l'indication de peau."""
        block_lower = block.lower()
        
        for pattern, label in self.skin_indications:
            if pattern in block_lower:
                return label
        
        return ""
    
    def _extract_first_match(self, pattern, text: str, default: str = "") -> str:
        """Extrait la première correspondance d'un pattern."""
        match = pattern.search(text)
        return match.group(1) if match else default


def get_qdrant_client():
    """Initialise le client Qdrant."""
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )


def get_embedding(text: str) -> List[float]:
    """Génère l'embedding d'un texte avec Vertex AI."""
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    
    project_id = os.getenv("GCS_PROJECT_ID", "bodycoachocr")
    location = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
    
    aiplatform.init(project=project_id, location=location)
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    embeddings = model.get_embeddings([text])
    return embeddings[0].values


def run_product_extraction_pipeline():
    """Pipeline complet d'extraction et indexation des produits."""
    print("\n" + "=" * 80)
    print("🚀 PIPELINE EXTRACTION FICHES PRODUITS BODY MINUTE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    source_collection = os.getenv("QDRANT_COLLECTION_NAME", "bodyminute_docs")
    target_collection = "bodyminute_products"
    
    client = get_qdrant_client()
    extractor = ProductExtractor()
    
    # ÉTAPE 1: Récupérer tous les chunks source
    print(f"\n📦 [1/4] Récupération des chunks de '{source_collection}'...")
    
    all_points = []
    offset = None
    
    while True:
        result = client.scroll(
            collection_name=source_collection,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        points, offset = result
        all_points.extend(points)
        
        if offset is None:
            break
    
    print(f"   ✅ {len(all_points)} chunks récupérés")
    
    # ÉTAPE 2: Extraire les produits
    print(f"\n🔍 [2/4] Extraction des fiches produits...")
    
    all_products: List[ProductCard] = []
    seen_refs = set()  # Pour éviter les doublons
    
    for point in all_points:
        payload = point.payload or {}
        text = payload.get("text", payload.get("content", payload.get("chunk", "")))
        
        if not text:
            continue
        
        products = extractor.extract_products_from_chunk(text, str(point.id))
        
        for product in products:
            # Éviter les doublons par référence
            if product.product_ref and product.product_ref in seen_refs:
                continue
            if product.product_ref:
                seen_refs.add(product.product_ref)
            
            # Filtrer les produits incomplets
            if product.product_name and (product.price_eur > 0 or product.product_ref):
                all_products.append(product)
    
    print(f"   ✅ {len(all_products)} produits extraits")
    
    # Afficher des exemples
    print(f"\n📋 Exemples de produits extraits:")
    for i, product in enumerate(all_products[:5], 1):
        print(f"\n   [{i}] {product.product_name}")
        print(f"       Ref: {product.product_ref} | Prix: {product.price_eur}€ | {product.natural_origin_pct or '?'}% naturel")
    
    # ÉTAPE 3: Créer la nouvelle collection
    print(f"\n📦 [3/4] Création de la collection '{target_collection}'...")
    
    from qdrant_client.models import Distance, VectorParams
    
    # Supprimer si existe
    try:
        client.delete_collection(target_collection)
        print(f"   ⚠️ Collection existante supprimée")
    except:
        pass
    
    # Créer la collection
    client.create_collection(
        collection_name=target_collection,
        vectors_config=VectorParams(
            size=768,  # Dimension text-embedding-004
            distance=Distance.COSINE
        )
    )
    print(f"   ✅ Collection '{target_collection}' créée")
    
    # ÉTAPE 4: Vectoriser et indexer les produits
    print(f"\n🔄 [4/4] Vectorisation et indexation...")
    
    from qdrant_client.models import PointStruct
    
    points_to_insert = []
    batch_size = 20
    
    for i, product in enumerate(all_products):
        print(f"\r   Traitement: {i+1}/{len(all_products)}", end="", flush=True)
        
        try:
            # Générer le texte et l'embedding
            product_text = product.to_text()
            embedding = get_embedding(product_text)
            
            # Créer le point
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=product.to_payload()
            )
            points_to_insert.append(point)
            
            # Insérer par batch
            if len(points_to_insert) >= batch_size:
                client.upsert(
                    collection_name=target_collection,
                    points=points_to_insert
                )
                points_to_insert = []
                
        except Exception as e:
            print(f"\n   ⚠️ Erreur pour '{product.product_name}': {e}")
    
    # Insérer les points restants
    if points_to_insert:
        client.upsert(
            collection_name=target_collection,
            points=points_to_insert
        )
    
    print(f"\n   ✅ {len(all_products)} produits indexés")
    
    # Vérification finale
    info = client.get_collection(target_collection)
    
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    print(f"\n✅ Collection '{target_collection}' créée avec {info.points_count} vecteurs")
    print(f"   Dimension: 768 (text-embedding-004)")
    print(f"   Distance: Cosine")
    
    print("\n📋 Exemples de payloads:")
    # Récupérer quelques exemples
    sample = client.scroll(
        collection_name=target_collection,
        limit=3,
        with_payload=True
    )[0]
    
    for i, point in enumerate(sample, 1):
        p = point.payload
        print(f"\n   [{i}] {p.get('product_name', 'N/A')}")
        print(f"       Ref: {p.get('product_ref')} | Prix: {p.get('price_eur')}€")
        print(f"       {p.get('natural_origin_pct', 'N/A')}% naturel | Yuka: {p.get('yuka_score', 'N/A')}/100")
        print(f"       Actifs: {p.get('key_actives', [])}")
    
    print("\n" + "=" * 80)
    
    return all_products


if __name__ == "__main__":
    products = run_product_extraction_pipeline()
