"""
Message Segmenter for Card View

Core logic for splitting long AI messages into 3-9 meaningful segments.

Constraints:
- Minimum 3 segments (unless message is short)
- Maximum 9 segments (merge if more)
- Don't split inside code blocks
- Respect existing markdown headings
- Preserve ordered lists
- Short messages (<100 chars) return 1 segment
- Handle unclosed code blocks gracefully
- Detect and flag truncated messages
"""

import re
from typing import List, Optional
from .schemas import Segment
from .detector import (
    detect_structure, 
    extract_code_blocks, 
    extract_markdown_headings,
    detect_truncation_hints,
)
from .headers import generate_header

# Constants
MIN_SEGMENTS = 3
MAX_SEGMENTS = 9
SHORT_MESSAGE_THRESHOLD = 100  # chars
MIN_SEGMENT_CHARS = 50  # Don't create tiny segments
MIN_CARD_CHARS = 120  # Threshold for tiny-card merge pass
INCOMPLETE_TAIL_THRESHOLD = 120  # Threshold for marking last card as truncated


def segment_message(
    text: str,
    min_segments: int = MIN_SEGMENTS,
    max_segments: int = MAX_SEGMENTS,
    use_ai_headers: bool = False,
) -> List[Segment]:
    """
    Segment a message into 3-9 card-ready pieces.
    
    Args:
        text: The message text to segment
        min_segments: Minimum segments (default 3)
        max_segments: Maximum segments (default 9)
        use_ai_headers: Use AI for weak headers (default False)
        
    Returns:
        List of Segment objects
        
    Examples:
        >>> segments = segment_message(long_ai_response)
        >>> len(segments)  # Will be 3-9
        5
        >>> segments[0].header
        'Understanding the Core Concepts'
    """
    if not text or not text.strip():
        return []
    
    text = text.strip()
    
    # Detect truncation hints early
    truncation_hints = detect_truncation_hints(text)
    
    # Short-circuit for short messages
    if len(text) < SHORT_MESSAGE_THRESHOLD:
        header, confidence = generate_header(text, use_ai_headers)
        return [Segment(
            header=header,
            body=text,
            start_idx=0,
            end_idx=len(text),
            segment_type="paragraph",
            confidence=confidence,
            is_truncated=truncation_hints["is_likely_truncated"],
        )]
    
    # Detect structure
    structure_type, stats = detect_structure(text)
    
    # Check for existing markdown headings (respect them)
    # But skip heading detection if we have unclosed code
    if not stats.get("has_unclosed_code", False):
        headings = extract_markdown_headings(text)
        if len(headings) >= min_segments:
            segments = _segment_by_headings(text, headings, max_segments, use_ai_headers)
            return _finalize_segments(segments, truncation_hints, min_segments)
    
    # Segment based on structure type
    if structure_type == "bullets":
        raw_segments = _segment_bullets(text)
    elif structure_type == "code":
        raw_segments = _segment_with_code(text)
    elif structure_type == "mixed":
        raw_segments = _segment_mixed(text)
    else:  # prose
        raw_segments = _segment_prose(text)
    
    # Enforce 3-9 constraint
    raw_segments = _enforce_segment_count(raw_segments, min_segments, max_segments)
    
    # Generate headers and create Segment objects
    segments = []
    for raw in raw_segments:
        header, confidence = generate_header(raw["body"], use_ai_headers)
        segments.append(Segment(
            header=header,
            body=raw["body"],
            start_idx=raw["start_idx"],
            end_idx=raw["end_idx"],
            segment_type=raw.get("type", "paragraph"),
            confidence=confidence,
            is_truncated=raw.get("is_truncated", False),
        ))
    
    return _finalize_segments(segments, truncation_hints, min_segments)


def _finalize_segments(
    segments: List[Segment], 
    truncation_hints: dict,
    min_segments: int,
) -> List[Segment]:
    """
    Final processing pass on segments:
    - Tiny-card merge pass
    - Tail merge for incomplete segments
    - Mark truncation on last segment if detected
    """
    if not segments:
        return segments
    
    # Tiny-card merge pass
    segments = _merge_tiny_cards(segments, min_segments)
    
    # Check last segment for truncation
    last_seg = segments[-1]
    
    # Mark as truncated if:
    # 1. Message has unclosed code and last segment contains it
    # 2. Last segment is too short and doesn't end properly
    # 3. Overall message appears truncated
    should_mark_truncated = (
        truncation_hints["has_unclosed_code"] or
        (
            last_seg.length < INCOMPLETE_TAIL_THRESHOLD and
            not last_seg.is_complete_sentence and
            truncation_hints["missing_sentence_end"]
        )
    )
    
    if should_mark_truncated and not last_seg.is_truncated:
        # Recreate with truncated flag
        segments[-1] = Segment(
            header=last_seg.header,
            body=last_seg.body,
            start_idx=last_seg.start_idx,
            end_idx=last_seg.end_idx,
            segment_type=last_seg.segment_type,
            confidence=last_seg.confidence,
            is_truncated=True,
        )
    
    # Tail merge: if last segment is incomplete/tiny and we can merge
    if len(segments) > 1:
        last_seg = segments[-1]
        if last_seg.is_truncated or (last_seg.length < MIN_CARD_CHARS and len(segments) > min_segments):
            # Merge into previous
            prev = segments[-2]
            merged = Segment(
                header=prev.header,
                body=prev.body + "\n\n" + last_seg.body,
                start_idx=prev.start_idx,
                end_idx=last_seg.end_idx,
                segment_type=prev.segment_type,
                confidence=min(prev.confidence, last_seg.confidence),
                is_truncated=last_seg.is_truncated,  # Preserve truncation flag
            )
            segments = segments[:-2] + [merged]
    
    return segments


def _segment_by_headings(
    text: str, 
    headings: list, 
    max_segments: int,
    use_ai_headers: bool,
) -> List[Segment]:
    """Segment using existing markdown headings."""
    segments = []
    
    for i, heading in enumerate(headings):
        # Find end of this section (start of next heading or end of text)
        start = heading["start"]
        if i + 1 < len(headings):
            end = headings[i + 1]["start"]
        else:
            end = len(text)
        
        body = text[start:end].strip()
        
        segments.append(Segment(
            header=heading["content"],
            body=body,
            start_idx=start,
            end_idx=end,
            segment_type="heading",
            confidence=1.0,  # Existing headings are trustworthy
        ))
    
    # Merge if too many
    if len(segments) > max_segments:
        segments = _merge_segments(segments, max_segments)
    
    return segments


def _segment_prose(text: str) -> List[dict]:
    """Segment prose by paragraphs (blank lines)."""
    # Split on double newlines (paragraph breaks)
    paragraphs = re.split(r'\n\s*\n', text)
    
    segments = []
    current_pos = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Find actual position in original text
        start = text.find(para, current_pos)
        if start == -1:
            start = current_pos
        end = start + len(para)
        current_pos = end
        
        segments.append({
            "body": para,
            "start_idx": start,
            "end_idx": end,
            "type": "paragraph",
        })
    
    return segments


def _segment_bullets(text: str) -> List[dict]:
    """Segment bullet lists into logical groups."""
    lines = text.split('\n')
    segments = []
    current_segment = []
    current_start = 0
    
    bullet_pattern = re.compile(r'^\s*[-*•◦▪▸►]\s+|\s*\d+[.)]\s+')
    
    for i, line in enumerate(lines):
        is_bullet = bool(bullet_pattern.match(line))
        
        if is_bullet:
            current_segment.append(line)
        elif line.strip():
            # Non-bullet, non-empty line - might be continuation or new section
            if current_segment:
                current_segment.append(line)
            else:
                current_segment = [line]
        else:
            # Empty line - potential segment break
            if current_segment and len('\n'.join(current_segment)) > MIN_SEGMENT_CHARS:
                body = '\n'.join(current_segment)
                start = text.find(body, current_start)
                if start == -1:
                    start = current_start
                segments.append({
                    "body": body,
                    "start_idx": start,
                    "end_idx": start + len(body),
                    "type": "bullet",
                })
                current_start = start + len(body)
                current_segment = []
    
    # Don't forget last segment
    if current_segment:
        body = '\n'.join(current_segment)
        start = text.find(body, current_start)
        if start == -1:
            start = current_start
        segments.append({
            "body": body,
            "start_idx": start,
            "end_idx": start + len(body),
            "type": "bullet",
        })
    
    return segments


def _segment_with_code(text: str) -> List[dict]:
    """
    Segment text containing code blocks (don't split code).
    
    Handles unclosed code fences by treating everything from the
    opening fence to EOF as a single code segment.
    """
    code_blocks = extract_code_blocks(text)
    
    if not code_blocks:
        return _segment_prose(text)
    
    segments = []
    last_end = 0
    
    for block in code_blocks:
        # Add prose before code block
        if block["start"] > last_end:
            prose = text[last_end:block["start"]].strip()
            if prose:
                prose_segments = _segment_prose(prose)
                # Adjust indices
                for seg in prose_segments:
                    seg["start_idx"] += last_end
                    seg["end_idx"] += last_end
                segments.extend(prose_segments)
        
        # Add code block as single segment
        is_unclosed = block.get("unclosed", False)
        segments.append({
            "body": block["content"],
            "start_idx": block["start"],
            "end_idx": block["end"],
            "type": "code",
            "is_truncated": is_unclosed,  # Mark unclosed code as truncated
        })
        last_end = block["end"]
    
    # Add remaining prose after last code block
    # (Only if code block was properly closed)
    last_block = code_blocks[-1] if code_blocks else None
    if last_block and not last_block.get("unclosed", False):
        if last_end < len(text):
            prose = text[last_end:].strip()
            if prose:
                prose_segments = _segment_prose(prose)
                for seg in prose_segments:
                    seg["start_idx"] += last_end
                    seg["end_idx"] += last_end
                segments.extend(prose_segments)
    
    return segments


def _segment_mixed(text: str) -> List[dict]:
    """Segment mixed bullet/prose content."""
    # Simple approach: split on double newlines, then handle each chunk
    chunks = re.split(r'\n\s*\n', text)
    segments = []
    current_pos = 0
    
    bullet_pattern = re.compile(r'^\s*[-*•◦▪▸►]\s+|\s*\d+[.)]\s+', re.MULTILINE)
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        
        start = text.find(chunk, current_pos)
        if start == -1:
            start = current_pos
        end = start + len(chunk)
        current_pos = end
        
        # Determine type
        bullet_lines = len(bullet_pattern.findall(chunk))
        total_lines = len(chunk.split('\n'))
        seg_type = "bullet" if bullet_lines > total_lines / 2 else "paragraph"
        
        segments.append({
            "body": chunk,
            "start_idx": start,
            "end_idx": end,
            "type": seg_type,
        })
    
    return segments


def _enforce_segment_count(
    segments: List[dict], 
    min_count: int, 
    max_count: int,
) -> List[dict]:
    """Merge or split segments to enforce count constraints."""
    # Too many segments - merge smallest adjacent pairs
    while len(segments) > max_count:
        segments = _merge_smallest_pair(segments)
    
    # Too few segments - split largest
    while len(segments) < min_count and len(segments) > 0:
        largest_idx = max(range(len(segments)), key=lambda i: len(segments[i]["body"]))
        largest = segments[largest_idx]
        
        # Only split if large enough
        if len(largest["body"]) < MIN_SEGMENT_CHARS * 2:
            break
        
        split_result = _split_segment(largest)
        if len(split_result) > 1:
            segments = segments[:largest_idx] + split_result + segments[largest_idx + 1:]
        else:
            break  # Can't split further
    
    return segments


def _merge_smallest_pair(segments: List[dict]) -> List[dict]:
    """Merge the two smallest adjacent segments."""
    if len(segments) < 2:
        return segments
    
    # Find smallest adjacent pair by combined length
    min_combined = float('inf')
    merge_idx = 0
    
    for i in range(len(segments) - 1):
        combined = len(segments[i]["body"]) + len(segments[i + 1]["body"])
        if combined < min_combined:
            min_combined = combined
            merge_idx = i
    
    # Merge
    merged = {
        "body": segments[merge_idx]["body"] + "\n\n" + segments[merge_idx + 1]["body"],
        "start_idx": segments[merge_idx]["start_idx"],
        "end_idx": segments[merge_idx + 1]["end_idx"],
        "type": segments[merge_idx]["type"],  # Keep first type
        "is_truncated": segments[merge_idx + 1].get("is_truncated", False),  # Preserve truncation
    }
    
    return segments[:merge_idx] + [merged] + segments[merge_idx + 2:]


def _merge_segments(segments: List[Segment], target: int) -> List[Segment]:
    """Merge Segment objects to reach target count."""
    while len(segments) > target:
        # Find smallest adjacent pair
        min_combined = float('inf')
        merge_idx = 0
        
        for i in range(len(segments) - 1):
            combined = segments[i].length + segments[i + 1].length
            if combined < min_combined:
                min_combined = combined
                merge_idx = i
        
        # Merge
        merged = Segment(
            header=segments[merge_idx].header,
            body=segments[merge_idx].body + "\n\n" + segments[merge_idx + 1].body,
            start_idx=segments[merge_idx].start_idx,
            end_idx=segments[merge_idx + 1].end_idx,
            segment_type=segments[merge_idx].segment_type,
            confidence=min(segments[merge_idx].confidence, segments[merge_idx + 1].confidence),
            is_truncated=segments[merge_idx + 1].is_truncated,  # Preserve truncation from second
        )
        
        segments = segments[:merge_idx] + [merged] + segments[merge_idx + 2:]
    
    return segments


def _merge_tiny_cards(segments: List[Segment], min_count: int) -> List[Segment]:
    """
    Merge very short cards into neighbors to avoid micro-cards.
    
    Rules:
    - Merge cards shorter than MIN_CARD_CHARS (120) if we have > min_count
    - ALWAYS merge truly micro cards (<60 chars) regardless of count
    - First card → merge into next
    - Last card → merge into previous
    - CTA (ends with ?) → merge into previous
    - Otherwise → merge into shorter neighbor
    
    Args:
        segments: List of Segment objects
        min_count: Minimum number of segments to maintain
        
    Returns:
        List of Segment objects with tiny cards merged
    """
    if len(segments) <= 1:
        return segments
    
    MICRO_CARD_THRESHOLD = 60  # Always merge cards this small
    
    # Keep merging until no tiny cards remain
    changed = True
    while changed and len(segments) > 1:
        changed = False
        
        for i, seg in enumerate(segments):
            # Determine if this card should be merged
            is_micro = seg.length < MICRO_CARD_THRESHOLD
            is_tiny = seg.length < MIN_CARD_CHARS
            can_reduce_count = len(segments) > min_count
            
            # Skip if card is large enough, unless it's micro
            if not is_micro and (not is_tiny or not can_reduce_count):
                continue
            
            # Found a tiny card - determine merge direction
            if i == 0:
                # First card → merge into next
                merge_target = 1
            elif i == len(segments) - 1:
                # Last card → merge into previous
                merge_target = i - 1
            elif seg.body.strip().endswith('?'):
                # CTA question → merge into previous
                merge_target = i - 1
            else:
                # Merge into shorter neighbor
                left_len = segments[i - 1].length
                right_len = segments[i + 1].length
                merge_target = i - 1 if left_len <= right_len else i + 1
            
            # Perform merge
            if merge_target < i:
                # Merge current into previous
                prev = segments[merge_target]
                merged = Segment(
                    header=prev.header,
                    body=prev.body + "\n\n" + seg.body,
                    start_idx=prev.start_idx,
                    end_idx=seg.end_idx,
                    segment_type=prev.segment_type,
                    confidence=min(prev.confidence, seg.confidence),
                    is_truncated=seg.is_truncated or prev.is_truncated,  # Preserve truncation
                )
                segments = segments[:merge_target] + [merged] + segments[i + 1:]
            else:
                # Merge next into current (keep current's header)
                next_seg = segments[merge_target]
                merged = Segment(
                    header=seg.header if seg.length > 60 else next_seg.header,
                    body=seg.body + "\n\n" + next_seg.body,
                    start_idx=seg.start_idx,
                    end_idx=next_seg.end_idx,
                    segment_type=seg.segment_type,
                    confidence=min(seg.confidence, next_seg.confidence),
                    is_truncated=seg.is_truncated or next_seg.is_truncated,  # Preserve truncation
                )
                segments = segments[:i] + [merged] + segments[merge_target + 1:]
            
            changed = True
            break  # Restart loop after merge
    
    return segments


def _split_segment(segment: dict) -> List[dict]:
    """Split a segment by sentence boundaries."""
    body = segment["body"]
    
    # Find sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', body)
    
    if len(sentences) < 2:
        return [segment]
    
    # Split roughly in half by sentence
    mid = len(sentences) // 2
    first_half = ' '.join(sentences[:mid])
    second_half = ' '.join(sentences[mid:])
    
    if len(first_half) < MIN_SEGMENT_CHARS or len(second_half) < MIN_SEGMENT_CHARS:
        return [segment]
    
    mid_idx = segment["start_idx"] + len(first_half)
    
    return [
        {
            "body": first_half,
            "start_idx": segment["start_idx"],
            "end_idx": mid_idx,
            "type": segment["type"],
        },
        {
            "body": second_half,
            "start_idx": mid_idx,
            "end_idx": segment["end_idx"],
            "type": segment["type"],
        },
    ]
