"""
Composants UI et fonctionnels de Body Touch.
"""

from .audio_handler import transcribe_audio, text_to_speech, get_speech_client
from .product_display import (
    find_product_by_name,
    find_product_by_ref,
    get_product_card_html,
    get_product_cards_for_response,
    get_reviews_for_product,
    display_product_in_streamlit,
)

__all__ = [
    # Audio
    "transcribe_audio", 
    "text_to_speech", 
    "get_speech_client",
    # Products
    "find_product_by_name",
    "find_product_by_ref",
    "get_product_card_html",
    "get_product_cards_for_response",
    "get_reviews_for_product",
    "display_product_in_streamlit",
]
