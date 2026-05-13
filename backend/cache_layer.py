"""
Cache Layer pour Mina V2.

Optimisations:
- Cache réponses fréquentes (TTL 1h)
- Cache contexte client (TTL 5min)
- Compression prompts
"""

import re
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Patterns cacheable (questions génériques)
CACHEABLE_PATTERNS = [
    r"horaire|ouvert|ferme",
    r"service|prestation",
    r"tarif|prix|coût",
    r"où|adresse|localisation",
    r"comment|qu'est.ce",
    r"^bonjour|^salut|^coucou|^hello|^hey",
    r"merci|au revoir|à bientôt",
]


class ResponseCache:
    """Cache réponses pour queries fréquentes."""
    
    def __init__(self, redis_client=None, ttl: int = 3600):
        self._redis = redis_client
        self._ttl = ttl
        self._local_cache: Dict[str, Any] = {}  # Fallback si Redis indispo
        self._stats = {"hits": 0, "misses": 0}
    
    def _get_cache_key(self, user_input: str, institut_id: Optional[str] = None) -> str:
        """Génère clé cache basée sur input normalisé."""
        normalized = user_input.lower().strip()
        cache_input = f"{normalized}|{institut_id or 'global'}"
        return f"mina:resp:{hashlib.md5(cache_input.encode()).hexdigest()[:16]}"
    
    def get(self, user_input: str, institut_id: Optional[str] = None) -> Optional[Dict]:
        """Récupère réponse cachée si existe."""
        key = self._get_cache_key(user_input, institut_id)
        
        # Try Redis first
        if self._redis:
            try:
                cached = self._redis.get(key)
                if cached:
                    self._stats["hits"] += 1
                    logger.info(f"🎯 Cache HIT: {key[:20]}...")
                    return json.loads(cached)
            except Exception as e:
                logger.debug(f"Redis get error: {e}")
        
        # Fallback local cache
        if key in self._local_cache:
            entry = self._local_cache[key]
            if entry["expires"] > datetime.now().timestamp():
                self._stats["hits"] += 1
                logger.info(f"🎯 Local cache HIT: {key[:20]}...")
                return entry["data"]
        
        self._stats["misses"] += 1
        return None
    
    def set(self, user_input: str, response: Dict, institut_id: Optional[str] = None):
        """Cache réponse si cacheable."""
        if not self._is_cacheable(user_input):
            return
        
        key = self._get_cache_key(user_input, institut_id)
        data = json.dumps(response, ensure_ascii=False)
        
        # Try Redis
        if self._redis:
            try:
                self._redis.setex(key, self._ttl, data)
                logger.debug(f"📦 Cached to Redis: {key[:20]}...")
                return
            except Exception as e:
                logger.debug(f"Redis set error: {e}")
        
        # Fallback local cache
        self._local_cache[key] = {
            "data": response,
            "expires": datetime.now().timestamp() + self._ttl
        }
        logger.debug(f"📦 Cached locally: {key[:20]}...")
    
    def _is_cacheable(self, user_input: str) -> bool:
        """Détermine si query peut être cachée."""
        input_lower = user_input.lower()
        return any(re.search(p, input_lower) for p in CACHEABLE_PATTERNS)
    
    @property
    def hit_rate(self) -> float:
        """Taux de cache hit."""
        total = self._stats["hits"] + self._stats["misses"]
        return self._stats["hits"] / total if total > 0 else 0.0


class ContextCache:
    """Cache contexte client (TTL court)."""
    
    def __init__(self, redis_client=None, ttl: int = 300):
        self._redis = redis_client
        self._ttl = ttl
        self._local_cache: Dict[str, Any] = {}
    
    def _get_key(self, client_id: str, institut_id: Optional[str] = None) -> str:
        return f"mina:ctx:{client_id}:{institut_id or 'none'}"
    
    def get(self, client_id: str, institut_id: Optional[str] = None) -> Optional[str]:
        """Récupère contexte caché."""
        if not client_id:
            return None
        
        key = self._get_key(client_id, institut_id)
        
        if self._redis:
            try:
                cached = self._redis.get(key)
                if cached:
                    logger.debug(f"🧠 Context cache HIT: {client_id[:8]}...")
                    return cached.decode() if isinstance(cached, bytes) else cached
            except:
                pass
        
        if key in self._local_cache:
            entry = self._local_cache[key]
            if entry["expires"] > datetime.now().timestamp():
                return entry["data"]
        
        return None
    
    def set(self, client_id: str, context: str, institut_id: Optional[str] = None):
        """Cache contexte."""
        if not client_id:
            return
        
        key = self._get_key(client_id, institut_id)
        
        if self._redis:
            try:
                self._redis.setex(key, self._ttl, context)
                return
            except:
                pass
        
        self._local_cache[key] = {
            "data": context,
            "expires": datetime.now().timestamp() + self._ttl
        }


def compress_prompt(prompt: str) -> str:
    """Compresse un prompt en retirant éléments superflus."""
    # Retire commentaires XML
    prompt = re.sub(r'<!--.*?-->', '', prompt, flags=re.DOTALL)
    # Retire balises XML (garde contenu)
    prompt = re.sub(r'<[^>]+>', ' ', prompt)
    # Retire espaces multiples
    prompt = re.sub(r'\s+', ' ', prompt)
    # Retire lignes vides
    prompt = re.sub(r'\n\s*\n', '\n', prompt)
    return prompt.strip()


# Singletons
_response_cache: Optional[ResponseCache] = None
_context_cache: Optional[ContextCache] = None


def get_response_cache() -> ResponseCache:
    """Retourne le cache réponses singleton."""
    global _response_cache
    if _response_cache is None:
        # Try to get Redis client
        redis_client = None
        try:
            from backend.memory.redis_client import get_redis_client
            redis_client = get_redis_client()._client
        except:
            pass
        _response_cache = ResponseCache(redis_client)
    return _response_cache


def get_context_cache() -> ContextCache:
    """Retourne le cache contexte singleton."""
    global _context_cache
    if _context_cache is None:
        redis_client = None
        try:
            from backend.memory.redis_client import get_redis_client
            redis_client = get_redis_client()._client
        except:
            pass
        _context_cache = ContextCache(redis_client)
    return _context_cache
