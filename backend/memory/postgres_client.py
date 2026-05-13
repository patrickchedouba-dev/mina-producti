"""
Client PostgreSQL pour mémoire long terme Mina.

Stocke l'historique des conversations et les profils clients.
Fallback gracieux si PostgreSQL indisponible.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PostgresClient:
    """
    Client PostgreSQL pour historique et profils clients.
    
    Tables:
    - conversations: historique complet des sessions
    - client_profiles: préférences et données client
    """
    
    def __init__(self, postgres_url: Optional[str] = None):
        """
        Initialise le client PostgreSQL.
        
        Args:
            postgres_url: URL PostgreSQL (postgresql://user:pass@host:port/db)
        """
        self.postgres_url = postgres_url or os.getenv(
            "POSTGRES_URL", 
            "postgresql://mina:mina@localhost:5432/mina"
        )
        self._pool = None
        self._connected = False
        self._fallback_conversations: Dict[str, Dict] = {}
        self._fallback_profiles: Dict[str, Dict] = {}
        self._connect()
    
    def _connect(self):
        """Tente la connexion à PostgreSQL."""
        try:
            import psycopg2
            from psycopg2 import pool
            
            self._pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=self.postgres_url
            )
            self._connected = True
            logger.info(f"✅ PostgreSQL connecté")
            self._init_schema()
        except ImportError:
            logger.warning("⚠️ Module psycopg2 non installé, fallback in-memory activé")
            self._connected = False
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL indisponible ({e}), fallback in-memory activé")
            self._connected = False
    
    @contextmanager
    def _get_cursor(self):
        """Context manager pour obtenir un curseur."""
        conn = None
        try:
            conn = self._pool.getconn()
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self._pool.putconn(conn)
    
    def _init_schema(self):
        """Initialise le schéma de base de données."""
        if not self._connected:
            return
        
        try:
            with self._get_cursor() as cursor:
                # Table conversations
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(64) NOT NULL,
                        client_id VARCHAR(64),
                        turns JSONB NOT NULL DEFAULT '[]',
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
                    CREATE INDEX IF NOT EXISTS idx_conv_client ON conversations(client_id);
                """)
                
                # Table profils clients
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS client_profiles (
                        client_id VARCHAR(64) PRIMARY KEY,
                        preferences JSONB DEFAULT '{}',
                        skin_type VARCHAR(32),
                        last_products JSONB DEFAULT '[]',
                        visit_count INTEGER DEFAULT 0,
                        last_visit TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                logger.info("✅ Schéma PostgreSQL initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation schéma: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Vérifie si PostgreSQL est disponible."""
        return self._connected
    
    def save_conversation(
        self, 
        session_id: str, 
        turns: List[Dict],
        client_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Sauvegarde une conversation complète.
        
        Args:
            session_id: Identifiant de session
            turns: Liste des tours de conversation
            client_id: Identifiant client optionnel
            metadata: Métadonnées additionnelles
            
        Returns:
            True si sauvegardé avec succès
        """
        if self._connected:
            try:
                with self._get_cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO conversations (session_id, client_id, turns, metadata, updated_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (session_id) DO UPDATE
                        SET turns = EXCLUDED.turns,
                            client_id = COALESCE(EXCLUDED.client_id, conversations.client_id),
                            metadata = conversations.metadata || EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        session_id,
                        client_id,
                        json.dumps(turns, ensure_ascii=False),
                        json.dumps(metadata or {}, ensure_ascii=False)
                    ))
                logger.debug(f"💾 Conversation {session_id[:8]}... sauvegardée")
                return True
            except Exception as e:
                logger.error(f"❌ Erreur sauvegarde conversation: {e}")
                return False
        else:
            # Fallback in-memory
            self._fallback_conversations[session_id] = {
                "turns": turns,
                "client_id": client_id,
                "metadata": metadata or {},
                "updated_at": datetime.now().isoformat()
            }
            return True
    
    def get_client_history(
        self, 
        client_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """
        Récupère l'historique des conversations d'un client.
        
        Args:
            client_id: Identifiant client
            limit: Nombre max de conversations
            
        Returns:
            Liste des conversations (plus récentes en premier)
        """
        if self._connected:
            try:
                with self._get_cursor() as cursor:
                    cursor.execute("""
                        SELECT session_id, turns, metadata, created_at
                        FROM conversations
                        WHERE client_id = %s
                        ORDER BY updated_at DESC
                        LIMIT %s
                    """, (client_id, limit))
                    
                    results = []
                    for row in cursor.fetchall():
                        results.append({
                            "session_id": row[0],
                            "turns": row[1] if isinstance(row[1], list) else json.loads(row[1]),
                            "metadata": row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}"),
                            "created_at": row[3].isoformat() if row[3] else None
                        })
                    return results
            except Exception as e:
                logger.error(f"❌ Erreur récupération historique: {e}")
                return []
        else:
            # Fallback
            return [
                {"session_id": k, **v}
                for k, v in self._fallback_conversations.items()
                if v.get("client_id") == client_id
            ][:limit]
    
    def get_client_profile(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le profil d'un client.
        
        Args:
            client_id: Identifiant client
            
        Returns:
            Profil client ou None
        """
        if self._connected:
            try:
                with self._get_cursor() as cursor:
                    cursor.execute("""
                        SELECT preferences, skin_type, last_products, visit_count, last_visit
                        FROM client_profiles
                        WHERE client_id = %s
                    """, (client_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            "client_id": client_id,
                            "preferences": row[0] if isinstance(row[0], dict) else json.loads(row[0] or "{}"),
                            "skin_type": row[1],
                            "last_products": row[2] if isinstance(row[2], list) else json.loads(row[2] or "[]"),
                            "visit_count": row[3] or 0,
                            "last_visit": row[4].isoformat() if row[4] else None
                        }
                    return None
            except Exception as e:
                logger.error(f"❌ Erreur récupération profil: {e}")
                return None
        else:
            return self._fallback_profiles.get(client_id)
    
    def update_client_profile(
        self, 
        client_id: str, 
        preferences: Optional[Dict] = None,
        skin_type: Optional[str] = None,
        last_products: Optional[List] = None
    ) -> bool:
        """
        Met à jour le profil d'un client.
        
        Args:
            client_id: Identifiant client
            preferences: Nouvelles préférences
            skin_type: Type de peau
            last_products: Derniers produits consultés
            
        Returns:
            True si mis à jour avec succès
        """
        if self._connected:
            try:
                with self._get_cursor() as cursor:
                    # Upsert avec COALESCE pour ne pas écraser les valeurs non fournies
                    cursor.execute("""
                        INSERT INTO client_profiles (client_id, preferences, skin_type, last_products, visit_count, last_visit, updated_at)
                        VALUES (%s, %s, %s, %s, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (client_id) DO UPDATE
                        SET preferences = COALESCE(%s, client_profiles.preferences) || client_profiles.preferences,
                            skin_type = COALESCE(%s, client_profiles.skin_type),
                            last_products = COALESCE(%s, client_profiles.last_products),
                            visit_count = client_profiles.visit_count + 1,
                            last_visit = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        client_id,
                        json.dumps(preferences or {}, ensure_ascii=False),
                        skin_type,
                        json.dumps(last_products or [], ensure_ascii=False),
                        json.dumps(preferences or {}, ensure_ascii=False) if preferences else None,
                        skin_type,
                        json.dumps(last_products or [], ensure_ascii=False) if last_products else None
                    ))
                logger.debug(f"👤 Profil {client_id[:8]}... mis à jour")
                return True
            except Exception as e:
                logger.error(f"❌ Erreur mise à jour profil: {e}")
                return False
        else:
            # Fallback
            existing = self._fallback_profiles.get(client_id, {})
            self._fallback_profiles[client_id] = {
                "client_id": client_id,
                "preferences": {**existing.get("preferences", {}), **(preferences or {})},
                "skin_type": skin_type or existing.get("skin_type"),
                "last_products": last_products or existing.get("last_products", []),
                "visit_count": existing.get("visit_count", 0) + 1,
                "last_visit": datetime.now().isoformat()
            }
            return True
    
    def close(self):
        """Ferme le pool de connexions."""
        if self._pool:
            self._pool.closeall()
            logger.info("🔌 PostgreSQL déconnecté")


# Singleton
_postgres_client: Optional[PostgresClient] = None


def get_postgres_client() -> PostgresClient:
    """Retourne l'instance singleton du client PostgreSQL."""
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgresClient()
    return _postgres_client
