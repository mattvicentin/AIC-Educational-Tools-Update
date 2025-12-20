"""
Card View Segmentation Module

Transforms long AI messages into structured, digestible card segments
for progressive disclosure and collaborative exploration.

Usage:
    from src.utils.card_view import segment_message, Segment
    
    segments = segment_message(long_ai_response)
    for seg in segments:
        print(f"{seg.header}: {seg.body[:50]}...")

AI-Enhanced Usage:
    from src.utils.card_view import segment_message, enhance_segments_with_ai
    
    segments = segment_message(message)
    ai_data = enhance_segments_with_ai(message, segments)
    # ai_data contains: guiding_question, relationships, ai_enhanced
"""

from .schemas import Segment
from .segmenter import segment_message
from .ai_helpers import (
    enhance_segments_with_ai,
    generate_guiding_question,
    generate_relationship_hints,
)

__all__ = [
    "segment_message",
    "Segment",
    "enhance_segments_with_ai",
    "generate_guiding_question",
    "generate_relationship_hints",
]
