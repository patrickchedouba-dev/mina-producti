// MINA Tablet Application
// Gestion reconnaissance vocale et interaction API

// Configuration
const CONFIG = {
    // IMPORTANT: Remplacer par l'URL de ton serveur déployé
    API_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000'
        : 'https://mina-api.onrender.com', // À ajuster avec ta vraie URL
    
    VOICE_LANG: 'fr-FR',
    SYNTHESIS_LANG: 'fr-FR',
    AUTO_STOP_TIMEOUT: 2000  // Stop après 2s de silence
};

// État application
const state = {
    isListening: false,
    recognition: null,
    synthesis: null,
    silenceTimer: null
};

// Éléments DOM
const elements = {
    bodyTouch: document.getElementById('bodyTouch'),
    finger: document.getElementById('finger'),
    status: document.getElementById('status'),
    loading: document.getElementById('loading'),
    responseArea: document.getElementById('responseArea'),
    responseText: document.getElementById('responseText')
};

// Initialisation
function init() {
    console.log('🚀 Initializing MINA...');
    
    // Vérifier support vocal
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('⚠️ Votre navigateur ne supporte pas la reconnaissance vocale. Utilisez Chrome.');
        return;
    }
    
    // Initialiser reconnaissance vocale
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    state.recognition = new SpeechRecognition();
    state.recognition.lang = CONFIG.VOICE_LANG;
    state.recognition.continuous = true;
    state.recognition.interimResults = true;
    
    // Initialiser synthèse vocale
    state.synthesis = window.speechSynthesis;
    
    // Events reconnaissance vocale
    state.recognition.onstart = handleRecognitionStart;
    state.recognition.onresult = handleRecognitionResult;
    state.recognition.onerror = handleRecognitionError;
    state.recognition.onend = handleRecognitionEnd;
    
    // Event Body Touch
    elements.bodyTouch.addEventListener('click', toggleListening);
    
    console.log('✅ MINA ready');
    updateStatus('✅ Prêt à vous écouter');
}

// Toggle écoute
function toggleListening() {
    if (state.isListening) {
        stopListening();
    } else {
        startListening();
    }
}

// Démarrer écoute
function startListening() {
    console.log('🎤 Starting listening...');
    
    try {
        state.recognition.start();
        state.isListening = true;
        
        elements.bodyTouch.classList.add('listening');
        elements.finger.style.display = 'none';
        updateStatus('🎤 Je vous écoute...');
        hideResponse();
        
    } catch (error) {
        console.error('Start listening error:', error);
        updateStatus('❌ Erreur micro');
    }
}

// Arrêter écoute
function stopListening() {
    console.log('🛑 Stopping listening...');
    
    if (state.recognition) {
        state.recognition.stop();
    }
    
    state.isListening = false;
    elements.bodyTouch.classList.remove('listening');
    elements.finger.style.display = 'block';
    
    clearTimeout(state.silenceTimer);
}

// Handler: Reconnaissance démarrée
function handleRecognitionStart() {
    console.log('Recognition started');
}

// Handler: Résultat reconnaissance
function handleRecognitionResult(event) {
    const result = event.results[event.results.length - 1];
    const transcript = result[0].transcript.trim();
    
    console.log('Transcript:', transcript, '| Final:', result.isFinal);
    
    // Reset timer silence
    clearTimeout(state.silenceTimer);
    
    if (result.isFinal) {
        // Résultat final: envoyer à Mina
        console.log('✅ Final transcript:', transcript);
        stopListening();
        processQuery(transcript);
    } else {
        // Résultat intermédiaire: afficher et timer
        updateStatus(`🎤 "${transcript}"`);
        
        // Auto-stop après silence
        state.silenceTimer = setTimeout(() => {
            if (state.isListening) {
                console.log('Auto-stop after silence');
                state.recognition.stop();
            }
        }, CONFIG.AUTO_STOP_TIMEOUT);
    }
}

// Handler: Erreur reconnaissance
function handleRecognitionError(event) {
    console.error('Recognition error:', event.error);
    
    state.isListening = false;
    elements.bodyTouch.classList.remove('listening');
    
    let message = '❌ Erreur micro';
    
    switch(event.error) {
        case 'no-speech':
            message = '🤷 Je n\'ai rien entendu';
            break;
        case 'network':
            message = '📡 Erreur réseau';
            break;
        case 'not-allowed':
            message = '🚫 Micro non autorisé';
            break;
    }
    
    updateStatus(message);
    
    setTimeout(() => {
        updateStatus('👆 Touchez pour réessayer');
        elements.finger.style.display = 'block';
    }, 2000);
}

// Handler: Reconnaissance terminée
function handleRecognitionEnd() {
    console.log('Recognition ended');
    state.isListening = false;
    elements.bodyTouch.classList.remove('listening');
}

// Traiter requête Mina
async function processQuery(query) {
    console.log('📤 Sending query to Mina:', query);
    
    updateStatus('🤔 Je réfléchis...');
    showLoading();
    hideResponse();
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                user_id: 'tablet_' + Date.now()
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📥 Mina response:', data);
        
        hideLoading();
        
        if (data.success && data.response) {
            displayResponse(data.response);
            speakResponse(data.response);
        } else {
            updateStatus('❌ Erreur: ' + (data.error || 'Réponse invalide'));
        }
        
    } catch (error) {
        console.error('Query processing error:', error);
        hideLoading();
        updateStatus('❌ Erreur de connexion');
        
        // Fallback message
        setTimeout(() => {
            updateStatus('👆 Touchez pour réessayer');
            elements.finger.style.display = 'block';
        }, 2000);
    }
}

// Afficher réponse
function displayResponse(text) {
    elements.responseText.textContent = text;
    elements.responseArea.classList.add('visible');
    updateStatus('💬 Voici ma réponse');
}

// Lire réponse vocalement
function speakResponse(text) {
    if (!state.synthesis) return;
    
    // Annuler toute lecture en cours
    state.synthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = CONFIG.SYNTHESIS_LANG;
    utterance.rate = 0.9;  // Légèrement plus lent pour clarté
    utterance.pitch = 1.0;
    
    utterance.onend = () => {
        console.log('Speech finished');
        setTimeout(() => {
            updateStatus('👆 Nouvelle question ?');
            elements.finger.style.display = 'block';
        }, 1000);
    };
    
    utterance.onerror = (error) => {
        console.error('Speech synthesis error:', error);
    };
    
    state.synthesis.speak(utterance);
}

// UI helpers
function updateStatus(text) {
    elements.status.textContent = text;
}

function showLoading() {
    elements.loading.classList.add('visible');
}

function hideLoading() {
    elements.loading.classList.remove('visible');
}

function hideResponse() {
    elements.responseArea.classList.remove('visible');
}

// Wake lock (empêcher mise en veille)
let wakeLock = null;

async function requestWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
            console.log('Wake Lock active');
        }
    } catch (err) {
        console.error('Wake Lock error:', err);
    }
}

// Lancer au chargement
document.addEventListener('DOMContentLoaded', () => {
    init();
    requestWakeLock();
});

// Réactiver Wake Lock si page redevient visible
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && wakeLock === null) {
        requestWakeLock();
    }
});
