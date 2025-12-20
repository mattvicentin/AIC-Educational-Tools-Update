"""
Card View AI Helpers

AI-powered enhancements for Card View:
- Guiding question generation
- Relationship hints between cards

Uses existing Anthropic/OpenAI utility layer with safe fallbacks.
Includes optional caching for dev/testing.
"""

import hashlib
import logging
import os
import re
import time
from typing import List, Optional, Tuple, Dict, Any

from .prompts import (
    format_guiding_question_prompt,
    format_relationship_hints_batch_prompt,
    format_relationship_hint_prompt,
    FALLBACK_GUIDING_QUESTION,
    FALLBACK_RELATIONSHIP_HINT,
)
from .schemas import Segment

logger = logging.getLogger(__name__)

# Token/character limits
MAX_MESSAGE_CHARS_FOR_GQ = 8000  # Max chars to send for guiding question
MAX_BODY_CHARS_PER_CARD = 400   # Max chars per card body for hints
MAX_PAIRS_FOR_BATCH = 8         # Max pairs in a single batch (to avoid timeout)
AI_TIMEOUT_SECONDS = 10         # Timeout for AI calls

# Caching config (dev-only by default)
# NOTE: This is an in-memory, per-process cache. In production with multiple
# workers (e.g., gunicorn with >1 worker), each worker has its own cache.
# Cache benefits are limited in multi-worker deployments and may cause
# inconsistent behavior. For production, consider Redis or disable caching.
CACHE_ENABLED = os.getenv("CARD_VIEW_CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
CACHE_TTL_SECONDS = int(os.getenv("CARD_VIEW_CACHE_TTL", "300"))  # 5 minutes default

# Simple in-memory cache (cleared on server restart, per-process only)
_cache: Dict[str, Tuple[Any, float]] = {}

DEFAULT_GUIDING_QUESTION = "What is the main point of this message?"


def _cache_key(prefix: str, content: str) -> str:
    """Generate a cache key from content hash."""
    content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"{prefix}:{content_hash}"


def _cache_get(key: str) -> Optional[Any]:
    """Get value from cache if not expired."""
    if not CACHE_ENABLED:
        return None
    
    entry = _cache.get(key)
    if entry is None:
        return None
    
    value, timestamp = entry
    if time.time() - timestamp > CACHE_TTL_SECONDS:
        # Expired
        del _cache[key]
        return None
    
    return value


def _cache_set(key: str, value: Any) -> None:
    """Store value in cache with timestamp."""
    if not CACHE_ENABLED:
        return
    
    # Simple size limit to prevent memory issues
    if len(_cache) > 100:
        # Clear oldest entries
        sorted_keys = sorted(_cache.keys(), key=lambda k: _cache[k][1])
        for k in sorted_keys[:50]:
            del _cache[k]
    
    _cache[key] = (value, time.time())


def clear_cache() -> int:
    """Clear the AI cache. Returns number of entries cleared."""
    count = len(_cache)
    _cache.clear()
    return count


def generate_guiding_question(
    message: str,
    use_ai: bool = True,
    max_chars: int = MAX_MESSAGE_CHARS_FOR_GQ,
) -> str:
    """
    Generate a guiding question for the entire message.
    
    Args:
        message: Full message text
        use_ai: Whether to use AI (False = return default)
        max_chars: Maximum characters to send to AI
        
    Returns:
        Guiding question string ending with '?' (never None)
    """
    # For very short messages, use default (still allows relationships)
    if not message or len(message.strip()) < 50:
        return DEFAULT_GUIDING_QUESTION
    
    if not use_ai:
        return DEFAULT_GUIDING_QUESTION
    
    # Check cache first
    cache_key = _cache_key("gq", message[:max_chars])
    cached = _cache_get(cache_key)
    if cached:
        logger.debug("Guiding question cache hit")
        return cached
    
    start_time = time.time()
    
    try:
        prompt = format_guiding_question_prompt(message, max_chars)
        
        # Call AI using existing utility
        response = _call_ai(prompt, max_tokens=100)
        
        elapsed = time.time() - start_time
        logger.debug(f"Guiding question AI call took {elapsed:.2f}s")
        
        if response:
            # Clean up the response
            question = response.strip()
            # Ensure it ends with ?
            if not question.endswith('?'):
                question += '?'
            # Remove any leading/trailing quotes
            question = question.strip('"\'')
            # Remove leading "Guiding question:" if model echoed it
            for prefix in ["Guiding question:", "Question:"]:
                if question.lower().startswith(prefix.lower()):
                    question = question[len(prefix):].strip()
            
            result = question if question else DEFAULT_GUIDING_QUESTION
            _cache_set(cache_key, result)
            return result
        
        return DEFAULT_GUIDING_QUESTION
        
    except Exception as e:
        logger.warning(f"Failed to generate guiding question: {e}")
        return DEFAULT_GUIDING_QUESTION


def generate_relationship_hints(
    guiding_question: str,
    segments: List[Segment],
    use_ai: bool = True,
    max_body_chars: int = MAX_BODY_CHARS_PER_CARD,
) -> List[str]:
    """
    Generate relationship hints between adjacent card pairs.
    
    Args:
        guiding_question: The guiding question for context
        segments: List of Segment objects
        use_ai: Whether to use AI (False = return fallback hints)
        max_body_chars: Maximum characters per card body to send
        
    Returns:
        List of hint strings, length = len(segments) - 1
        Fallback hints if AI fails or is disabled
    """
    # Need at least 2 segments to have any pairs
    if not segments or len(segments) < 2:
        return []
    
    num_hints = len(segments) - 1
    
    # If AI is disabled, return fallback hints
    if not use_ai:
        return [FALLBACK_RELATIONSHIP_HINT] * num_hints
    
    if not guiding_question:
        guiding_question = "What is the main point of this message?"
    
    try:
        # Use batched approach for efficiency
        hints = _generate_hints_batched(guiding_question, segments, max_body_chars)
        # Ensure no empty hints
        return [h if h.strip() else FALLBACK_RELATIONSHIP_HINT for h in hints]
    except Exception as e:
        logger.warning(f"Failed to generate relationship hints: {e}")
        return [FALLBACK_RELATIONSHIP_HINT] * num_hints


def _generate_hints_batched(
    guiding_question: str,
    segments: List[Segment],
    max_body_chars: int,
) -> List[str]:
    """Generate all hints in batched API call(s)."""
    total_pairs = len(segments) - 1
    
    # Check cache first (key based on guiding question + segment bodies)
    cache_content = guiding_question + "".join(s.body[:200] for s in segments)
    cache_key = _cache_key("hints", cache_content)
    cached = _cache_get(cache_key)
    if cached:
        logger.debug("Relationship hints cache hit")
        return cached
    
    start_time = time.time()
    all_hints = []
    
    # Process in chunks to avoid timeout on very long messages
    for chunk_start in range(0, total_pairs, MAX_PAIRS_FOR_BATCH):
        chunk_end = min(chunk_start + MAX_PAIRS_FOR_BATCH, total_pairs)
        chunk_segments = segments[chunk_start:chunk_end + 1]  # +1 to include last card
        
        prompt = format_relationship_hints_batch_prompt(
            guiding_question, chunk_segments, max_body_chars
        )
        
        # Scale max_tokens based on number of pairs in chunk
        chunk_pairs = len(chunk_segments) - 1
        max_tokens = min(80 * chunk_pairs, 500)
        
        response = _call_ai(prompt, max_tokens=max_tokens)
        
        if response:
            chunk_hints = _parse_numbered_hints(response, expected_count=chunk_pairs)
            all_hints.extend(chunk_hints)
        else:
            # Pad with fallbacks for this chunk
            all_hints.extend([FALLBACK_RELATIONSHIP_HINT] * chunk_pairs)
    
    elapsed = time.time() - start_time
    logger.debug(f"Relationship hints AI call took {elapsed:.2f}s for {total_pairs} pairs")
    
    # Cache the result
    _cache_set(cache_key, all_hints)
    
    return all_hints


def _generate_hints_individually(
    guiding_question: str,
    segments: List[Segment],
    max_body_chars: int,
) -> List[str]:
    """Generate hints one at a time (fallback if batching fails)."""
    hints = []
    
    for i in range(len(segments) - 1):
        card_a = segments[i]
        card_b = segments[i + 1]
        
        prompt = format_relationship_hint_prompt(
            guiding_question,
            card_a.header,
            card_a.body,
            card_b.header,
            card_b.body,
            max_body_chars,
        )
        
        response = _call_ai(prompt, max_tokens=80)
        hint = response.strip() if response else FALLBACK_RELATIONSHIP_HINT
        hints.append(hint)
    
    return hints


def _parse_numbered_hints(response: str, expected_count: int) -> List[str]:
    """
    Parse a numbered list response into individual hints.
    
    Handles formats like:
    1. First hint
    2. Second hint
    - Bullet hint
    Or just plain lines
    """
    hints = []
    
    # Try to extract numbered/bulleted items first
    pattern = r'^\s*(?:\d+[\.\)]|[-•*])\s*(.+)$'
    lines = response.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        match = re.match(pattern, line)
        if match:
            hint = match.group(1).strip()
            if hint:
                hints.append(hint)
        elif len(hints) < expected_count and len(line) > 10:
            # Fallback: accept non-empty lines if we need more hints
            # Skip very short lines that might be artifacts
            hints.append(line)
    
    # Pad with fallbacks if we didn't get enough
    while len(hints) < expected_count:
        hints.append(FALLBACK_RELATIONSHIP_HINT)
    
    # Truncate if we got too many
    hints = hints[:expected_count]
    
    # Replace any blank/whitespace-only hints with fallback
    hints = [h if h.strip() else FALLBACK_RELATIONSHIP_HINT for h in hints]
    
    return hints


def _call_ai(prompt: str, max_tokens: int = 200) -> Optional[str]:
    """
    Call AI using the existing Anthropic-first utility layer.
    
    Returns the response text or None on failure.
    """
    try:
        # Prefer Anthropic; fall back to OpenAI if configured
        from src.utils.openai_utils import call_anthropic_api, call_openai_api
        
        # Try Anthropic first (use fast/cheap haiku model for helpers)
        try:
            import os
            # Temporarily override model for card view helpers
            original_model = os.environ.get("ANTHROPIC_MODEL")
            os.environ["ANTHROPIC_MODEL"] = "claude-3-haiku-20240307"
            
            text, _ = call_anthropic_api(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a concise reasoning assistant.",
                max_tokens=max_tokens,
            )
            
            # Restore original model
            if original_model:
                os.environ["ANTHROPIC_MODEL"] = original_model
            elif "ANTHROPIC_MODEL" in os.environ:
                del os.environ["ANTHROPIC_MODEL"]
                
            if text:
                return text
        except Exception as e:
            logger.warning(f"Anthropic call failed: {e}")
        
        # Fallback to OpenAI if Anthropic missing/unavailable
        try:
            text, _ = call_openai_api(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a concise reasoning assistant.",
                max_tokens=max_tokens,
            )
            if text:
                return text
        except Exception as e:
            logger.warning(f"OpenAI fallback failed: {e}")
        
        return None
        
    except Exception as e:
        logger.warning(f"AI call failed: {e}")
        return None


def get_ai_availability() -> Tuple[bool, str]:
    """
    Check if AI is available for guiding questions and hints.
    
    Returns:
        Tuple of (is_available, status_message)
    """
    try:
        from src.utils.openai_utils import get_ai_client
        client = get_ai_client()
        if client:
            return True, "AI available"
        return False, "No AI client configured"
    except Exception as e:
        return False, f"AI check failed: {e}"


def enhance_segments_with_ai(
    message: str,
    segments: List[Segment],
    use_ai: bool = True,
) -> dict:
    """
    Convenience function to generate all AI enhancements for segments.
    
    Args:
        message: Original full message text
        segments: List of segmented cards
        use_ai: Whether to use AI (False = return empty/null values)
        
    Returns:
        Dict with:
        - guiding_question: str or None
        - relationships: List[str] (len = segments - 1)
        - ai_enhanced: bool (True if AI was used successfully)
        - _meta: dict with timing/cache info (for debugging)
    """
    start_time = time.time()
    
    result = {
        "guiding_question": None,
        "relationships": [],
        "ai_enhanced": False,
        "_meta": {
            "cache_enabled": CACHE_ENABLED,
            "latency_ms": 0,
            "errors": [],
        },
    }
    
    if not use_ai or not segments:
        result["_meta"]["latency_ms"] = int((time.time() - start_time) * 1000)
        return result
    
    # Generate guiding question
    try:
        guiding_question = generate_guiding_question(message, use_ai=True)
        result["guiding_question"] = guiding_question
        
        # Track if we got a real AI response vs fallback
        is_default = guiding_question == DEFAULT_GUIDING_QUESTION
        result["_meta"]["guiding_question_source"] = "fallback" if is_default else "ai"
    except Exception as e:
        result["_meta"]["errors"].append(f"guiding_question: {e}")
        result["guiding_question"] = DEFAULT_GUIDING_QUESTION
    
    # Generate relationship hints if we have 2+ segments
    if len(segments) >= 2 and result["guiding_question"]:
        try:
            relationships = generate_relationship_hints(
                result["guiding_question"], segments, use_ai=True
            )
            result["relationships"] = relationships
            
            # Track if we got real AI hints vs fallbacks
            fallback_count = sum(1 for h in relationships if h == FALLBACK_RELATIONSHIP_HINT)
            result["_meta"]["hints_fallback_count"] = fallback_count
        except Exception as e:
            result["_meta"]["errors"].append(f"relationships: {e}")
            result["relationships"] = [FALLBACK_RELATIONSHIP_HINT] * (len(segments) - 1)
    
    # Mark as enhanced if we got non-fallback responses
    gq_source = result["_meta"].get("guiding_question_source", "fallback")
    hints_fallbacks = result["_meta"].get("hints_fallback_count", len(segments) - 1)
    result["ai_enhanced"] = (gq_source == "ai") or (hints_fallbacks < len(segments) - 1)
    
    result["_meta"]["latency_ms"] = int((time.time() - start_time) * 1000)
    
    return result
