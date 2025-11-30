"""
MINA - Claude Brain Implementation
Implémentation du cerveau Claude pour Mina
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
import os
import anthropic

from integrations.base_brain import BaseBrain, BrainError

logger = logging.getLogger(__name__)


class ClaudeBrain(BaseBrain):
    """
    Implémentation Claude Sonnet 4.5 pour Mina
    
    Utilise l'API Anthropic pour traiter les requêtes
    avec contexte mémoire Qdrant intégré
    """
    
    CAPABILITIES = [
        'text_generation',
        'analysis',
        'reasoning',
        'french',
        'body_minute_expertise'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise Claude Brain
        
        Args:
            config: {
                'api_key': str,
                'model': str,
                'max_tokens': int,
                'temperature': float
            }
        """
        super().__init__(config)
        
        self.api_key = config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        self.model = config.get('model', 'claude-sonnet-4-20250514')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 1.0)
        
        if not self.api_key:
            raise BrainError("ANTHROPIC_API_KEY not provided")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        logger.info(f"ClaudeBrain initialized with model {self.model}")
    
    async def think(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une requête avec Claude
        
        Args:
            query: Question utilisateur
            context: {
                'memory': List[Dict] - Résultats Qdrant,
                'user_id': str,
                'history': List[Dict],
                'metadata': Dict
            }
        
        Returns:
            Réponse structurée de Claude
        """
        start_time = datetime.now()
        
        try:
            # Construction du prompt avec contexte mémoire
            system_prompt = self._build_system_prompt()
            user_message = self._build_user_message(query, context)
            
            logger.info(f"Sending query to Claude: '{query[:50]}...'")
            
            # Appel API Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Extraction réponse
            answer = response.content[0].text
            
            # Extraction sources depuis contexte mémoire
            sources = [
                item.get('source', 'unknown')
                for item in context.get('memory', [])
            ]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'response': answer,
                'confidence': self._calculate_confidence(context.get('memory', [])),
                'sources': list(set(sources)),
                'metadata': {
                    'model': self.model,
                    'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
                    'memory_items_used': len(context.get('memory', []))
                },
                'processing_time': processing_time
            }
            
            logger.info(f"Claude response generated in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Claude think() failed: {e}")
            raise BrainError(f"Claude processing failed: {e}")
    
    async def analyze(self, data: Any) -> Dict[str, Any]:
        """
        Analyse des données avec Claude
        
        Args:
            data: Données à analyser (texte, structure)
        
        Returns:
            Analyse détaillée
        """
        try:
            analysis_prompt = f"""Analyse les données suivantes et fournis:
1. Une synthèse claire
2. Les insights principaux
3. Des recommandations actionnables

Données à analyser:
{data}

Format ta réponse en JSON avec les clés: synthesis, insights, recommendations"""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": analysis_prompt}
                ]
            )
            
            answer = response.content[0].text
            
            return {
                'analysis': answer,
                'insights': [],  # TODO: Parser JSON response
                'recommendations': [],
                'confidence': 0.85
            }
            
        except Exception as e:
            logger.error(f"Claude analyze() failed: {e}")
            raise BrainError(f"Analysis failed: {e}")
    
    def get_capabilities(self) -> List[str]:
        """Liste des capacités de Claude"""
        return self.CAPABILITIES.copy()
    
    async def health_check(self) -> bool:
        """
        Vérifie que l'API Claude est accessible
        
        Returns:
            True si OK, False sinon
        """
        try:
            # Test simple avec requête minimale
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "test"}
                ]
            )
            
            self._last_health_check = datetime.now()
            logger.info("Claude health check: OK")
            return True
            
        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
            return False
    
    def _build_system_prompt(self) -> str:
        """
        Construit le prompt système pour Claude
        
        Returns:
            Prompt système optimisé Body Minute
        """
        return """Tu es MINA, l'assistant IA expert de Body Minute.

CONTEXTE:
Body Minute est un réseau de 450+ instituts de beauté en France et Suisse.
Tu connais parfaitement tous les produits, soins, protocoles et procédures Body Minute.

TON RÔLE:
- Répondre aux questions des esthéticiennes sur les produits, soins, protocoles
- Fournir des informations précises basées sur la documentation officielle Body Minute
- Être concise, claire, et professionnelle
- Toujours citer tes sources quand tu utilises la documentation

RÈGLES:
- Si l'information est dans le contexte mémoire fourni, utilise-la en priorité
- Si tu n'es pas certaine, dis-le clairement
- Reste dans le périmètre Body Minute (produits, soins, procédures)
- Réponds en français professionnel et accessible

FORMAT:
- Réponses courtes et directes (2-3 phrases max sauf si détails demandés)
- Structure claire si liste d'informations
- Ton amical mais professionnel"""
    
    def _build_user_message(self, query: str, context: Dict[str, Any]) -> str:
        """
        Construit le message utilisateur avec contexte
        
        Args:
            query: Question utilisateur
            context: Contexte complet
        
        Returns:
            Message formaté pour Claude
        """
        message_parts = []
        
        # Contexte mémoire
        memory = context.get('memory', [])
        if memory:
            message_parts.append("CONTEXTE PERTINENT (Documentation Body Minute):")
            for i, item in enumerate(memory, 1):
                content = item.get('content', '')
                source = item.get('source', 'unknown')
                score = item.get('score', 0)
                message_parts.append(f"\n[Source {i}: {source} | Pertinence: {score:.2f}]")
                message_parts.append(content)
            message_parts.append("\n---")
        
        # Question utilisateur
        message_parts.append(f"\nQUESTION: {query}")
        
        # Instructions finales
        message_parts.append("\nRéponds en utilisant prioritairement le contexte fourni ci-dessus.")
        
        return "\n".join(message_parts)
    
    def _calculate_confidence(self, memory_items: List[Dict[str, Any]]) -> float:
        """
        Calcule un score de confiance basé sur la qualité du contexte mémoire
        
        Args:
            memory_items: Items de mémoire utilisés
        
        Returns:
            Score de confiance 0-1
        """
        if not memory_items:
            return 0.5  # Confiance moyenne sans contexte
        
        # Moyenne des scores de pertinence
        scores = [item.get('score', 0) for item in memory_items]
        avg_score = sum(scores) / len(scores) if scores else 0.5
        
        # Bonus si plusieurs sources convergent
        num_sources = len(memory_items)
        source_bonus = min(num_sources * 0.05, 0.2)
        
        confidence = min(avg_score + source_bonus, 1.0)
        
        return round(confidence, 2)


# Enregistrement automatique du brain
from core.brain_manager import BrainManager
BrainManager.register_brain('claude', ClaudeBrain)

logger.info("ClaudeBrain registered successfully")
