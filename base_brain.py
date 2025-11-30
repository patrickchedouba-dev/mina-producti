"""
MINA - Base Brain Interface
Toutes les IAs intégrées doivent implémenter cette interface
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseBrain(ABC):
    """
    Interface commune à tous les cerveaux IA de Mina
    
    Chaque IA (Claude, ChatGPT, Gemini, Perplexity) implémente cette classe
    pour garantir cohérence et interopérabilité
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialisation du cerveau
        
        Args:
            config: Configuration spécifique à l'IA
        """
        self.config = config
        self.name = config.get('name', 'Unknown Brain')
        self.version = config.get('version', '1.0.0')
        self._initialized = False
        self._last_health_check = None
        
        logger.info(f"Initializing {self.name} v{self.version}")
    
    @abstractmethod
    async def think(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une requête avec contexte
        
        Args:
            query: Question/requête utilisateur
            context: {
                'memory': données Qdrant pertinentes,
                'history': historique conversation,
                'metadata': métadonnées additionnelles,
                'user_id': identifiant utilisateur
            }
        
        Returns:
            {
                'response': str,              # Réponse générée
                'confidence': float,          # 0-1, confiance dans la réponse
                'sources': List[str],         # Sources utilisées
                'metadata': Dict[str, Any],   # Métadonnées additionnelles
                'processing_time': float      # Temps de traitement en secondes
            }
        """
        pass
    
    @abstractmethod
    async def analyze(self, data: Any) -> Dict[str, Any]:
        """
        Analyse des données (texte, code, image selon capacités)
        
        Args:
            data: Données à analyser
        
        Returns:
            {
                'analysis': Dict[str, Any],        # Résultats analyse
                'insights': List[str],             # Insights clés
                'recommendations': List[str],      # Recommandations
                'confidence': float                # Confiance globale
            }
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Liste des capacités du cerveau
        
        Returns:
            ['text_generation', 'code', 'vision', 'analysis', ...]
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Vérifie que le cerveau est opérationnel
        
        Returns:
            True si opérationnel, False sinon
        """
        pass
    
    # Méthodes communes (non-abstract)
    
    def is_capable_of(self, capability: str) -> bool:
        """
        Vérifie si le cerveau possède une capacité
        
        Args:
            capability: Capacité à vérifier
        
        Returns:
            True si capable, False sinon
        """
        return capability in self.get_capabilities()
    
    async def warm_up(self) -> bool:
        """
        Pré-charge le cerveau (optionnel)
        
        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"Warming up {self.name}")
            result = await self.health_check()
            self._initialized = result
            self._last_health_check = datetime.now()
            return result
        except Exception as e:
            logger.error(f"Warm-up failed for {self.name}: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        Retourne les informations du cerveau
        
        Returns:
            Dictionnaire avec infos du brain
        """
        return {
            'name': self.name,
            'version': self.version,
            'capabilities': self.get_capabilities(),
            'initialized': self._initialized,
            'last_health_check': self._last_health_check.isoformat() if self._last_health_check else None
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', version='{self.version}')>"


class BrainError(Exception):
    """Exception de base pour les erreurs de cerveau"""
    pass


class BrainNotAvailableError(BrainError):
    """Levée quand un cerveau n'est pas disponible"""
    pass


class BrainTimeoutError(BrainError):
    """Levée quand un cerveau timeout"""
    pass


class BrainConfigError(BrainError):
    """Levée quand la configuration est invalide"""
    pass
