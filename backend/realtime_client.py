#!/usr/bin/env python3
"""
Gemini Live API Client - Architecture Temps Réel Hybride

Ce module gère la connexion WebSocket bidirectionnelle avec Gemini Live API
tout en conservant l'accès au RAG Qdrant pour les données métier.

Architecture:
    Audio Client <--> WebSocket <--> Gemini Live <--> RAG Context
"""

import os
import asyncio
import logging
from typing import Optional, AsyncGenerator, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Google Generative AI
try:
    from google import genai
    from google.genai import types
    HAS_GENAI_LIVE = True
except ImportError:
    HAS_GENAI_LIVE = False

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class ConnectionState(Enum):
    """États de la connexion WebSocket."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class RealtimeConfig:
    """Configuration du client temps réel."""
    model: str = "gemini-2.0-flash-exp"
    voice: str = "Kore"  # Voix Gemini (Puck, Charon, Kore, Fenrir, Aoede)
    language: str = "fr"
    
    # Audio settings
    sample_rate_input: int = 16000  # 16kHz pour input
    sample_rate_output: int = 24000  # 24kHz pour output
    
    # Timeouts
    connection_timeout: float = 10.0
    response_timeout: float = 30.0
    
    # RAG Integration
    enable_rag_context: bool = True
    rag_collection: str = "bodyminute_docs"


# System prompt pour Mina avec contexte RAG
MINA_REALTIME_SYSTEM_PROMPT = """Tu es Mina, conseillère vocale experte Body Minute.

PERSONNALITÉ:
- Chaleureuse, professionnelle, tutoyante
- Réponses courtes (2-3 phrases max pour la voix)
- Toujours basée sur les DONNÉES MÉTIER fournies

RÈGLES STRICTES:
1. Pour les produits et prix → Utilise UNIQUEMENT les données du contexte RAG
2. Pour les protocoles → Cite les étapes exactes de la documentation
3. Si l'info n'est pas dans le contexte → Dis "je vais vérifier" et ne pas inventer

CONTEXTE RAG ACTUEL:
{rag_context}

Réponds de façon naturelle et fluide pour la synthèse vocale."""


# =============================================================================
# CLIENT GEMINI LIVE
# =============================================================================

class GeminiLiveClient:
    """
    Client WebSocket pour Gemini Live API avec intégration RAG.
    
    Gère:
    - Connexion/reconnexion WebSocket
    - Streaming audio bidirectionnel
    - Barge-in (interruption utilisateur)
    - Injection de contexte RAG
    """
    
    def __init__(
        self,
        config: Optional[RealtimeConfig] = None,
        rag_provider: Optional[Callable[[str], str]] = None
    ):
        """
        Initialise le client.
        
        Args:
            config: Configuration du client
            rag_provider: Fonction pour obtenir le contexte RAG
        """
        self.config = config or RealtimeConfig()
        self.rag_provider = rag_provider
        
        self.session = None
        self.state = ConnectionState.DISCONNECTED
        self.is_speaking = False  # Mina parle actuellement
        self.is_interrupted = False  # Barge-in détecté
        
        # Callbacks
        self._on_audio_callback: Optional[Callable[[bytes], None]] = None
        self._on_text_callback: Optional[Callable[[str], None]] = None
        self._on_state_change: Optional[Callable[[ConnectionState], None]] = None
        
        # Vérifier disponibilité
        if not HAS_GENAI_LIVE:
            logger.error("google-genai package not installed or outdated")
            raise ImportError("pip install google-genai>=0.8.0")
    
    def _set_state(self, state: ConnectionState):
        """Met à jour l'état et notifie."""
        self.state = state
        logger.info(f"🔌 État connexion: {state.value}")
        if self._on_state_change:
            self._on_state_change(state)
    
    async def connect(self, initial_context: str = "") -> bool:
        """
        Établit la connexion WebSocket avec Gemini Live.
        
        Args:
            initial_context: Contexte RAG initial
            
        Returns:
            True si connecté avec succès
        """
        try:
            self._set_state(ConnectionState.CONNECTING)
            
            # Configurer le client
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set")
            
            self._client = genai.Client(api_key=api_key)
            
            # Préparer le system prompt avec contexte RAG
            system_prompt = MINA_REALTIME_SYSTEM_PROMPT.format(
                rag_context=initial_context or "Aucun contexte spécifique."
            )
            
            # Configuration de la session
            self._config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.config.voice
                        )
                    )
                ),
                system_instruction=system_prompt
            )
            
            # Le context manager doit être stocké pour rester ouvert
            self._session_cm = self._client.aio.live.connect(
                model=self.config.model,
                config=self._config
            )
            
            # Entrer dans le context manager
            self.session = await self._session_cm.__aenter__()
            
            self._set_state(ConnectionState.CONNECTED)
            logger.info(f"✅ Connecté à Gemini Live ({self.config.model})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion Gemini Live: {e}")
            self._set_state(ConnectionState.ERROR)
            return False
    
    async def disconnect(self):
        """Ferme proprement la connexion."""
        if self._session_cm:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Erreur fermeture session: {e}")
            finally:
                self.session = None
                self._session_cm = None
                self._set_state(ConnectionState.DISCONNECTED)
    
    async def send_audio(self, audio_chunk: bytes):
        """
        Envoie un chunk audio vers Gemini.
        
        Args:
            audio_chunk: Données audio PCM 16-bit
        """
        if not self.session or self.state != ConnectionState.CONNECTED:
            logger.warning("Session non connectée, audio ignoré")
            return
        
        try:
            await self.session.send(
                input={"data": audio_chunk, "mime_type": "audio/pcm"}
            )
        except Exception as e:
            logger.error(f"Erreur envoi audio: {e}")
            self._set_state(ConnectionState.ERROR)
    
    async def send_text(self, text: str):
        """
        Envoie du texte vers Gemini (pour injection RAG).
        
        Args:
            text: Texte à envoyer
        """
        if not self.session or self.state != ConnectionState.CONNECTED:
            return
        
        try:
            await self.session.send(input=text, end_of_turn=True)
        except Exception as e:
            logger.error(f"Erreur envoi texte: {e}")
    
    async def inject_rag_context(self, query: str):
        """
        Injecte le contexte RAG basé sur la requête.
        
        Args:
            query: Requête utilisateur pour recherche RAG
        """
        if not self.rag_provider or not self.config.enable_rag_context:
            return
        
        try:
            context = self.rag_provider(query)
            if context:
                # Envoyer le contexte comme instruction système
                await self.send_text(f"[CONTEXTE RAG ACTUALISÉ]\n{context}")
                logger.info(f"📚 Contexte RAG injecté ({len(context)} chars)")
        except Exception as e:
            logger.error(f"Erreur injection RAG: {e}")
    
    async def receive_responses(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Reçoit les réponses en streaming.
        
        Yields:
            Dict avec 'type' (audio/text/interrupted) et 'data'
        """
        if not self.session:
            return
        
        try:
            self.is_speaking = True
            
            async for response in self.session.receive():
                # Vérifier interruption (barge-in)
                if hasattr(response, 'server_content') and response.server_content:
                    if hasattr(response.server_content, 'interrupted') and response.server_content.interrupted:
                        self.is_interrupted = True
                        self.is_speaking = False
                        logger.info("🛑 Barge-in détecté - interruption")
                        yield {"type": "interrupted", "data": None}
                        break
                    
                    # Extraire audio/texte
                    if hasattr(response.server_content, 'model_turn'):
                        for part in response.server_content.model_turn.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                yield {
                                    "type": "audio",
                                    "data": part.inline_data.data,
                                    "mime_type": getattr(part.inline_data, 'mime_type', 'audio/pcm')
                                }
                            elif hasattr(part, 'text') and part.text:
                                yield {"type": "text", "data": part.text}
            
            self.is_speaking = False
            
        except Exception as e:
            logger.error(f"Erreur réception: {e}")
            self.is_speaking = False
            yield {"type": "error", "data": str(e)}
    
    def on_audio(self, callback: Callable[[bytes], None]):
        """Enregistre callback pour audio reçu."""
        self._on_audio_callback = callback
    
    def on_text(self, callback: Callable[[str], None]):
        """Enregistre callback pour texte reçu."""
        self._on_text_callback = callback
    
    def on_state_change(self, callback: Callable[[ConnectionState], None]):
        """Enregistre callback pour changement d'état."""
        self._on_state_change = callback


# =============================================================================
# INTÉGRATION RAG
# =============================================================================

def create_rag_provider(qdrant_client, embedding_func, collection: str = "bodyminute_docs"):
    """
    Crée un provider RAG compatible avec GeminiLiveClient.
    
    Args:
        qdrant_client: Client Qdrant
        embedding_func: Fonction pour générer embeddings
        collection: Nom de la collection
        
    Returns:
        Fonction (query: str) -> str
    """
    def get_rag_context(query: str) -> str:
        try:
            # Générer embedding
            query_vector = embedding_func(query)
            
            # Rechercher dans Qdrant
            results = qdrant_client.query_points(
                collection_name=collection,
                query=list(query_vector),
                limit=3,
                with_payload=True
            )
            
            # Construire contexte
            if not results.points:
                return ""
            
            context_parts = []
            for hit in results.points[:3]:
                text = hit.payload.get("text", "")[:500]
                doc_type = hit.payload.get("doc_type", "général")
                context_parts.append(f"[{doc_type}] {text}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Erreur RAG: {e}")
            return ""
    
    return get_rag_context


# =============================================================================
# FACTORY ET HELPERS
# =============================================================================

async def create_realtime_session(
    rag_client=None,
    embedding_func=None,
    initial_query: str = ""
) -> GeminiLiveClient:
    """
    Factory pour créer une session Gemini Live avec RAG.
    
    Args:
        rag_client: Client Qdrant (optionnel)
        embedding_func: Fonction embedding (optionnel)
        initial_query: Requête initiale pour contexte
        
    Returns:
        Client connecté
    """
    # Créer provider RAG si disponible
    rag_provider = None
    if rag_client and embedding_func:
        rag_provider = create_rag_provider(rag_client, embedding_func)
    
    # Créer client
    client = GeminiLiveClient(rag_provider=rag_provider)
    
    # Obtenir contexte initial
    initial_context = ""
    if rag_provider and initial_query:
        initial_context = rag_provider(initial_query)
    
    # Connecter
    success = await client.connect(initial_context)
    if not success:
        raise ConnectionError("Impossible de se connecter à Gemini Live")
    
    return client


# =============================================================================
# TEST STANDALONE
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from dotenv import load_dotenv
    load_dotenv()
    
    async def test_connection():
        """Test basique de connexion."""
        print("🧪 Test connexion Gemini Live API...")
        
        try:
            client = GeminiLiveClient()
            success = await client.connect("Test de connexion Mina.")
            
            if success:
                print("✅ Connexion réussie!")
                
                # Envoyer un texte de test
                await client.send_text("Bonjour, je suis Mina. Comment puis-je t'aider ?")
                
                # Recevoir réponse
                async for response in client.receive_responses():
                    print(f"📨 Réponse: {response['type']} - {len(response.get('data', b''))} bytes")
                    if response['type'] == 'text':
                        print(f"   Texte: {response['data']}")
                    break  # Juste le premier pour le test
                
                await client.disconnect()
                print("✅ Test terminé avec succès!")
            else:
                print("❌ Échec connexion")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(test_connection())
