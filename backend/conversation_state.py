"""
Module de détection d'état conversationnel pour Mina.

Implémente une machine à états qui reconnaît les situations universelles
(hésitation, confusion, rush, etc.) et suggère des stratégies de réponse.

Architecture:
    INPUT (texte + latence)
        ↓
    Détection d'état (patterns + timing)
        ↓
    ConversationState avec règle suggérée
"""

import re
import logging
from enum import Enum
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES D'ÉTATS CONVERSATIONNELS
# =============================================================================

class StateType(Enum):
    """États conversationnels universels - Le Code de la Conversation."""
    
    NEUTRAL = "neutral"              # Conversation fluide, pas d'intervention
    HESITATION = "hesitation"        # Cliente hésitante → réduire les choix
    CONFUSION = "confusion"          # Incompréhension → reformuler simplement
    RUSH = "rush"                    # Cliente pressée → réponse ultra-courte
    CURIOSITY = "curiosity"          # Veut en savoir plus → approfondir
    DOUBT = "doubt"                  # Esthéticienne en doute → rassurer
    SATURATION = "saturation"        # Trop d'infos → récapituler
    CONFIRMATION = "confirmation"    # Attente validation → confirmer
    OBJECTION = "objection"          # Résistance implicite → adresser
    GREETING = "greeting"            # Salutation → accueil chaleureux


# =============================================================================
# PATTERNS DE DÉTECTION
# =============================================================================

# Patterns pour chaque état (regex, case-insensitive)
STATE_PATTERNS = {
    StateType.HESITATION: [
        r"\beuh+\b",
        r"\bhmm+\b",
        r"\bje\s+(ne\s+)?sais\s+pas\b",
        r"\bpeut-?être\b",
        r"\bje\s+(ne\s+)?suis\s+pas\s+sûre?\b",
        r"\bcomment\s+dire\b",
        r"\bc'est\s+difficile\b",
        r"\bj'hésite\b",
        r"^(bon|alors|donc|bah)$",  # Mots de remplissage seuls
    ],
    StateType.CONFUSION: [
        r"\bje\s+(ne\s+)?comprends?\s+pas\b",
        r"\bc'est\s+quoi\b",
        r"\bqu'est[- ]ce\s+que\s+ça\s+veut\s+dire\b",
        r"\btu\s+peux\s+répéter\b",
        r"\bje\s+suis\s+perdue?\b",
        r"\bc'est\s+compliqué\b",
        r"\bje\s+capte\s+pas\b",
    ],
    StateType.RUSH: [
        r"\bvite\b",
        r"\brapidement\b",
        r"\bpas\s+le\s+temps\b",
        r"\bjuste\s+(le\s+)?prix\b",
        r"\ben\s+deux\s+mots\b",
        r"\bcourt(ement)?\b",
        r"\bpressée?\b",
        r"\bdépêche\b",
    ],
    StateType.CURIOSITY: [
        r"\bpourquoi\b",
        r"\bcomment\s+ça\s+(marche|fonctionne)\b",
        r"\bexplique[- ]moi\b",
        r"\bc'est\s+intéressant\b",
        r"\bdis[- ]m'en\s+plus\b",
        r"\bet\s+si\b",
        r"\bqu'est[- ]ce\s+qui\s+se\s+passe\s+si\b",
    ],
    StateType.DOUBT: [
        r"\btu\s+es\s+sûre?\b",
        r"\bvraiment\s*\?\b",
        r"\bc'est\s+certain\b",
        r"\bj'ai\s+un\s+doute\b",
        r"\bje\s+doute\b",
        r"\bça\s+m'étonne\b",
        r"\btu\s+confirmes?\b",
    ],
    StateType.SATURATION: [
        r"\bok\s+ok\b",
        r"\bd'accord\s+d'accord\b",
        r"\bc'est\s+bon\s+c'est\s+bon\b",
        r"\bj'ai\s+compris\s+j'ai\s+compris\b",
        r"\bstop\b",
        r"\bsuffit\b",
        r"\btrop\s+d'infos?\b",
    ],
    StateType.CONFIRMATION: [
        r"\bc'est\s+ça\s*\?\b",
        r"\bje\s+prends\b",
        r"\balors\s+je\s+fais\s+ça\b",
        r"\bon\s+y\s+va\b",
        r"\bdonc\s+(c'est|je)\b",
        r"\bparfait\b",
    ],
    StateType.OBJECTION: [
        r"\bmais\s+c'est\s+cher\b",
        r"\bje\s+sais\s+pas\s+si\b",
        r"\bça\s+vaut\s+le\s+coup\b",
        r"\bje\s+(ne\s+)?suis\s+pas\s+convaincue?\b",
        r"\bbof\b",
        r"\bouais\s+mais\b",
    ],
    StateType.GREETING: [
        r"^bonjour\b",
        r"^salut\b",
        r"^coucou\b",
        r"^hello\b",
        r"^bonsoir\b",
    ],
}

# Seuils de latence (en millisecondes)
LATENCY_THRESHOLDS = {
    "hesitation": 2000,    # > 2s → probable hésitation
    "rush": 500,           # < 0.5s → probablement pressé
}


# =============================================================================
# STRUCTURES DE DONNÉES
# =============================================================================

@dataclass
class ConversationState:
    """
    État conversationnel détecté avec contexte.
    
    Attributes:
        state: Type d'état détecté
        confidence: Score de confiance (0.0 - 1.0)
        triggers: Patterns qui ont déclenché la détection
        latency_ms: Latence mesurée (si disponible)
    """
    state: StateType
    confidence: float
    triggers: List[str] = field(default_factory=list)
    latency_ms: Optional[int] = None
    
    def __str__(self) -> str:
        return f"[{self.state.value}] confidence={self.confidence:.2f}"
    
    @property
    def is_actionable(self) -> bool:
        """Retourne True si l'état nécessite une action."""
        return self.state != StateType.NEUTRAL and self.confidence >= 0.6


# =============================================================================
# DÉTECTION D'ÉTAT
# =============================================================================

def detect_state(
    text: str,
    latency_ms: Optional[int] = None,
    previous_response_length: Optional[int] = None
) -> ConversationState:
    """
    Détecte l'état conversationnel à partir du texte et du contexte.
    
    Args:
        text: Texte de l'utilisateur (transcription ou saisie)
        latency_ms: Temps de réponse en ms (pour détecter hésitation/rush)
        previous_response_length: Longueur réponse précédente (pour saturation)
    
    Returns:
        ConversationState avec état détecté et confiance
    """
    text_lower = text.lower().strip()
    detected_states: List[Tuple[StateType, float, List[str]]] = []
    
    # 1. Détection par patterns textuels
    for state_type, patterns in STATE_PATTERNS.items():
        triggers = []
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                triggers.append(pattern)
        
        if triggers:
            # Confiance basée sur nombre de patterns matchés
            confidence = min(0.5 + len(triggers) * 0.2, 1.0)
            detected_states.append((state_type, confidence, triggers))
    
    # 2. Ajustement par latence
    if latency_ms is not None:
        # Hésitation si latence élevée + patterns vagues
        if latency_ms > LATENCY_THRESHOLDS["hesitation"]:
            hesitation_states = [s for s in detected_states if s[0] == StateType.HESITATION]
            if hesitation_states:
                # Boost confiance si hésitation + latence élevée
                idx = detected_states.index(hesitation_states[0])
                detected_states[idx] = (
                    StateType.HESITATION,
                    min(hesitation_states[0][1] + 0.2, 1.0),
                    hesitation_states[0][2]
                )
            elif len(text_lower.split()) < 5:
                # Question courte + latence élevée = probable hésitation
                detected_states.append((StateType.HESITATION, 0.6, ["latence_elevee"]))
        
        # Rush si latence très faible
        if latency_ms < LATENCY_THRESHOLDS["rush"]:
            rush_states = [s for s in detected_states if s[0] == StateType.RUSH]
            if rush_states:
                idx = detected_states.index(rush_states[0])
                detected_states[idx] = (
                    StateType.RUSH,
                    min(rush_states[0][1] + 0.2, 1.0),
                    rush_states[0][2]
                )
    
    # 3. Détection saturation (après longue réponse + confirmation rapide)
    if previous_response_length and previous_response_length > 200:
        if any(s[0] == StateType.CONFIRMATION for s in detected_states):
            # Courte confirmation après longue réponse = possible saturation
            detected_states.append((StateType.SATURATION, 0.5, ["longue_reponse_precedente"]))
    
    # 4. Sélectionner l'état avec la plus haute confiance
    if detected_states:
        best_state = max(detected_states, key=lambda x: x[1])
        logger.debug(f"État détecté: {best_state[0].value} (conf: {best_state[1]:.2f})")
        return ConversationState(
            state=best_state[0],
            confidence=best_state[1],
            triggers=best_state[2],
            latency_ms=latency_ms
        )
    
    # État neutre par défaut
    return ConversationState(
        state=StateType.NEUTRAL,
        confidence=1.0,
        triggers=[],
        latency_ms=latency_ms
    )


def detect_hesitation_patterns(text: str) -> bool:
    """
    Détection rapide d'hésitation (pour audio_handler).
    
    Args:
        text: Texte transcrit
        
    Returns:
        True si des patterns d'hésitation sont détectés
    """
    text_lower = text.lower()
    for pattern in STATE_PATTERNS[StateType.HESITATION]:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


# =============================================================================
# UTILITAIRES
# =============================================================================

def get_state_description(state: StateType) -> str:
    """Retourne une description humaine de l'état."""
    descriptions = {
        StateType.NEUTRAL: "Conversation fluide",
        StateType.HESITATION: "Cliente hésitante",
        StateType.CONFUSION: "Incompréhension détectée",
        StateType.RUSH: "Cliente pressée",
        StateType.CURIOSITY: "Curiosité, veut en savoir plus",
        StateType.DOUBT: "Doute exprimé",
        StateType.SATURATION: "Saturation d'information",
        StateType.CONFIRMATION: "Attente de confirmation",
        StateType.OBJECTION: "Objection implicite",
        StateType.GREETING: "Salutation",
    }
    return descriptions.get(state, "État inconnu")


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    test_cases = [
        ("Euh... je sais pas trop...", None),
        ("Vite ! C'est quoi le prix ?", 300),
        ("Je comprends pas, c'est quoi ce produit ?", None),
        ("Ok ok d'accord d'accord", None),
        ("Pourquoi ça marche comme ça ?", None),
        ("Tu es sûre pour le vapozone ?", None),
        ("Bonjour !", None),
        ("Quel est le prix de l'Hydratempo ?", None),  # Neutre
    ]
    
    print("=== Test Détection d'État ===\n")
    for text, latency in test_cases:
        state = detect_state(text, latency)
        print(f"'{text}'")
        print(f"  → {state.state.value} (confidence: {state.confidence:.2f})")
        if state.triggers:
            print(f"  → triggers: {state.triggers}")
        print()
