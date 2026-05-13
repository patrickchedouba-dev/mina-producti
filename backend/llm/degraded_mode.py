"""
Degraded Mode Agent - Réponses scriptées si tous LLM down.

Dernier niveau de protection : Mina ne plante JAMAIS.
"""

import re
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DegradedModeAgent:
    """
    Agent de secours avec réponses pré-scriptées.
    
    Utilisé quand:
    - Gemini DOWN
    - Claude DOWN
    - Tous les LLM indisponibles
    
    Objectif: Ne jamais retourner d'erreur 500 à l'utilisateur.
    """
    
    def __init__(self):
        self._activated_at: Optional[datetime] = None
        self._call_count = 0
        
        # Réponses par catégorie
        self._responses = {
            "greeting": (
                "Bonjour ! 👋 Je rencontre actuellement un souci technique temporaire. "
                "Un conseiller vous contactera très rapidement. "
                "En attendant, n'hésitez pas à nous appeler au numéro de votre institut. 💜"
            ),
            
            "booking": (
                "Pour prendre rendez-vous, je vous invite à appeler directement votre institut Body Minute. "
                "Notre équipe se fera un plaisir de vous accueillir ! "
                "Désolée pour ce désagrément temporaire. 🙏"
            ),
            
            "product": (
                "Je ne peux pas accéder aux informations produits pour le moment. "
                "Nos conseillères en institut pourront vous guider parfaitement. "
                "La situation devrait se rétablir très vite ! 💄"
            ),
            
            "skin": (
                "Je ne peux pas réaliser de diagnostic peau actuellement. "
                "Nos esthéticiennes expertes en institut peuvent vous faire "
                "un bilan personnalisé gratuit. À très vite ! ✨"
            ),
            
            "memory": (
                "Je ne retrouve pas vos informations pour le moment. "
                "Pas d'inquiétude, notre équipe en institut a accès à votre historique. "
                "Nous restons à votre disposition ! 💜"
            ),
            
            "default": (
                "Je rencontre un problème technique temporaire. 🔧 "
                "Merci de réessayer dans quelques instants ou de contacter votre institut. "
                "Toutes mes excuses pour la gêne occasionnée !"
            ),
            
            "goodbye": (
                "À très bientôt ! 💜 "
                "Je devrais fonctionner normalement très rapidement. "
                "Merci de votre patience !"
            )
        }
        
        # Patterns de classification
        self._patterns = {
            "greeting": r"bonjour|salut|coucou|hello|hey|bonsoir",
            "booking": r"rendez.?vous|rdv|réserv|disponib|horaire|quand|heure",
            "product": r"produit|crème|sérum|soin|recommand|conseil",
            "skin": r"peau|acné|ride|sèche|grasse|sensible|diagnostic",
            "memory": r"historique|profil|souvien|dernière fois|préférence",
            "goodbye": r"merci|au revoir|à bientôt|bye|ciao"
        }
    
    def get_response(self, user_input: str) -> str:
        """
        Retourne une réponse scriptée appropriée.
        
        Args:
            user_input: Message utilisateur
        
        Returns:
            Réponse scriptée
        """
        if self._activated_at is None:
            self._activated_at = datetime.now()
            logger.warning("⚠️ Degraded Mode ACTIVÉ - Réponses scriptées")
        
        self._call_count += 1
        
        input_lower = user_input.lower()
        
        # Classifier l'input
        for category, pattern in self._patterns.items():
            if re.search(pattern, input_lower):
                logger.debug(f"📝 Degraded: category={category}")
                return self._responses[category]
        
        # Default
        return self._responses["default"]
    
    def is_active(self) -> bool:
        """Vérifie si le mode dégradé a été activé."""
        return self._activated_at is not None
    
    def get_stats(self) -> dict:
        """Retourne les statistiques du mode dégradé."""
        duration = None
        if self._activated_at:
            duration = (datetime.now() - self._activated_at).total_seconds()
        
        return {
            "active": self.is_active(),
            "activated_at": self._activated_at.isoformat() if self._activated_at else None,
            "duration_seconds": duration,
            "call_count": self._call_count
        }
    
    def reset(self):
        """Reset après retour à la normale."""
        if self._activated_at:
            duration = (datetime.now() - self._activated_at).total_seconds()
            logger.info(f"✅ Degraded Mode désactivé après {duration:.0f}s, {self._call_count} appels")
        
        self._activated_at = None
        self._call_count = 0


# Singleton
_degraded_agent: Optional[DegradedModeAgent] = None


def get_degraded_agent() -> DegradedModeAgent:
    """Retourne l'instance singleton."""
    global _degraded_agent
    if _degraded_agent is None:
        _degraded_agent = DegradedModeAgent()
    return _degraded_agent
