"""
Client Redis pour mémoire court terme Mina.

Gère les sessions conversationnelles avec TTL configurable.
Fallback gracieux si Redis indisponible (mode in-memory).
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# TTL par défaut: 30 minutes
DEFAULT_SESSION_TTL = 1800


class RedisMemoryClient:
    """
    Client Redis pour cache de sessions conversationnelles.
    
    Features:
    - Stockage sessions avec TTL
    - Cache conversations en cours
    - Fallback in-memory si Redis indisponible
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialise le client Redis.
        
        Args:
            redis_url: URL Redis (redis://host:port/db)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._fallback_store: Dict[str, Dict] = {}  # In-memory fallback
        self._connected = False
        self._connect()
    
    def _connect(self):
        """Tente la connexion à Redis."""
        try:
            import redis
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test de connexion
            self._client.ping()
            self._connected = True
            logger.info(f"✅ Redis connecté: {self.redis_url.split('@')[-1]}")
        except ImportError:
            logger.warning("⚠️ Module redis non installé, fallback in-memory activé")
            self._connected = False
        except Exception as e:
            logger.warning(f"⚠️ Redis indisponible ({e}), fallback in-memory activé")
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Vérifie si Redis est disponible."""
        return self._connected
    
    def store_session(
        self, 
        session_id: str, 
        data: Dict[str, Any],
        ttl: int = DEFAULT_SESSION_TTL
    ) -> bool:
        """
        Stocke les données de session.
        
        Args:
            session_id: Identifiant unique de session
            data: Données à stocker (dict)
            ttl: Time-to-live en secondes
            
        Returns:
            True si stocké avec succès
        """
        key = f"mina:session:{session_id}"
        
        try:
            if self._connected and self._client:
                self._client.setex(key, ttl, json.dumps(data, ensure_ascii=False))
                logger.debug(f"📝 Session {session_id[:8]}... stockée (TTL={ttl}s)")
                return True
            else:
                # Fallback in-memory
                self._fallback_store[key] = {
                    "data": data,
                    "expires": datetime.now().timestamp() + ttl
                }
                return True
        except Exception as e:
            logger.error(f"❌ Erreur stockage session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les données de session.
        
        Args:
            session_id: Identifiant de session
            
        Returns:
            Données de session ou None si expirée/inexistante
        """
        key = f"mina:session:{session_id}"
        
        try:
            if self._connected and self._client:
                data = self._client.get(key)
                if data:
                    return json.loads(data)
                return None
            else:
                # Fallback in-memory
                entry = self._fallback_store.get(key)
                if entry:
                    if datetime.now().timestamp() < entry["expires"]:
                        return entry["data"]
                    else:
                        del self._fallback_store[key]
                return None
        except Exception as e:
            logger.error(f"❌ Erreur récupération session: {e}")
            return None
    
    def extend_ttl(self, session_id: str, ttl: int = DEFAULT_SESSION_TTL) -> bool:
        """
        Prolonge le TTL d'une session.
        
        Args:
            session_id: Identifiant de session
            ttl: Nouveau TTL en secondes
            
        Returns:
            True si prolongé avec succès
        """
        key = f"mina:session:{session_id}"
        
        try:
            if self._connected and self._client:
                return self._client.expire(key, ttl)
            else:
                entry = self._fallback_store.get(key)
                if entry:
                    entry["expires"] = datetime.now().timestamp() + ttl
                    return True
                return False
        except Exception as e:
            logger.error(f"❌ Erreur extension TTL: {e}")
            return False
    
    def add_turn_to_session(
        self, 
        session_id: str, 
        user_message: str, 
        assistant_message: str
    ) -> bool:
        """
        Ajoute un tour de conversation à la session.
        
        Args:
            session_id: Identifiant de session
            user_message: Message utilisateur
            assistant_message: Réponse de Mina
            
        Returns:
            True si ajouté avec succès
        """
        session_data = self.get_session(session_id) or {
            "turns": [],
            "created_at": datetime.now().isoformat(),
            "client_id": None
        }
        
        session_data["turns"].append({
            "user": user_message,
            "assistant": assistant_message,
            "timestamp": datetime.now().isoformat()
        })
        session_data["updated_at"] = datetime.now().isoformat()
        
        # Limiter à 20 derniers tours en mémoire court terme
        if len(session_data["turns"]) > 20:
            session_data["turns"] = session_data["turns"][-20:]
        
        return self.store_session(session_id, session_data)
    
    def get_recent_turns(self, session_id: str, limit: int = 5) -> List[Dict]:
        """
        Récupère les derniers tours de conversation.
        
        Args:
            session_id: Identifiant de session
            limit: Nombre max de tours
            
        Returns:
            Liste des derniers tours
        """
        session_data = self.get_session(session_id)
        if session_data and "turns" in session_data:
            return session_data["turns"][-limit:]
        return []
    
    def delete_session(self, session_id: str) -> bool:
        """Supprime une session."""
        key = f"mina:session:{session_id}"
        
        try:
            if self._connected and self._client:
                return self._client.delete(key) > 0
            else:
                if key in self._fallback_store:
                    del self._fallback_store[key]
                    return True
                return False
        except Exception as e:
            logger.error(f"❌ Erreur suppression session: {e}")
            return False


# Singleton
_redis_client: Optional[RedisMemoryClient] = None


def get_redis_client() -> RedisMemoryClient:
    """Retourne l'instance singleton du client Redis."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisMemoryClient()
    return _redis_client
