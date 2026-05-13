#!/usr/bin/env python3
"""
Enrichissement des 20 fiches produits/soins premium pour Mina.
Ajoute des champs vocaux pour réponses professionnelles.
"""

import os
import sys
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


# === DÉFINITION DES 20 FICHES PREMIUM ===

PREMIUM_PRODUCTS = [
    # === VISAGE ===
    {
        "product_ref": "V012.0",
        "product_name": "SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ",
        "skin_need": "Peaux mixtes à grasses, sujettes aux imperfections et à l'acné",
        "primary_mechanism": "Le Clarimatt associé à l'extrait de Saule Noir régule l'excès de sébum et purifie les pores en profondeur",
        "key_actives_summary": "Clarimatt (sébo-régulateur), Extrait de Saule Noir (purifiant), Menthol (effet fraîcheur antibactérien)",
        "voice_answer_template": "Le Sérum S-Détox Spray Anti-Acné, référence V012.0, est formulé à 88% d'origine naturelle pour les peaux à imperfections. Il contient du Clarimatt et de l'extrait de Saule Noir qui purifient et régulent le sébum. Prix client : 15,80 euros."
    },
    {
        "product_ref": "V018.0",
        "product_name": "CRÈME SENSIMINE ULTRA NOURRISSANTE",
        "skin_need": "Peaux sensibles et très sèches, besoin de nutrition intense",
        "primary_mechanism": "L'Eau des Glaciers Suisses et le Pin des Alpes apportent une hydratation profonde et renforcent la barrière cutanée",
        "key_actives_summary": "Eau des Glaciers Suisse (hydratation), Pin des Alpes Suisse (protection), 97% d'origine naturelle",
        "voice_answer_template": "La Crème Sensimine Ultra Nourrissante, référence V018.0, est à 97% naturelle avec un score Yuka de 93. Enrichie en Eau des Glaciers Suisses, elle nourrit intensément les peaux sensibles et sèches. Prix : 16,60 euros."
    },
    {
        "product_ref": "V017.0",
        "product_name": "CRÈME SENSIMINE ULTRA APAISANTE",
        "skin_need": "Peaux sensibles réactives, rougeurs, inconfort cutané",
        "primary_mechanism": "Formule à 94% naturelle qui calme les irritations et hydrate en profondeur grâce aux actifs suisses",
        "key_actives_summary": "Eau des Glaciers Suisse (apaisante), Pin des Alpes Suisse (hydrate profondément)",
        "voice_answer_template": "La Crème Sensimine Ultra Apaisante, référence V017.0, calme les peaux sensibles et réactives. À 94% naturelle avec un Yuka de 93, elle apaise les rougeurs. Prix : 14,80 euros."
    },
    {
        "product_ref": "V015.0",
        "product_name": "HYA SÉRUM 3D HYDRATEMPO",
        "skin_need": "Peaux déshydratées, perte d'éclat, premiers signes de l'âge",
        "primary_mechanism": "L'acide hyaluronique 3D stimule la production de collagène et retient l'eau dans les couches profondes de la peau",
        "key_actives_summary": "Acide Hyaluronique 3D (repulpant), Polysaccharides (stimule le collagène), 99% naturel",
        "voice_answer_template": "Le Hya Sérum 3D Hydratempo, référence V015.0, est notre sérum star à 99% naturel. Son acide hyaluronique 3D repulpe et stimule le collagène pour une peau éclatante. Prix : 25,60 euros."
    },
    {
        "product_ref": "V002.0",
        "product_name": "GEL MOUSSE FLORAL NETTOYANT VISAGE",
        "skin_need": "Tous types de peaux, nettoyage quotidien doux",
        "primary_mechanism": "La combinaison Fleur d'Oranger, Bleuet et Grenade nettoie en douceur tout en tonifiant le teint",
        "key_actives_summary": "Fleur d'Oranger (tonifie), Bleuet (décongestionne), Extrait de Grenade (exfolie en douceur)",
        "voice_answer_template": "Le Gel Mousse Floral Nettoyant, référence V002.0, convient à toutes les peaux. À 89% naturel, il nettoie délicatement grâce à la Fleur d'Oranger et au Bleuet. Prix : 6,70 euros."
    },
    {
        "product_ref": "V008.0",
        "product_name": "GEL S-DÉTOX MATT ++",
        "skin_need": "Peaux mixtes à grasses, excès de brillance",
        "primary_mechanism": "Formule matifiante longue durée qui contrôle le sébum et affine le grain de peau",
        "key_actives_summary": "Complexe matifiant (contrôle sébum), 91% naturel",
        "voice_answer_template": "Le Gel S-Détox Matt Plus Plus, référence V008.0, est un soin matifiant à 91% naturel. Il contrôle la brillance et affine le grain de peau des peaux grasses. Prix : 16,20 euros."
    },
    {
        "product_ref": "V007.0",
        "product_name": "CRÈME S-DÉTOX EQUILIBREXPRESS",
        "skin_need": "Peaux mixtes déséquilibrées, zones grasses et sèches",
        "primary_mechanism": "Le Symbiocell et l'Epicalmin rééquilibrent la peau et boostent le système immunitaire cutané",
        "key_actives_summary": "Symbiocell (améliore le confort), Epicalmin (booste l'immunité cutanée), Enzyme de Grenade (antioxydant)",
        "voice_answer_template": "La Crème S-Détox Equilibrexpress, référence V007.0, rééquilibre les peaux mixtes à 87% naturel. Elle contient du Symbiocell pour le confort et de l'Epicalmin pour l'immunité. Prix : 17,20 euros."
    },
    {
        "product_ref": "V025.0",
        "product_name": "CONTOUR DES YEUX REGARD LIFTANT",
        "skin_need": "Cernes, poches, rides du contour de l'œil",
        "primary_mechanism": "Action liftante et défatigante qui réduit visiblement les signes de fatigue du regard",
        "key_actives_summary": "Complexe liftant (anti-rides), Actifs décongestionnants (anti-poches), 90% naturel",
        "voice_answer_template": "Le Contour des Yeux Regard Liftant, référence V025.0, est à 90% naturel. Il liftte, défatigue et réduit cernes et poches pour un regard plus jeune. Prix : 24,80 euros."
    },
    {
        "product_ref": "C011.0",
        "product_name": "MASQUE 2.0 SENSIMINE PRO",
        "skin_need": "Peaux sensibles, rougeurs, besoin d'apaisement professionnel",
        "primary_mechanism": "La Calmosensine calme instantanément les irritations et renforce la résistance cutanée",
        "key_actives_summary": "Calmosensine (apaise), Actifs protecteurs (renforce la peau)",
        "voice_answer_template": "Le Masque 2.0 Sensimine Pro, référence C011.0, est notre masque professionnel pour peaux sensibles. Sa Calmosensine apaise instantanément les irritations. Prix cabine : 24,60 euros."
    },
    {
        "product_ref": "V006.0",
        "product_name": "EAU MICELLAIRE À L'ALOE VERA",
        "skin_need": "Tous types de peaux, démaquillage doux et hydratant",
        "primary_mechanism": "Les micelles captent les impuretés tandis que l'Aloe Vera cicatrise et apaise",
        "key_actives_summary": "Aloe Vera (cicatrise, apaise, hydrate), Micelles (nettoient en douceur), 93% naturel",
        "voice_answer_template": "L'Eau Micellaire à l'Aloe Vera, référence V006.0, démaquille et apaise à 93% naturel. Son Aloe Vera hydrate et cicatrise la peau. Score Yuka : 45. Prix : 9,40 euros."
    },
    
    # === CORPS ===
    {
        "product_ref": "V030.0",
        "product_name": "GOMME CORPS EXFOLIANT INTENSE",
        "skin_need": "Peaux ternes, rugueuses, besoin de renouvellement cellulaire",
        "primary_mechanism": "L'exfoliation mécanique avec l'Eau d'Hamamélis active le renouvellement cellulaire et raffermit",
        "key_actives_summary": "Grains exfoliants (renouvellement cellulaire), Eau d'Hamamélis (tonifie, resserre les pores), 94% naturel",
        "voice_answer_template": "La Gomme Corps Exfoliant Intense, référence V030.0, est à 94% naturelle. Son Eau d'Hamamélis active le renouvellement cellulaire pour une peau lisse et tonifiée. Prix : 11,60 euros."
    },
    {
        "product_ref": "V032.0",
        "product_name": "SOIN CORPS PROFOND HYPER HYDRATANT",
        "skin_need": "Peaux sèches à très sèches, déshydratation corporelle",
        "primary_mechanism": "La Glycérine Végétale et les actifs hydratants créent un réservoir d'eau pour 24h d'hydratation",
        "key_actives_summary": "Glycérine Végétale (fort pouvoir hydratant), Hydration After Hours (hydratation longue durée), 90% naturel",
        "voice_answer_template": "Le Soin Corps Profond Hyper Hydratant, référence V032.0, hydrate intensément pendant 24 heures grâce à la Glycérine Végétale. Format professionnel 500ml à 90% naturel. Prix : 15,90 euros."
    },
    {
        "product_ref": "V062.0",
        "product_name": "HUILE APAISANTE APRÈS ÉPILATION",
        "skin_need": "Peaux irritées post-épilation, rougeurs, sensations de tiraillement",
        "primary_mechanism": "Le Calendula et l'Huile de Tournesol cicatrisent et calment instantanément les irritations",
        "key_actives_summary": "Calendula (cicatrise), Huile de Tournesol (nourrit et apaise), 99% naturel",
        "voice_answer_template": "L'Huile Apaisante Après Épilation, référence V062.0, est à 99% naturelle. Son Calendula cicatrise et calme les peaux sensibilisées après l'épilation. Prix : 8,70 euros."
    },
    {
        "product_ref": "V035.0",
        "product_name": "CRÈME MAINS",
        "skin_need": "Mains sèches, abîmées, besoin de réparation",
        "primary_mechanism": "L'Huile d'Amande Douce Bio et l'Edelweiss réparent et protègent les mains desséchées",
        "key_actives_summary": "Huile d'Amande Douce Bio (répare), Extrait d'Edelweiss (protège), 99% naturel",
        "voice_answer_template": "La Crème Mains, référence V035.0, est à 99% naturelle. Son Huile d'Amande Douce Bio et Edelweiss réparent et adoucissent vos mains. Prix : 5,30 euros."
    },
    {
        "product_ref": "V054.0",
        "product_name": "LAIT CORPS DOUX",
        "skin_need": "Tous types de peaux, hydratation quotidienne légère",
        "primary_mechanism": "La Glycérine Végétale et l'Huile de Tournesol hydratent sans effet gras",
        "key_actives_summary": "Glycérine Végétale (hydratation), Huile de Tournesol (nutrition légère), 92% naturel",
        "voice_answer_template": "Le Lait Corps Doux, référence V054.0, est un soin quotidien à 92% naturel. Sa Glycérine Végétale hydrate sans graisser. Prix : 10,20 euros."
    },
    
    # === PROTOCOLES / SOINS (dans bodyminute_docs) ===
    {
        "protocol_name": "CURE SILHOUETTE",
        "is_protocol": True,
        "skin_need": "Remodelage corporel, cellulite, relâchement cutané",
        "primary_mechanism": "L'enveloppement chauffant associé au massage palper-rouler stimule la circulation et déstocke les graisses",
        "key_actives_summary": "Crème Enveloppement Cure Silhouette à Chaud (Thym Rouge détoxifiant, Citron drainant)",
        "voice_answer_template": "La Cure Silhouette est notre protocole minceur phare. L'enveloppement chauffant au Thym Rouge et Citron stimule le déstockage et raffermit la silhouette. Durée : environ 1 heure."
    },
    {
        "protocol_name": "SOIN LONGUE TENUE ANTI-COMÉDONS",
        "is_protocol": True,
        "skin_need": "Peaux grasses à imperfections, comédons, pores dilatés",
        "primary_mechanism": "Le Vapozone ouvre les pores, l'extraction manuelle élimine les comédons, le masque purifiant resserre",
        "key_actives_summary": "Vapozone (ouverture des pores), Masque Anti-Comédons PRO (purifie), Extraction manuelle",
        "voice_answer_template": "Le Soin Longue Tenue Anti-Comédons dure 1 heure. Le Vapozone ouvre les pores pour l'extraction, puis le Masque Anti-Comédons purifie et resserre. Idéal pour les peaux grasses."
    },
    {
        "protocol_name": "SOIN ANTISTRESS",
        "is_protocol": True,
        "skin_need": "Stress, tensions, fatigue musculaire",
        "primary_mechanism": "Le massage relaxant aux huiles détend les tensions et apporte une sensation de bien-être profond",
        "key_actives_summary": "Huile Massage Corps relaxante, Digito-pression points de tension",
        "voice_answer_template": "Le Soin Antistress de 30 minutes est un massage relaxant qui libère les tensions. Les points de digito-pression apportent un bien-être immédiat. Parfait pour décompresser."
    },
    {
        "protocol_name": "SOIN REGARD LIFTANT",
        "is_protocol": True,
        "skin_need": "Fatigue du regard, rides d'expression, poches et cernes",
        "primary_mechanism": "Le Bioactif Collagène et la feuille de Collagène liftent et repulpent instantanément le contour des yeux",
        "key_actives_summary": "Bioactif Collagène (repulpe), Feuille de Collagène (lifting), Contour des Yeux Regard Liftant",
        "voice_answer_template": "Le Soin Regard Liftant sublime le contour des yeux. La feuille de Collagène et le Bioactif repulpent et liftent pour un regard défatigué et rajeuni."
    },
    {
        "protocol_name": "HOME SPA METABOLISSIME",
        "is_protocol": True,
        "skin_need": "Peau terne, fatiguée, manque d'éclat",
        "primary_mechanism": "La routine stimulante Metabolissime active le métabolisme cellulaire pour redonner de l'éclat",
        "key_actives_summary": "Elixir Cell Flash Metabolissime (Vitamine C raffermissante), Actifs stimulants",
        "voice_answer_template": "La routine Home Spa Metabolissime réveille les peaux fatiguées. L'Elixir Cell Flash à la Vitamine C booste le métabolisme cellulaire pour un teint éclatant."
    }
]


def get_qdrant_client():
    """Initialise le client Qdrant."""
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )


def find_product_in_qdrant(client, product_ref: str, collection: str = "bodyminute_products"):
    """Trouve un produit par sa référence dans Qdrant (sans index)."""
    
    # Scroll toute la collection et filtrer manuellement
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
    
    # Chercher le produit par sa référence
    for point in all_points:
        if point.payload.get("product_ref") == product_ref:
            return point
    
    return None


def update_product_payload(client, point_id: str, new_fields: Dict, collection: str = "bodyminute_products"):
    """Met à jour le payload d'un point Qdrant."""
    from qdrant_client.models import SetPayloadOperation, PointIdsList
    
    client.set_payload(
        collection_name=collection,
        payload=new_fields,
        points=[point_id]
    )


def run_enrichment():
    """Exécute l'enrichissement des 20 fiches premium."""
    print("\n" + "=" * 80)
    print("🎯 ENRICHISSEMENT FICHES PREMIUM MINA")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    
    enriched = []
    not_found = []
    
    # Traitement des produits
    products = [p for p in PREMIUM_PRODUCTS if not p.get("is_protocol")]
    protocols = [p for p in PREMIUM_PRODUCTS if p.get("is_protocol")]
    
    print(f"\n📦 Produits à enrichir: {len(products)}")
    print(f"📋 Protocoles à enrichir: {len(protocols)}")
    
    # === PRODUITS ===
    print("\n" + "-" * 80)
    print("🏷️ ENRICHISSEMENT PRODUITS")
    print("-" * 80)
    
    for product in products:
        ref = product["product_ref"]
        name = product["product_name"]
        
        print(f"\n[{ref}] {name}")
        
        # Chercher le produit dans Qdrant
        point = find_product_in_qdrant(client, ref)
        
        if point:
            # Préparer les nouveaux champs
            new_fields = {
                "skin_need": product["skin_need"],
                "primary_mechanism": product["primary_mechanism"],
                "key_actives_summary": product["key_actives_summary"],
                "voice_answer_template": product["voice_answer_template"],
                "is_premium": True
            }
            
            # Mettre à jour
            update_product_payload(client, point.id, new_fields)
            
            print(f"   ✅ Enrichi avec données vocales")
            enriched.append({
                "ref": ref,
                "name": name,
                "type": "PRODUIT",
                **product
            })
        else:
            print(f"   ⚠️ Non trouvé dans Qdrant")
            not_found.append({"ref": ref, "name": name, "type": "PRODUIT"})
    
    # === PROTOCOLES (stockés dans un fichier séparé ou logs) ===
    print("\n" + "-" * 80)
    print("📋 DONNÉES PROTOCOLES (pour référence)")
    print("-" * 80)
    
    for protocol in protocols:
        name = protocol["protocol_name"]
        print(f"\n[PROTOCOLE] {name}")
        print(f"   ✅ Données préparées (non indexées dans bodyminute_products)")
        enriched.append({
            "ref": "PROTOCOLE",
            "name": name,
            "type": "PROTOCOLE",
            **protocol
        })
    
    # === RAPPORT FINAL ===
    print("\n" + "=" * 80)
    print("📊 RAPPORT FINAL")
    print("=" * 80)
    
    print(f"\n✅ Enrichis: {len(enriched)}")
    print(f"⚠️ Non trouvés: {len(not_found)}")
    
    print("\n" + "-" * 80)
    print("📋 FICHES PREMIUM ENRICHIES")
    print("-" * 80)
    
    for item in enriched:
        print(f"\n{'='*60}")
        print(f"📦 {item['type']}: {item['name']}")
        if item.get('product_ref'):
            print(f"   Réf: {item['product_ref']}")
        print(f"   🎯 Besoin peau: {item['skin_need']}")
        print(f"   ⚙️ Mécanisme: {item['primary_mechanism']}")
        print(f"   🎤 Réponse vocale: {item['voice_answer_template']}")
    
    if not_found:
        print("\n⚠️ Produits non trouvés:")
        for item in not_found:
            print(f"   - {item['ref']}: {item['name']}")
    
    print("\n" + "=" * 80)
    print("✅ ENRICHISSEMENT TERMINÉ")
    print("=" * 80)
    
    return enriched, not_found


if __name__ == "__main__":
    enriched, not_found = run_enrichment()
