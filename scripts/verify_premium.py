#!/usr/bin/env python3
"""Vérifie les enrichissements premium dans Qdrant."""

import os
import sys
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


def main():
    client = get_qdrant_client()
    
    # Récupérer tous les points avec is_premium=True
    results, _ = client.scroll(
        collection_name="bodyminute_products",
        limit=100,
        with_payload=True
    )
    
    premium_products = [p for p in results if p.payload.get("is_premium")]
    
    print("\n" + "=" * 80)
    print("📋 RAPPORT FINAL - FICHES PREMIUM ENRICHIES")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    print(f"\n✅ Produits premium trouvés: {len(premium_products)}")
    
    for i, p in enumerate(premium_products, 1):
        payload = p.payload
        print(f"\n{'─'*60}")
        print(f"[{i}] {payload.get('product_name', 'N/A')}")
        print(f"    Réf: {payload.get('product_ref', 'N/A')}")
        print(f"    Prix: {payload.get('price_eur', 'N/A')}€")
        print(f"    🎯 skin_need: {payload.get('skin_need', '—')}")
        print(f"    ⚙️ primary_mechanism: {payload.get('primary_mechanism', '—')}")
        print(f"    🔬 key_actives_summary: {payload.get('key_actives_summary', '—')}")
        print(f"    🎤 voice_answer_template: {payload.get('voice_answer_template', '—')}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
