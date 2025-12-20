"""
Card View Data Schemas

Defines the Segment dataclass and related types.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import re
import uuid

# Pattern to detect list markers in body content
LIST_MARKER_PATTERN = re.compile(r'^\s*[-*•◦▪▸►]\s+|\s*\d+[.)]\s+', re.MULTILINE)


SegmentType = Literal["bullet", "paragraph", "code", "mixed", "heading"]


@dataclass
class Segment:
    """
    A single card segment extracted from a message.
    
    Attributes:
        id: Unique identifier for this segment
        header: Short descriptive header (6-12 words)
        body: Full content of the segment
        start_idx: Character offset where segment starts in original text
        end_idx: Character offset where segment ends in original text
        segment_type: Type of content (bullet, paragraph, code, mixed, heading)
        confidence: Header quality score (1.0 = heuristic, 0.8 = AI-generated)
        is_truncated: Whether this segment appears to be truncated/incomplete
    """
    header: str
    body: str
    start_idx: int
    end_idx: int
    segment_type: SegmentType = "paragraph"
    confidence: float = 1.0
    is_truncated: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def __post_init__(self):
        """Validate segment after creation."""
        if self.end_idx <= self.start_idx:
            raise ValueError(f"end_idx ({self.end_idx}) must be > start_idx ({self.start_idx})")
        if not self.header.strip():
            raise ValueError("header cannot be empty")
        if not self.body.strip():
            raise ValueError("body cannot be empty")
    
    @property
    def length(self) -> int:
        """Character length of the body."""
        return len(self.body)
    
    @property
    def word_count(self) -> int:
        """Approximate word count of the body."""
        return len(self.body.split())
    
    @property
    def is_complete_sentence(self) -> bool:
        """Check if segment ends with sentence-ending punctuation or is a list."""
        body = self.body.strip()
        if not body:
            return False
        # Valid endings: sentence punctuation or code blocks
        last_char = body[-1]
        if last_char in '.?!':
            return True
        if body.endswith('```'):
            return True
        # Bullet/numbered lists don't need punctuation - that's OK
        if self.segment_type == "bullet":
            return True
        # Also check body content for list markers (handles mixed/paragraph types with lists)
        if LIST_MARKER_PATTERN.search(body):
            return True
        return False
    
    @property
    def is_complete(self) -> bool:
        """
        Check if segment is complete (not truncated and proper ending).
        
        A segment is complete if:
        - It is not marked as truncated
        - It ends with sentence-ending punctuation (for prose)
        - Or it's a code/bullet type which doesn't need punctuation
        """
        if self.is_truncated:
            return False
        return self.is_complete_sentence
    
    @property
    def ending_char(self) -> str:
        """Get the last character of the body."""
        body = self.body.strip()
        return body[-1] if body else ''
    
    def to_dict(self, message_id: Optional[int] = None, segment_index: Optional[int] = None) -> dict:
        """
        Convert to dictionary for JSON serialization.
        
        Args:
            message_id: Optional message ID for generating stable card_key
            segment_index: Optional index for generating stable card_key
            
        Returns:
            Dictionary representation with optional card_key
        """
        data = {
            "id": self.id,
            "header": self.header,
            "body": self.body,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "segment_type": self.segment_type,
            "confidence": self.confidence,
            "length": self.length,
            "word_count": self.word_count,
            "is_complete": self.is_complete,
            "is_truncated": self.is_truncated,
        }
        
        # Add card_key if we have message context
        if message_id is not None and segment_index is not None:
            data["card_key"] = self.generate_card_key(message_id, segment_index)
            data["body_hash"] = self.generate_body_hash()
        
        return data
    
    def generate_card_key(self, message_id: int, segment_index: int) -> str:
        """
        Generate a stable card key for this segment.
        
        The key is based on message_id + segment_index + body hash,
        ensuring comments stay attached even if segmentation changes slightly.
        
        Args:
            message_id: ID of the source message
            segment_index: Index of this segment (0-based)
            
        Returns:
            SHA1 hash string (40 chars)
        """
        import hashlib
        content = f"{message_id}:{segment_index}:{self.body[:200]}"
        return hashlib.sha1(content.encode()).hexdigest()
    
    def generate_body_hash(self) -> str:
        """Generate a hash of the body for mismatch detection."""
        import hashlib
        return hashlib.md5(self.body.encode()).hexdigest()[:16]
