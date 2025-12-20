"""
Header Generation for Card View

Generates concise headers (6-12 words) for card segments.
Uses heuristic approach first, with optional AI fallback.
"""

import re
from typing import Optional

# Words that make weak headers when appearing alone
WEAK_HEADER_WORDS = {
    "the", "a", "an", "this", "that", "these", "those",
    "it", "they", "we", "you", "i", "he", "she",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might",
    "here", "there", "also", "however", "therefore",
    "first", "second", "third", "finally", "next",
}

# Patterns for cleaning headers
BULLET_PREFIX = re.compile(r'^[\s\-*•◦▪▸►\d.)\]]+')
TRAILING_PUNCT = re.compile(r'[.:;,]+$')

# Words to keep lowercase in title case (articles, conjunctions, prepositions)
TITLE_CASE_LOWERCASE = {
    "a", "an", "the",                           # articles
    "and", "but", "or", "nor", "for", "yet", "so",  # conjunctions
    "at", "by", "in", "of", "on", "to", "up",   # short prepositions
    "as", "if", "vs", "via",                    # misc short words
}


def normalize_header_case(header: str) -> str:
    """
    Normalize header case: convert ALL CAPS to Title Case, leave mixed-case intact.
    
    Rules:
    - ALL CAPS → Title Case (e.g., "KEY MARKERS" → "Key Markers")
    - all lowercase → Title Case
    - Mixed case → preserve (e.g., "JavaScript Basics" stays as-is)
    - Short articles/conjunctions/prepositions stay lowercase (except first word)
    
    Args:
        header: The header string to normalize
        
    Returns:
        Normalized header string
    """
    if not header or not header.strip():
        return header
    
    # Check if transformation is needed
    is_all_caps = header.isupper() and len(header) > 1
    is_all_lower = header.islower()
    
    if not is_all_caps and not is_all_lower:
        # Mixed case - leave mostly intact (already has intentional casing)
        return header
    
    # Apply title case transformation
    words = header.split()
    result = []
    
    for i, word in enumerate(words):
        word_lower = word.lower()
        
        # First word always capitalized
        if i == 0:
            result.append(word.capitalize())
        # Short words stay lowercase (unless all caps input)
        elif word_lower in TITLE_CASE_LOWERCASE:
            result.append(word_lower)
        # Capitalize other words
        else:
            result.append(word.capitalize())
    
    return ' '.join(result)


def generate_header_heuristic(chunk: str, max_words: int = 10) -> str:
    """
    Generate a header from chunk content using heuristics.
    
    Strategy:
    1. Look for section title (line ending with ":" or ALL CAPS/Title Case)
    2. Fall back to first sentence
    3. Clean bullet prefixes
    4. Trim to max_words
    5. Capitalize appropriately
    
    Args:
        chunk: The text content to generate a header for
        max_words: Maximum words in header (default 10)
        
    Returns:
        A concise header string (6-12 words typically)
    """
    if not chunk or not chunk.strip():
        return "Content"
    
    lines = [ln.strip() for ln in chunk.strip().split('\n') if ln.strip()]
    
    if not lines:
        return "Content"
    
    # First pass: look for section title lines
    title_line = None
    for ln in lines:
        # Skip bullet lines
        if ln.startswith(('-', '*', '•', '–', '—')) or re.match(r'^\d+[\.\)]\s', ln):
            continue
        
        # Likely a section title if short and ends with ":"
        if ln.endswith(':') and len(ln) <= 60:
            title_line = ln.rstrip(':')
            break
        
        # ALL CAPS line (short, no punctuation at end)
        if len(ln) <= 50 and ln.isupper() and ln[-1].isalnum():
            title_line = ln
            break
        
        # Short Title Case line without sentence-ending punctuation
        if len(ln) <= 60 and ln[-1].isalnum() and ln.istitle():
            title_line = ln
            break
    
    # Second pass: fall back to first meaningful line (existing behavior)
    first_line = title_line
    if not first_line:
        for line in lines:
            cleaned = BULLET_PREFIX.sub('', line).strip()
            if cleaned and len(cleaned) > 10:
                first_line = cleaned
                break
        
        if not first_line:
            first_line = BULLET_PREFIX.sub('', lines[0]).strip() if lines else "Content"
    
    if not first_line:
        return "Content"
    
    # Extract first sentence (up to period, question mark, or exclamation)
    sentence_end = re.search(r'[.!?]', first_line)
    if sentence_end and sentence_end.start() > 15:
        first_line = first_line[:sentence_end.start()]
    
    # Split into words and trim
    words = first_line.split()
    if len(words) > max_words:
        words = words[:max_words]
    
    # Remove trailing weak words
    while words and words[-1].lower() in WEAK_HEADER_WORDS:
        words.pop()
    
    # Ensure we have something
    if not words:
        words = ["Content"]
    
    # Clean up trailing punctuation and join
    header = ' '.join(words)
    header = TRAILING_PUNCT.sub('', header)
    
    # Normalize case (ALL CAPS → Title Case, preserve mixed case)
    header = normalize_header_case(header)
    
    return header


def is_weak_header(header: str) -> bool:
    """
    Check if a header is too generic or weak.
    
    A header is weak if:
    - Less than 3 words
    - Mostly stop words
    - Too generic (e.g., "The following", "Here is")
    """
    words = header.lower().split()
    
    if len(words) < 3:
        return True
    
    # Count meaningful words
    meaningful = [w for w in words if w not in WEAK_HEADER_WORDS]
    if len(meaningful) < 2:
        return True
    
    # Check for generic patterns
    generic_patterns = [
        "here is", "here are", "the following", "as follows",
        "in this", "this is", "there are", "there is",
        "we can", "you can", "let's", "let us",
    ]
    header_lower = header.lower()
    for pattern in generic_patterns:
        if header_lower.startswith(pattern):
            return True
    
    return False


def generate_header_ai(chunk: str, client=None) -> Optional[str]:
    """
    Generate a header using AI (fallback for weak heuristic headers).
    
    Args:
        chunk: The text content to generate a header for
        client: Optional AI client (uses Anthropic by default)
        
    Returns:
        AI-generated header, or None if unavailable
    """
    # TODO: Implement AI header generation
    # For now, return None to indicate AI not available
    # When implemented:
    # - Use a strict prompt: "Generate a 6-10 word header for this content. No punctuation except commas."
    # - Timeout: 2 seconds max
    # - Return None on any error
    return None


def generate_header(chunk: str, use_ai_fallback: bool = False) -> tuple:
    """
    Generate the best header for a chunk.
    
    Args:
        chunk: Text content
        use_ai_fallback: Whether to use AI if heuristic is weak
        
    Returns:
        Tuple of (header, confidence) where confidence is:
        - 1.0 for strong heuristic
        - 0.9 for weak heuristic (no AI available)
        - 0.8 for AI-generated
    """
    header = generate_header_heuristic(chunk)
    
    if is_weak_header(header):
        if use_ai_fallback:
            ai_header = generate_header_ai(chunk)
            if ai_header:
                return ai_header, 0.8
        return header, 0.9
    
    return header, 1.0
