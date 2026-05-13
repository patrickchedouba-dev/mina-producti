"""
Système de mémoire unifié pour Mina.

Combine les 3 niveaux de mémoire:
- Court terme (Redis): session courante
- Long terme (PostgreSQL): historique et profils
- Sémantique (Qdrant): recherche par similarité

Usage:
    from backend.memory import get_memory_system
    memory = get_memory_system()
    memory.store_interaction(session_id, client_id, user_msg, assistant_msg)
    context = memory.get_unified_context(client_id)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

from .redis_client import get_redis_client, RedisMemoryClient
from .postgres_client import get_postgres_client, PostgresClient

logger = logging.getLogger(__name__)


@dataclass
class UnifiedContext:
    """Contexte unifié pour le LLM."""
    
    # Session courante
    current_session_id: str = ""
    recent_turns: List[Dict] = field(default_factory=list)
    
    # Profil client
    client_id: Optional[str] = None
    client_profile: Optional[Dict] = None
    
    # Historique long terme
    past_conversations_summary: str = ""
    
    # Pour prompt injection
    def to_prompt_context(self) -> str:
        """Génère le contexte à injecter dans le prompt."""
        parts = []
        
        # Profil client
        if self.client_profile:
            profile_str = []
            if self.client_profile.get("skin_type"):
                profile_str.append(f"Type de peau: {self.client_profile['skin_type']}")
            if self.client_profile.get("preferences"):
                prefs = self.client_profile["preferences"]
                if prefs.get("favorite_products"):
                    profile_str.append(f"Produits préférés: {', '.join(prefs['favorite_products'][:3])}")
            if self.client_profile.get("visit_count", 0) > 1:
                profile_str.append(f"Cliente fidèle ({self.client_profile['visit_count']} visites)")
            
            if profile_str:
                parts.append(f"📋 PROFIL CLIENTE:\n" + "\n".join(profile_str))
        
        # Historique récent
        if self.recent_turns:
            history = []
            for turn in self.recent_turns[-3:]:  # 3 derniers tours max
                history.append(f"Cliente: {turn.get('user', '')[:100]}")
                history.append(f"Mina: {turn.get('assistant', '')[:100]}")
            parts.append(f"💬 CONVERSATION EN COURS:\n" + "\n".join(history))
        
        # Résumé historique
        if self.past_conversations_summary:
            parts.append(f"📚 HISTORIQUE:\n{self.past_conversations_summary}")
        
        return "\n\n".join(parts) if parts else ""


class MemorySystem:
    """
    Interface unifiée pour le système de mémoire multi-niveaux.
    
    Orchestre Redis (court terme), PostgreSQL (long terme) et Qdrant (sémantique).
    """
    
    def __init__(self):
        """Initialise les clients mémoire."""
        self._redis = get_redis_client()
        self._postgres = get_postgres_client()
        self._qdrant = None  # Lazy loading pour éviter import circulaire
        
        logger.info(f"🧠 MemorySystem initialisé (Redis={self._redis.is_connected}, Postgres={self._postgres.is_connected})")
    
    def _get_qdrant(self):
        """Lazy loading du client Qdrant."""
        if self._qdrant is None:
            try:
                from backend.qdrant_client import get_qdrant_client
                self._qdrant = get_qdrant_client()
            except ImportError:
                logger.warning("⚠️ Qdrant client non disponible pour mémoire sémantique")
        return self._qdrant
    
    def store_interaction(
        self,
        session_id: str,
        client_id: Optional[str],
        user_message: str,
        assistant_message: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Stocke une interaction dans tous les niveaux de mémoire.
        
        Args:
            session_id: ID de session unique
            client_id: ID client (optionnel, pour profil)
            user_message: Message de l'utilisateur
            assistant_message: Réponse de Mina
            metadata: Données additionnelles (produits mentionnés, etc.)
            
        Returns:
            True si stocké avec succès
        """
        timestamp = datetime.now().isoformat()
        
        # 1. Redis - Session courante (court terme)
        redis_ok = self._redis.add_turn_to_session(
            session_id, 
            user_message, 
            assistant_message
        )
        
        # Mettre à jour client_id dans la session si fourni
        if client_id:
            session_data = self._redis.get_session(session_id) or {}
            session_data["client_id"] = client_id
            self._redis.store_session(session_id, session_data)
        
        # 2. PostgreSQL - Historique (long terme)
        # On récupère tous les turns de Redis pour sauvegarder la session complète
        recent_turns = self._redis.get_recent_turns(session_id, limit=50)
        postgres_ok = self._postgres.save_conversation(
            session_id=session_id,
            turns=recent_turns,
            client_id=client_id,
            metadata=metadata
        )
        
        # 3. Mise à jour profil client si applicable
        if client_id and metadata:
            # Extraire les produits mentionnés pour le profil
            products = metadata.get("products_mentioned", [])
            if products:
                self._postgres.update_client_profile(
                    client_id=client_id,
                    last_products=products[:5]  # Garder les 5 derniers
                )
        
        logger.debug(f"💾 Interaction stockée: Redis={redis_ok}, Postgres={postgres_ok}")
        return redis_ok and postgres_ok
    
    def get_unified_context(
        self, 
        session_id: str,
        client_id: Optional[str] = None
    ) -> UnifiedContext:
        """
        Récupère le contexte unifié pour le LLM.
        
        Combine:
        - Session courante (Redis)
        - Profil client (PostgreSQL)
        - Historique résumé (PostgreSQL)
        
        Args:
            session_id: ID de session
            client_id: ID client optionnel
            
        Returns:
            UnifiedContext avec toutes les données
        """
        context = UnifiedContext(current_session_id=session_id)
        
        # 1. Session courante depuis Redis
        context.recent_turns = self._redis.get_recent_turns(session_id, limit=5)
        
        # Récupérer client_id depuis session si pas fourni
        if not client_id:
            session_data = self._redis.get_session(session_id)
            if session_data:
                client_id = session_data.get("client_id")
        
        context.client_id = client_id
        
        # 2. Profil client depuis PostgreSQL
        if client_id:
            context.client_profile = self._postgres.get_client_profile(client_id)
            
            # 3. Résumé historique (dernières 5 conversations)
            history = self._postgres.get_client_history(client_id, limit=5)
            if history:
                # Créer un résumé des sujets abordés
                topics = []
                for conv in history:
                    for turn in conv.get("turns", [])[:2]:  # Premiers tours seulement
                        user_msg = turn.get("user", "")[:50]
                        if user_msg:
                            topics.append(user_msg)
                
                if topics:
                    context.past_conversations_summary = f"Sujets précédents: {'; '.join(topics[:5])}"
        
        return context
    
    def get_client_profile(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le profil complet d'un client.
        
        Args:
            client_id: Identifiant client
            
        Returns:
            Profil client ou None
        """
        return self._postgres.get_client_profile(client_id)
    
    def update_client_profile(
        self,
        client_id: str,
        skin_type: Optional[str] = None,
        preferences: Optional[Dict] = None
    ) -> bool:
        """
        Met à jour les informations client.
        
        Args:
            client_id: Identifiant client
            skin_type: Type de peau (grasse, sèche, mixte, normale)
            preferences: Dict de préférences
            
        Returns:
            True si mis à jour
        """
        return self._postgres.update_client_profile(
            client_id=client_id,
            skin_type=skin_type,
            preferences=preferences
        )
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Raccourci pour récupérer une session Redis."""
        return self._redis.get_session(session_id)
    
    def search_semantic_memory(
        self, 
        query: str, 
        client_id: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict]:
        """
        Recherche sémantique dans l'historique.
        
        Args:
            query: Texte de recherche
            client_id: Filtrer par client (optionnel)
            limit: Nombre de résultats
            
        Returns:
            Liste de résultats pertinents
        """
        qdrant = self._get_qdrant()
        if not qdrant:
            return []
        
        # TODO: Implémenter recherche dans collection conversations
        # Pour l'instant, utiliser la collection existante
        try:
            results = qdrant.search_similar(
                query=query,
                collection="bodyminute_docs",
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"❌ Erreur recherche sémantique: {e}")
            return []


# Singleton
_memory_system: Optional[MemorySystem] = None


def get_memory_system() -> MemorySystem:
    """Retourne l'instance singleton du système de mémoire."""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem()
    return _memory_system
