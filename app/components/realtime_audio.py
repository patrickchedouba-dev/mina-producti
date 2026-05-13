#!/usr/bin/env python3
"""
Realtime Audio Component pour Streamlit - Architecture Temps Réel

Ce composant intègre :
- Capture audio via MediaRecorder API (navigateur)
- Communication WebSocket avec Gemini Live
- Playback audio streaming
- Support barge-in (interruption)

Usage dans Streamlit:
    from app.components.realtime_audio import realtime_voice_chat
    realtime_voice_chat(rag_provider=my_rag_function)
"""

import os
import asyncio
import base64
import json
import logging
from typing import Optional, Callable
import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

SAMPLE_RATE = 16000  # 16kHz pour Gemini Live
CHUNK_DURATION_MS = 100  # Envoyer audio toutes les 100ms

# =============================================================================
# COMPOSANT HTML/JS POUR AUDIO TEMPS RÉEL
# =============================================================================

REALTIME_AUDIO_HTML = """
<!DOCTYPE html>
<html>
<head>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', sans-serif;
        }
        
        .realtime-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 20px;
            min-height: 200px;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
            color: #fff;
            font-size: 14px;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #666;
            transition: background 0.3s;
        }
        
        .status-dot.connecting { background: #f39c12; animation: pulse 1s infinite; }
        .status-dot.connected { background: #27ae60; }
        .status-dot.speaking { background: #e91e63; animation: pulse 0.5s infinite; }
        .status-dot.listening { background: #3498db; animation: pulse 1s infinite; }
        .status-dot.error { background: #e74c3c; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(1.2); }
        }
        
        .mic-button {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(145deg, #e91e63, #c2185b);
            color: white;
            font-size: 40px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 8px 25px rgba(233, 30, 99, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 0 12px 35px rgba(233, 30, 99, 0.5);
        }
        
        .mic-button.active {
            background: linear-gradient(145deg, #27ae60, #1e8449);
            box-shadow: 0 8px 25px rgba(39, 174, 96, 0.4);
            animation: pulse-ring 1.5s infinite;
        }
        
        @keyframes pulse-ring {
            0% { box-shadow: 0 0 0 0 rgba(39, 174, 96, 0.7); }
            70% { box-shadow: 0 0 0 20px rgba(39, 174, 96, 0); }
            100% { box-shadow: 0 0 0 0 rgba(39, 174, 96, 0); }
        }
        
        .transcript {
            margin-top: 20px;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            color: #fff;
            font-size: 14px;
            min-height: 60px;
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        
        .transcript.user { border-left: 3px solid #3498db; }
        .transcript.mina { border-left: 3px solid #e91e63; }
        
        .visualizer {
            display: flex;
            gap: 4px;
            height: 40px;
            align-items: center;
            margin: 15px 0;
        }
        
        .visualizer-bar {
            width: 6px;
            background: #e91e63;
            border-radius: 3px;
            transition: height 0.1s;
        }
    </style>
</head>
<body>
    <div class="realtime-container" id="container">
        <div class="status-indicator">
            <div class="status-dot" id="statusDot"></div>
            <span id="statusText">Prêt à parler</span>
        </div>
        
        <div class="visualizer" id="visualizer">
            <!-- Barres générées dynamiquement -->
        </div>
        
        <button class="mic-button" id="micButton" onclick="toggleRecording()">
            🎤
        </button>
        
        <div class="transcript" id="transcript">
            <em>Appuie sur le micro pour parler à Mina</em>
        </div>
    </div>
    
    <audio id="audioPlayer" style="display:none;"></audio>
    
    <script>
        // Configuration
        const WS_URL = 'WEBSOCKET_URL_PLACEHOLDER';
        const SAMPLE_RATE = 16000;
        
        // État
        let isRecording = false;
        let mediaRecorder = null;
        let audioContext = null;
        let analyser = null;
        let websocket = null;
        let audioQueue = [];
        let isPlaying = false;
        
        // Éléments DOM
        const micButton = document.getElementById('micButton');
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const transcript = document.getElementById('transcript');
        const visualizer = document.getElementById('visualizer');
        const audioPlayer = document.getElementById('audioPlayer');
        
        // Initialiser visualiseur
        for (let i = 0; i < 15; i++) {
            const bar = document.createElement('div');
            bar.className = 'visualizer-bar';
            bar.style.height = '5px';
            visualizer.appendChild(bar);
        }
        
        function setStatus(status, text) {
            statusDot.className = 'status-dot ' + status;
            statusText.textContent = text;
        }
        
        function updateVisualizer(dataArray) {
            const bars = visualizer.querySelectorAll('.visualizer-bar');
            const step = Math.floor(dataArray.length / bars.length);
            bars.forEach((bar, i) => {
                const value = dataArray[i * step] || 0;
                const height = Math.max(5, (value / 255) * 40);
                bar.style.height = height + 'px';
            });
        }
        
        async function toggleRecording() {
            if (isRecording) {
                stopRecording();
            } else {
                await startRecording();
            }
        }
        
        async function startRecording() {
            try {
                setStatus('connecting', 'Connexion...');
                
                // Demander accès micro
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        sampleRate: SAMPLE_RATE,
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true
                    }
                });
                
                // Créer contexte audio pour visualisation
                audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
                analyser = audioContext.createAnalyser();
                const source = audioContext.createMediaStreamSource(stream);
                source.connect(analyser);
                analyser.fftSize = 256;
                
                // MediaRecorder pour capture
                mediaRecorder = new MediaRecorder(stream, {
                    mimeType: 'audio/webm;codecs=opus'
                });
                
                mediaRecorder.ondataavailable = async (event) => {
                    if (event.data.size > 0 && websocket?.readyState === WebSocket.OPEN) {
                        // Convertir en base64 et envoyer
                        const reader = new FileReader();
                        reader.onload = () => {
                            const base64 = reader.result.split(',')[1];
                            // Envoyer à Streamlit via postMessage
                            window.parent.postMessage({
                                type: 'audio_chunk',
                                data: base64
                            }, '*');
                        };
                        reader.readAsDataURL(event.data);
                    }
                };
                
                // Démarrer enregistrement
                mediaRecorder.start(100); // Chunk toutes les 100ms
                isRecording = true;
                micButton.classList.add('active');
                micButton.textContent = '🛑';
                setStatus('listening', "J'écoute...");
                
                // Animation visualiseur
                animateVisualizer();
                
                // Notifier Streamlit
                window.parent.postMessage({ type: 'recording_started' }, '*');
                
            } catch (error) {
                console.error('Erreur micro:', error);
                setStatus('error', 'Erreur micro: ' + error.message);
            }
        }
        
        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
            
            isRecording = false;
            micButton.classList.remove('active');
            micButton.textContent = '🎤';
            setStatus('connected', 'Mina répond...');
            
            // Notifier Streamlit
            window.parent.postMessage({ type: 'recording_stopped' }, '*');
        }
        
        function animateVisualizer() {
            if (!isRecording || !analyser) return;
            
            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            analyser.getByteFrequencyData(dataArray);
            updateVisualizer(dataArray);
            
            requestAnimationFrame(animateVisualizer);
        }
        
        // Recevoir audio de Mina
        window.addEventListener('message', (event) => {
            if (event.data.type === 'play_audio') {
                playAudioChunk(event.data.data);
            } else if (event.data.type === 'transcript') {
                showTranscript(event.data.text, event.data.speaker);
            } else if (event.data.type === 'status') {
                setStatus(event.data.status, event.data.text);
            }
        });
        
        async function playAudioChunk(base64Audio) {
            try {
                const audioData = atob(base64Audio);
                const arrayBuffer = new ArrayBuffer(audioData.length);
                const view = new Uint8Array(arrayBuffer);
                for (let i = 0; i < audioData.length; i++) {
                    view[i] = audioData.charCodeAt(i);
                }
                
                // Décoder et jouer
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);
                source.start();
                
            } catch (error) {
                console.error('Erreur playback:', error);
            }
        }
        
        function showTranscript(text, speaker) {
            transcript.className = 'transcript ' + speaker;
            transcript.innerHTML = (speaker === 'user' ? '🗣️ ' : '💆 ') + text;
        }
        
        // Barge-in: interrompre Mina si l'utilisateur parle
        function handleBargeIn() {
            if (isPlaying) {
                audioPlayer.pause();
                audioQueue = [];
                isPlaying = false;
                window.parent.postMessage({ type: 'barge_in' }, '*');
            }
        }
    </script>
</body>
</html>
"""

# =============================================================================
# COMPOSANT STREAMLIT
# =============================================================================

def realtime_voice_chat(
    rag_provider: Optional[Callable[[str], str]] = None,
    height: int = 350,
    key: str = "realtime_audio"
) -> Optional[dict]:
    """
    Composant Streamlit pour chat vocal temps réel avec Gemini Live.
    
    Args:
        rag_provider: Fonction pour obtenir contexte RAG (query -> context)
        height: Hauteur du composant en pixels
        key: Clé unique pour le composant
        
    Returns:
        Dict avec dernière interaction ou None
    """
    
    # Initialiser session state
    if 'realtime_session' not in st.session_state:
        st.session_state.realtime_session = None
    if 'realtime_transcript' not in st.session_state:
        st.session_state.realtime_transcript = []
    
    # Afficher le composant HTML
    component_html = REALTIME_AUDIO_HTML
    
    # Rendu du composant
    components.html(
        component_html,
        height=height,
        scrolling=False
    )
    
    # Instructions
    st.caption("💡 Appuie sur le micro, parle, puis relâche. Mina répondra en temps réel.")
    
    return None


def create_realtime_page():
    """
    Page Streamlit complète pour le mode temps réel.
    À intégrer dans app_chatbot.py.
    """
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #e91e63;">🎙️ Mode Conversation Temps Réel</h2>
        <p style="color: #888;">Parlez naturellement, Mina répond instantanément</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Composant audio
    realtime_voice_chat()
    
    # Historique
    if st.session_state.get('realtime_transcript'):
        st.markdown("### 📝 Historique")
        for entry in st.session_state.realtime_transcript[-5:]:
            icon = "🗣️" if entry['speaker'] == 'user' else "💆"
            st.markdown(f"{icon} **{entry['speaker'].capitalize()}:** {entry['text']}")


# =============================================================================
# BACKEND HANDLER (pour WebSocket)
# =============================================================================

class RealtimeSessionHandler:
    """
    Gère une session temps réel complète.
    Connecte le composant UI au client Gemini Live.
    """
    
    def __init__(self, rag_provider: Optional[Callable[[str], str]] = None):
        self.rag_provider = rag_provider
        self.client = None
        self.is_active = False
    
    async def start_session(self):
        """Démarre une session Gemini Live."""
        from backend.realtime_client import GeminiLiveClient, create_rag_provider
        
        self.client = GeminiLiveClient(rag_provider=self.rag_provider)
        success = await self.client.connect()
        
        if success:
            self.is_active = True
            logger.info("✅ Session temps réel démarrée")
        
        return success
    
    async def process_audio(self, audio_chunk: bytes) -> bytes:
        """
        Traite un chunk audio et retourne la réponse.
        
        Args:
            audio_chunk: Audio PCM de l'utilisateur
            
        Returns:
            Audio PCM de la réponse Mina
        """
        if not self.client or not self.is_active:
            return b''
        
        # Envoyer audio
        await self.client.send_audio(audio_chunk)
        
        # Collecter réponse
        response_audio = b''
        async for response in self.client.receive_responses():
            if response['type'] == 'audio':
                response_audio += response['data']
            elif response['type'] == 'interrupted':
                break
        
        return response_audio
    
    async def end_session(self):
        """Termine la session."""
        if self.client:
            await self.client.disconnect()
        self.is_active = False


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    # Test en mode standalone
    st.set_page_config(page_title="Mina Realtime Test", page_icon="🎙️")
    create_realtime_page()
