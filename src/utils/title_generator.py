"""
AI-powered short title generation for rooms
Creates concise 1-5 word titles from room names and goals
"""

from typing import Optional
from flask import current_app
import re


def generate_short_title(room_name: str, room_goals: Optional[str] = None) -> str:
    """
    Generate a concise 2-4 word title for a room using AI.
    Trust the AI to follow instructions - no complex fallbacks.
    """
    try:
        # Use AI generation - trust it to follow the prompt
        ai_title = _generate_ai_title(room_name, room_goals)
        if ai_title and ai_title.strip():
            current_app.logger.info(f"✅ AI title: '{room_name}' → '{ai_title}'")
            return ai_title.strip()
            
    except Exception as e:
        current_app.logger.error(f"❌ AI title generation error: {e}")
    
    # Simple fallback: just use the original name
    current_app.logger.info(f"⚠️ Fallback: using original title '{room_name}'")
    return room_name


def _generate_ai_title(room_name: str, room_goals: Optional[str] = None) -> Optional[str]:
    """Use AI to generate a concise room title."""
    try:
        from src.utils.openai_utils import call_anthropic_api
        
        # Create focused prompt for title generation
        context = f"Room name: {room_name}"
        if room_goals:
            context += f"\nRoom goals: {room_goals[:200]}"
        
        prompt = f"""Create a concise, catchy title (2-4 words) for this learning room:

{context}

Requirements:
- 2-4 words maximum (never more than 4 words)
- Clear and descriptive
- Capture the main subject and approach
- Remove filler words like "to study", "to learn about", "using a"
- Make it memorable and specific

Examples:
"to study string theory using a theological perspective" → "Theological String Theory"
"To learn about succulent plants and how to grow them" → "Succulent Gardening"
"To learn about the history of Japan" → "Japanese History"
"Entrepreneurship Business Hub" → "Business Hub"
"to study artificial intelligence and machine learning" → "AI Machine Learning"

Respond with ONLY the short title (2-4 words), nothing else."""

        response = call_anthropic_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.3
        )
        
        if response and response.strip():
            # Clean the response and trust the AI
            title = response.strip().strip('"\'')
            return title
            
    except Exception as e:
        current_app.logger.warning(f"AI title generation error: {e}")
        return None


def _extract_smart_title(room_name: str) -> str:
    """Extract key words from room name using smart rules."""
    # Remove common prefixes and suffixes
    title = room_name.lower()
    
    # Remove common learning prefixes
    prefixes_to_remove = [
        "to learn about",
        "to learn",
        "to study",
        "learning about",
        "studying"
    ]
    
    for prefix in prefixes_to_remove:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
            break
    
    # Remove common words but keep important connecting words for context
    words_to_remove = {"the", "and", "of", "in", "on", "at", "for", "with", "about", "a", "an", "how", "to", "them"}
    
    words = title.split()
    filtered_words = [word for word in words if word not in words_to_remove]
    
    # Smart selection: prioritize key concepts, limit to 3 words max
    if len(filtered_words) <= 3:
        key_words = filtered_words
    else:
        # For longer phrases, intelligently select the most important words
        # Look for academic subjects, methodologies, and key concepts
        important_words = []
        for word in filtered_words:
            if len(important_words) >= 3:
                break
            # Prioritize substantial academic terms
            if len(word) > 3 or word.lower() in ['ai', 'ml', 'ux', 'ui']:
                important_words.append(word)
        
        key_words = important_words if important_words else filtered_words[:3]
    
    # Capitalize properly
    result = " ".join(word.capitalize() for word in key_words)
    
    return result if result else room_name


def _truncate_title(room_name: str) -> str:
    """Simple truncation fallback."""
    words = room_name.split()
    if len(words) <= 5:
        return room_name
    return " ".join(words[:4]) + "..."


def _is_valid_short_title(title: str) -> bool:
    """Validate that a title meets our criteria."""
    if not title or not title.strip():
        return False
    
    words = title.strip().split()
    return 1 <= len(words) <= 5 and len(title) <= 50


def get_display_title(room) -> str:
    """
    Get the best title for display.
    For existing rooms, use simple truncation to avoid over-processing.
    """
    # For existing rooms, just use simple truncation
    words = room.name.split()
    if len(words) <= 4:
        return room.name
    
    # Simple truncation for long titles
    return " ".join(words[:4]) + "..."
