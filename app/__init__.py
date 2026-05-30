"""
Application Body Touch - Interface vocale Mina Body Minute.
"""

from .config import (
    BLEU_PROFOND, ROSE_FUCHSIA, ROSE_CLAIR, BLANC, GRIS_CLAIR,
    COLLECTION_PRODUCTS, END_CONVERSATION_KEYWORDS, is_social_greeting,
    get_seasonal_tip, LLM_CONFIG, TTS_CONFIG, LOG_FILE_PATH
)
from .styles import BODY_TOUCH_CSS, HEADER_HTML, FOOTER_HTML, get_response_html

__all__ = [
    # Colors
    "BLEU_PROFOND", "ROSE_FUCHSIA", "ROSE_CLAIR", "BLANC", "GRIS_CLAIR",
    # Config
    "COLLECTION_PRODUCTS", "END_CONVERSATION_KEYWORDS", "is_social_greeting",
    "get_seasonal_tip", "LLM_CONFIG", "TTS_CONFIG", "LOG_FILE_PATH",
    # Styles
    "BODY_TOUCH_CSS", "HEADER_HTML", "FOOTER_HTML", "get_response_html",
]
