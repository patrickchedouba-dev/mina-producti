#!/usr/bin/env python3
"""
Création d'un index vectoriel unifié 'mina_knowledge' à partir des données enrichies.
Compile produits V0xx.0, services, protocoles, et diagnostics.

Usage:
    python scripts/create_products_index.py
    python scripts/create_products_index.py --test  # Lance les 10 questions test
"""

import os
import sys
import uuid
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Utilitaires centralisés (Phase 2 Refactoring)
from utils import get_qdrant_client, get_embedding


# =============================================================================
# IMPORT DES DONNÉES ENRICHIES
# =============================================================================

from scripts.enrich_services import (
    SERVICES_DATA,
    PRODUCTS_ENRICHMENT,
    SKIN_DIAGNOSTICS
)


# =============================================================================
# PRODUITS RETAIL EXISTANTS (base)
# =============================================================================

PRODUCTS_RETAIL_BASE = [
    # === GAMME S-DÉTOX ===
    {
        "product_ref": "V012.0",
        "product_name": "SÉRUM S-DÉTOX SPRAY ANTI-ACNÉ",
        "key_actives": ["Clarimatt", "Extrait de Saule Noir", "Menthol"],
        "natural_origin_pct": 88,
        "price_eur": 15.80,
        "skin_type": "Peaux mixtes à grasses, imperfections et acné",
        "usage_advice": "Vaporiser sur peau propre matin et soir, éviter le contour des yeux",
        "volume_ml": 50,
    },
    {
        "product_ref": "V018.0",
        "product_name": "CRÈME SENSIMINE ULTRA NOURRISSANTE",
        "key_actives": ["Eau des Glaciers Suisse", "Pin des Alpes Suisse"],
        "natural_origin_pct": 97,
        "price_eur": 16.60,
        "skin_type": "Peaux sensibles et très sèches",
        "usage_advice": "Appliquer matin et soir sur peau propre",
        "volume_ml": 50,
        "yuka_score": 93,
    },
    {
        "product_ref": "V017.0",
        "product_name": "CRÈME SENSIMINE ULTRA APAISANTE",
        "key_actives": ["Eau des Glaciers Suisse", "Pin des Alpes Suisse"],
        "natural_origin_pct": 94,
        "price_eur": 14.80,
        "skin_type": "Peaux sensibles réactives, rougeurs",
        "usage_advice": "Appliquer matin et soir sur peau propre",
        "volume_ml": 50,
        "yuka_score": 93,
    },
    {
        "product_ref": "V015.0",
        "product_name": "HYA SÉRUM 3D HYDRATEMPO",
        "key_actives": ["Acide Hyaluronique 3D", "Polysaccharides"],
        "natural_origin_pct": 99,
        "price_eur": 25.60,
        "skin_type": "Peaux déshydratées, premiers signes de l'âge",
        "usage_advice": "Appliquer quelques gouttes matin et soir avant la crème",
        "volume_ml": 30,
    },
    {
        "product_ref": "V002.0",
        "product_name": "GEL MOUSSE FLORAL NETTOYANT VISAGE",
        "key_actives": ["Fleur d'Oranger", "Bleuet", "Extrait de Grenade"],
        "natural_origin_pct": 89,
        "price_eur": 6.70,
        "skin_type": "Tous types de peaux",
        "usage_advice": "Utiliser matin et soir, masser et rincer",
        "volume_ml": 150,
    },
    {
        "product_ref": "V008.0",
        "product_name": "GEL S-DÉTOX MATT ++",
        "key_actives": ["Complexe matifiant"],
        "natural_origin_pct": 91,
        "price_eur": 16.20,
        "skin_type": "Peaux mixtes à grasses, excès de brillance",
        "usage_advice": "Appliquer matin et soir sur zones T",
        "volume_ml": 50,
    },
    {
        "product_ref": "V007.0",
        "product_name": "CRÈME S-DÉTOX EQUILIBREXPRESS",
        "key_actives": ["Symbiocell", "Epicalmin", "Enzyme de Grenade"],
        "natural_origin_pct": 87,
        "price_eur": 17.20,
        "skin_type": "Peaux mixtes déséquilibrées",
        "usage_advice": "Appliquer matin et soir",
        "volume_ml": 50,
    },
    {
        "product_ref": "V025.0",
        "product_name": "CONTOUR DES YEUX REGARD LIFTANT",
        "key_actives": ["Complexe liftant", "Actifs décongestionnants"],
        "natural_origin_pct": 90,
        "price_eur": 24.80,
        "skin_type": "Cernes, poches, rides du contour de l'œil",
        "usage_advice": "Appliquer matin et soir par petits tapotements",
        "volume_ml": 15,
    },
    {
        "product_ref": "V030.0",
        "product_name": "GOMME CORPS EXFOLIANT INTENSE",
        "key_actives": ["Grains exfoliants", "Eau d'Hamamélis"],
        "natural_origin_pct": 94,
        "price_eur": 11.60,
        "skin_type": "Peaux ternes, rugueuses",
        "usage_advice": "Utiliser 1 à 2 fois par semaine sur peau humide",
        "volume_ml": 200,
    },
    {
        "product_ref": "V032.0",
        "product_name": "SOIN CORPS PROFOND HYPER HYDRATANT",
        "key_actives": ["Glycérine Végétale", "Hydration After Hours"],
        "natural_origin_pct": 90,
        "price_eur": 15.90,
        "skin_type": "Peaux sèches à très sèches",
        "usage_advice": "Appliquer quotidiennement sur tout le corps",
        "volume_ml": 500,
    },
    {
        "product_ref": "V033.0",
        "product_name": "BAUME RICHE CORPS RÉPARATEUR ++",
        "key_actives": ["Beurre de Karité", "Cire d'Abeille", "Vitamine E"],
        "natural_origin_pct": 95,
        "price_eur": 18.50,
        "skin_type": "Peaux très sèches, zones rugueuses, besoin de réparation intense",
        "usage_advice": "Appliquer sur zones rugueuses (coudes, genoux, talons)",
        "volume_ml": 200,
    },
    {
        "product_ref": "V062.0",
        "product_name": "HUILE APAISANTE APRÈS ÉPILATION",
        "key_actives": ["Calendula", "Huile de Tournesol"],
        "natural_origin_pct": 99,
        "price_eur": 8.70,
        "skin_type": "Peaux irritées post-épilation",
        "usage_advice": "Appliquer immédiatement après l'épilation",
        "volume_ml": 100,
    },
    {
        "product_ref": "V035.0",
        "product_name": "CRÈME MAINS",
        "key_actives": ["Huile d'Amande Douce Bio", "Extrait d'Edelweiss"],
        "natural_origin_pct": 99,
        "price_eur": 5.30,
        "skin_type": "Mains sèches, abîmées",
        "usage_advice": "Appliquer aussi souvent que nécessaire",
        "volume_ml": 50,
    },
    {
        "product_ref": "V054.0",
        "product_name": "LAIT CORPS DOUX",
        "key_actives": ["Glycérine Végétale", "Huile de Tournesol"],
        "natural_origin_pct": 92,
        "price_eur": 10.20,
        "skin_type": "Tous types de peaux",
        "usage_advice": "Appliquer quotidiennement après la douche",
        "volume_ml": 200,
    },
    {
        "product_ref": "V011.0",
        "product_name": "LOTION S-DÉTOX PURIFIANTE",
        "key_actives": ["Acide Salicylique", "Zinc", "Extrait de Saule"],
        "natural_origin_pct": 88,
        "price_eur": 12.50,
        "skin_type": "Peaux mixtes à grasses, pores dilatés",
        "usage_advice": "Appliquer avec un coton après le nettoyage matin et soir",
        "volume_ml": 200,
    },
    # === SHAMPOINGS ===
    {
        "product_ref": "V047.0",
        "product_name": "SHAMPOO ANTI-PELLICULAIRE FLEUR DE LOTUS & ROMARIN",
        "key_actives": ["Zinc Pyrithione", "Romarin", "Fleur de Lotus"],
        "natural_origin_pct": 88,
        "price_eur": 8.90,
        "skin_type": "Cuir chevelu irrité, pellicules, démangeaisons",
        "usage_advice": "Utiliser 2 à 3 fois par semaine",
        "volume_ml": 250,
    },
    {
        "product_ref": "V048.0",
        "product_name": "SHAMPOO DOUX QUOTIDIEN YLANG-YLANG & MIEL",
        "key_actives": ["Miel", "Ylang-Ylang", "Protéines de Blé"],
        "natural_origin_pct": 90,
        "price_eur": 7.50,
        "skin_type": "Cheveux normaux, usage fréquent",
        "usage_advice": "Peut être utilisé quotidiennement",
        "volume_ml": 250,
    },
    {
        "product_ref": "V049.0",
        "product_name": "SHAMPOO CHEVEUX SECS BAIES D'AÇAI & ALOE VERA",
        "key_actives": ["Baies d'Açai", "Aloe Vera", "Huile d'Argan"],
        "natural_origin_pct": 92,
        "price_eur": 8.50,
        "skin_type": "Cheveux secs et abîmés, pointes fourchues",
        "usage_advice": "Utiliser 2 à 3 fois par semaine",
        "volume_ml": 250,
    },
    {
        "product_ref": "V050.0",
        "product_name": "SHAMPOO CHEVEUX COLORÉS ALOE VERA & GRENADE",
        "key_actives": ["Grenade", "Aloe Vera", "Filtre UV"],
        "natural_origin_pct": 89,
        "price_eur": 8.90,
        "skin_type": "Cheveux colorés, protection couleur",
        "usage_advice": "Utiliser après chaque coloration et régulièrement",
        "volume_ml": 250,
    },
    # === BASIQUES ===
    {
        "product_ref": "V001.0",
        "product_name": "GOMMAGE VISAGE PRO",
        "key_actives": ["Grains de Bambou", "Aloe Vera", "Vitamine E"],
        "natural_origin_pct": 91,
        "price_eur": 9.80,
        "skin_type": "Tous types de peaux",
        "usage_advice": "Utiliser 1 à 2 fois par semaine, masser en douceur",
        "volume_ml": 75,
    },
    {
        "product_ref": "V003.0",
        "product_name": "LAIT DÉMAQ'",
        "key_actives": ["Huile d'Amande Douce", "Eau de Rose", "Vitamine E"],
        "natural_origin_pct": 94,
        "price_eur": 11.20,
        "skin_type": "Peaux sèches à normales",
        "usage_advice": "Appliquer matin et soir, masser et rincer",
        "volume_ml": 200,
    },
    {
        "product_ref": "V004.0",
        "product_name": "TONIQ' 3 FLEURS",
        "key_actives": ["Eau de Rose", "Eau de Bleuet", "Eau de Fleur d'Oranger"],
        "natural_origin_pct": 97,
        "price_eur": 9.90,
        "skin_type": "Tous types de peaux",
        "usage_advice": "Appliquer matin et soir après le démaquillage",
        "volume_ml": 200,
    },
    {
        "product_ref": "V005.0",
        "product_name": "DEMAQ' XPRESS 3-EN-1",
        "key_actives": ["Micelles", "Aloe Vera", "Eau de Rose"],
        "natural_origin_pct": 92,
        "price_eur": 10.80,
        "skin_type": "Tous types de peaux",
        "usage_advice": "Appliquer avec un coton, sans rinçage",
        "volume_ml": 200,
    },
]


# =============================================================================
# FUSION DES DONNÉES
# =============================================================================

def merge_product_data() -> List[Dict]:
    """Fusionne les produits de base avec les enrichissements."""
    # Créer un dictionnaire par référence
    products_by_ref = {}
    
    # D'abord les produits de base
    for p in PRODUCTS_RETAIL_BASE:
        products_by_ref[p["product_ref"]] = p.copy()
    
    # Ensuite les enrichissements (écrasent/complètent)
    for p in PRODUCTS_ENRICHMENT:
        ref = p["product_ref"]
        if ref in products_by_ref:
            # Fusionner les données
            products_by_ref[ref].update(p)
        else:
            # Nouveau produit
            products_by_ref[ref] = p.copy()
    
    return list(products_by_ref.values())


# =============================================================================
# CLIENTS ET EMBEDDINGS
# =============================================================================

# get_qdrant_client et get_embedding importés depuis utils (voir ligne 25)


# =============================================================================
# GÉNÉRATION DES TEXTES D'INDEXATION
# =============================================================================

def product_to_text(product: Dict) -> str:
    """Génère le texte d'indexation pour un produit."""
    parts = [f"Produit: {product.get('product_name', '')}"]
    
    if product.get('product_ref'):
        parts.append(f"Référence: {product['product_ref']}")
    
    if product.get('price_eur'):
        parts.append(f"Prix: {product['price_eur']:.2f}€")
    
    if product.get('volume_ml'):
        parts.append(f"Contenance: {product['volume_ml']}ml")
    
    if product.get('natural_origin_pct'):
        parts.append(f"{product['natural_origin_pct']}% d'ingrédients d'origine naturelle")
    
    if product.get('skin_type'):
        parts.append(f"Type de peau / Indication: {product['skin_type']}")
    
    if product.get('key_actives'):
        parts.append(f"Principes actifs: {', '.join(product['key_actives'])}")
    
    if product.get('usage_advice'):
        parts.append(f"Conseil d'utilisation: {product['usage_advice']}")
    
    if product.get('clinical_result'):
        parts.append(f"Résultat clinique: {product['clinical_result']}")
    
    if product.get('benefit_detail'):
        parts.append(f"Bénéfice: {product['benefit_detail']}")
    
    if product.get('texture_specificity'):
        parts.append(f"Texture: {product['texture_specificity']}")
    
    if product.get('actives_actions'):
        for aa in product['actives_actions']:
            parts.append(f"{aa['active']}: {aa['action']}")
    
    return ". ".join(parts)


def service_to_text(service: Dict) -> str:
    """Génère le texte d'indexation pour un service/protocole."""
    parts = [f"Service: {service.get('service_name', '')}"]
    
    parts.append(f"Type: {service.get('service_type', '')}")
    
    if service.get('duration_total'):
        parts.append(f"Durée: {service['duration_total']}")
    elif service.get('duration_minutes'):
        parts.append(f"Durée: {service['duration_minutes']} minutes")
    
    if service.get('objective'):
        parts.append(f"Objectif: {service['objective']}")
    
    if service.get('description'):
        parts.append(service['description'])
    
    if service.get('skin_indication'):
        parts.append(f"Indication: {service['skin_indication']}")
    
    # Pour les protocoles avec étapes
    if service.get('steps'):
        steps_text = []
        for step in service['steps']:
            step_str = f"Étape {step['step']} {step['name']}: {step.get('product', step.get('action', ''))}"
            steps_text.append(step_str)
        parts.append("Étapes: " + " | ".join(steps_text))
    
    if service.get('phases'):
        phases_text = []
        for phase in service['phases']:
            phases_text.append(f"Phase {phase['step']} {phase['name']}: {phase['action']}")
        parts.append("Phases: " + " | ".join(phases_text))
    
    # Pour les 7 clés
    if service.get('keys'):
        keys_text = []
        for key in service['keys']:
            keys_text.append(f"{key['number']}. {key['name']}: {key['description']}")
        parts.append("Clés: " + " | ".join(keys_text))
    
    # Pour les capsules
    if service.get('forms'):
        forms_text = []
        for form in service['forms']:
            forms_text.append(f"{form['form_name']}: {form['aesthetic_objective']} - {form['recommendation']}")
        parts.append("Formes: " + " | ".join(forms_text))
    
    if service.get('voice_answer_template'):
        parts.append(service['voice_answer_template'])
    
    return ". ".join(parts)


def diagnostic_to_text(diag: Dict) -> str:
    """Génère le texte d'indexation pour un diagnostic de peau."""
    parts = [f"Diagnostic: {diag.get('skin_type', '')}"]
    
    if diag.get('characteristics'):
        parts.append(f"Caractéristiques: {', '.join(diag['characteristics'])}")
    
    if diag.get('causes'):
        parts.append(f"Causes: {', '.join(diag['causes'])}")
    
    if diag.get('recommended_range'):
        parts.append(f"Gamme recommandée: {diag['recommended_range']}")
    
    if diag.get('key_products'):
        parts.append(f"Produits clés: {', '.join(diag['key_products'])}")
    
    if diag.get('voice_answer_template'):
        parts.append(diag['voice_answer_template'])
    
    return ". ".join(parts)


# =============================================================================
# CRÉATION DES INDEX
# =============================================================================

def create_unified_index():
    """Crée l'index unifié products_index avec tous les contenus."""
    from qdrant_client.models import Distance, VectorParams, PointStruct
    
    print("\n" + "=" * 80)
    print("🚀 CRÉATION INDEX UNIFIÉ 'products_index'")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    collection_name = "products_index"
    client = get_qdrant_client()
    
    # Préparer les données
    all_products = merge_product_data()
    all_services = SERVICES_DATA
    all_diagnostics = SKIN_DIAGNOSTICS
    
    print(f"\n📊 Données à indexer:")
    print(f"   - {len(all_products)} produits")
    print(f"   - {len(all_services)} services/protocoles")
    print(f"   - {len(all_diagnostics)} diagnostics de peau")
    total = len(all_products) + len(all_services) + len(all_diagnostics)
    print(f"   = {total} entrées totales")
    
    # Recréer la collection
    print(f"\n📦 [1/4] Préparation de la collection...")
    try:
        client.delete_collection(collection_name)
        print(f"   ⚠️ Collection existante supprimée")
    except:
        pass
    
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
    print(f"   ✅ Collection créée")
    
    # Indexer les produits
    print(f"\n🔄 [2/4] Indexation des produits...")
    points = []
    
    for i, product in enumerate(all_products, 1):
        print(f"\r   Produit {i}/{len(all_products)}: {product.get('product_ref', 'N/A')}", end="", flush=True)
        
        try:
            text = product_to_text(product)
            embedding = get_embedding(text)
            
            payload = {
                "doc_type": "product",
                "text": text,
                **product
            }
            
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            ))
        except Exception as e:
            print(f"\n   ⚠️ Erreur {product.get('product_ref')}: {e}")
    
    print(f"\n   ✅ {len(points)} produits traités")
    
    # Indexer les services
    print(f"\n🔄 [3/4] Indexation des services...")
    services_count = 0
    
    for service in all_services:
        print(f"\r   Service: {service.get('service_name', 'N/A')[:40]}", end="", flush=True)
        
        try:
            text = service_to_text(service)
            embedding = get_embedding(text)
            
            payload = {
                "doc_type": "service",
                "text": text,
                **service
            }
            
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            ))
            services_count += 1
        except Exception as e:
            print(f"\n   ⚠️ Erreur service: {e}")
    
    print(f"\n   ✅ {services_count} services traités")
    
    # Indexer les diagnostics
    print(f"\n   Indexation des diagnostics...")
    for diag in all_diagnostics:
        try:
            text = diagnostic_to_text(diag)
            embedding = get_embedding(text)
            
            payload = {
                "doc_type": "diagnostic",
                "text": text,
                **diag
            }
            
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            ))
        except Exception as e:
            print(f"   ⚠️ Erreur diagnostic: {e}")
    
    # Upsert final
    print(f"\n📥 [4/4] Insertion dans Qdrant...")
    client.upsert(collection_name=collection_name, points=points)
    
    # Vérification
    info = client.get_collection(collection_name)
    print(f"\n   ✅ Collection '{collection_name}': {info.points_count} vecteurs")
    
    print("\n" + "=" * 80)
    print("✅ INDEX UNIFIÉ CRÉÉ AVEC SUCCÈS")
    print("=" * 80)
    
    return info.points_count


# =============================================================================
# TESTS DES 10 QUESTIONS
# =============================================================================

def run_10_questions_test():
    """Exécute les 10 questions de référence."""
    print("\n" + "=" * 80)
    print("🧪 TEST DES 10 QUESTIONS DE RÉFÉRENCE")
    print("=" * 80)
    
    client = get_qdrant_client()
    collection_name = "products_index"
    
    questions = [
        {
            "id": 1,
            "question": "Quels sont les deux bénéfices principaux de l'Eau Micellaire à l'Aloe Vera ?",
            "search": "Eau Micellaire Aloe Vera V006.0 bénéfices démaquiller apaiser"
        },
        {
            "id": 2,
            "question": "Quels sont les deux composants du Savoir Être (7 clés de la réussite) ?",
            "search": "7 clés réussite Savoir Être hygiène attitude non verbal"
        },
        {
            "id": 3,
            "question": "Pour le Gel Hydratempo Water Bomb, quel actif stoppe la déshydratation et quel est le résultat prouvé ?",
            "search": "Gel Hydratempo Water Bomb acide hyaluronique +58% hydratation"
        },
        {
            "id": 4,
            "question": "Nommez les trois formes de Roll-On Quartz et leurs bénéfices.",
            "search": "Roll-On Quartz Rose Cristal Améthyste régénération éclat apaisement"
        },
        {
            "id": 5,
            "question": "Quel est le rôle du Sérum 8.0 Metabolissime pour les peaux matures ?",
            "search": "Sérum 8.0 Metabolissime Matrixyl réparation cutanée radicaux libres"
        },
        {
            "id": 6,
            "question": "Quels sont les principes actifs du SOS Poil Sous Peau et leurs actions ?",
            "search": "SOS Poil Sous Peau V063.0 acide salicylique kératolytique désinfectant"
        },
        {
            "id": 7,
            "question": "Quelles sont les caractéristiques de la peau sèche/déshydratée Hydratempo ?",
            "search": "peau sèche déshydratée Hydratempo tiraillements squames causes"
        },
        {
            "id": 8,
            "question": "Quelle est la particularité du Baume Fondant Massage lors de son application ?",
            "search": "Baume Fondant Massage texture baume solide huile chaleur peau"
        },
        {
            "id": 9,
            "question": "Quelle est la durée de la Cure Silhouette et son objectif mesuré ?",
            "search": "Cure Silhouette 8 séances 1 mois perte centimètres"
        },
        {
            "id": 10,
            "question": "Quelles sont les trois formes de capsules américaines et leurs recommandations ?",
            "search": "capsules américaines Amande Coffin Square ongles allongeant"
        },
    ]
    
    for q in questions:
        print(f"\n{'─' * 80}")
        print(f"❓ Q{q['id']}: {q['question']}")
        
        try:
            query_vector = get_embedding(q['search'])
            
            results = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=2,
                with_payload=True
            )
            
            if results.points:
                best = results.points[0]
                print(f"\n✅ Score: {best.score:.3f}")
                print(f"   Type: {best.payload.get('doc_type', 'N/A')}")
                
                # Afficher la réponse vocale si disponible
                voice = best.payload.get('voice_answer_template')
                if voice:
                    print(f"\n💬 MINA: {voice}")
                else:
                    # Fallback sur le texte
                    text = best.payload.get('text', '')[:300]
                    print(f"\n📄 Extrait: {text}...")
            else:
                print(f"\n⚠️ Aucun résultat trouvé")
                
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
    
    print("\n" + "=" * 80)
    print("✅ TESTS TERMINÉS")
    print("=" * 80)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Lance les 10 questions test")
    parser.add_argument("--skip-index", action="store_true", help="Sauter la création d'index")
    args = parser.parse_args()
    
    if not args.skip_index:
        count = create_unified_index()
    
    if args.test or not args.skip_index:
        run_10_questions_test()
