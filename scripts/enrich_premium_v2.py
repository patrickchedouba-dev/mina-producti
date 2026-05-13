#!/usr/bin/env python3
"""
Extension Premium V2 - Enrichissement 80% couverture terrain.
Produits et protocoles supplémentaires.
"""

import os
import sys
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


# === PRODUITS V2 (30 produits supplémentaires) ===

PRODUCTS_V2 = [
    # === GAMME HYDRATEMPO ===
    {
        "product_ref": "V013.0",
        "name": "HYA CRÈME 24H HYDRATEMPO",
        "skin_need": "Peaux déshydratées, ridules de déshydratation, manque de confort",
        "primary_mechanism": "L'acide hyaluronique multi-poids maintient l'hydratation 24h en créant un réservoir d'eau cutané",
        "key_actives_summary": "Acide Hyaluronique (repulpant), Glycérine Végétale (hydratant), Vitamine E (antioxydant)",
        "voice_answer_template": "La HYA Crème 24H Hydratempo, référence V013.0, hydrate intensément pendant 24 heures grâce à l'Acide Hyaluronique multi-poids. Elle repulpe les ridules de déshydratation pour une peau souple et confortable."
    },
    {
        "product_ref": "V069.0",
        "name": "MASQUE DE NUIT WATER BOMB HYDRATEMPO",
        "skin_need": "Peaux déshydratées, besoin de régénération nocturne, teint terne au réveil",
        "primary_mechanism": "La formule gel-crème libère ses actifs hydratants pendant le sommeil pour un effet repulpé au réveil",
        "key_actives_summary": "TM Complex (boost hydratation), Acide Hyaluronique (repulpant), Aloe Vera (apaisante)",
        "voice_answer_template": "Le Masque de Nuit Water Bomb Hydratempo, référence V069.0, agit pendant le sommeil. Son TM Complex booste l'hydratation pour un effet repulpé au réveil. À appliquer en fine couche avant le coucher."
    },
    
    # === GAMME METABOLISSIME / ANTI-ÂGE ===
    {
        "product_ref": "V019.0",
        "name": "CRÈME METABOLIC COLLAGEN PRO",
        "skin_need": "Peaux matures, perte de fermeté, rides installées",
        "primary_mechanism": "Le Collagène Marin stimule la synthèse du collagène naturel pour raffermir et repulper",
        "key_actives_summary": "Collagène Marin (restructurant), Peptides (anti-rides), Vitamine C (éclat)",
        "voice_answer_template": "La Crème Metabolic Collagen Pro, référence V019.0, combat la perte de fermeté. Son Collagène Marin et ses Peptides restructurent la peau pour un effet liftant visible."
    },
    {
        "product_ref": "V024.0",
        "name": "SOIN CELL FLASH ACTIVATEUR GLOBAL METABOLISSIME",
        "skin_need": "Peaux fatiguées, teint terne, premiers signes de l'âge",
        "primary_mechanism": "La Vitamine C booste le métabolisme cellulaire et l'éclat du teint",
        "key_actives_summary": "Vitamine C (antioxydant, éclat), Acide Hyaluronique (hydratant), Peptides (anti-âge)",
        "voice_answer_template": "Le Soin Cell Flash Metabolissime, référence V024.0, réveille les peaux fatiguées. Sa Vitamine C booste l'éclat et active le métabolisme cellulaire. Résultat : un teint lumineux."
    },
    {
        "product_ref": "V026.0",
        "name": "ELIXIR CELL FLASH METABOLISSIME",
        "skin_need": "Peaux ternes, besoin d'éclat immédiat, anti-fatigue",
        "primary_mechanism": "Concentré actif qui réactive instantanément l'éclat et l'énergie cellulaire",
        "key_actives_summary": "Concentré Vitamine C (éclat flash), Niacinamide (uniformisant), Q10 (énergisant)",
        "voice_answer_template": "L'Elixir Cell Flash Metabolissime, référence V026.0, offre un coup d'éclat instantané. Son concentré de Vitamine C et Q10 réactive l'énergie cellulaire pour un teint lumineux."
    },
    {
        "product_ref": "V028.0",
        "name": "CRÈME PREMIUM NUIT ROSE ALPINE ÉTERNELLE",
        "skin_need": "Peaux matures exigeantes, régénération nocturne, anti-âge global",
        "primary_mechanism": "La Rose Alpine régénère intensément pendant la nuit pour un effet anti-âge global",
        "key_actives_summary": "Extrait de Rose Alpine (régénérant), Rétinol doux (anti-rides), Peptides (fermeté)",
        "voice_answer_template": "La Crème Premium Nuit Rose Alpine Éternelle, référence V028.0, est notre soin nocturne luxe. L'extrait de Rose Alpine régénère la peau pendant le sommeil pour un effet anti-âge global."
    },
    {
        "product_ref": "V070.0",
        "name": "METABOLIC GEL PERFECT",
        "skin_need": "Peaux mixtes à grasses matures, pores dilatés, manque de fermeté",
        "primary_mechanism": "Formule légère qui matifie tout en apportant les actifs anti-âge",
        "key_actives_summary": "Niacinamide (pores), Peptides (fermeté), Zinc (matifiant)",
        "voice_answer_template": "Le Metabolic Gel Perfect, référence V070.0, combine l'anti-âge et le matifiant. Sa Niacinamide resserre les pores tandis que les Peptides raffermissent. Idéal pour les peaux mixtes matures."
    },
    
    # === GAMME CORPS ===
    {
        "product_ref": "V037.0",
        "name": "SÉRUM SCULPTANT ANTI-CELLULITE ZONES REBELLES",
        "skin_need": "Cellulite localisée, zones rebelles (cuisses, ventre, bras)",
        "primary_mechanism": "La Caféine et les actifs lipolytiques ciblent les amas graisseux pour affiner la silhouette",
        "key_actives_summary": "Caféine (lipolytique), Carnitine (brûle-graisses), Algues (drainante)",
        "voice_answer_template": "Le Sérum Sculptant Anti-Cellulite, référence V037.0, cible les zones rebelles. Sa Caféine et sa Carnitine déstockent les graisses localisées. Résultat visible en cure de 4 semaines."
    },
    {
        "product_ref": "V038.0",
        "name": "GEL-CRÈME CRYO BODY POSITIVE",
        "skin_need": "Jambes lourdes, rétention d'eau, peau d'orange",
        "primary_mechanism": "L'effet cryo active la microcirculation et draine les tissus engorgés",
        "key_actives_summary": "Menthol (effet froid), Caféine (drainante), Algues (détoxifiante)",
        "voice_answer_template": "Le Gel-Crème Cryo Body Positive, référence V038.0, apporte un effet froid drainant. Son Menthol et sa Caféine activent la microcirculation pour des jambes légères."
    },
    {
        "product_ref": "V031.0",
        "name": "HUILE SATIN SUBLISSIME MASSAGE",
        "skin_need": "Peaux sèches, besoin de nutrition, massage relaxant",
        "primary_mechanism": "Les huiles végétales nourrissantes enveloppent la peau d'un film satiné",
        "key_actives_summary": "Huile d'Argan (nourrissante), Huile de Macadamia (satinée), Vitamine E (protectrice)",
        "voice_answer_template": "L'Huile Satin Sublissime, référence V031.0, offre un massage sensoriel. Ses Huiles d'Argan et Macadamia nourrissent intensément pour une peau satinée."
    },
    {
        "product_ref": "V033.0",
        "name": "BAUME RICHE CORPS RÉPARATEUR ++",
        "skin_need": "Peaux très sèches, zones rugueuses, besoin de réparation intense",
        "primary_mechanism": "La formule ultra-riche répare et nourrit en profondeur les peaux désséchées",
        "key_actives_summary": "Beurre de Karité (réparant), Cire d'Abeille (protectrice), Vitamine E (cicatrisante)",
        "voice_answer_template": "Le Baume Riche Réparateur, référence V033.0, répare les peaux très sèches. Son Beurre de Karité et sa Cire d'Abeille forment un bouclier protecteur pour les zones rugueuses."
    },
    {
        "product_ref": "V034.0",
        "name": "LAIT CORPS APAISANT ABSORPTION ++",
        "skin_need": "Peaux sensibles du corps, rougeurs, tiraillements",
        "primary_mechanism": "La formule légère pénètre rapidement pour apaiser et hydrater sans effet gras",
        "key_actives_summary": "Aloe Vera (apaisante), Bisabolol (anti-irritant), Glycérine (hydratante)",
        "voice_answer_template": "Le Lait Corps Apaisant, référence V034.0, calme les peaux sensibles du corps. Son Aloe Vera et son Bisabolol apaisent les irritations avec une absorption rapide."
    },
    {
        "product_ref": "V036.0",
        "name": "BAUME FONDANT MASSAGE PROFESSIONNEL",
        "skin_need": "Massage cabine, glisse optimale, soin nourrissant",
        "primary_mechanism": "Texture fondante qui permet les manœuvres de massage tout en nourrissant",
        "key_actives_summary": "Huiles végétales (glisse), Beurre de Karité (nourrissant), Vitamine E (antioxydant)",
        "voice_answer_template": "Le Baume Fondant Massage Professionnel, référence V036.0, est notre incontournable cabine. Sa texture fondante offre une glisse parfaite pour les modelages tout en nourrissant la peau."
    },
    
    # === NETTOYANTS ===
    {
        "product_ref": "V001.0",
        "name": "GOMMAGE VISAGE PRO",
        "skin_need": "Tous types de peaux, renouvellement cellulaire, préparation aux soins",
        "primary_mechanism": "Les grains exfoliants éliminent les cellules mortes pour une peau lisse et réceptive",
        "key_actives_summary": "Grains de Bambou (exfoliant), Aloe Vera (apaisante), Vitamine E (protectrice)",
        "voice_answer_template": "Le Gommage Visage Pro, référence V001.0, est le geste essentiel avant chaque soin cabine. Ses grains de Bambou affinent le grain de peau pour optimiser la pénétration des actifs."
    },
    {
        "product_ref": "V003.0",
        "name": "LAIT DÉMAQ'",
        "skin_need": "Peaux sèches à normales, démaquillage en douceur, confort",
        "primary_mechanism": "La texture lactée dissout le maquillage tout en préservant le film hydrolipidique",
        "key_actives_summary": "Huile d'Amande Douce (nourrit), Eau de Rose (apaise), Vitamine E (protège)",
        "voice_answer_template": "Le Lait Démaq, référence V003.0, démaquille en douceur les peaux sèches. Son Huile d'Amande Douce et son Eau de Rose laissent la peau propre et confortable."
    },
    {
        "product_ref": "V004.0",
        "name": "TONIQ' 3 FLEURS",
        "skin_need": "Tous types de peaux, tonification, préparation au soin",
        "primary_mechanism": "Les trois eaux florales tonifient et préparent la peau à recevoir les soins",
        "key_actives_summary": "Eau de Rose (apaisante), Eau de Bleuet (décongestionne), Eau de Fleur d'Oranger (tonifie)",
        "voice_answer_template": "Le Toniq 3 Fleurs, référence V004.0, complète le rituel de nettoyage. Ses eaux de Rose, Bleuet et Fleur d'Oranger tonifient et préparent la peau aux soins."
    },
    {
        "product_ref": "V005.0",
        "name": "DEMAQ' XPRESS 3-EN-1",
        "skin_need": "Tous types de peaux, démaquillage rapide, gain de temps",
        "primary_mechanism": "Formule micellaire 3-en-1 qui démaquille, nettoie et tonifie en un geste",
        "key_actives_summary": "Micelles (nettoient), Aloe Vera (apaise), Eau de Rose (tonifie)",
        "voice_answer_template": "Le Démaq Xpress 3-en-1, référence V005.0, est le démaquillant express. Sa formule micellaire démaquille, nettoie et tonifie en un seul geste. Parfait pour les clientes pressées."
    },
    
    # === GAMME DOUCHE/BAIN ===
    {
        "product_ref": "V042.0",
        "name": "GEL DOUCHE RELAXANT FIGUE & HIBISCUS",
        "skin_need": "Tous types de peaux, besoin de détente, moment bien-être",
        "primary_mechanism": "Les extraits de Figue et Hibiscus offrent un moment de relaxation sous la douche",
        "key_actives_summary": "Extrait de Figue (adoucissant), Hibiscus (antioxydant), Glycérine (hydratante)",
        "voice_answer_template": "Le Gel Douche Relaxant Figue et Hibiscus, référence V042.0, transforme la douche en moment détente. Son parfum enveloppant et ses actifs adoucissants laissent la peau douce."
    },
    {
        "product_ref": "V044.0",
        "name": "GEL DOUCHE TONIFIANT CITRON & ALOE VERA",
        "skin_need": "Tous types de peaux, besoin d'énergie, réveil matinal",
        "primary_mechanism": "Le Citron et l'Aloe Vera réveillent les sens tout en hydratant",
        "key_actives_summary": "Citron (tonifiant), Aloe Vera (hydratante), Glycérine (adoucissante)",
        "voice_answer_template": "Le Gel Douche Tonifiant Citron et Aloe Vera, référence V044.0, dynamise le réveil. Son parfum frais de citron et son Aloe Vera laissent la peau énergisée et hydratée."
    },
    {
        "product_ref": "V045.0",
        "name": "CRÈME DOUCHE NOURRISSANTE JOJOBA & ROSE",
        "skin_need": "Peaux sèches, besoin de nutrition sous la douche, confort",
        "primary_mechanism": "L'Huile de Jojoba nourrit pendant que l'eau de Rose adoucit",
        "key_actives_summary": "Huile de Jojoba (nourrissante), Eau de Rose (apaisante), Beurre de Karité (protecteur)",
        "voice_answer_template": "La Crème Douche Nourrissante Jojoba et Rose, référence V045.0, nourrit les peaux sèches dès la douche. Son Huile de Jojoba laisse un film protecteur sans graisser."
    },
    {
        "product_ref": "V053.0",
        "name": "CRÈME HYDRATANTE BÉBÉ J'AIME SA PEAU DOUCE",
        "skin_need": "Peau de bébé, peaux très sensibles, hydratation douce",
        "primary_mechanism": "Formule ultra-douce sans parfum qui hydrate et protège les peaux fragiles",
        "key_actives_summary": "Glycérine (hydratante), Beurre de Karité (protecteur), Allantoïne (apaisante)",
        "voice_answer_template": "La Crème J'aime Sa Peau Douce, référence V053.0, est formulée pour les bébés. Sans parfum et hypoallergénique, elle hydrate et protège les peaux les plus fragiles."
    },
    
    # === ÉPILATION ===
    {
        "product_ref": "V055.0",
        "name": "HUILE DE MASSAGE POST-ÉPILATION",
        "skin_need": "Peaux épilées, irritations, résidus de cire",
        "primary_mechanism": "L'huile élimine les résidus de cire tout en apaisant les irritations post-épilation",
        "key_actives_summary": "Huile de Tournesol (dissout cire), Calendula (apaisante), Vitamine E (cicatrisante)",
        "voice_answer_template": "L'Huile de Massage Post-Épilation, référence V055.0, élimine les résidus de cire et apaise la peau. Son Calendula calme les irritations pour un confort post-épilation."
    },
    {
        "product_ref": "V063.0",
        "name": "SOS POIL SOUS PEAU PROFESSIONAL",
        "skin_need": "Poils incarnés, folliculite, zones épilées récurrentes",
        "primary_mechanism": "Les AHA exfolient en douceur pour libérer les poils sous-cutanés",
        "key_actives_summary": "AHA (exfoliant), Acide Salicylique (désincruste), Tea Tree (antibactérien)",
        "voice_answer_template": "Le SOS Poil Sous Peau Professional, référence V063.0, traite les poils incarnés. Ses AHA et Acide Salicylique libèrent les poils coincés tout en prévenant les récidives."
    },
    
    # === SÉRUMS PRO CABINE ===
    {
        "product_ref": "C004.0",
        "name": "SÉRUM 4.0 HYDRATEMPO CABINE",
        "skin_need": "Peaux déshydratées, soin cabine, hydratation intensive",
        "primary_mechanism": "Concentration professionnelle d'acide hyaluronique pour les protocoles cabine",
        "key_actives_summary": "Acide Hyaluronique concentré (repulpant), Aloe Vera (apaisante), Vitamine B5 (réparatrice)",
        "voice_answer_template": "Le Sérum 4.0 Hydratempo Cabine, référence C004.0, est notre sérum professionnel pour le protocole Hydratempo. Sa concentration d'Acide Hyaluronique optimise les résultats du soin."
    },
    
    # === CAPILLAIRES ===
    {
        "product_ref": "V047.0",
        "name": "SHAMPOO ANTI-PELLICULAIRE FLEUR DE LOTUS & ROMARIN",
        "skin_need": "Cuir chevelu irrité, pellicules, démangeaisons",
        "primary_mechanism": "Le Zinc Pyrithione élimine les pellicules tandis que le Romarin apaise le cuir chevelu",
        "key_actives_summary": "Zinc Pyrithione (anti-pelliculaire), Romarin (apaisant), Fleur de Lotus (purifiant)",
        "voice_answer_template": "Le Shampoo Anti-Pelliculaire, référence V047.0, élimine les pellicules dès la première application. Son Zinc Pyrithione et son Romarin assainissent le cuir chevelu en douceur."
    },
    {
        "product_ref": "V048.0",
        "name": "SHAMPOO DOUX QUOTIDIEN YLANG-YLANG & MIEL",
        "skin_need": "Cheveux normaux, usage fréquent, brillance",
        "primary_mechanism": "La formule douce nettoie en préservant l'éclat naturel des cheveux",
        "key_actives_summary": "Miel (brillance), Ylang-Ylang (parfum), Protéines de Blé (fortifiant)",
        "voice_answer_template": "Le Shampoo Doux Quotidien, référence V048.0, convient à un usage quotidien. Son Miel apporte brillance et ses Protéines de Blé renforcent la fibre capillaire."
    },
    {
        "product_ref": "V049.0",
        "name": "SHAMPOO CHEVEUX SECS BAIES D'AÇAI & ALOE VERA",
        "skin_need": "Cheveux secs et abîmés, besoin de nutrition, pointes fourchues",
        "primary_mechanism": "Les Baies d'Açai et l'Aloe Vera nourrissent et réparent la fibre capillaire",
        "key_actives_summary": "Baies d'Açai (nourrissant), Aloe Vera (hydratant), Huile d'Argan (réparatrice)",
        "voice_answer_template": "Le Shampoo Cheveux Secs, référence V049.0, nourrit intensément les cheveux abîmés. Ses Baies d'Açai et son Huile d'Argan réparent et disciplinent les pointes fourchues."
    },
    {
        "product_ref": "V050.0",
        "name": "SHAMPOO CHEVEUX COLORÉS ALOE VERA & GRENADE",
        "skin_need": "Cheveux colorés, protection couleur, brillance",
        "primary_mechanism": "L'Aloe Vera et la Grenade préservent l'éclat de la coloration plus longtemps",
        "key_actives_summary": "Grenade (antioxydant), Aloe Vera (protecteur), Filtre UV (prolonge couleur)",
        "voice_answer_template": "Le Shampoo Cheveux Colorés, référence V050.0, préserve l'éclat des colorations. Son extrait de Grenade et son filtre UV protègent la couleur lavage après lavage."
    }
]


# === PROTOCOLES V2 (10 soins cabine supplémentaires) ===

PROTOCOLS_V2 = [
    {
        "name": "SOIN PROFOND SENSIMINE",
        "search_terms": ["sensimine", "peau sensible", "apaisant"],
        "skin_need": "Peau sensible et réactive, rougeurs diffuses, échauffements cutanés, couperose légère",
        "protocol_summary": "Soin apaisant déstressant en 4 phases : démaquillage doux à l'Eau Micellaire Aloe Vera, gommage ultra-doux, Sérum Sensimine avec manœuvres passives apaisantes 5 min, Masque Sensimine 10 min, modelage délicat.",
        "key_steps": [
            "Démaquillage Eau Micellaire Aloe Vera + Gommage doux",
            "Sérum N°2.0 SENSIMINE + manœuvres passives 5 min",
            "Masque N°2.0 SENSIMINE 10 min",
            "Rinçage + Sérum Gel Perfect + modelage doux 10 min"
        ],
        "duration_minutes": 50,
        "main_products": [
            {"name": "Eau Micellaire à l'Aloe Vera", "ref": "V006.0"},
            {"name": "Sérum N°2.0 SENSIMINE", "ref": "PRO cabine"},
            {"name": "Masque N°2.0 SENSIMINE", "ref": "C011.0"},
            {"name": "Crème SENSIMINE Ultra Apaisante", "ref": "V017.0"}
        ],
        "voice_answer_template_protocol": "Le Soin Profond Sensimine apaise et décongestionne les peaux sensibles et réactives. Le Sérum Sensimine calme les irritations, puis le Masque Sensimine réduit les rougeurs pendant 10 minutes. Idéal pour diminuer la réactivité cutanée. Durée : 50 minutes."
    },
    {
        "name": "SOIN METABOLISSIME ÉCLAT",
        "search_terms": ["metabolissime", "éclat", "anti-âge", "cell flash"],
        "skin_need": "Peaux matures, teint terne, premiers signes de l'âge, manque d'éclat",
        "protocol_summary": "Soin revitalisant anti-âge en 4 phases : démaquillage, Sérum Cell Flash avec manœuvres stimulantes, Masque Metabolissime 10 min, modelage liftant pour effet bonne mine immédiat.",
        "key_steps": [
            "Démaquillage + Gommage Visage PRO",
            "Elixir Cell Flash + manœuvres stimulantes 5 min",
            "Masque Metabolissime 10 min",
            "Rinçage + Crème Metabolic Collagen + modelage liftant"
        ],
        "duration_minutes": 50,
        "main_products": [
            {"name": "Elixir Cell Flash Metabolissime", "ref": "V026.0"},
            {"name": "Crème Metabolic Collagen Pro", "ref": "V019.0"},
            {"name": "Soin Cell Flash Activateur Global", "ref": "V024.0"}
        ],
        "voice_answer_template_protocol": "Le Soin Metabolissime Éclat réveille les peaux ternes et fatiguées. L'Elixir Cell Flash à la Vitamine C booste l'éclat, puis le Masque Metabolissime raffermit. Résultat : un teint lumineux et rajeuni. Durée : 50 minutes."
    },
    {
        "name": "SOIN REGARD LIFTANT",
        "search_terms": ["regard", "contour des yeux", "cernes", "poches", "liftant"],
        "skin_need": "Fatigue du regard, cernes, poches, ridules pattes d'oie",
        "protocol_summary": "Soin ciblé contour de l'œil : démaquillage délicat, Sérum Regard avec digito-pression, patchs collagène 15 min, modelage drainant du contour.",
        "key_steps": [
            "Démaquillage délicat contour des yeux",
            "Sérum Regard + digito-pression 5 min",
            "Patchs Collagène contour des yeux 15 min",
            "Modelage drainant + Contour des Yeux Liftant"
        ],
        "duration_minutes": 30,
        "main_products": [
            {"name": "Contour des Yeux Regard Liftant", "ref": "V025.0"},
            {"name": "Patchs Collagène Contour des Yeux", "ref": "cabine"}
        ],
        "voice_answer_template_protocol": "Le Soin Regard Liftant cible les signes de fatigue du contour de l'œil. Les Patchs Collagène repulpent pendant 15 minutes tandis que le modelage drainant réduit cernes et poches. Durée : 30 minutes."
    },
    {
        "name": "SOIN ANTISTRESS",
        "search_terms": ["antistress", "relaxant", "massage", "détente"],
        "skin_need": "Stress, tensions, fatigue nerveuse, besoin de lâcher-prise",
        "protocol_summary": "Soin relaxation totale : huile essentielle de Lavande, massage du dos et nuque 20 min, modelage visage apaisant, finition crème confort.",
        "key_steps": [
            "Application Huile Essentielle Relaxante",
            "Massage dos et nuque 20 min",
            "Modelage visage apaisant 10 min",
            "Finition Crème Confort"
        ],
        "duration_minutes": 45,
        "main_products": [
            {"name": "Huile Massage Relaxante", "ref": "V055.0"},
            {"name": "Baume Fondant Massage", "ref": "V036.0"}
        ],
        "voice_answer_template_protocol": "Le Soin Antistress offre une parenthèse de détente. Le massage du dos et de la nuque libère les tensions pendant 20 minutes, suivi d'un modelage visage apaisant. Durée : 45 minutes."
    },
    {
        "name": "GOMMAGE CORPS COMPLET",
        "search_terms": ["gommage corps", "exfoliant corps", "peau lisse"],
        "skin_need": "Peau rugueuse, cellules mortes, préparation avant bronzage ou soin corps",
        "protocol_summary": "Exfoliation corporelle complète : gommage en cabine avec la Gomme Corps, rinçage, application lait hydratant pour peau lisse et douce.",
        "key_steps": [
            "Préparation et installation cabine",
            "Application Gomme Corps sur tout le corps",
            "Massage circulaire exfoliant 15 min",
            "Rinçage + Lait Corps Doux"
        ],
        "duration_minutes": 30,
        "main_products": [
            {"name": "Gomme Corps Exfoliant Intense", "ref": "V030.0"},
            {"name": "Lait Corps Doux", "ref": "V054.0"}
        ],
        "voice_answer_template_protocol": "Le Gommage Corps Complet élimine les cellules mortes sur tout le corps. La Gomme Corps Exfoliant Intense lisse la peau par massage circulaire, suivi d'un Lait Corps Doux. Durée : 30 minutes."
    },
    {
        "name": "SOIN JAMBES LÉGÈRES",
        "search_terms": ["jambes légères", "jambes lourdes", "circulation", "drainant"],
        "skin_need": "Jambes lourdes, rétention d'eau, mauvaise circulation, sensation de gonflement",
        "protocol_summary": "Soin drainant ciblé jambes : application Gel Cryo, massage drainant ascendant, enveloppement frais, finition légèreté.",
        "key_steps": [
            "Application Gel-Crème Cryo sur les jambes",
            "Massage drainant ascendant 15 min",
            "Enveloppement frais 10 min",
            "Finition hydratation légère"
        ],
        "duration_minutes": 40,
        "main_products": [
            {"name": "Gel-Crème Cryo Body Positive", "ref": "V038.0"},
            {"name": "Lait Corps Doux", "ref": "V054.0"}
        ],
        "voice_answer_template_protocol": "Le Soin Jambes Légères soulage les jambes lourdes et gonflées. Le Gel-Crème Cryo apporte un effet froid drainant, suivi d'un massage ascendant qui active la circulation. Durée : 40 minutes."
    },
    {
        "name": "ÉPILATION MAILLOT INTÉGRAL",
        "search_terms": ["épilation", "maillot", "intégral", "cire"],
        "skin_need": "Épilation zones intimes, peau sensible post-épilation",
        "protocol_summary": "Épilation professionnelle maillot complet : cire adaptée à la zone, technique précise, application huile apaisante.",
        "key_steps": [
            "Préparation et désinfection de la zone",
            "Application cire par bandes ou sans bande",
            "Épilation technique professionnelle",
            "Huile Apaisante Après Épilation"
        ],
        "duration_minutes": 30,
        "main_products": [
            {"name": "Huile Apaisante Après Épilation", "ref": "V062.0"},
            {"name": "SOS Poil Sous Peau", "ref": "V063.0"}
        ],
        "voice_answer_template_protocol": "L'Épilation Maillot Intégral offre un résultat impeccable et durable. La technique professionnelle minimise l'inconfort, et l'Huile Apaisante calme la peau. Durée : environ 30 minutes."
    },
    {
        "name": "SOIN COLLAGÈNE INTENSE",
        "search_terms": ["collagène", "anti-rides", "fermeté", "restructurant"],
        "skin_need": "Rides profondes, perte de fermeté, relâchement cutané",
        "protocol_summary": "Soin restructurant anti-âge intensif : Sérum Collagène, masque feuille collagène 20 min, modelage liftant, finition crème anti-rides.",
        "key_steps": [
            "Démaquillage + Gommage doux",
            "Sérum Collagène + manœuvres stimulantes",
            "Masque feuille Collagène 20 min",
            "Modelage liftant + Crème Metabolic Collagen"
        ],
        "duration_minutes": 60,
        "main_products": [
            {"name": "Crème Metabolic Collagen Pro", "ref": "V019.0"},
            {"name": "Crème Premium Nuit Rose Alpine", "ref": "V028.0"}
        ],
        "voice_answer_template_protocol": "Le Soin Collagène Intense combat les rides et le relâchement. Le Masque feuille Collagène restructure pendant 20 minutes, suivi d'un modelage liftant. Effet rajeunissant visible. Durée : 1 heure."
    },
    {
        "name": "SOIN HYDRATATION CORPS",
        "search_terms": ["hydratation corps", "peau sèche corps", "nourrissant"],
        "skin_need": "Peau du corps déshydratée, tiraillements, zones sèches (coudes, genoux)",
        "protocol_summary": "Bain d'hydratation corporel : gommage léger, enveloppement hydratant, massage au baume fondant.",
        "key_steps": [
            "Gommage léger corps entier",
            "Enveloppement hydratant 15 min",
            "Massage au Baume Fondant 15 min",
            "Finition Lait Corps"
        ],
        "duration_minutes": 50,
        "main_products": [
            {"name": "Soin Corps Profond Hyper Hydratant", "ref": "V032.0"},
            {"name": "Baume Fondant Massage", "ref": "V036.0"},
            {"name": "Lait Corps Doux", "ref": "V054.0"}
        ],
        "voice_answer_template_protocol": "Le Soin Hydratation Corps nourrit intensément les peaux désséchées. L'enveloppement hydratant est suivi d'un massage au Baume Fondant pour une peau souple et confortable. Durée : 50 minutes."
    },
    {
        "name": "SOIN EXPRESS ÉCLAT",
        "search_terms": ["express", "éclat", "rapide", "coup d'éclat"],
        "skin_need": "Teint terne, besoin d'éclat rapide, avant événement",
        "protocol_summary": "Soin flash 20 minutes pour un coup d'éclat immédiat : Sérum Vitamine C, masque coup d'éclat 5 min, finition lumière.",
        "key_steps": [
            "Nettoyage express",
            "Elixir Cell Flash Vitamine C",
            "Masque coup d'éclat 5 min",
            "Finition hydratante lumière"
        ],
        "duration_minutes": 20,
        "main_products": [
            {"name": "Elixir Cell Flash Metabolissime", "ref": "V026.0"},
            {"name": "Soin Cell Flash Activateur", "ref": "V024.0"}
        ],
        "voice_answer_template_protocol": "Le Soin Express Éclat offre un coup de frais en 20 minutes. L'Elixir Vitamine C illumine instantanément le teint. Idéal avant un événement ou pour un boost rapide."
    }
]

# ========== IMPORTS CENTRALISÉS ==========
# Ajouter scripts/ au path pour trouver utils (déjà fait ligne 12)
from utils.qdrant_utils import get_qdrant_client
from utils.embedding_utils import get_embedding

def find_product_by_ref(client, product_ref: str, collection: str = "bodyminute_products"):
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


def find_protocol_chunks(client, search_terms, collection: str = "bodyminute_docs"):
    """Trouve les chunks correspondant à un protocole."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    # Exclure les chunks déjà premium V1
    all_matching_ids = []
    
    for term in search_terms:
        query_vector = get_embedding(term)
        results = client.query_points(
            collection_name=collection,
            query=query_vector,
            query_filter=Filter(
                must_not=[
                    FieldCondition(
                        key="is_protocol_premium",
                        match=MatchValue(value=True)
                    )
                ]
            ),
            limit=5,
            with_payload=True
        )
        
        for hit in results.points:
            if hit.score > 0.45:
                all_matching_ids.append(hit.id)
    
    return list(set(all_matching_ids))[:6]  # Max 6 chunks par protocole


def run_enrichment_v2():
    """Exécute l'enrichissement V2."""
    print("\n" + "=" * 80)
    print("🚀 EXTENSION PREMIUM V2 - COUVERTURE 80%")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    
    products_enriched = 0
    protocols_enriched = 0
    
    # === PRODUITS V2 ===
    print("\n" + "-" * 80)
    print(f"📦 ENRICHISSEMENT PRODUITS V2 ({len(PRODUCTS_V2)} produits)")
    print("-" * 80)
    
    for prod in PRODUCTS_V2:
        ref = prod["product_ref"]
        name = prod["name"]
        
        point = find_product_by_ref(client, ref)
        
        if point and not point.payload.get("is_premium"):
            # Enrichir le produit
            new_fields = {
                "skin_need": prod["skin_need"],
                "primary_mechanism": prod["primary_mechanism"],
                "key_actives_summary": prod["key_actives_summary"],
                "voice_answer_template": prod["voice_answer_template"],
                "is_premium": True
            }
            
            client.set_payload(
                collection_name="bodyminute_products",
                payload=new_fields,
                points=[point.id]
            )
            
            # Re-vectoriser avec texte enrichi
            indexation_text = f"Produit: {name} | Réf: {ref} | Besoin: {prod['skin_need']} | Actifs: {prod['key_actives_summary']}"
            new_vector = get_embedding(indexation_text)
            
            from qdrant_client.models import PointVectors
            client.update_vectors(
                collection_name="bodyminute_products",
                points=[PointVectors(id=point.id, vector=new_vector)]
            )
            
            print(f"   ✅ [{ref}] {name[:40]}...")
            products_enriched += 1
        elif point and point.payload.get("is_premium"):
            print(f"   ⏭️ [{ref}] Déjà premium V1")
        else:
            print(f"   ⚠️ [{ref}] Non trouvé")
    
    # === PROTOCOLES V2 ===
    print("\n" + "-" * 80)
    print(f"🏥 ENRICHISSEMENT PROTOCOLES V2 ({len(PROTOCOLS_V2)} protocoles)")
    print("-" * 80)
    
    for proto in PROTOCOLS_V2:
        name = proto["name"]
        print(f"\n🏥 {name}")
        
        # Trouver les chunks correspondants (non premium V1)
        matching_ids = find_protocol_chunks(client, proto["search_terms"])
        
        if matching_ids:
            new_fields = {
                "skin_need": proto["skin_need"],
                "protocol_summary": proto["protocol_summary"],
                "key_steps": proto["key_steps"],
                "duration_minutes": proto["duration_minutes"],
                "main_products": proto["main_products"],
                "voice_answer_template_protocol": proto["voice_answer_template_protocol"],
                "is_protocol_premium": True,
                "protocol_name": name
            }
            
            # Construire texte d'indexation
            steps_text = " ; ".join(proto["key_steps"])
            indexation_text = f"Soin: {name} | Durée: {proto['duration_minutes']} min | Peau: {proto['skin_need']} | Étapes: {steps_text}"
            new_vector = get_embedding(indexation_text)
            
            from qdrant_client.models import PointVectors
            
            for point_id in matching_ids:
                client.set_payload(
                    collection_name="bodyminute_docs",
                    payload=new_fields,
                    points=[point_id]
                )
                client.update_vectors(
                    collection_name="bodyminute_docs",
                    points=[PointVectors(id=point_id, vector=new_vector)]
                )
            
            print(f"   ✅ {len(matching_ids)} chunks enrichis et re-vectorisés")
            protocols_enriched += len(matching_ids)
        else:
            print(f"   ⚠️ Aucun chunk trouvé")
    
    # Rapport
    print("\n" + "=" * 80)
    print("📊 RAPPORT ENRICHISSEMENT V2")
    print("=" * 80)
    print(f"\n✅ Produits enrichis V2: {products_enriched}")
    print(f"✅ Chunks protocoles enrichis V2: {protocols_enriched}")
    print("\n" + "=" * 80)
    
    return products_enriched, protocols_enriched


if __name__ == "__main__":
    run_enrichment_v2()
