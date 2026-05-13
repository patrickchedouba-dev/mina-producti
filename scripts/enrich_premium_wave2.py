#!/usr/bin/env python3
"""
Vague 2 d'enrichissement premium pour Mina-voix.
Protocoles phares + produits associés.
Max 20 nouvelles fiches.
"""

import os
import sys
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


# === PROTOCOLES PHARES (5) + PRODUITS ASSOCIÉS ===

WAVE2_ENTRIES = [
    # === PROTOCOLES ===
    {
        "name": "CURE SILHOUETTE",
        "type": "PROTOCOLE",
        "search_in": "bodyminute_docs",
        "skin_need": "Remodelage corporel, cellulite installée, relâchement cutané post-grossesse ou perte de poids",
        "primary_mechanism": "L'enveloppement à chaud au Thym Rouge crée un effet sauna qui active la lipolyse, tandis que le massage palper-rouler décolle les adipocytes",
        "key_actives_summary": "Thym Rouge (détoxifiant thermogène), Citron (drainant lymphatique), Crème Enveloppement à Chaud",
        "voice_answer_template": "La Cure Silhouette cible la cellulite et le relâchement cutané. L'enveloppement chauffant au Thym Rouge active le déstockage des graisses pendant environ 20 minutes, suivi d'un massage palper-rouler. Elle utilise la Crème Enveloppement Cure Silhouette à Chaud. Durée totale : environ 1 heure."
    },
    {
        "name": "SOIN LONGUE TENUE ANTI-COMÉDONS",
        "type": "PROTOCOLE",
        "search_in": "bodyminute_docs",
        "skin_need": "Peaux grasses à très grasses, comédons ouverts et fermés, pores dilatés, brillance excessive",
        "primary_mechanism": "Le Vapozone dilate les pores pour faciliter l'extraction manuelle des comédons, le masque purifiant resserre et régule le sébum",
        "key_actives_summary": "Vapozone (ouverture des pores), Masque Anti-Comédons PRO (purifie, matifie), Extraction manuelle douce",
        "voice_answer_template": "Le Soin Longue Tenue Anti-Comédons est idéal pour les peaux grasses avec imperfections. Le Vapozone ouvre les pores pendant 10 minutes pour faciliter l'extraction des comédons. Ensuite, le Masque Anti-Comédons PRO purifie et resserre les pores. Durée : 1 heure."
    },
    {
        "name": "SOIN HYDRATEMPO CABINE",
        "type": "PROTOCOLE",
        "search_in": "bodyminute_docs",
        "skin_need": "Peaux déshydratées, tiraillements, teint terne, premiers signes de l'âge",
        "primary_mechanism": "L'acide hyaluronique 3D pénètre en profondeur pour créer un réservoir d'hydratation et stimuler le collagène naturel",
        "key_actives_summary": "HYA Sérum 3D (acide hyaluronique multi-poids), Masque Hydratempo (repulpant), Massage liftant",
        "voice_answer_template": "Le Soin Hydratempo Cabine repulpe et hydrate les peaux déshydratées. Il utilise le HYA Sérum 3D à l'acide hyaluronique qui stimule le collagène. Le Masque Hydratempo apporte un effet repulpant immédiat. Durée : environ 45 minutes."
    },
    {
        "name": "SOIN SENSIMINE CABINE",
        "type": "PROTOCOLE",
        "search_in": "bodyminute_docs",
        "skin_need": "Peaux sensibles, réactives, couperose légère, rougeurs diffuses",
        "primary_mechanism": "La Calmosensine et les actifs suisses apaisent les irritations et renforcent la barrière cutanée fragilisée",
        "key_actives_summary": "Calmosensine (apaisante), Eau des Glaciers Suisse (hydratante), Masque Sensimine PRO (protecteur)",
        "voice_answer_template": "Le Soin Sensimine Cabine est conçu pour les peaux sensibles et réactives. La Calmosensine calme les irritations tandis que l'Eau des Glaciers Suisse hydrate en profondeur. Le Masque Sensimine PRO renforce la barrière cutanée. Durée : 45 minutes."
    },
    {
        "name": "SOIN S-DÉTOX CABINE",
        "type": "PROTOCOLE",
        "search_in": "bodyminute_docs",
        "skin_need": "Peaux mixtes à grasses, imperfections, teint brouillé par la pollution urbaine",
        "primary_mechanism": "Les actifs détoxifiants éliminent les toxines et polluants accumulés, le Clarimatt régule la production de sébum",
        "key_actives_summary": "Clarimatt (sébo-régulateur), Saule Noir (purifiant antibactérien), Gel S-Détox (matifiant longue tenue)",
        "voice_answer_template": "Le Soin S-Détox Cabine purifie les peaux mixtes à grasses exposées à la pollution. Le Clarimatt régule le sébum pendant que le Saule Noir élimine les impuretés. Le Gel S-Détox offre un fini mat longue durée. Durée : 45 minutes."
    },
    
    # === PRODUITS ASSOCIÉS AUX PROTOCOLES ===
    
    # Cure Silhouette
    {
        "product_ref": "V027.0",
        "name": "CRÈME ENVELOPPEMENT CURE SILHOUETTE À CHAUD",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Cellulite, rétention d'eau, peau d'orange",
        "primary_mechanism": "L'effet thermogène du Thym Rouge active la microcirculation et favorise le déstockage des graisses",
        "key_actives_summary": "Thym Rouge (thermogène), Citron (drainant), Huile de Coco (nourrit)",
        "voice_answer_template": "La Crème Enveloppement Cure Silhouette à Chaud, utilisée en cabine, crée un effet sauna grâce au Thym Rouge thermogène. Elle draine et aide à déstocker les graisses localisées."
    },
    
    # Anti-Comédons
    {
        "product_ref": "V010.0",
        "name": "MASQUE ANTI-COMÉDONS PRO",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Peaux grasses, comédons, points noirs",
        "primary_mechanism": "L'argile verte absorbe l'excès de sébum tandis que les actifs purifiants resserrent les pores",
        "key_actives_summary": "Argile Verte (absorbante), Zinc (sébo-régulateur), Acide Salicylique (kératolytique)",
        "voice_answer_template": "Le Masque Anti-Comédons PRO est notre masque professionnel pour peaux grasses. Son Argile Verte absorbe l'excès de sébum et le Zinc régule la production. Idéal après extraction des comédons."
    },
    {
        "product_ref": "V009.0",
        "name": "GEL S-DÉTOX SNAP SPOT",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Boutons isolés, imperfections localisées, acné légère",
        "primary_mechanism": "Action ciblée SOS qui assèche les boutons et accélère leur cicatrisation",
        "key_actives_summary": "Clarimatt (asséchant), Saule Noir (antibactérien), 96% naturel",
        "voice_answer_template": "Le Gel S-Détox Snap Spot, référence V009.0, est un soin SOS à 96% naturel. Il assèche rapidement les boutons grâce au Clarimatt et au Saule Noir antibactérien. Prix : 12,30 euros."
    },
    
    # Hydratempo
    {
        "product_ref": "V016.0",
        "name": "MASQUE HYDRATEMPO PRO",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Peaux déshydratées, ridules de déshydratation, manque d'éclat",
        "primary_mechanism": "L'acide hyaluronique multi-poids crée une réserve d'eau profonde pour une hydratation 24h",
        "key_actives_summary": "Acide Hyaluronique 3D (repulpant), Aloe Vera (apaisante), 98% naturel",
        "voice_answer_template": "Le Masque Hydratempo PRO, utilisé en cabine, apporte une hydratation intense grâce à l'Acide Hyaluronique 3D. Il repulpe visiblement les ridules de déshydratation. Effet fraîcheur immédiat."
    },
    
    # Sensimine
    {
        "product_ref": "V020.0",
        "name": "SÉRUM SENSIMINE APAISANT",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Peaux sensibles, rougeurs, échauffements cutanés",
        "primary_mechanism": "La Calmosensine calme instantanément les inflammations et renforce la tolérance de la peau",
        "key_actives_summary": "Calmosensine (anti-inflammatoire), Eau des Glaciers (hydratante), 95% naturel",
        "voice_answer_template": "Le Sérum Sensimine Apaisant calme instantanément les peaux sensibles et réactives. Sa Calmosensine réduit les rougeurs et renforce la barrière cutanée. Formule à 95% naturelle."
    },
    
    # S-Détox
    {
        "product_ref": "V011.0",
        "name": "LOTION S-DÉTOX PURIFIANTE",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Peaux mixtes à grasses, pores dilatés, teint terne",
        "primary_mechanism": "Les acides de fruits éliminent les cellules mortes et affinent le grain de peau",
        "key_actives_summary": "AHA (exfoliant doux), Saule Noir (purifiant), Menthol (fraîcheur)",
        "voice_answer_template": "La Lotion S-Détox Purifiante prépare la peau au soin cabine. Ses AHA affinent le grain de peau et le Saule Noir purifie les pores. Sensation fraîcheur immédiate."
    },
    
    # Produits complémentaires
    {
        "product_ref": "V014.0",
        "name": "CRÈME ANTI-ÂGE METABOLIC",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Peaux matures, rides installées, perte de fermeté",
        "primary_mechanism": "Le Collagène Marin et la Vitamine C stimulent la synthèse de collagène et luttent contre le relâchement",
        "key_actives_summary": "Collagène Marin (restructurant), Vitamine C (antioxydant), Acide Hyaluronique",
        "voice_answer_template": "La Crème Anti-Âge Metabolic, référence V014.0, combat les rides et la perte de fermeté. Son Collagène Marin et sa Vitamine C raffermissent visiblement la peau."
    },
    {
        "product_ref": "V021.0",
        "name": "HUILE MASSAGE VISAGE RELAXANTE",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Tous types de peaux, besoin de détente, massage facial",
        "primary_mechanism": "Les huiles végétales nourrissantes permettent un massage glissant tout en apportant des actifs anti-âge",
        "key_actives_summary": "Huile d'Argan (nourrissante), Huile de Rose Musquée (régénérante), Vitamine E",
        "voice_answer_template": "L'Huile Massage Visage Relaxante est utilisée pour les massages faciaux en cabine. Son Huile d'Argan nourrit pendant que la Rose Musquée régénère. Parfaite pour les soins anti-âge."
    },
    {
        "product_ref": "V022.0",
        "name": "GOMMAGE VISAGE ÉCLAT",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Teint terne, peau rugueuse, cellules mortes",
        "primary_mechanism": "Les grains exfoliants éliminent les cellules mortes pour révéler un teint lumineux",
        "key_actives_summary": "Grains de Bambou (exfoliant doux), Vitamine C (éclat), Aloe Vera (apaisante)",
        "voice_answer_template": "Le Gommage Visage Éclat exfolie délicatement grâce aux grains de Bambou. La Vitamine C booste l'éclat du teint. À utiliser 1 à 2 fois par semaine."
    },
    {
        "product_ref": "V023.0",
        "name": "TONIQUE FRAÎCHEUR PEAUX NORMALES",
        "type": "PRODUIT",
        "search_in": "bodyminute_products",
        "skin_need": "Peaux normales à mixtes, rafraîchissement, préparation au soin",
        "primary_mechanism": "L'Hamamélis tonifie et resserre les pores tandis que les eaux florales rafraîchissent",
        "key_actives_summary": "Hamamélis (astringent), Eau de Rose (apaisante), Concombre (fraîcheur)",
        "voice_answer_template": "Le Tonique Fraîcheur pour peaux normales complète le rituel de nettoyage. Son Hamamélis resserre les pores et l'Eau de Rose apaise. À appliquer matin et soir."
    }
]


def get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )


def find_product_by_ref(client, product_ref: str, collection: str):
    """Trouve un produit par référence."""
    all_points = []
    offset = None
    
    while True:
        results, next_offset = client.scroll(
            collection_name=collection,
            limit=100,
            offset=offset,
            with_payload=True
        )
        all_points.extend(results)
        if next_offset is None:
            break
        offset = next_offset
    
    for point in all_points:
        if point.payload.get("product_ref") == product_ref:
            return point
    return None


def update_payload(client, point_id: str, new_fields: Dict, collection: str):
    """Met à jour le payload d'un point."""
    client.set_payload(
        collection_name=collection,
        payload=new_fields,
        points=[point_id]
    )


def run_wave2():
    """Exécute l'enrichissement vague 2."""
    print("\n" + "=" * 80)
    print("🚀 ENRICHISSEMENT PREMIUM - VAGUE 2")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    
    enriched = []
    not_found = []
    
    protocols = [e for e in WAVE2_ENTRIES if e["type"] == "PROTOCOLE"]
    products = [e for e in WAVE2_ENTRIES if e["type"] == "PRODUIT"]
    
    print(f"\n📋 Protocoles à enrichir: {len(protocols)}")
    print(f"📦 Produits à enrichir: {len(products)}")
    print(f"📊 Total: {len(WAVE2_ENTRIES)} fiches (max 20)")
    
    # === PRODUITS ===
    print("\n" + "-" * 80)
    print("🏷️ ENRICHISSEMENT PRODUITS")
    print("-" * 80)
    
    for entry in products:
        ref = entry.get("product_ref", "")
        name = entry["name"]
        collection = entry["search_in"]
        
        print(f"\n[{ref}] {name}")
        
        point = find_product_by_ref(client, ref, collection)
        
        if point:
            new_fields = {
                "skin_need": entry["skin_need"],
                "primary_mechanism": entry["primary_mechanism"],
                "key_actives_summary": entry["key_actives_summary"],
                "voice_answer_template": entry["voice_answer_template"],
                "is_premium": True
            }
            
            update_payload(client, point.id, new_fields, collection)
            print(f"   ✅ Enrichi")
            enriched.append(entry)
        else:
            print(f"   ⚠️ Non trouvé dans {collection}")
            not_found.append(entry)
    
    # === PROTOCOLES (référence seulement) ===
    print("\n" + "-" * 80)
    print("📋 PROTOCOLES (données de référence)")
    print("-" * 80)
    
    for entry in protocols:
        name = entry["name"]
        print(f"\n[PROTOCOLE] {name}")
        print(f"   ✅ Données vocales préparées")
        enriched.append(entry)
    
    # === RAPPORT FINAL ===
    print("\n" + "=" * 80)
    print("📊 RAPPORT FINAL - VAGUE 2")
    print("=" * 80)
    
    print(f"\n✅ Enrichis: {len(enriched)}")
    print(f"⚠️ Non trouvés: {len(not_found)}")
    
    # Détail par protocole
    print("\n" + "-" * 80)
    print("📋 PROTOCOLES ET PRODUITS ASSOCIÉS")
    print("-" * 80)
    
    for proto in protocols:
        print(f"\n{'='*60}")
        print(f"🏥 {proto['name']}")
        print(f"   🎯 Besoin: {proto['skin_need'][:60]}...")
        print(f"   🎤 Voice: {proto['voice_answer_template'][:100]}...")
        
        # Produits associés
        associated = [p for p in products if any(
            keyword in p["name"].upper() or keyword in proto["name"].upper()
            for keyword in ["SILHOUETTE", "COMÉDONS", "HYDRA", "SENSI", "DÉTOX"]
            if keyword in proto["name"].upper() and keyword in p.get("key_actives_summary", "").upper() + p["name"].upper()
        )]
    
    print("\n" + "-" * 80)
    print("📦 TOUS LES PRODUITS ENRICHIS")
    print("-" * 80)
    
    for p in [e for e in enriched if e["type"] == "PRODUIT"]:
        print(f"\n[{p.get('product_ref', 'N/A')}] {p['name']}")
        print(f"   🎤 {p['voice_answer_template']}")
    
    print("\n" + "=" * 80)
    print("✅ ENRICHISSEMENT VAGUE 2 TERMINÉ")
    print("=" * 80)
    
    return enriched, not_found


if __name__ == "__main__":
    enriched, not_found = run_wave2()
