"""
Générateur de réponses vocales pour Mina.

Priorité aux templates vocaux premium si disponibles,
sinon génération depuis les champs bruts.
Supporte aussi les réponses mixtes (protocole + produit).
Intègre le Code de la Conversation pour adaptation situationnelle.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MixedAnswer:
    """Structure pour réponse mixte protocole + produit."""
    protocol_payload: Dict[str, Any]
    product_payload: Dict[str, Any]
    protocol_score: float = 0.0
    product_score: float = 0.0


class VoiceResponseGenerator:
    """
    Génère des réponses optimisées pour la synthèse vocale.
    
    Utilise en priorité voice_answer_template si disponible,
    sinon construit une réponse depuis les champs bruts.
    """
    
    def generate_voice_response(
        self,
        payload: Dict[str, Any],
        include_price_if_missing: bool = True
    ) -> str:
        """
        Génère la réponse vocale à partir du payload Qdrant.
        
        Args:
            payload: Payload du résultat Qdrant
            include_price_if_missing: Ajouter prix/contenance si absent du template
            
        Returns:
            Texte prêt pour la synthèse vocale
        """
        # Vérifier si un template vocal existe (produit premium)
        voice_template = payload.get("voice_answer_template")
        
        if voice_template:
            logger.info("Utilisation du template vocal premium")
            return self._build_premium_response(payload, voice_template, include_price_if_missing)
        
        # Sinon, générer depuis les champs bruts
        logger.info("Génération depuis champs bruts")
        return self._build_raw_response(payload)
    
    def build_mixed_voice_answer(self, mixed: MixedAnswer) -> str:
        """
        Génère une réponse vocale mixte combinant protocole + produit.
        
        Structure de la réponse:
        - Phrase 1: Objectif de l'étape protocole
        - Phrase 2: Description du produit PRO associé
        - Phrase 3 (optionnelle): Durée totale du soin
        
        Args:
            mixed: MixedAnswer avec protocol_payload et product_payload
            
        Returns:
            Réponse vocale fusionnée
        """
        logger.info("Génération réponse MIXTE (protocole + produit)")
        
        parts = []
        
        # === PHRASE 1: Protocole ===
        proto = mixed.protocol_payload
        prod = mixed.product_payload
        
        # Vérifier si protocole premium avec template dédié
        proto_template = proto.get("voice_answer_template_protocol") or proto.get("voice_answer_template")
        is_protocol_premium = proto.get("is_protocol_premium", False)
        
        if proto_template:
            logger.info(f"Utilisation template protocole premium: {is_protocol_premium}")
            # Prendre le template complet ou la première phrase selon contexte
            if is_protocol_premium:
                # Pour protocole premium, prendre 2 premières phrases
                sentences = proto_template.split('.')
                first_two = '.'.join(sentences[:2]) + '.' if len(sentences) >= 2 else proto_template
                parts.append(first_two)
            else:
                first_sentence = proto_template.split('.')[0] + '.'
                parts.append(first_sentence)
        else:
            # Sinon extraire les infos clés du protocole brut
            proto_content = proto.get("content", proto.get("text", ""))
            if proto_content:
                proto_summary = self._extract_protocol_summary(proto_content)
                if proto_summary:
                    parts.append(proto_summary)
        
        # === PHRASE 2: Produit ===
        prod_template = prod.get("voice_answer_template")
        if prod_template:
            parts.append(prod_template)
        else:
            # Générer depuis les champs bruts du produit
            prod_name = prod.get("product_name", "")
            prod_ref = prod.get("product_ref", "")
            skin_need = prod.get("skin_need", "")
            key_actives = prod.get("key_actives_summary", prod.get("key_actives", []))
            
            if prod_name:
                prod_parts = []
                if prod_ref:
                    prod_parts.append(f"Le {prod_name}, référence {prod_ref}")
                else:
                    prod_parts.append(f"Le {prod_name}")
                
                if isinstance(key_actives, str) and key_actives:
                    prod_parts.append(f"contient {key_actives.split(',')[0].strip()}")
                elif isinstance(key_actives, list) and key_actives:
                    first_active = key_actives[0].split('\n')[0]
                    prod_parts.append(f"contient {first_active}")
                
                if skin_need:
                    prod_parts.append(f"et convient aux {skin_need.lower()}")
                
                parts.append(" ".join(prod_parts) + ".")
        
        # === PHRASE 3: Durée (optionnelle) ===
        primary_mechanism = proto.get("primary_mechanism", "")
        if "durée" in primary_mechanism.lower() or "minute" in primary_mechanism.lower():
            pass  # Déjà dans le mécanisme
        else:
            # Chercher la durée dans le contenu
            proto_content = proto.get("content", proto.get("text", ""))
            duration = self._extract_duration(proto_content)
            if duration:
                parts.append(f"Durée totale du soin : {duration}.")
        
        return " ".join(parts)
    
    def _extract_protocol_summary(self, content: str) -> str:
        """Extrait un résumé du protocole depuis le contenu brut."""
        content_lower = content.lower()
        
        # Chercher des mentions de Vapozone, extraction, etc.
        if "vapozone" in content_lower:
            # Extraire la phrase contenant Vapozone
            sentences = content.split('.')
            for sentence in sentences:
                if "vapozone" in sentence.lower():
                    return sentence.strip() + '.'
        
        # Sinon prendre les 150 premiers caractères
        if len(content) > 150:
            return content[:150].strip() + "..."
        return content
    
    def _extract_duration(self, content: str) -> Optional[str]:
        """Extrait la durée du soin depuis le contenu."""
        import re
        
        # Chercher des patterns de durée
        patterns = [
            r"(\d+)\s*(h|heure|heures?|min|minutes?)",
            r"durée\s*:\s*(\d+)\s*(min|minutes?|h|heures?)",
            r"environ\s*(\d+)\s*(min|minutes?|h|heures?)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content.lower())
            if match:
                value = match.group(1)
                unit = match.group(2)
                if 'h' in unit:
                    return f"{value} heure{'s' if int(value) > 1 else ''}"
                else:
                    return f"{value} minutes"
        
        return None
    
    def _build_premium_response(
        self,
        payload: Dict[str, Any],
        template: str,
        include_price_if_missing: bool
    ) -> str:
        """Construit la réponse premium avec template vocal."""
        response = template
        
        # Vérifier si le prix est déjà mentionné dans le template
        price = payload.get("price_eur")
        volume = payload.get("volume_ml")
        
        # Ajouter prix/contenance si non présents dans le template et disponibles
        if include_price_if_missing and price:
            price_mention = f"{price}" in template or "euros" in template.lower() or "€" in template
            
            if not price_mention:
                extra = f" Prix client : {price:.2f}€"
                if volume:
                    extra += f" pour {volume}ml"
                extra += "."
                response += extra
        
        return response
    
    def _build_raw_response(self, payload: Dict[str, Any]) -> str:
        """Construit une réponse depuis les champs bruts du payload."""
        doc_type = payload.get("doc_type", "")
        
        if doc_type == "product_card":
            return self._build_product_response(payload)
        else:
            return self._build_protocol_response(payload)
    
    def _build_product_response(self, payload: Dict[str, Any]) -> str:
        """Réponse pour un produit depuis les champs bruts."""
        name = payload.get("product_name", "Ce produit")
        ref = payload.get("product_ref", "")
        price = payload.get("price_eur")
        volume = payload.get("volume_ml")
        natural_pct = payload.get("natural_origin_pct")
        actives = payload.get("key_actives", [])
        skin_need = payload.get("skin_need")
        
        parts = []
        
        # Nom et référence
        if ref:
            parts.append(f"{name}, référence {ref}")
        else:
            parts.append(name)
        
        # Pourcentage naturel
        if natural_pct:
            parts.append(f"est à {natural_pct}% d'origine naturelle")
        
        # Besoin de peau
        if skin_need:
            parts.append(f"Il convient aux {skin_need.lower()}")
        
        # Actifs principaux
        if actives:
            actives_clean = [a.split('\n')[0] for a in actives[:2]]
            parts.append(f"Ses actifs clés sont : {', '.join(actives_clean)}")
        
        # Prix et contenance
        if price:
            price_str = f"Prix client : {price:.2f} euros"
            if volume:
                price_str += f" pour {volume}ml"
            parts.append(price_str)
        
        return ". ".join(parts) + "."
    
    def _build_protocol_response(self, payload: Dict[str, Any]) -> str:
        """Réponse pour un protocole depuis les champs bruts."""
        content = payload.get("content", payload.get("text", ""))
        
        # Prendre les 300 premiers caractères pertinents
        if len(content) > 300:
            content = content[:300] + "..."
        
        return content


def generate_voice_answer(
    search_results: List[Any],
    min_score: float = 0.5
) -> Optional[str]:
    """
    Génère la réponse vocale à partir des résultats de recherche.
    
    Args:
        search_results: Liste de SearchResult depuis Qdrant
        min_score: Score minimum pour considérer un résultat pertinent
        
    Returns:
        Réponse vocale ou None si aucun résultat pertinent
    """
    if not search_results:
        return None
    
    # Prendre le meilleur résultat
    best = search_results[0]
    
    if best.score < min_score:
        logger.warning(f"Score trop bas: {best.score:.3f} < {min_score}")
        return None
    
    generator = VoiceResponseGenerator()
    
    # Le payload est dans metadata (SearchResult) ou directement accessible
    payload = getattr(best, 'metadata', None) or getattr(best, 'payload', {})
    
    return generator.generate_voice_response(payload)


def generate_mixed_voice_answer(
    protocol_results: List[Any],
    product_results: List[Any],
    min_score: float = 0.4
) -> Optional[str]:
    """
    Génère une réponse vocale mixte à partir de résultats protocole et produit.
    
    Args:
        protocol_results: Résultats de recherche protocole
        product_results: Résultats de recherche produit
        min_score: Score minimum
        
    Returns:
        Réponse vocale mixte ou None
    """
    if not protocol_results or not product_results:
        return None
    
    proto_best = protocol_results[0]
    prod_best = product_results[0]
    
    proto_payload = getattr(proto_best, 'payload', {}) or getattr(proto_best, 'metadata', {})
    prod_payload = getattr(prod_best, 'payload', {}) or getattr(prod_best, 'metadata', {})
    
    mixed = MixedAnswer(
        protocol_payload=proto_payload,
        product_payload=prod_payload,
        protocol_score=getattr(proto_best, 'score', 0),
        product_score=getattr(prod_best, 'score', 0)
    )
    
    generator = VoiceResponseGenerator()
    return generator.build_mixed_voice_answer(mixed)


def generate_adaptive_voice_answer(
    search_results: List[Any],
    user_input: str,
    latency_ms: Optional[int] = None,
    tension_level: str = "medium",
    min_score: float = 0.5
) -> Optional[str]:
    """
    Génère une réponse vocale adaptée au Code de la Conversation.
    
    Détecte l'état conversationnel (hésitation, confusion, rush, etc.)
    et applique les règles universelles pour transformer la réponse.
    
    Module également le TON selon la tension vocale détectée:
    - LOW: Réponse complète, posée
    - MEDIUM: Réponse standard
    - HIGH: Réponse ultra-directe, courte
    
    Args:
        search_results: Liste de SearchResult depuis Qdrant
        user_input: Texte de l'utilisateur (pour détection d'état)
        latency_ms: Latence de réponse en ms (boost détection)
        tension_level: Niveau de tension vocale ("low", "medium", "high")
        min_score: Score minimum pour résultat pertinent
        
    Returns:
        Réponse vocale adaptée ou None si aucun résultat
    """
    # Générer la réponse de base
    base_response = generate_voice_answer(search_results, min_score)
    
    if not base_response:
        return None
    
    # Appliquer le Code de la Conversation + modulation tension
    try:
        from .conversation_rules import transform_response_with_state
        adapted_response = transform_response_with_state(
            response=base_response,
            user_input=user_input,
            latency_ms=latency_ms,
            tension_level=tension_level
        )
        return adapted_response
    except Exception as e:
        logger.warning(f"Erreur transformation conversationnelle: {e}")
        return base_response


# Raccourcis pour import simple
get_voice_response = generate_voice_answer
get_mixed_voice_response = generate_mixed_voice_answer
get_adaptive_voice_response = generate_adaptive_voice_answer

