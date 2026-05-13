"""
Analyseur de tension vocale pour Mina.

Mesure la tension dans la voix à partir de signaux physiques:
- Variation de pitch (hauteur de voix)
- Vitesse de parole
- Pauses irrégulières
- Intensité/énergie

⚠️ Ce n'est PAS une analyse émotionnelle.
C'est un capteur de signal physique, comme un radar mesure une vitesse.

La tension n'est JAMAIS stockée - utilisée en temps réel uniquement.
"""

import logging
from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# NIVEAUX DE TENSION
# =============================================================================

class TensionLevel(Enum):
    """Niveaux de tension vocale mesurés."""
    LOW = "low"        # Calme, posé
    MEDIUM = "medium"  # Normal, un peu de pression
    HIGH = "high"      # Stress, agacement, urgence


@dataclass
class TensionAnalysis:
    """
    Résultat de l'analyse de tension vocale.
    
    Attributes:
        level: Niveau de tension (low/medium/high)
        confidence: Score de confiance
        indicators: Signaux détectés
    """
    level: TensionLevel
    confidence: float
    indicators: dict
    
    def __str__(self) -> str:
        return f"[TENSION: {self.level.value}] conf={self.confidence:.2f}"


# =============================================================================
# ANALYSE DE TENSION (SIGNAUX TEXTUELS)
# =============================================================================

# Patterns textuels indicateurs de tension élevée
HIGH_TENSION_PATTERNS = [
    # Expressions de pression temporelle
    r"\bpas\s+le\s+temps\b",
    r"\bpressée?\b",
    r"\bvite\b",
    r"\bdépêche\b",
    r"\burgent\b",
    r"\btout\s+de\s+suite\b",
    r"\bmaintenant\b",
    # Expressions d'agacement
    r"\bbon\s+alors\b",
    r"\bje\s+t'ai\s+dit\b",
    r"\bje\s+répète\b",
    r"\bc'est\s+pas\s+compliqué\b",
    r"\bpourquoi\s+c'est\s+si\b",
    # Formes contractées/brusques
    r"\bj'sais\s+pas\b",
    r"\bj'ai\s+pas\b",
    r"\bbon\b(?=\s*[,!.])",
]

# Patterns indicateurs de tension basse (calme)
LOW_TENSION_PATTERNS = [
    r"\bs'il\s+te\s+plaît\b",
    r"\bmerci\b",
    r"\bj'aimerais\b",
    r"\bpourriez-vous\b",
    r"\bquand\s+vous\s+(voulez|pouvez)\b",
    r"\bpas\s+pressée?\b",
    r"\btranquillement\b",
    r"\bje\s+voudrais\s+savoir\b",
]


def analyze_tension_from_text(
    text: str,
    latency_ms: Optional[int] = None,
    hesitation_detected: bool = False
) -> TensionAnalysis:
    """
    Analyse la tension vocale à partir du texte transcrit.
    
    Version 1: basée sur les patterns textuels et le timing.
    Version future: ajoutera l'analyse audio directe.
    
    Args:
        text: Texte transcrit
        latency_ms: Latence de réponse
        hesitation_detected: Si patterns d'hésitation détectés
        
    Returns:
        TensionAnalysis avec niveau et indicateurs
    """
    import re
    
    text_lower = text.lower().strip()
    indicators = {
        "high_patterns": 0,
        "low_patterns": 0,
        "short_sentences": False,
        "fast_response": False,
        "has_hesitation": hesitation_detected,
    }
    
    # Compter les patterns
    for pattern in HIGH_TENSION_PATTERNS:
        if re.search(pattern, text_lower):
            indicators["high_patterns"] += 1
    
    for pattern in LOW_TENSION_PATTERNS:
        if re.search(pattern, text_lower):
            indicators["low_patterns"] += 1
    
    # Analyser la structure
    words = text.split()
    indicators["word_count"] = len(words)
    indicators["short_sentences"] = len(words) < 6 and not hesitation_detected
    
    # Analyser le timing
    if latency_ms is not None:
        indicators["latency_ms"] = latency_ms
        indicators["fast_response"] = latency_ms < 500
    
    # Calculer le niveau de tension
    tension_score = 0.0
    
    # Points pour tension haute
    tension_score += indicators["high_patterns"] * 0.25
    if indicators["short_sentences"] and not hesitation_detected:
        tension_score += 0.2
    if indicators["fast_response"]:
        tension_score += 0.15
    
    # Points pour tension basse (soustraction)
    tension_score -= indicators["low_patterns"] * 0.2
    if hesitation_detected:
        tension_score -= 0.1  # L'hésitation indique souvent moins de stress
    
    # Déterminer le niveau
    if tension_score >= 0.4:
        level = TensionLevel.HIGH
        confidence = min(0.5 + tension_score, 0.95)
    elif tension_score <= -0.2:
        level = TensionLevel.LOW
        confidence = min(0.5 + abs(tension_score), 0.9)
    else:
        level = TensionLevel.MEDIUM
        confidence = 0.6
    
    logger.debug(f"Tension analysée: {level.value} (score: {tension_score:.2f})")
    
    return TensionAnalysis(
        level=level,
        confidence=confidence,
        indicators=indicators
    )


# =============================================================================
# ANALYSE AUDIO DIRECTE (PRÉPARATION FUTURE)
# =============================================================================

def analyze_tension_from_audio(audio_bytes: bytes) -> Optional[TensionAnalysis]:
    """
    Analyse la tension vocale directement depuis l'audio.
    
    🚧 VERSION FUTURE - Nécessite librosa ou autre lib audio.
    
    Signaux à analyser:
    - Variation de pitch (F0)
    - Jitter (micro-variations)
    - Shimmer (variations d'amplitude)
    - Vitesse de parole (syllabes/seconde)
    - Ratio pause/parole
    
    Args:
        audio_bytes: Données audio brutes
        
    Returns:
        TensionAnalysis ou None si analyse non disponible
    """
    # TODO: Implémenter avec librosa quand disponible
    # Pour l'instant, on retourne None et on se base sur le texte
    return None


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def get_tension_level(
    text: str,
    audio_bytes: Optional[bytes] = None,
    latency_ms: Optional[int] = None,
    hesitation_detected: bool = False
) -> TensionLevel:
    """
    Retourne le niveau de tension vocale.
    
    Point d'entrée principal pour le Code de la Conversation.
    
    Args:
        text: Texte transcrit
        audio_bytes: Audio brut (optionnel, pour analyse future)
        latency_ms: Latence de réponse
        hesitation_detected: Si hésitation détectée
        
    Returns:
        TensionLevel (LOW, MEDIUM, HIGH)
    """
    # Essayer d'abord l'analyse audio (plus précise)
    if audio_bytes:
        audio_analysis = analyze_tension_from_audio(audio_bytes)
        if audio_analysis:
            return audio_analysis.level
    
    # Sinon, analyse textuelle
    text_analysis = analyze_tension_from_text(
        text=text,
        latency_ms=latency_ms,
        hesitation_detected=hesitation_detected
    )
    
    return text_analysis.level


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    test_cases = [
        # (texte, latency, hesitation, tension_attendue)
        ("Euh... je sais pas trop...", 2000, True, "low/medium"),
        ("Vite le prix !", 300, False, "high"),
        ("Bon j'ai pas le temps là !", 400, False, "high"),
        ("S'il te plaît, j'aimerais savoir le prix", None, False, "low"),
        ("Quel est le prix ?", 1000, False, "medium"),
        ("J'sais pas, dépêche !", 200, False, "high"),
    ]
    
    print("=== Test Analyseur de Tension Vocale ===\n")
    for text, latency, hesitation, expected in test_cases:
        analysis = analyze_tension_from_text(text, latency, hesitation)
        print(f"'{text}'")
        print(f"  → {analysis.level.value} (attendu: {expected})")
        print(f"  → Indicateurs: {analysis.indicators}")
        print()
