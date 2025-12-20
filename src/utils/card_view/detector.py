"""
Structure Detection for Card View

Detects the dominant structure type in a message:
- bullets (list-heavy)
- prose (paragraph-heavy)
- mixed (combination)
- code (code block present)
"""

import re
from typing import Literal, Tuple, List

StructureType = Literal["bullets", "prose", "mixed", "code"]

# Patterns
BULLET_PATTERN = re.compile(r'^\s*[-*•◦▪▸►]\s+', re.MULTILINE)
NUMBERED_PATTERN = re.compile(r'^\s*\d+[.)]\s+', re.MULTILINE)
CODE_FENCE_OPEN = re.compile(r'```\w*')
CODE_FENCE_CLOSE = re.compile(r'```')
INLINE_CODE_PATTERN = re.compile(r'`[^`]+`')
MARKDOWN_HEADING_PATTERN = re.compile(r'^#{1,6}\s+.+$', re.MULTILINE)


def detect_structure(text: str) -> Tuple[StructureType, dict]:
    """
    Analyze text and determine its dominant structure.
    
    Args:
        text: The message text to analyze
        
    Returns:
        Tuple of (structure_type, stats_dict)
        
    Examples:
        >>> detect_structure("- Item 1\\n- Item 2\\n- Item 3")
        ('bullets', {'bullet_lines': 3, 'total_lines': 3, 'bullet_ratio': 1.0, ...})
    """
    if not text or not text.strip():
        return "prose", {"empty": True}
    
    lines = text.strip().split('\n')
    total_lines = len(lines)
    non_empty_lines = [l for l in lines if l.strip()]
    
    # Extract code blocks (handles unclosed fences)
    code_blocks = extract_code_blocks(text)
    
    # Count structural elements
    bullet_matches = BULLET_PATTERN.findall(text)
    numbered_matches = NUMBERED_PATTERN.findall(text)
    
    # Headings (excluding those inside code blocks)
    headings = extract_markdown_headings(text)
    
    bullet_lines = len(bullet_matches) + len(numbered_matches)
    code_chars = sum(b["end"] - b["start"] for b in code_blocks)
    
    # Calculate ratios
    bullet_ratio = bullet_lines / max(len(non_empty_lines), 1)
    code_ratio = code_chars / max(len(text), 1)
    
    # Check if we have an unclosed code block
    has_unclosed_code = any(b.get("unclosed", False) for b in code_blocks)
    
    stats = {
        "total_lines": total_lines,
        "non_empty_lines": len(non_empty_lines),
        "bullet_lines": bullet_lines,
        "bullet_ratio": round(bullet_ratio, 2),
        "code_blocks": len(code_blocks),
        "code_ratio": round(code_ratio, 2),
        "headings": len(headings),
        "total_chars": len(text),
        "has_unclosed_code": has_unclosed_code,
    }
    
    # Determine dominant structure
    # Code-heavy: >30% of text is code
    if code_ratio > 0.3:
        return "code", stats
    
    # Bullet-heavy: >40% of lines are bullets/numbered
    if bullet_ratio > 0.4:
        return "bullets", stats
    
    # Mixed: has both bullets and substantial prose
    if bullet_ratio > 0.15 and bullet_ratio <= 0.4:
        return "mixed", stats
    
    # Default: prose
    return "prose", stats


def has_code_blocks(text: str) -> bool:
    """Check if text contains code blocks that shouldn't be split."""
    return bool(CODE_FENCE_OPEN.search(text))


def extract_code_blocks(text: str) -> List[dict]:
    """
    Extract code blocks with their positions.
    
    Handles unclosed code fences: if an opening ``` has no matching close,
    treats everything from the opening fence to EOF as one code block.
    
    Returns:
        List of dicts with 'content', 'start', 'end', and 'unclosed' keys
    """
    blocks = []
    
    # First, handle inline code (single backticks) - we skip these for code blocks
    # but track them for exclusion
    
    # Find all opening fences
    opens = list(CODE_FENCE_OPEN.finditer(text))
    
    if not opens:
        return blocks
    
    i = 0
    while i < len(opens):
        open_match = opens[i]
        open_pos = open_match.end()  # Position after opening fence
        
        # Find the next closing fence after this opening
        close_match = None
        search_start = open_pos
        
        # Skip past the first line (language specifier line)
        newline_pos = text.find('\n', open_pos)
        if newline_pos != -1:
            search_start = newline_pos + 1
        
        # Look for closing fence
        for match in CODE_FENCE_CLOSE.finditer(text, search_start):
            # Make sure this isn't another opening fence
            if match.start() == open_match.start():
                continue
            # Check it's at start of line or preceded by newline
            if match.start() == 0 or text[match.start() - 1] == '\n':
                close_match = match
                break
        
        if close_match:
            # Found a proper close
            blocks.append({
                "content": text[open_match.start():close_match.end()],
                "start": open_match.start(),
                "end": close_match.end(),
                "unclosed": False,
            })
            # Skip any opens that fall within this block
            while i + 1 < len(opens) and opens[i + 1].start() < close_match.end():
                i += 1
        else:
            # Unclosed fence - treat everything to EOF as code
            blocks.append({
                "content": text[open_match.start():],
                "start": open_match.start(),
                "end": len(text),
                "unclosed": True,
            })
            # No more blocks after unclosed
            break
        
        i += 1
    
    return blocks


def extract_markdown_headings(text: str) -> List[dict]:
    """
    Extract markdown headings with their positions.
    
    Skips headings that fall inside code blocks.
    
    Returns:
        List of dicts with 'content', 'level', 'start', 'end' keys
    """
    # First, get all code blocks to exclude headings inside them
    code_blocks = extract_code_blocks(text)
    
    def is_inside_code_block(pos: int) -> bool:
        """Check if a position falls inside any code block."""
        for block in code_blocks:
            if block["start"] <= pos < block["end"]:
                return True
        return False
    
    headings = []
    for match in MARKDOWN_HEADING_PATTERN.finditer(text):
        # Skip if inside a code block
        if is_inside_code_block(match.start()):
            continue
        
        level = len(match.group().split()[0])  # Count #'s
        headings.append({
            "content": match.group().lstrip('#').strip(),
            "level": level,
            "start": match.start(),
            "end": match.end(),
        })
    
    return headings


def detect_truncation_hints(text: str) -> dict:
    """
    Detect hints that a message may be truncated.
    
    Checks for:
    - Unclosed code fence
    - Trailing incomplete list item
    - Abrupt ending (no sentence punctuation)
    
    Returns:
        Dict with truncation hint flags
    """
    hints = {
        "has_unclosed_code": False,
        "has_trailing_list_item": False,
        "missing_sentence_end": False,
        "is_likely_truncated": False,
    }
    
    if not text or not text.strip():
        return hints
    
    text = text.strip()
    
    # Check for unclosed code fence
    code_blocks = extract_code_blocks(text)
    hints["has_unclosed_code"] = any(b.get("unclosed", False) for b in code_blocks)
    
    # Check for trailing incomplete list item
    lines = text.split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    if non_empty_lines:
        last_line = non_empty_lines[-1].strip()
        # Is it a list item?
        is_list_item = bool(
            re.match(r'^\s*[-*•◦▪▸►]\s+', last_line) or 
            re.match(r'^\s*\d+[.)]\s+', last_line)
        )
        # Does text end without a blank line after it?
        ends_without_break = not text.endswith('\n\n') and not text.endswith('\n \n')
        hints["has_trailing_list_item"] = is_list_item and ends_without_break
    
    # Check for missing sentence ending
    last_char = text[-1]
    # Normal endings: sentence punctuation, code blocks, or bullet lists
    has_normal_ending = (
        last_char in '.?!"\')' or
        text.endswith('```') or
        hints["has_trailing_list_item"]  # List items don't need punctuation
    )
    hints["missing_sentence_end"] = not has_normal_ending
    
    # Overall assessment
    hints["is_likely_truncated"] = (
        hints["has_unclosed_code"] or
        (hints["missing_sentence_end"] and not hints["has_trailing_list_item"])
    )
    
    return hints
