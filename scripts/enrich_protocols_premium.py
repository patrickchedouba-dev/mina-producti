#!/usr/bin/env python3
"""
Enrichissement des 5 protocoles premium dans bodyminute_docs.
Structure alignée avec les fiches NotebookLM.
"""

import os
import sys
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


# === 5 PROTOCOLES PREMIUM (structure NotebookLM) ===

PROTOCOL_ENRICHMENTS = [
    {
        "name": "CURE SILHOUETTE",
        "search_terms": ["cure silhouette", "enveloppement", "silhouette"],
        "skin_need": "Cellulite, rondeurs, relâchement cutané, mauvaise circulation sanguine et lymphatique",
        "protocol_summary": "Soin minceur en 4 phases : préparation avec gel enveloppement, massage manuel ciblé 20 min sur les zones à traiter, enveloppement plastique chaud ou froid 30 min pour activer la sudation, puis phase de récupération et finition.",
        "key_steps": [
            "Installation couverture chauffante + application Gel Enveloppement",
            "Massage manuel ciblé 20 min (améliore métabolisme tissulaire)",
            "Enveloppement plastique 30 min (sudation/cryothérapie)",
            "Retrait, nettoyage et finition du soin"
        ],
        "duration_minutes": 60,
        "main_products": [
            {"name": "Gel Enveloppement Cure Silhouette à Chaud", "ref": "cabine"},
            {"name": "Lotion Enveloppement Cure Silhouette", "ref": "cabine"},
            {"name": "Sérum Sculptant Anti-Cellulite Zones Rebelles", "ref": "V037.0"},
            {"name": "Gel-Crème Cryo Body Positive", "ref": "V038.0"}
        ],
        "voice_answer_template_protocol": "La Cure Silhouette affine et tonifie la silhouette en luttant contre la cellulite. Elle comprend un massage manuel de 20 minutes sur les zones ciblées, suivi d'un enveloppement chaud ou froid pendant 30 minutes. Durée totale : 1 heure, idéalement en cure de 8 séances."
    },
    {
        "name": "SOIN LONGUE TENUE ANTI-COMÉDONS",
        "search_terms": ["anti-comédons", "longue tenue", "vapozone", "comédons"],
        "skin_need": "Peau grasse, acnéique, comédons et imperfections accumulées, pores dilatés",
        "protocol_summary": "Soin purifiant intensif en 5 étapes : démaquillage et gommage, application Sérum Désincrustant avec manœuvres actives, Vapozone 10 min pour dilater les pores et extraction des comédons, masque purifiant 10 min, finition avec modelage.",
        "key_steps": [
            "Démaquillage + Gommage Visage PRO",
            "Sérum N°1.3 Désincrustant + manœuvres actives 5 min",
            "Vapozone 10 min (vapeur + ozone) + extraction comédons",
            "Masque N°2.0 SENSIMINE 10 min",
            "Rinçage + Sérum Gel Perfect + modelage final 10 min"
        ],
        "duration_minutes": 60,
        "main_products": [
            {"name": "Sérum N°1.3 Désincrustant", "ref": "PRO cabine"},
            {"name": "Masque N°2.0 SENSIMINE", "ref": "C011.0"},
            {"name": "Sérum Gel Perfect", "ref": "finition"},
            {"name": "Crème de Massage", "ref": "cabine"}
        ],
        "voice_answer_template_protocol": "Le Soin Longue Tenue Anti-Comédons nettoie en profondeur les peaux grasses et acnéiques. Le Vapozone dilate les pores pendant 10 minutes pour faciliter l'extraction des comédons. Le Masque Sensimine purifie ensuite pendant 10 minutes. Durée : 1 heure."
    },
    {
        "name": "SOIN PROFOND HYDRATEMPO",
        "search_terms": ["hydratempo", "hydra", "peau sèche", "déshydrat"],
        "skin_need": "Peau sèche, déshydratée, alipidique, barrière cutanée fragilisée, manque de souplesse",
        "protocol_summary": "Soin hydratant intensif en 4 phases : démaquillage et gommage doux, Sérum Hydratempo avec manœuvres passives 5 min, Masque Hydratempo 10 min pour saturer la peau en eau, modelage final avec Baume Fondant.",
        "key_steps": [
            "Démaquillage + Gommage Visage PRO délicat",
            "Sérum N°4.0 HYDRATEMPO + manœuvres passives 5 min",
            "Masque N°4.0 HYDRATEMPO 10 min",
            "Rinçage + Sérum Gel Perfect + modelage Baume Fondant 10 min"
        ],
        "duration_minutes": 50,
        "main_products": [
            {"name": "Sérum N°4.0 HYDRATEMPO", "ref": "PRO cabine"},
            {"name": "Masque N°4.0 HYDRATEMPO", "ref": "PRO cabine"},
            {"name": "Sérum Gel Perfect", "ref": "finition"},
            {"name": "Baume Fondant Massage Professionnel", "ref": "cabine"}
        ],
        "voice_answer_template_protocol": "Le Soin Profond Hydratempo réhydrate intensément les peaux sèches et déshydratées. Le Sérum Hydratempo pénètre en profondeur grâce aux manœuvres passives, puis le Masque Hydratempo restaure la barrière cutanée pendant 10 minutes. Durée : 50 minutes."
    },
    {
        "name": "SOIN PROFOND SENSIMINE",
        "search_terms": ["sensimine", "peau sensible", "rougeurs", "apaisant"],
        "skin_need": "Peau sensible et réactive, rougeurs diffuses, échauffements cutanés, faible seuil de tolérance",
        "protocol_summary": "Soin apaisant déstressant en 4 phases : démaquillage doux à l'Eau Micellaire Aloe Vera, gommage ultra-doux, Sérum Sensimine avec manœuvres passives apaisantes, Masque Sensimine 10 min, modelage délicat.",
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
        "name": "SOIN PROFOND S-DÉTOX",
        "search_terms": ["s-détox", "peau grasse", "matifier", "pores"],
        "skin_need": "Peau mixte à grasse, brillances excessives, pores dilatés, teint brouillé par les impuretés",
        "protocol_summary": "Soin purifiant matifiant en 4 phases : démaquillage et gommage désincrust, Sérum S-Détox avec manœuvres actives pour activer la microcirculation, Masque S-Détox 10 min pour absorber le sébum, modelage final.",
        "key_steps": [
            "Démaquillage + Gommage Visage PRO affinant",
            "Sérum N°1.0 S-DÉTOX + manœuvres actives 5 min",
            "Masque N°1.0 S-DÉTOX 10 min",
            "Rinçage + Sérum Gel Perfect + modelage 10 min"
        ],
        "duration_minutes": 50,
        "main_products": [
            {"name": "Sérum N°1.0 S-DÉTOX", "ref": "PRO cabine"},
            {"name": "Masque N°1.0 S-DÉTOX", "ref": "PRO cabine"},
            {"name": "Gel Mousse S-DÉTOX", "ref": "V010.0"},
            {"name": "GEL S-DÉTOX MATT++", "ref": "V008.0"}
        ],
        "voice_answer_template_protocol": "Le Soin Profond S-Détox purifie et matifie les peaux mixtes à grasses. Le Sérum S-Détox régule le sébum grâce aux manœuvres actives, puis le Masque S-Détox absorbe les impuretés pendant 10 minutes. Fini mat longue durée garanti. Durée : 50 minutes."
    }
]

# ========== IMPORTS CENTRALISÉS ==========
from utils.qdrant_utils import get_qdrant_client
from utils.embedding_utils import get_embedding

def find_protocol_chunks(client, search_terms: List[str], collection: str = "bodyminute_docs"):
    """Trouve les chunks correspondant à un protocole."""
    all_matching_ids = []
    
    for term in search_terms:
        query_vector = get_embedding(term)
        results = client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=3,
            with_payload=True
        )
        
        for hit in results.points:
            if hit.score > 0.5:
                all_matching_ids.append(hit.id)
    
    # Dédupliquer
    return list(set(all_matching_ids))


def update_protocol_chunks(client, point_ids: List, enrichment: Dict, collection: str = "bodyminute_docs"):
    """Met à jour les chunks avec les champs protocole premium."""
    new_fields = {
        "skin_need": enrichment["skin_need"],
        "protocol_summary": enrichment["protocol_summary"],
        "key_steps": enrichment["key_steps"],
        "duration_minutes": enrichment["duration_minutes"],
        "main_products": enrichment["main_products"],
        "voice_answer_template_protocol": enrichment["voice_answer_template_protocol"],
        "is_protocol_premium": True,
        "protocol_name": enrichment["name"]
    }
    
    for point_id in point_ids:
        client.set_payload(
            collection_name=collection,
            payload=new_fields,
            points=[point_id]
        )
    
    return len(point_ids)


def run_enrichment():
    """Exécute l'enrichissement des 5 protocoles."""
    print("\n" + "=" * 80)
    print("🏥 ENRICHISSEMENT PROTOCOLES PREMIUM (NotebookLM)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    client = get_qdrant_client()
    
    total_enriched = 0
    
    for i, proto in enumerate(PROTOCOL_ENRICHMENTS, 1):
        print(f"\n{'─'*60}")
        print(f"[{i}/5] {proto['name']}")
        print(f"   🎯 {proto['skin_need'][:60]}...")
        
        # Trouver les chunks correspondants
        matching_ids = find_protocol_chunks(client, proto["search_terms"])
        print(f"   📄 Chunks trouvés: {len(matching_ids)}")
        
        if matching_ids:
            # Mettre à jour les chunks
            count = update_protocol_chunks(client, matching_ids, proto)
            print(f"   ✅ {count} chunks enrichis")
            total_enriched += count
        else:
            print(f"   ⚠️ Aucun chunk trouvé")
    
    # Rapport
    print("\n" + "=" * 80)
    print("📊 RAPPORT FINAL")
    print("=" * 80)
    
    print(f"\n✅ Total chunks enrichis: {total_enriched}")
    
    print("\n📋 PROTOCOLES PREMIUM:")
    for proto in PROTOCOL_ENRICHMENTS:
        print(f"\n   🏥 {proto['name']}")
        print(f"      Durée: {proto['duration_minutes']} min")
        print(f"      🎤 \"{proto['voice_answer_template_protocol'][:80]}...\"")
    
    print("\n" + "=" * 80)
    print("✅ ENRICHISSEMENT TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    run_enrichment()
