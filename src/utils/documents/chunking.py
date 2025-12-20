"""
Text chunking utilities for document indexing.
Supports fixed-size and paragraph-based chunking strategies.
"""

from typing import List
import re


class Chunk:
    """Represents a text chunk with metadata."""
    
    def __init__(self, text: str, index: int, start_char: int, end_char: int):
        self.text = text
        self.index = index
        self.start_char = start_char
        self.end_char = end_char
        self.token_count = estimate_tokens(text)
    
    def to_dict(self):
        """Convert chunk to dictionary for database storage."""
        return {
            'text': self.text,
            'index': self.index,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'token_count': self.token_count
        }


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation using character count / 4.
    This is a simple approximation: 1 token ≈ 4 characters for English text.
    """
    return len(text) // 4


def chunk_by_fixed_size(
    text: str, 
    chunk_size: int = 1000, 
    overlap: int = 200
) -> List[Chunk]:
    """
    Split text into fixed-size chunks with overlap.
    
    Intelligently breaks at sentence or word boundaries when possible
    to avoid cutting mid-sentence.
    
    Args:
        text: Input text to chunk
        chunk_size: Target size in characters (default 1000)
        overlap: Overlap between consecutive chunks (default 200)
        
    Returns:
        List of Chunk objects
        
    Example:
        >>> text = "This is a long document. It has many sentences..."
        >>> chunks = chunk_by_fixed_size(text, chunk_size=500, overlap=100)
        >>> len(chunks)
        5
    """
    chunks = []
    start = 0
    index = 0
    text_length = len(text)
    
    while start < text_length:
        # Determine end position
        end = min(start + chunk_size, text_length)
        
        # Try to break at natural boundaries if not at document end
        if end < text_length:
            # Look for sentence boundaries (., ?, !)
            sentence_break = max(
                text.rfind('.', start, end),
                text.rfind('?', start, end),
                text.rfind('!', start, end)
            )
            
            # If we found a sentence break at least halfway through the chunk, use it
            if sentence_break > start + chunk_size // 2:
                end = sentence_break + 1
            else:
                # Fallback to word boundary
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
        
        # Extract chunk text and clean it
        chunk_text = text[start:end].strip()
        
        # Only add non-empty chunks
        if chunk_text:
            chunks.append(Chunk(chunk_text, index, start, end))
            index += 1
        
        # Move start forward with overlap
        # Ensure we always make progress (don't get stuck)
        start = max(start + 1, end - overlap)
    
    return chunks


def chunk_by_paragraph(
    text: str, 
    max_chunk_size: int = 1000
) -> List[Chunk]:
    """
    Split text by paragraphs, combining small ones to reach target size.
    
    This method preserves document structure by respecting paragraph boundaries.
    Good for documents with clear paragraph structure.
    
    Args:
        text: Input text
        max_chunk_size: Maximum chunk size in characters (default 1000)
        
    Returns:
        List of Chunk objects
        
    Example:
        >>> text = "Para 1.\\n\\nPara 2.\\n\\nPara 3."
        >>> chunks = chunk_by_paragraph(text, max_chunk_size=50)
        >>> len(chunks)
        2
    """
    # Split by double newlines (paragraph separators)
    paragraphs = re.split(r'\n\n+', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    current_start = 0
    index = 0
    
    char_position = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            char_position += 2  # Account for paragraph separator
            continue
        
        para_size = len(para)
        
        # If adding this paragraph would exceed max size and we have content, save current chunk
        if current_size + para_size > max_chunk_size and current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(Chunk(
                chunk_text, 
                index, 
                current_start, 
                current_start + len(chunk_text)
            ))
            index += 1
            
            # Start new chunk
            current_chunk = []
            current_size = 0
            current_start = char_position
        
        # Add paragraph to current chunk
        current_chunk.append(para)
        current_size += para_size + 2  # +2 for paragraph separator
        char_position += para_size + 2
    
    # Add final chunk if it has content
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        chunks.append(Chunk(
            chunk_text, 
            index, 
            current_start, 
            current_start + len(chunk_text)
        ))
    
    return chunks


def chunk_text(
    text: str,
    method: str = 'paragraph',
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[Chunk]:
    """
    Main chunking function with method selection.
    
    Args:
        text: Text to chunk
        method: Chunking method - 'fixed' or 'paragraph' (default)
        chunk_size: Target size for chunks (used by both methods)
        overlap: Overlap size (only for 'fixed' method)
        
    Returns:
        List of Chunk objects
        
    Raises:
        ValueError: If method is not recognized
        
    Example:
        >>> text = "Long document text..."
        >>> chunks = chunk_text(text, method='paragraph')
        >>> for chunk in chunks:
        ...     print(f"Chunk {chunk.index}: {len(chunk.text)} chars")
    """
    if not text or not text.strip():
        return []
    
    if method == 'fixed':
        return chunk_by_fixed_size(text, chunk_size, overlap)
    elif method == 'paragraph':
        return chunk_by_paragraph(text, chunk_size)
    else:
        raise ValueError(f"Unknown chunking method: {method}. Use 'fixed' or 'paragraph'.")


def get_chunk_stats(chunks: List[Chunk]) -> dict:
    """
    Get statistics about a list of chunks.
    
    Useful for debugging and optimization.
    
    Args:
        chunks: List of Chunk objects
        
    Returns:
        Dictionary with statistics
        
    Example:
        >>> chunks = chunk_text("Some text...", method='paragraph')
        >>> stats = get_chunk_stats(chunks)
        >>> print(f"Average chunk size: {stats['avg_size']} chars")
    """
    if not chunks:
        return {
            'count': 0,
            'total_chars': 0,
            'avg_size': 0,
            'min_size': 0,
            'max_size': 0,
            'total_tokens': 0
        }
    
    sizes = [len(chunk.text) for chunk in chunks]
    tokens = [chunk.token_count for chunk in chunks]
    
    return {
        'count': len(chunks),
        'total_chars': sum(sizes),
        'avg_size': sum(sizes) // len(sizes),
        'min_size': min(sizes),
        'max_size': max(sizes),
        'total_tokens': sum(tokens)
    }


