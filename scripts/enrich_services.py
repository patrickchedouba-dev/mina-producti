#!/usr/bin/env python3
"""
Enrichissement des Protocoles et Services Body Minute / Nail'minute.
Contient les données structurées pour les services cabine, formations, et ongles.

Usage:
    python scripts/enrich_services.py
"""

import os
import sys
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# SERVICES ET PROTOCOLES
# =============================================================================

SERVICES_DATA = [
    # === CURE SILHOUETTE ===
    {
        "service_ref": "CURE-SILH-001",
        "service_name": "CURE SILHOUETTE",
        "service_type": "protocole_cabine",
        "duration_total": "8 séances de 1h sur 1 mois (2 séances/semaine)",
        "duration_minutes": 60,
        "sessions_count": 8,
        "objective": "Affinage visible de la silhouette et perte de centimètres mesurable",
        "target_areas": ["Cuisses", "Ventre", "Bras", "Hanches"],
        "key_techniques": ["Massage drainant", "Palper-rouler", "Enveloppement", "Cryothérapie localisée"],
        "products_used": ["Sérum Sculptant Anti-Cellulite V037.0", "Gel-Crème Cryo Body Positive V038.0"],
        "contraindications": ["Grossesse", "Problèmes circulatoires graves", "Inflammation cutanée"],
        "voice_answer_template": "La Cure Silhouette est un programme intensif de 8 séances d'environ 1 heure chacune, réparties sur 1 mois à raison de 2 séances par semaine. Son objectif est l'affinage visible de la silhouette avec une perte de centimètres mesurable. Elle combine le massage drainant, le palper-rouler et des enveloppements pour des résultats durables."
    },
    
    # === 7 CLÉS DE LA RÉUSSITE ===
    {
        "service_ref": "FORM-7CLES-001",
        "service_name": "LES 7 CLÉS DE LA RÉUSSITE",
        "service_type": "formation",
        "description": "Les 7 piliers de l'excellence professionnelle Body Minute",
        "keys": [
            {
                "number": 1,
                "name": "Savoir Être - Hygiène et Apparence",
                "type": "non_verbal",
                "description": "Propreté des mains, des ongles, uniforme impeccable. Construit la confiance et le professionnalisme.",
                "impact": "Confiance et professionnalisme perçu"
            },
            {
                "number": 2,
                "name": "Savoir Être - Attitude Aimable",
                "type": "non_verbal",
                "description": "Accueil chaleureux, écoute active, bienveillance sans jugement ni indiscrétion.",
                "impact": "Moment de détente et de confort pour la cliente"
            },
            {
                "number": 3,
                "name": "Savoir Faire - Maîtrise Technique",
                "type": "verbal",
                "description": "Excellence dans les gestes professionnels, protocoles maîtrisés.",
                "impact": "Qualité du soin et résultats"
            },
            {
                "number": 4,
                "name": "Savoir Dire - Communication",
                "type": "verbal",
                "description": "Explications claires, conseils personnalisés, vocabulaire professionnel.",
                "impact": "Compréhension et fidélisation"
            },
            {
                "number": 5,
                "name": "Savoir Écouter",
                "type": "verbal",
                "description": "Écoute active des besoins, reformulation, empathie.",
                "impact": "Personnalisation du service"
            },
            {
                "number": 6,
                "name": "Savoir Conseiller",
                "type": "verbal",
                "description": "Recommandations produits adaptées, conseils d'entretien à domicile.",
                "impact": "Vente additionnelle et satisfaction"
            },
            {
                "number": 7,
                "name": "Savoir Fidéliser",
                "type": "verbal",
                "description": "Suivi client, prise de rendez-vous, programme fidélité.",
                "impact": "Récurrence et recommandation"
            }
        ],
        "voice_answer_template": "Les 7 Clés de la Réussite regroupent les piliers de l'excellence Body Minute. Le Savoir Être, partie non verbale, comprend l'Hygiène et Apparence Irréprochable qui construit la confiance, et l'Attitude Aimable qui crée un moment de détente sans jugement. Les 5 autres clés couvrent le Savoir Faire technique, le Savoir Dire, Écouter, Conseiller et Fidéliser."
    },
    
    # === CAPSULES AMÉRICAINES (NAIL'MINUTE) ===
    {
        "service_ref": "NAIL-CAPS-001",
        "service_name": "CAPSULES AMÉRICAINES SOFT GEL TIPS",
        "service_type": "onglerie",
        "description": "Extensions d'ongles en gel souple, pose rapide et résultat naturel",
        "duration_minutes": 45,
        "forms": [
            {
                "form_name": "Amande (Almond)",
                "shape_code": "ALMOND",
                "aesthetic_objective": "Effet allongeant et féminin",
                "recommendation": "Idéale pour affiner les ongles étroits ou courts. Donne une illusion de longueur élégante.",
                "best_for": ["Ongles courts", "Ongles étroits", "Doigts fins"]
            },
            {
                "form_name": "Carrée (Coffin/Square)",
                "shape_code": "COFFIN",
                "aesthetic_objective": "Style net, structuré et moderne",
                "recommendation": "Parfaite pour les ongles larges ou les doigts longs. Look tendance et sophistiqué.",
                "best_for": ["Ongles larges", "Doigts longs", "Style moderne"]
            },
            {
                "form_name": "Arrondie (Round/Oval)",
                "shape_code": "ROUND",
                "aesthetic_objective": "Rendu classique et naturel",
                "recommendation": "Convient aux doigts courts et à un usage quotidien. Entretien facile.",
                "best_for": ["Doigts courts", "Usage quotidien", "Style naturel"]
            }
        ],
        "voice_answer_template": "Les Capsules Américaines Soft Gel Tips sont disponibles en trois formes principales. La forme Amande offre un effet allongeant et féminin, idéale pour affiner les ongles courts. La forme Carrée ou Coffin donne un style net et moderne, parfaite pour les ongles larges. La forme Arrondie apporte un rendu classique et naturel pour un usage quotidien."
    },
    
    # === SOIN S-DÉTOX CABINE ===
    {
        "service_ref": "PROTO-SDETOX-001",
        "service_name": "SOIN PROFOND S-DÉTOX",
        "service_type": "protocole_cabine",
        "duration_minutes": 50,
        "phases_count": 4,
        "skin_indication": "Peaux mixtes à grasses, imperfections, excès de sébum",
        "phases": [
            {"step": 1, "name": "NETTOYER", "action": "Double nettoyage doux pour éliminer impuretés"},
            {"step": 2, "name": "PURIFIER", "action": "Vapozone + extraction des comédons"},
            {"step": 3, "name": "TRAITER", "action": "Application Sérum et Masque S-Détox"},
            {"step": 4, "name": "PROTÉGER", "action": "Crème S-Détox Equilibrexpress pour rééquilibrer"}
        ],
        "products_used": [
            "Gel Mousse Floral V002.0 (nettoyage)",
            "Sérum S-Détox V012.0 (traitement)",
            "Crème S-Détox Equilibrexpress V007.0 (protection)"
        ],
        "voice_answer_template": "Le Soin Profond S-Détox dure 50 minutes en 4 phases. La phase NETTOYER élimine les impuretés. La phase PURIFIER utilise le Vapozone pour l'extraction. La phase TRAITER applique le Sérum S-Détox. Enfin, la phase PROTÉGER utilise la Crème S-Détox Equilibrexpress, référence V007.0, pour rééquilibrer la peau."
    },
    
    # === HOME SPA S-DÉTOX 7 ÉTAPES ===
    {
        "service_ref": "PROTO-HOMESPA-SDETOX-001",
        "service_name": "HOME SPA S-DÉTOX 7 ÉTAPES",
        "service_type": "routine_domicile",
        "duration_minutes": 30,
        "skin_indication": "Peaux mixtes à grasses (routine domicile)",
        "steps": [
            {"step": 1, "name": "DÉMAQUILLER", "product": "Eau Micellaire Aloe Vera V006.0"},
            {"step": 2, "name": "NETTOYER", "product": "Gel Mousse Floral V002.0"},
            {"step": 3, "name": "TONIFIER", "product": "Lotion S-Détox Purifiante V011.0"},
            {"step": 4, "name": "EXFOLIER", "product": "Gommage Visage Pro V001.0 (1x/semaine)"},
            {"step": 5, "name": "TRAITER", "product": "Sérum S-Détox Spray V012.0"},
            {"step": 6, "name": "MASQUER", "product": "Masque S-Détox (2x/semaine)"},
            {"step": 7, "name": "PROTÉGER", "product": "Crème S-Détox Equilibrexpress V007.0"}
        ],
        "voice_answer_template": "Le Home Spa S-Détox en 7 étapes est une routine domicile pour peaux mixtes à grasses. L'étape 7 PROTÉGER utilise la Crème S-Détox Equilibrexpress, référence V007.0, pour rééquilibrer la peau sans la graisser et la protéger toute la journée."
    },
    
    # === HOME SPA METABOLISSIME ===
    {
        "service_ref": "PROTO-HOMESPA-META-001",
        "service_name": "HOME SPA METABOLISSIME",
        "service_type": "routine_domicile",
        "duration_minutes": 20,
        "skin_indication": "Peaux matures, anti-âge global",
        "steps": [
            {"step": 1, "name": "DÉMAQUILLER", "product": "Lait Démaq' V003.0", "duration": 2},
            {"step": 2, "name": "NETTOYER", "product": "Gel Mousse Floral V002.0", "duration": 2},
            {"step": 3, "name": "TONIFIER", "product": "Toniq' 3 Fleurs V004.0", "duration": 1},
            {"step": 4, "name": "STIMULER", "product": "Elixir Cell Flash Metabolissime V026.0", "duration": 3},
            {"step": 5, "name": "TRAITER", "product": "Crème Metabolic Collagen Pro V019.0", "duration": 3},
            {"step": 6, "name": "REGARD", "product": "Contour des Yeux Regard Liftant V025.0", "duration": 2}
        ],
        "voice_answer_template": "Dans la routine Home Spa Metabolissime, l'étape STIMULER utilise l'Elixir Cell Flash Metabolissime, référence V026.0. Ce sérum concentré en Vitamine C réactive l'éclat et l'énergie cellulaire en 3 minutes de massage. Il prépare la peau à recevoir le soin anti-âge suivant."
    },
]


# =============================================================================
# PRODUITS ADDITIONNELS (Roll-On Quartz, enrichissements)
# =============================================================================

PRODUCTS_ENRICHMENT = [
    # === ROLL-ON QUARTZ ===
    {
        "product_ref": "V080.0",
        "product_name": "ROLL-ON QUARTZ ROSE",
        "key_actives": ["Pierre de Quartz Rose", "Huile de Rose Musquée", "Vitamine E"],
        "natural_origin_pct": 98,
        "price_eur": 19.90,
        "skin_type": "Peaux matures ou ridées, besoin de régénération",
        "usage_advice": "Rouler sur le visage après le sérum, en mouvements ascendants. Conserver au frais pour effet décongestionnant.",
        "benefit_primary": "Régénération et anti-âge",
        "benefit_detail": "Optimise les effets du sérum et stimule les échanges cellulaires pour une peau régénérée.",
        "voice_answer_template": "Le Roll-On Quartz Rose, référence V080.0, est recommandé pour la régénération et l'anti-âge. Sa pierre de quartz rose optimise les effets du sérum et stimule les échanges cellulaires. Idéal pour les peaux matures ou ridées. Prix client: 19,90€."
    },
    {
        "product_ref": "V081.0",
        "product_name": "ROLL-ON QUARTZ CRISTAL",
        "key_actives": ["Pierre de Quartz Cristal", "Extrait de Citron", "Niacinamide"],
        "natural_origin_pct": 98,
        "price_eur": 19.90,
        "skin_type": "Peaux mixtes ou grasses, teint terne, pores dilatés",
        "usage_advice": "Rouler sur le visage après le sérum. Idéal le matin pour un effet bonne mine.",
        "benefit_primary": "Éclat et purification",
        "benefit_detail": "Purifie les pores et booste l'éclat du teint pour une peau lumineuse.",
        "voice_answer_template": "Le Roll-On Quartz Cristal, référence V081.0, apporte éclat et purification. Sa pierre de quartz cristal et son extrait de citron illuminent le teint et purifient les pores. Parfait pour les peaux mixtes ou grasses. Prix client: 19,90€."
    },
    {
        "product_ref": "V082.0",
        "product_name": "ROLL-ON QUARTZ AMÉTHYSTE",
        "key_actives": ["Pierre de Quartz Améthyste", "Lavande", "Bisabolol"],
        "natural_origin_pct": 98,
        "price_eur": 19.90,
        "skin_type": "Peaux sensibles ou mixtes, rougeurs, stress cutané",
        "usage_advice": "Rouler délicatement sur le visage après le sérum. Effet relaxant recommandé le soir.",
        "benefit_primary": "Apaisement et détoxification",
        "benefit_detail": "Calme les peaux irritées et détoxifie grâce aux propriétés apaisantes de l'améthyste.",
        "voice_answer_template": "Le Roll-On Quartz Améthyste, référence V082.0, est conseillé pour l'apaisement et la détoxification. Sa pierre d'améthyste et sa lavande calment les peaux sensibles et détoxifient. Idéal pour le rituel du soir. Prix client: 19,90€."
    },
    
    # === GEL HYDRATEMPO WATER BOMB (enrichissement) ===
    {
        "product_ref": "V014.0",
        "product_name": "GEL HYDRATEMPO WATER BOMB",
        "key_actives": ["Acide Hyaluronique Multi-Poids", "TM Complex", "Aloe Vera Bio"],
        "natural_origin_pct": 95,
        "price_eur": 22.50,
        "skin_type": "Peaux déshydratées, tous types de peau",
        "usage_advice": "Appliquer matin et soir sur peau propre avant la crème.",
        "clinical_result": "+58% d'hydratation après une seule application",
        "benefit_primary": "Hydratation intense",
        "benefit_detail": "L'Acide Hyaluronique multi-poids stoppe la déshydratation et crée un effet repulpant immédiat.",
        "voice_answer_template": "Le Gel Hydratempo Water Bomb, référence V014.0, a un actif clé : l'Acide Hyaluronique multi-poids qui stoppe la déshydratation. Résultat prouvé : +58% d'hydratation après une seule application. Prix client: 22,50€."
    },
    
    # === EAU MICELLAIRE (enrichissement) ===
    {
        "product_ref": "V006.0",
        "product_name": "EAU MICELLAIRE À L'ALOE VERA",
        "key_actives": ["Aloe Vera Bio", "Micelles nettoyantes", "Glycérine végétale"],
        "natural_origin_pct": 93,
        "price_eur": 9.40,
        "skin_type": "Tous types de peaux, même sensibles",
        "usage_advice": "Appliquer matin et soir avec un coton sur visage, yeux et lèvres.",
        "volume_ml": 200,
        "yuka_score": 45,
        "benefit_primary": "Démaquillage et apaisement",
        "benefit_detail": "Démaquille efficacement et apaise la peau pour un aspect net, frais et apaisé.",
        "voice_answer_template": "L'Eau Micellaire à l'Aloe Vera, référence V006.0, a deux bénéfices principaux : démaquiller efficacement et apaiser la peau. Après utilisation, la peau a un aspect net, frais et apaisé. 93% d'origine naturelle. Prix: 9,40€."
    },
    
    # === SÉRUM 8.0 METABOLISSIME (enrichissement) ===
    {
        "product_ref": "V027.0",
        "product_name": "SÉRUM 8.0 METABOLISSIME",
        "key_actives": ["Matrixyl 3000", "Vitamine C stabilisée", "Acide Hyaluronique"],
        "natural_origin_pct": 90,
        "price_eur": 32.00,
        "skin_type": "Peaux matures, perte de fermeté, rides installées",
        "usage_advice": "Appliquer 3-4 gouttes matin et soir avant la crème. Masser en mouvements liftants.",
        "benefit_primary": "Réparation cutanée et anti-radicalaire",
        "benefit_detail": "Le Matrixyl 3000 renforce la réparation cutanée. La Vitamine C lutte contre les radicaux libres pour améliorer tonicité et élasticité.",
        "voice_answer_template": "Le Sérum 8.0 Metabolissime, référence V027.0, renforce le processus de réparation cutanée grâce au Matrixyl 3000 et lutte contre les radicaux libres avec sa Vitamine C. Il améliore la tonicité et l'élasticité des peaux matures. Prix client: 32€."
    },
    
    # === SOS POIL SOUS PEAU (enrichissement) ===
    {
        "product_ref": "V063.0",
        "product_name": "SOS POIL SOUS PEAU PROFESSIONAL",
        "key_actives": ["Acide Salicylique", "Alcohol Denat.", "Tea Tree"],
        "natural_origin_pct": 85,
        "price_eur": 12.90,
        "skin_type": "Poils incarnés, folliculite, zones épilées récurrentes",
        "usage_advice": "Appliquer quotidiennement sur zones concernées avec un coton. Éviter soleil direct après application.",
        "actives_actions": [
            {"active": "Acide Salicylique", "action": "Kératolytique - exfolie en douceur pour déboucher les pores et libérer les poils incarnés"},
            {"active": "Alcohol Denat.", "action": "Désinfectant et purifiant - élimine les bactéries et assainit la zone"}
        ],
        "voice_answer_template": "Le produit SOS Poil Sous Peau, référence V063.0, contient deux principes actifs clés. L'Acide Salicylique a une action kératolytique qui exfolie en douceur pour déboucher les pores. L'Alcool a une action désinfectante et purifiante pour éliminer les bactéries. Prix: 12,90€."
    },
    
    # === BAUME FONDANT MASSAGE (enrichissement) ===
    {
        "product_ref": "V036.0",
        "product_name": "BAUME FONDANT MASSAGE PROFESSIONNEL",
        "key_actives": ["Huiles végétales nobles", "Beurre de Karité", "Vitamine E"],
        "natural_origin_pct": 97,
        "price_eur": 24.50,
        "skin_type": "Massage cabine, tous types de peau",
        "usage_advice": "Prendre une noisette dans le creux de la main. Frotter jusqu'à liquéfaction. Appliquer en manœuvres de modelage.",
        "volume_ml": 500,
        "texture_specificity": "Baume solide qui se transforme en huile de massage au contact de la chaleur de la peau",
        "benefit_primary": "Glisse optimale et nutrition",
        "voice_answer_template": "Le Baume Fondant Massage Professionnel, référence V036.0, a une particularité unique : sa texture de baume solide se transforme en huile au contact de la chaleur de la peau. Prendre une noisette, frotter dans les mains jusqu'à liquéfaction, puis masser. Glisse optimale garantie."
    },
]


# =============================================================================
# DIAGNOSTICS ET TYPOLOGIES DE PEAU
# =============================================================================

SKIN_DIAGNOSTICS = [
    {
        "skin_type": "HYDRATEMPO - Peau Sèche/Déshydratée",
        "characteristics": [
            "Tiraillements",
            "Squames et peau rêche",
            "Manque de souplesse et de confort",
            "Crevasses aux zones exposées"
        ],
        "causes": [
            "Manque d'eau (déshydratation)",
            "Manque de lipides (peau alipidique)",
            "Conditions climatiques extrêmes (froid, chaud, vent)",
            "Évaporation excessive de l'eau cutanée"
        ],
        "recommended_range": "HYDRATEMPO",
        "key_products": ["V013.0", "V014.0", "V015.0", "V069.0"],
        "voice_answer_template": "La peau sèche/déshydratée Hydratempo présente des caractéristiques comme les tiraillements, les squames, le manque de souplesse et les crevasses. Les causes sont principalement un manque d'eau ou de lipides, aggravé par les conditions climatiques extrêmes. La gamme Hydratempo répond à ces besoins."
    },
    {
        "skin_type": "METABOLISSIME - Peau Mature",
        "characteristics": [
            "Perte de fermeté",
            "Rides installées",
            "Teint terne et fatigué",
            "Manque d'élasticité"
        ],
        "causes": [
            "Ralentissement du renouvellement cellulaire",
            "Dégradation du collagène et de l'élastine",
            "Stress oxydatif et radicaux libres",
            "Diminution de la production d'acide hyaluronique"
        ],
        "recommended_range": "METABOLISSIME",
        "key_products": ["V019.0", "V024.0", "V026.0", "V027.0", "V028.0"],
        "voice_answer_template": "Les problématiques de la peau mature Metabolissime sont causées par le ralentissement du renouvellement cellulaire et la dégradation des structures de soutien (collagène et élastine). Cela se manifeste par une perte de fermeté, d'hydratation et d'éclat. La gamme Metabolissime cible ces préoccupations."
    },
]


def get_all_services():
    """Retourne tous les services et protocoles."""
    return SERVICES_DATA


def get_all_product_enrichments():
    """Retourne tous les enrichissements produits."""
    return PRODUCTS_ENRICHMENT


def get_skin_diagnostics():
    """Retourne les diagnostics de peau."""
    return SKIN_DIAGNOSTICS


if __name__ == "__main__":
    print("\n📋 SERVICES ET PROTOCOLES DISPONIBLES:")
    for s in SERVICES_DATA:
        print(f"  - {s['service_name']} ({s['service_type']})")
    
    print(f"\n📦 ENRICHISSEMENTS PRODUITS: {len(PRODUCTS_ENRICHMENT)} produits")
    for p in PRODUCTS_ENRICHMENT:
        print(f"  - {p['product_ref']}: {p['product_name']}")
    
    print(f"\n🔬 DIAGNOSTICS DE PEAU: {len(SKIN_DIAGNOSTICS)} typologies")
