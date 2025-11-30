"""
MINA - Orchestrator
Cerveau décisionnel principal
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from core.brain_manager import BrainManager
from core.memory_manager import MemoryManager
from integrations.base_brain import BaseBrain

logger = logging.getLogger(__name__)


class MinaOrchestrator:
    """
    Orchestrateur principal de Mina
    
    Coordonne Brain Manager et Memory Manager
    Routage intelligent des requêtes
    Orchestration multi-brain si nécessaire
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise l'orchestrateur
        
        Args:
            config: Configuration globale Mina
        """
        self.config = config
        
        # Initialiser les managers
        self.brain_manager = BrainManager(config.get('brain_manager', {}))
        self.memory_manager = MemoryManager(config.get('memory_manager', {}))
        
        self._initialized = False
        self._stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_response_time': 0.0
        }
        
        logger.info("MinaOrchestrator initialized")
    
    async def initialize(self) -> bool:
        """
        Initialise tous les composants
        
        Returns:
            True si succès, False sinon
        """
        try:
            logger.info("Initializing Mina Orchestrator...")
            
            # Initialiser mémoire
            if not await self.memory_manager.initialize():
                logger.error("Memory Manager initialization failed")
                return False
            
            # Charger brain par défaut
            default_brain = self.config.get('brain_manager', {}).get('default_brain', 'claude')
            await self.brain_manager.load_brain(default_brain)
            
            self._initialized = True
            logger.info("Mina Orchestrator ready ✓")
            return True
            
        except Exception as e:
            logger.error(f"Orchestrator initialization failed: {e}")
            return False
    
    async def process(
        self,
        query: str,
        user_id: Optional[str] = None,
        brain_name: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Traite une requête utilisateur
        
        Args:
            query: Requête utilisateur
            user_id: Identifiant utilisateur
            brain_name: Brain spécifique à utiliser (None = auto)
            options: Options additionnelles
        
        Returns:
            Réponse structurée
        """
        start_time = datetime.now()
        self._stats['total_queries'] += 1
        
        try:
            logger.info(f"Processing query: '{query[:50]}...'")
            
            # 1. Recherche contexte dans mémoire
            memory_context = await self._get_memory_context(query, options)
            
            # 2. Sélection du brain optimal
            selected_brain = await self._select_brain(query, brain_name, options)
            
            # 3. Construction du contexte complet
            full_context = self._build_context(
                memory=memory_context,
                user_id=user_id,
                options=options
            )
            
            # 4. Traitement par le brain
            brain = await self.brain_manager.get_brain(selected_brain)
            response = await brain.think(query, full_context)
            
            # 5. Post-processing
            final_response = self._post_process(response, start_time)
            
            self._stats['successful_queries'] += 1
            
            return final_response
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            self._stats['failed_queries'] += 1
            
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
    
    async def multi_brain_process(
        self,
        query: str,
        brains: List[str],
        mode: str = 'sequential'
    ) -> Dict[str, Any]:
        """
        Traite une requête avec plusieurs cerveaux
        
        Args:
            query: Requête utilisateur
            brains: Liste des brains à utiliser
            mode: 'sequential' | 'parallel' | 'cascade'
        
        Returns:
            Réponse fusionnée
        """
        try:
            logger.info(f"Multi-brain processing with {len(brains)} brains ({mode})")
            
            if mode == 'parallel':
                return await self._parallel_process(query, brains)
            elif mode == 'cascade':
                return await self._cascade_process(query, brains)
            else:  # sequential
                return await self._sequential_process(query, brains)
                
        except Exception as e:
            logger.error(f"Multi-brain processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_memory_context(
        self, 
        query: str, 
        options: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Récupère le contexte pertinent de la mémoire
        
        Args:
            query: Requête
            options: Options de recherche
        
        Returns:
            Liste de résultats pertinents
        """
        try:
            limit = options.get('memory_limit', 5) if options else 5
            threshold = options.get('memory_threshold', 0.7) if options else 0.7
            
            results = await self.memory_manager.search(
                query=query,
                limit=limit,
                score_threshold=threshold
            )
            
            logger.info(f"Found {len(results)} relevant memory items")
            return results
            
        except Exception as e:
            logger.error(f"Memory context retrieval failed: {e}")
            return []
    
    async def _select_brain(
        self,
        query: str,
        brain_name: Optional[str],
        options: Optional[Dict[str, Any]]
    ) -> str:
        """
        Sélectionne le brain optimal
        
        Args:
            query: Requête
            brain_name: Brain spécifié (prioritaire)
            options: Options additionnelles
        
        Returns:
            Nom du brain à utiliser
        """
        if brain_name:
            return brain_name
        
        # Auto-sélection basée sur les capacités requises
        required_caps = options.get('required_capabilities') if options else None
        
        return await self.brain_manager.select_best_brain(query, required_caps)
    
    def _build_context(
        self,
        memory: List[Dict[str, Any]],
        user_id: Optional[str],
        options: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Construit le contexte complet pour le brain
        
        Args:
            memory: Résultats mémoire
            user_id: ID utilisateur
            options: Options additionnelles
        
        Returns:
            Contexte structuré
        """
        return {
            'memory': memory,
            'user_id': user_id,
            'history': options.get('history', []) if options else [],
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'options': options or {}
            }
        }
    
    def _post_process(
        self,
        response: Dict[str, Any],
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Post-traitement de la réponse
        
        Args:
            response: Réponse brute du brain
            start_time: Timestamp début traitement
        
        Returns:
            Réponse enrichie
        """
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Mise à jour stats
        self._update_stats(processing_time)
        
        # Enrichissement réponse
        response['success'] = True
        response['total_processing_time'] = processing_time
        response['timestamp'] = datetime.now().isoformat()
        
        return response
    
    async def _parallel_process(
        self,
        query: str,
        brains: List[str]
    ) -> Dict[str, Any]:
        """Traitement parallèle par plusieurs brains"""
        tasks = []
        for brain_name in brains:
            brain = await self.brain_manager.get_brain(brain_name)
            task = brain.think(query, {})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Fusion des résultats
        return {
            'mode': 'parallel',
            'brains': brains,
            'results': [r if not isinstance(r, Exception) else {'error': str(r)} for r in results]
        }
    
    async def _sequential_process(
        self,
        query: str,
        brains: List[str]
    ) -> Dict[str, Any]:
        """Traitement séquentiel par plusieurs brains"""
        results = []
        current_query = query
        
        for brain_name in brains:
            brain = await self.brain_manager.get_brain(brain_name)
            result = await brain.think(current_query, {})
            results.append(result)
            
            # Utiliser la réponse comme input du suivant
            current_query = result.get('response', current_query)
        
        return {
            'mode': 'sequential',
            'brains': brains,
            'results': results,
            'final_response': results[-1] if results else None
        }
    
    async def _cascade_process(
        self,
        query: str,
        brains: List[str]
    ) -> Dict[str, Any]:
        """Traitement en cascade (analyse puis synthèse)"""
        # Premier brain: analyse
        analyzer = await self.brain_manager.get_brain(brains[0])
        analysis = await analyzer.analyze(query)
        
        # Autres brains: traitement basé sur l'analyse
        results = [analysis]
        for brain_name in brains[1:]:
            brain = await self.brain_manager.get_brain(brain_name)
            result = await brain.think(query, {'analysis': analysis})
            results.append(result)
        
        return {
            'mode': 'cascade',
            'brains': brains,
            'analysis': analysis,
            'results': results
        }
    
    def _update_stats(self, processing_time: float):
        """Met à jour les statistiques"""
        n = self._stats['successful_queries']
        current_avg = self._stats['avg_response_time']
        
        # Moyenne glissante
        self._stats['avg_response_time'] = (current_avg * (n - 1) + processing_time) / n
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques
        
        Returns:
            Statistiques d'utilisation
        """
        return {
            **self._stats,
            'brain_stats': self.brain_manager.get_stats(),
            'memory_stats': asyncio.run(self.memory_manager.get_stats()),
            'initialized': self._initialized
        }
    
    async def shutdown(self):
        """Arrêt propre"""
        logger.info("Shutting down Mina Orchestrator...")
        await self.brain_manager.shutdown()
        logger.info("Mina Orchestrator shutdown complete")
    
    def __repr__(self) -> str:
        return f"<MinaOrchestrator(initialized={self._initialized}, queries={self._stats['total_queries']})>"
