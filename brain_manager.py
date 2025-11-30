"""
MINA - Brain Manager
Gestion du cycle de vie des cerveaux IA
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from integrations.base_brain import BaseBrain, BrainNotAvailableError

logger = logging.getLogger(__name__)


class BrainManager:
    """
    Gestionnaire de cerveaux IA
    
    Charge, initialise, switche entre les différents brains
    Maintient le health monitoring et les métriques
    """
    
    # Registry des brains disponibles (sera peuplé dynamiquement)
    AVAILABLE_BRAINS: Dict[str, type] = {}
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le gestionnaire de cerveaux
        
        Args:
            config: Configuration globale des brains
        """
        self.config = config
        self.active_brains: Dict[str, BaseBrain] = {}
        self.brain_configs: Dict[str, Dict[str, Any]] = config.get('brains', {})
        self.default_brain: Optional[str] = config.get('default_brain', 'claude')
        self.health_check_interval = config.get('health_check_interval', 300)  # 5 min
        self._last_health_check: Dict[str, datetime] = {}
        
        logger.info(f"BrainManager initialized with {len(self.AVAILABLE_BRAINS)} available brains")
    
    async def load_brain(self, brain_name: str) -> BaseBrain:
        """
        Charge et initialise un cerveau
        
        Args:
            brain_name: Nom du cerveau à charger
        
        Returns:
            Instance du brain chargé
        
        Raises:
            BrainNotAvailableError: Si le brain n'existe pas
        """
        try:
            # Vérifier si déjà chargé
            if brain_name in self.active_brains:
                logger.info(f"Brain '{brain_name}' already loaded")
                return self.active_brains[brain_name]
            
            # Vérifier disponibilité
            if brain_name not in self.AVAILABLE_BRAINS:
                raise BrainNotAvailableError(f"Brain '{brain_name}' not registered")
            
            # Récupérer config
            brain_config = self.brain_configs.get(brain_name, {})
            
            # Instancier le brain
            brain_class = self.AVAILABLE_BRAINS[brain_name]
            brain = brain_class(brain_config)
            
            # Warm-up
            if await brain.warm_up():
                self.active_brains[brain_name] = brain
                self._last_health_check[brain_name] = datetime.now()
                logger.info(f"Brain '{brain_name}' loaded and ready")
                return brain
            else:
                raise BrainNotAvailableError(f"Brain '{brain_name}' warm-up failed")
                
        except Exception as e:
            logger.error(f"Failed to load brain '{brain_name}': {e}")
            raise
    
    async def get_brain(self, brain_name: Optional[str] = None) -> BaseBrain:
        """
        Récupère un cerveau (charge si nécessaire)
        
        Args:
            brain_name: Nom du cerveau (None = default)
        
        Returns:
            Instance du brain
        """
        name = brain_name or self.default_brain
        
        if name not in self.active_brains:
            await self.load_brain(name)
        
        return self.active_brains[name]
    
    async def switch_brain(self, from_brain: str, to_brain: str) -> bool:
        """
        Switche d'un cerveau à un autre
        
        Args:
            from_brain: Cerveau actuel
            to_brain: Cerveau cible
        
        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"Switching brain: {from_brain} → {to_brain}")
            
            # Charger le nouveau brain si nécessaire
            await self.load_brain(to_brain)
            
            # Optionnel: décharger l'ancien brain si non utilisé
            # (pour l'instant on garde tous les brains en mémoire)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch brain: {e}")
            return False
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        Health check de tous les brains actifs
        
        Returns:
            Dictionnaire {brain_name: is_healthy}
        """
        results = {}
        
        for name, brain in self.active_brains.items():
            try:
                is_healthy = await brain.health_check()
                results[name] = is_healthy
                self._last_health_check[name] = datetime.now()
                
                if not is_healthy:
                    logger.warning(f"Brain '{name}' health check failed")
                    
            except Exception as e:
                logger.error(f"Health check error for '{name}': {e}")
                results[name] = False
        
        return results
    
    async def select_best_brain(
        self, 
        query: str, 
        required_capabilities: Optional[List[str]] = None
    ) -> str:
        """
        Sélectionne le meilleur cerveau pour une requête
        
        Args:
            query: Requête à traiter
            required_capabilities: Capacités requises
        
        Returns:
            Nom du brain optimal
        """
        # TODO: Implémenter logique de sélection intelligente
        # - Analyser la requête
        # - Vérifier les capacités
        # - Considérer la charge et performance
        
        # Pour l'instant: retour du brain par défaut
        if required_capabilities:
            for name, brain in self.active_brains.items():
                if all(brain.is_capable_of(cap) for cap in required_capabilities):
                    return name
        
        return self.default_brain
    
    def get_all_capabilities(self) -> Dict[str, List[str]]:
        """
        Liste toutes les capacités disponibles
        
        Returns:
            Dictionnaire {brain_name: [capabilities]}
        """
        return {
            name: brain.get_capabilities()
            for name, brain in self.active_brains.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Statistiques des brains
        
        Returns:
            Dictionnaire avec statistiques
        """
        return {
            'available_brains': list(self.AVAILABLE_BRAINS.keys()),
            'active_brains': list(self.active_brains.keys()),
            'default_brain': self.default_brain,
            'total_registered': len(self.AVAILABLE_BRAINS),
            'total_active': len(self.active_brains),
            'last_health_checks': {
                name: check.isoformat() if check else None
                for name, check in self._last_health_check.items()
            }
        }
    
    async def shutdown(self):
        """
        Arrêt propre de tous les brains
        """
        logger.info("Shutting down all brains...")
        
        for name in list(self.active_brains.keys()):
            try:
                # TODO: Implémenter cleanup si nécessaire
                del self.active_brains[name]
                logger.info(f"Brain '{name}' shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down '{name}': {e}")
        
        self.active_brains.clear()
        logger.info("All brains shutdown complete")
    
    @classmethod
    def register_brain(cls, name: str, brain_class: type):
        """
        Enregistre un nouveau type de cerveau
        
        Args:
            name: Nom du brain (ex: 'claude', 'chatgpt')
            brain_class: Classe implémentant BaseBrain
        """
        if not issubclass(brain_class, BaseBrain):
            raise TypeError(f"{brain_class} must inherit from BaseBrain")
        
        cls.AVAILABLE_BRAINS[name] = brain_class
        logger.info(f"Brain '{name}' registered: {brain_class.__name__}")
    
    def __repr__(self) -> str:
        return f"<BrainManager(active={len(self.active_brains)}, available={len(self.AVAILABLE_BRAINS)})>"
