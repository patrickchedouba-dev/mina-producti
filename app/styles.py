#!/usr/bin/env python3
"""
Styles CSS Body Touch - Design visuel de l'application Mina.
"""

from .config import BLEU_PROFOND, ROSE_FUCHSIA, ROSE_CLAIR, BLANC, GRIS_CLAIR

# =============================================================================
# CSS BODY TOUCH - Style premium Body Minute
# =============================================================================

BODY_TOUCH_CSS = f"""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    /* Global */
    .stApp {{
        background: linear-gradient(135deg, {BLEU_PROFOND} 0%, #16213e 100%);
        font-family: 'Poppins', sans-serif;
    }}
    
    /* Hide Streamlit elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* Logo */
    .logo-container {{
        text-align: center;
        margin-bottom: 2rem;
    }}
    
    .logo-text {{
        font-size: 2.5rem;
        font-weight: 700;
        color: {BLANC};
        margin-bottom: 0.5rem;
    }}
    
    .logo-subtitle {{
        font-size: 1rem;
        color: {GRIS_CLAIR};
        letter-spacing: 0.2em;
    }}
    
    /* Response area */
    .response-container {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
        max-width: 600px;
        width: 100%;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    
    .response-text {{
        color: {BLANC};
        font-size: 1.1rem;
        line-height: 1.8;
    }}
    
    .response-title {{
        color: {ROSE_FUCHSIA};
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }}
    
    /* Question display */
    .question-text {{
        color: {ROSE_CLAIR};
        font-style: italic;
        font-size: 1rem;
        margin-bottom: 1rem;
        padding: 0.5rem 1rem;
        border-left: 3px solid {ROSE_FUCHSIA};
    }}
    
    /* Status messages */
    .status-listening {{
        color: {ROSE_FUCHSIA};
        animation: pulse 1.5s infinite;
    }}
    
    @keyframes pulse {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
        100% {{ opacity: 1; }}
    }}
    
    /* Audio styling */
    [data-testid="stAudio"] {{
        max-width: 400px;
        margin: 1rem auto;
    }}
</style>
"""

# =============================================================================
# HTML TEMPLATES
# =============================================================================

HEADER_HTML = """
<div class="logo-container">
    <div class="logo-text">✨ MINA</div>
    <div class="logo-subtitle">VOTRE ASSISTANTE BODY MINUTE</div>
</div>
"""

FOOTER_HTML = """
<div style="text-align: center; color: #666; font-size: 0.8rem;">
    Body Touch by Body Minute • Propulsé par Mina AI
</div>
"""

def get_response_html(question: str, response: str) -> str:
    """Génère le HTML de la réponse formatée."""
    return f"""
    <div class="response-container">
        <div class="question-text">"{question}"</div>
        <div class="response-title">💆 Mina répond :</div>
        <div class="response-text">{response}</div>
    </div>
    """
