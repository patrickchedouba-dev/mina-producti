#!/usr/bin/env python3
"""
Chatbot Terminal Mina - Body Minute.
Version terminal interactive utilisant products_index.

Usage:
    python scripts/chatbot_terminal.py
"""

import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Utilitaires centralisés (Phase 2 Refactoring)
from utils import get_qdrant_client, get_embedding


# =============================================================================
# CONFIGURATION
# =============================================================================

COLLECTION_PRODUCTS = "products_index"
COLLECTION_PROTOCOLS = "bodyminute_docs"

PRODUCT_KEYWORDS = {
    "prix", "tarif", "€", "euro", "euros", "coûte",
    "référence", "ref", "réf", "v0",
    "ml", "contenance", "volume",
    "naturel", "origine naturelle", "ingrédients", "%",
    "actifs", "principes actifs", "actif",
    "peaux grasses", "peaux sèches", "peaux sensibles", "peaux mixtes",
    "sérum", "crème", "gel", "mousse", "gommage", "lait", "huile", "baume",
    "démaq", "lotion", "masque", "spray", "shampooing", "shampoo",
    "eau micellaire", "hydratempo", "sensimine", "s-détox",
    "poil", "épilation", "cellulite", "mains", "corps"
}

PROTOCOL_KEYWORDS = {
    "soin", "protocole", "cure", "cabine", "étapes",
    "vapozone", "extraction", "modelage", "massage", "enveloppement",
    "durée", "minutes", "home spa"
}


# =============================================================================
# CLIENTS
# =============================================================================

# get_qdrant_client et get_embedding importés depuis utils (voir ligne 20)


# =============================================================================
# ROUTAGE ET RECHERCHE
# =============================================================================

def choose_collection(question: str) -> str:
    """Choisit la collection appropriée pour la question."""
    question_lower = question.lower()
    
    product_count = sum(1 for kw in PRODUCT_KEYWORDS if kw in question_lower)
    protocol_count = sum(1 for kw in PROTOCOL_KEYWORDS if kw in question_lower)
    
    if protocol_count > product_count and protocol_count >= 2:
        return COLLECTION_PROTOCOLS
    return COLLECTION_PRODUCTS


def search_qdrant(question: str, collection: str, limit: int = 5) -> List[Dict]:
    """Recherche sémantique dans Qdrant."""
    client = get_qdrant_client()
    query_vector = get_embedding(question)
    
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit,
        with_payload=True
    )
    
    return [{"score": hit.score, "payload": hit.payload} for hit in results.points]


# =============================================================================
# FORMATAGE
# =============================================================================

def format_product_response(payload: Dict) -> str:
    """Formate une réponse produit structurée."""
    lines = []
    
    name = payload.get("product_name", "Produit inconnu")
    ref = payload.get("product_ref", "")
    
    if ref:
        lines.append(f"📦 {name} (Réf: {ref})")
    else:
        lines.append(f"📦 {name}")
    
    price = payload.get("price_eur")
    if price:
        lines.append(f"   💰 Prix: {price:.2f}€")
    
    natural_pct = payload.get("natural_origin_pct")
    if natural_pct:
        lines.append(f"   🌿 % Naturel: {natural_pct}%")
    
    actives = payload.get("key_actives", [])
    if actives:
        lines.append(f"   🧪 Actifs: {', '.join(actives)}")
    
    skin_type = payload.get("skin_type", "")
    if skin_type:
        lines.append(f"   🎯 Indication: {skin_type}")
    
    usage = payload.get("usage_advice", "")
    if usage:
        lines.append(f"   📝 Conseil: {usage}")
    
    yuka = payload.get("yuka_score")
    if yuka:
        lines.append(f"   📊 Score Yuka: {yuka}/100")
    
    return "\n".join(lines)


def format_protocol_response(payload: Dict) -> str:
    """Formate une réponse protocole."""
    lines = []
    
    name = payload.get("protocol_name", "")
    if name:
        lines.append(f"📋 {name}")
    
    voice_template = payload.get("voice_answer_template_protocol") or payload.get("voice_answer_template")
    if voice_template:
        lines.append(f"   {voice_template[:300]}...")
    else:
        text = payload.get("text") or payload.get("content", "")
        if text:
            lines.append(f"   {text[:300]}...")
    
    return "\n".join(lines)


# =============================================================================
# CHATBOT PRINCIPAL
# =============================================================================

def run_chatbot():
    """Exécute le chatbot en mode terminal."""
    print("\n" + "=" * 70)
    print("💆 MINA - Assistant Body Minute (Terminal)")
    print("=" * 70)
    print("Utilise la collection 'products_index' pour les questions produits.")
    print("Tapez 'quit' ou 'q' pour quitter.\n")
    
    # Vérifier la connexion
    try:
        client = get_qdrant_client()
        info = client.get_collection("products_index")
        print(f"✅ Connecté à Qdrant - products_index: {info.points_count} produits\n")
    except Exception as e:
        print(f"❌ Erreur connexion Qdrant: {e}")
        return
    
    while True:
        try:
            question = input("\n🗣️ Vous: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ["quit", "q", "exit"]:
                print("\n👋 Au revoir!")
                break
            
            # 1. Choisir la collection
            collection = choose_collection(question)
            print(f"\n🎯 Collection: {collection}")
            
            # 2. Recherche
            print("🔍 Recherche en cours...")
            results = search_qdrant(question, collection, limit=3)
            
            if not results:
                print("\n⚠️ Aucun résultat trouvé.")
                continue
            
            # 3. Afficher les résultats
            print("\n" + "-" * 70)
            print("📋 RÉSULTATS:")
            print("-" * 70)
            
            for i, r in enumerate(results, 1):
                payload = r["payload"]
                score = r["score"]
                
                print(f"\n[{i}] Score: {score:.3f}")
                
                if collection == COLLECTION_PRODUCTS:
                    print(format_product_response(payload))
                else:
                    print(format_protocol_response(payload))
            
            print("-" * 70)
            
            # 4. Générer réponse synthétique
            best = results[0]["payload"]
            
            print("\n💬 MINA:")
            if collection == COLLECTION_PRODUCTS:
                name = best.get("product_name", "Ce produit")
                ref = best.get("product_ref", "")
                
                answer_parts = [f"Le {name}"]
                if ref:
                    answer_parts[0] += f" (référence {ref})"
                
                if best.get("key_actives"):
                    actives = best["key_actives"]
                    answer_parts.append(f"contient les actifs suivants: {', '.join(actives)}")
                
                if best.get("price_eur"):
                    answer_parts.append(f"Son prix est de {best['price_eur']:.2f}€")
                
                if best.get("natural_origin_pct"):
                    answer_parts.append(f"Il est à {best['natural_origin_pct']}% d'origine naturelle")
                
                if best.get("usage_advice"):
                    answer_parts.append(f"Conseil d'utilisation: {best['usage_advice']}")
                
                print("   " + ". ".join(answer_parts) + ".")
            else:
                text = best.get("voice_answer_template") or best.get("text") or best.get("content", "")
                if text:
                    print(f"   {text[:400]}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Au revoir!")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")


if __name__ == "__main__":
    run_chatbot()
