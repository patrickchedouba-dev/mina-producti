#!/usr/bin/env python3
"""
Rapport de couverture premium Mina.
Calcule le taux de fiches enrichies et l'estimation de couverture.
"""

import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )


def scroll_all(client, collection: str):
    """Récupère tous les points d'une collection."""
    all_points = []
    offset = None
    
    while True:
        results, next_offset = client.scroll(
            collection_name=collection,
            limit=200,
            offset=offset,
            with_payload=True
        )
        all_points.extend(results)
        if next_offset is None:
            break
        offset = next_offset
    
    return all_points


def analyze_skin_types(payloads):
    """Analyse la distribution des types de peau couverts."""
    skin_types = Counter()
    
    keywords = {
        "peaux grasses": ["grasse", "grasses", "sébum", "brillance", "matifi"],
        "peaux sèches": ["sèche", "sèches", "déshydrat", "nutrition"],
        "peaux sensibles": ["sensible", "sensibles", "réactive", "rougeur", "apais"],
        "peaux matures": ["mature", "anti-âge", "rides", "fermeté", "collagène"],
        "peaux mixtes": ["mixte", "mixtes", "zone t"],
        "tous types": ["tous types", "universel", "quotidien"]
    }
    
    for payload in payloads:
        skin_need = (payload.get("skin_need", "") or "").lower()
        for skin_type, kws in keywords.items():
            if any(kw in skin_need for kw in kws):
                skin_types[skin_type] += 1
    
    return skin_types


def analyze_care_types(payloads):
    """Analyse la distribution des types de soins."""
    care_types = Counter()
    
    keywords = {
        "visage hydratation": ["hydra", "déshydrat", "repulp"],
        "visage anti-âge": ["anti-âge", "rides", "fermeté", "collagène", "liftant"],
        "visage purifiant": ["purifiant", "détox", "comédons", "sébum", "matifi"],
        "visage apaisant": ["apaisant", "sensim", "rougeur", "calme"],
        "corps minceur": ["silhouette", "cellulite", "minceur", "sculptan"],
        "corps hydratation": ["corps", "hydratant corps", "lait corps"],
        "épilation": ["épilation", "cire", "poil"],
        "massage": ["massage", "relaxant", "antistress"]
    }
    
    for payload in payloads:
        name = (payload.get("protocol_name", "") or payload.get("product_name", "") or "").lower()
        skin_need = (payload.get("skin_need", "") or "").lower()
        combined = f"{name} {skin_need}"
        
        for care_type, kws in keywords.items():
            if any(kw in combined for kw in kws):
                care_types[care_type] += 1
    
    return care_types


def run_report():
    """Génère le rapport de couverture."""
    print("\n" + "=" * 80)
    print("📊 RAPPORT DE COUVERTURE PREMIUM MINA")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    
    # === PRODUITS ===
    print("\n" + "-" * 80)
    print("📦 COLLECTION: bodyminute_products")
    print("-" * 80)
    
    products = scroll_all(client, "bodyminute_products")
    total_products = len(products)
    premium_products = [p for p in products if p.payload.get("is_premium")]
    
    print(f"\n   Total produits: {total_products}")
    print(f"   Produits premium: {len(premium_products)}")
    print(f"   📈 Taux de couverture: {len(premium_products)/total_products*100:.1f}%")
    
    # Types de peau couverts (produits)
    prod_skin_types = analyze_skin_types([p.payload for p in premium_products])
    print("\n   Distribution types de peau (produits premium):")
    for skin_type, count in prod_skin_types.most_common():
        print(f"      • {skin_type}: {count}")
    
    # === PROTOCOLES ===
    print("\n" + "-" * 80)
    print("🏥 COLLECTION: bodyminute_docs")
    print("-" * 80)
    
    docs = scroll_all(client, "bodyminute_docs")
    total_docs = len(docs)
    premium_protocols = [d for d in docs if d.payload.get("is_protocol_premium")]
    
    # Protocoles distincts
    protocol_names = set(p.payload.get("protocol_name") for p in premium_protocols if p.payload.get("protocol_name"))
    
    print(f"\n   Total chunks docs: {total_docs}")
    print(f"   Chunks protocoles premium: {len(premium_protocols)}")
    print(f"   Protocoles distincts: {len(protocol_names)}")
    print(f"   📈 Taux chunks premium: {len(premium_protocols)/total_docs*100:.1f}%")
    
    # Liste des protocoles
    print("\n   Protocoles premium indexés:")
    for name in sorted(protocol_names):
        print(f"      • {name}")
    
    # Types de soins couverts
    proto_care_types = analyze_care_types([p.payload for p in premium_protocols])
    print("\n   Distribution types de soins (protocoles):")
    for care_type, count in proto_care_types.most_common():
        print(f"      • {care_type}: {count}")
    
    # === ESTIMATION COUVERTURE GLOBALE ===
    print("\n" + "-" * 80)
    print("📈 ESTIMATION COUVERTURE GLOBALE")
    print("-" * 80)
    
    # Calcul pondéré : produits comptent 60%, protocoles 40%
    prod_coverage = len(premium_products) / total_products
    proto_coverage = len(protocol_names) / 15  # Sur 15 soins cabine typiques
    
    # Limiter proto_coverage à 100%
    proto_coverage = min(proto_coverage, 1.0)
    
    global_coverage = (prod_coverage * 0.6) + (proto_coverage * 0.4)
    
    print(f"\n   • Couverture produits: {prod_coverage*100:.1f}% ({len(premium_products)}/{total_products})")
    print(f"   • Couverture protocoles: {proto_coverage*100:.1f}% ({len(protocol_names)}/15 soins types)")
    print(f"\n   🎯 COUVERTURE GLOBALE ESTIMÉE: {global_coverage*100:.1f}%")
    
    # Qualité des réponses
    with_voice_template = len([p for p in premium_products if p.payload.get("voice_answer_template")])
    proto_with_template = len([p for p in premium_protocols if p.payload.get("voice_answer_template_protocol")])
    
    print("\n   Qualité des réponses vocales:")
    print(f"      • Produits avec voice_template: {with_voice_template}/{len(premium_products)}")
    print(f"      • Protocoles avec voice_template: {proto_with_template}/{len(premium_protocols)}")
    
    print("\n" + "=" * 80)
    print("✅ RAPPORT TERMINÉ")
    print("=" * 80)
    
    return {
        "total_products": total_products,
        "premium_products": len(premium_products),
        "total_docs": total_docs,
        "premium_protocols": len(premium_protocols),
        "protocol_names": len(protocol_names),
        "global_coverage": global_coverage
    }


if __name__ == "__main__":
    run_report()
