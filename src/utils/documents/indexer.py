"""
Document indexing module using SQLAlchemy and Railway PostgreSQL.
Replaces Supabase-based implementation with Railway PostgreSQL.
Includes feature flag for safe migration and Supabase fallback.
"""

import os
from typing import List, Dict, Any, Optional
from uuid import uuid4
from sqlalchemy import func, text
from flask import current_app
from src.app import db
from src.models.document import Document, DocumentChunk
from src.models.room import Room
from src.utils.documents.chunking import chunk_text, Chunk, get_chunk_stats

# Feature flags
# Default to Railway-only (no Supabase fallback available in this codebase)
USE_RAILWAY_DOCUMENTS = os.getenv('USE_RAILWAY_DOCUMENTS', 'true').lower() == 'true'
ENABLE_RAILWAY_FALLBACK = os.getenv('ENABLE_RAILWAY_FALLBACK', 'false').lower() == 'true'


def index_document_railway(
    file_id: str,
    file_name: str,
    full_text: str,
    room_id: int,
    uploaded_by: int = None,
    chunking_method: str = 'paragraph',
    chunk_size: int = 1000,
    overlap: int = 200,
    file_size_bytes: int = None,
    summary: str = None
) -> Dict[str, Any]:
    """
    Index a document using SQLAlchemy and Railway PostgreSQL.
    
    Args:
        file_id: Unique file identifier
        file_name: Original filename
        full_text: Complete document text
        room_id: Room ID (required for scoping)
        uploaded_by: User ID who uploaded (optional)
        chunking_method: 'paragraph' or 'fixed'
        chunk_size: Target chunk size
        overlap: Overlap for fixed method
        file_size_bytes: File size in bytes
        summary: Document summary (optional)
        
    Returns:
        Dict with document_id, chunk_count, success status
    """
    try:
        # Verify room exists
        room = Room.query.get(room_id)
        if not room:
            raise ValueError(f"Room {room_id} not found")
        
        # Chunk the text
        chunks = chunk_text(
            full_text,
            method=chunking_method,
            chunk_size=chunk_size,
            overlap=overlap if chunking_method == 'fixed' else 200
        )
        
        stats = get_chunk_stats(chunks)
        
        # Create document record
        document = Document(
            file_id=file_id,
            name=file_name,
            full_text=full_text,
            file_size=file_size_bytes if file_size_bytes else len(full_text),
            room_id=room_id,
            uploaded_by=uploaded_by,
            summary=summary
        )
        
        db.session.add(document)
        db.session.flush()  # Get document.id
        
        # Insert chunks
        chunk_objects = []
        for chunk in chunks:
            chunk_obj = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.index,
                chunk_text=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                token_count=chunk.token_count
            )
            chunk_objects.append(chunk_obj)
        
        db.session.bulk_save_objects(chunk_objects)
        db.session.commit()
        
        current_app.logger.info(
            f"Railway: Indexed {len(chunks)} chunks for document {file_id} in room {room_id}"
        )
        
        return {
            'document_id': document.id,
            'file_id': file_id,
            'chunk_count': len(chunks),
            'total_tokens': stats['total_tokens'],
            'success': True
        }
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Railway indexing failed for {file_name}: {e}")
        raise Exception(f"Indexing failed for {file_name}: {str(e)}")


def search_railway(
    query: str,
    room_id: int,
    limit: int = 5,
    min_rank: float = 0.01
) -> List[Dict[str, Any]]:
    """
    Search chunks using PostgreSQL Full-Text Search via SQLAlchemy.
    
    Args:
        query: Search query
        room_id: Room ID to scope search
        limit: Maximum results
        min_rank: Minimum relevance score
        
    Returns:
        List of matching chunks with metadata
    """
    # Extract meaningful terms (keep existing function)
    search_query = extract_search_terms(query)
    
    try:
        # Build query using SQLAlchemy
        # Note: search_vector is TSVECTOR type, so we can use it directly
        search_query_ts = func.websearch_to_tsquery('english', search_query)
        
        base_query = db.session.query(
            DocumentChunk.id.label('chunk_id'),
            DocumentChunk.document_id,
            Document.name.label('document_name'),
            DocumentChunk.chunk_text,
            DocumentChunk.chunk_index,
            func.ts_rank(
                DocumentChunk.search_vector,
                search_query_ts
            ).label('rank')
        ).join(
            Document, DocumentChunk.document_id == Document.id
        ).filter(
            Document.room_id == room_id
        ).filter(
            DocumentChunk.search_vector.op('@@')(search_query_ts)
        )
        
        # Filter by minimum rank and order
        results = base_query.filter(
            func.ts_rank(
                DocumentChunk.search_vector,
                search_query_ts
            ) > min_rank
        ).order_by(
            text('rank DESC'),
            DocumentChunk.document_id,
            DocumentChunk.chunk_index
        ).limit(limit).all()
        
        # Format results
        formatted_results = []
        for row in results:
            formatted_results.append({
                'chunk_id': row.chunk_id,
                'document_id': row.document_id,
                'document_name': row.document_name,
                'chunk_text': row.chunk_text,
                'chunk_index': row.chunk_index,
                'rank': float(row.rank) if row.rank else 0.0
            })
        
        return formatted_results
        
    except Exception as e:
        current_app.logger.error(f"Railway search error: {e}", exc_info=True)
        return []


def index_document_supabase(
    file_id: str,
    file_name: str,
    full_text: str,
    room_id: int = None,
    uploaded_by: int = None,
    chunking_method: str = 'paragraph',
    chunk_size: int = 1000,
    overlap: int = 200,
    file_size_bytes: int = None,
    summary: str = None
) -> Dict[str, Any]:
    """
    Index document using Supabase (fallback/legacy).
    
    NOTE: Supabase is not available in this codebase. This function raises an error.
    Use Railway PostgreSQL instead by setting USE_RAILWAY_DOCUMENTS=true.
    """
    raise Exception(
        "Supabase is not available in this codebase. "
        "Set USE_RAILWAY_DOCUMENTS=true to use Railway PostgreSQL for document storage."
    )
    # Original Supabase code removed - not available in this codebase
    try:
        from src.utils.documents.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Generate document UUID
        doc_uuid = str(uuid4())
        
        # Save document metadata
        doc_data = {
            'id': doc_uuid,
            'file_id': file_id,
            'name': file_name,
            'full_text': full_text,
            'file_size': file_size_bytes if file_size_bytes else len(full_text),
            'room_id': room_id,
            'uploaded_by': uploaded_by,
            'summary': summary
        }
        
        doc_response = supabase.table('documents').insert(doc_data).execute()
        
        if hasattr(doc_response, 'error') and doc_response.error:
            raise Exception(f"Failed to insert document: {doc_response.error}")
        
        # Chunk the text
        chunks = chunk_text(
            full_text,
            method=chunking_method,
            chunk_size=chunk_size,
            overlap=overlap if chunking_method == 'fixed' else 200
        )
        
        stats = get_chunk_stats(chunks)
        
        # Insert chunks
        inserted_count = 0
        for chunk in chunks:
            chunk_record = {
                'document_id': doc_uuid,
                'chunk_index': chunk.index,
                'chunk_text': chunk.text,
                'start_char': chunk.start_char,
                'end_char': chunk.end_char,
                'token_count': chunk.token_count
            }
            
            response = supabase.table('document_chunks').insert(chunk_record).execute()
            
            if not (hasattr(response, 'error') and response.error):
                inserted_count += 1
        
        return {
            'document_id': doc_uuid,
            'file_id': file_id,
            'chunk_count': inserted_count,
            'total_tokens': stats['total_tokens'],
            'success': True
        }
        
    except Exception as e:
        current_app.logger.error(f"Supabase indexing failed: {e}")
        raise Exception(f"Supabase indexing failed: {str(e)}")


def search_supabase(
    query: str,
    room_id: int = None,
    limit: int = 5,
    min_rank: float = 0.01
) -> List[Dict[str, Any]]:
    """
    Search chunks using Supabase (fallback/legacy).
    
    NOTE: Supabase is not available in this codebase. This function raises an error.
    Use Railway PostgreSQL instead by setting USE_RAILWAY_DOCUMENTS=true to use Railway PostgreSQL for document search.
    """
    raise Exception(
        "Supabase is not available in this codebase. "
        "Set USE_RAILWAY_DOCUMENTS=true to use Railway PostgreSQL for document search."
    )
    # Original Supabase code removed - not available in this codebase
    try:
        from src.utils.documents.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        search_query = extract_search_terms(query)
        
        # Call PostgreSQL function for FTS
        params = {
            'query_text': search_query,
            'match_limit': limit,
            'min_rank': min_rank
        }
        
        if room_id:
            # Use room-scoped search if available
            response = supabase.rpc(
                'search_chunks_by_room',
                {'target_room_id': room_id, **params}
            ).execute()
        else:
            response = supabase.rpc('search_chunks', params).execute()
        
        if hasattr(response, 'error') and response.error:
            current_app.logger.error(f"Supabase search error: {response.error}")
            return []
        
        results = response.data or []
        
        # Format results
        formatted_results = []
        for row in results:
            formatted_results.append({
                'chunk_id': row.get('chunk_id'),
                'document_id': row.get('document_id'),
                'document_name': row.get('document_name', 'Unknown'),
                'chunk_text': row.get('chunk_text', ''),
                'chunk_index': row.get('chunk_index', 0),
                'rank': float(row.get('rank', 0.0))
            })
        
        return formatted_results
        
    except Exception as e:
        current_app.logger.error(f"Supabase search error: {e}", exc_info=True)
        return []


def index_document(
    file_id: str,
    file_name: str,
    full_text: str,
    room_id: int,
    uploaded_by: int = None,
    chunking_method: str = 'paragraph',
    chunk_size: int = 1000,
    overlap: int = 200,
    file_size_bytes: int = None,
    summary: str = None
) -> Dict[str, Any]:
    """
    Index a document with feature flag support.
    
    Uses Railway if USE_RAILWAY_DOCUMENTS=true, otherwise Supabase.
    """
    if USE_RAILWAY_DOCUMENTS:
        return index_document_railway(
            file_id=file_id,
            file_name=file_name,
            full_text=full_text,
            room_id=room_id,
            uploaded_by=uploaded_by,
            chunking_method=chunking_method,
            chunk_size=chunk_size,
            overlap=overlap,
            file_size_bytes=file_size_bytes,
            summary=summary
        )
    else:
        # Railway disabled - Supabase not available in this codebase
        current_app.logger.error(
            f"USE_RAILWAY_DOCUMENTS=false but Supabase not available. "
            f"Cannot index document. Set USE_RAILWAY_DOCUMENTS=true to enable Library Tool."
        )
        raise Exception(
            "Library Tool requires USE_RAILWAY_DOCUMENTS=true. "
            "Supabase fallback is not available in this codebase."
        )


def search_indexed_chunks(
    query: str,
    room_id: int,
    limit: int = 5,
    min_rank: float = 0.01
) -> List[Dict[str, Any]]:
    """
    Search chunks with Railway and Supabase fallback.
    
    If Railway is enabled, tries Railway first, then falls back to Supabase
    if Railway fails or returns empty results.
    """
    if USE_RAILWAY_DOCUMENTS:
        try:
            results = search_railway(query, room_id, limit, min_rank)
            if results:
                current_app.logger.info(
                    f"Railway search successful: {len(results)} results for room {room_id}"
                )
                return results
            else:
                current_app.logger.warning(
                    f"Railway search returned empty results for room {room_id}, query: {query[:50]}"
                )
        except Exception as e:
            current_app.logger.error(
                f"Railway search failed for room {room_id}: {e}",
                exc_info=True
            )
        
        # Fallback to Supabase (disabled by default - Supabase not available)
        if ENABLE_RAILWAY_FALLBACK:
            current_app.logger.warning(
                f"ENABLE_RAILWAY_FALLBACK=true but Supabase not available in this codebase. "
                f"Returning empty results for room {room_id}."
            )
            return []
    
    # Default: Railway only (Supabase not available in this codebase)
    # If Railway is disabled, return empty results rather than failing
    current_app.logger.warning(
        f"USE_RAILWAY_DOCUMENTS=false but Supabase not available. "
        f"Returning empty results for room {room_id}. "
        f"Set USE_RAILWAY_DOCUMENTS=true to enable Library Tool."
    )
    return []


def extract_search_terms(query: str) -> str:
    """
    Extract meaningful search terms from natural language queries.
    
    Removes common stop words and question words that don't help FTS.
    Uses OR logic so any matching term will return results.
    Falls back to original query if no terms remain.
    
    Args:
        query: Natural language query
        
    Returns:
        Cleaned query with OR operators between terms
    """
    # Comprehensive stop words list
    stop_words = {
        # Question words
        'what', 'when', 'where', 'who', 'why', 'how', 'which', 'whose',
        # Verbs
        'does', 'do', 'did', 'doing', 'done',
        'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'having',
        'can', 'could', 'would', 'should', 'may', 'might', 'will', 'shall',
        # Articles and determiners
        'the', 'a', 'an', 'this', 'that', 'these', 'those',
        # Pronouns
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their',
        'my', 'your', 'his', 'her', 'its', 'our',
        # Prepositions
        'in', 'on', 'at', 'to', 'for', 'of', 'with', 'from', 'by',
        'about', 'as', 'into', 'through', 'during', 'before', 'after',
        'above', 'below', 'between', 'under', 'over',
        # Conjunctions
        'and', 'or', 'but', 'if', 'than', 'because', 'while',
        # Common verbs
        'say', 'says', 'said', 'tell', 'tells', 'told',
        'according', 'according to'
    }
    
    # Split into words and remove punctuation
    import re
    words = re.findall(r'\b\w+\b', query.lower())
    
    # Keep words that aren't stop words and are longer than 2 characters
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for w in meaningful_words:
        if w not in seen:
            seen.add(w)
            unique_words.append(w)
    
    # If we removed everything, use original query
    if not unique_words:
        return query
    
    # Join with OR operator for PostgreSQL websearch_to_tsquery
    cleaned_query = ' OR '.join(unique_words)
    
    # Log the transformation
    if cleaned_query != query.lower():
        current_app.logger.debug(
            f"Query simplified: '{query}' → '{cleaned_query}'"
        )
    
    return cleaned_query


def get_document_by_file_id(file_id: str, room_id: int = None) -> Optional[Dict[str, Any]]:
    """
    Get document metadata by file_id.
    
    Args:
        file_id: Application file identifier
        room_id: Optional room ID for scoping
        
    Returns:
        Document record or None if not found
    """
    if USE_RAILWAY_DOCUMENTS:
        from src.utils.documents.database import get_document_by_file_id as get_railway_doc
        doc = get_railway_doc(file_id, room_id)
        if doc:
            return {
                'id': doc.id,
                'file_id': doc.file_id,
                'name': doc.name,
                'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                'summary': doc.summary,
                'file_size': doc.file_size
            }
        return None
    else:
        # Railway disabled - Supabase not available
        current_app.logger.error(
            "USE_RAILWAY_DOCUMENTS=false but Supabase not available. "
            "Set USE_RAILWAY_DOCUMENTS=true to enable Library Tool."
        )
        return None


def get_all_documents(room_id: int = None) -> List[Dict[str, Any]]:
    """
    Get all documents with chunk counts.
    
    Args:
        room_id: Optional room ID for scoping
        
    Returns:
        List of document dictionaries
    """
    if USE_RAILWAY_DOCUMENTS:
        from src.utils.documents.database import get_all_documents as get_railway_docs
        documents = get_railway_docs(room_id)
        
        result = []
        for doc in documents:
            chunk_count = db.session.query(func.count(DocumentChunk.id))\
                .filter_by(document_id=doc.id).scalar() or 0
            
            result.append({
                'id': doc.id,
                'file_id': doc.file_id,
                'name': doc.name,
                'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                'chunk_count': chunk_count,
                'summary': doc.summary or '',
                'file_size': doc.file_size
            })
        
        return result
    else:
        # Railway disabled - Supabase not available
        current_app.logger.error(
            "USE_RAILWAY_DOCUMENTS=false but Supabase not available. "
            "Set USE_RAILWAY_DOCUMENTS=true to enable Library Tool."
        )
        return []


def delete_document_and_chunks(file_id: str, room_id: int = None) -> bool:
    """
    Delete document and chunks by file_id.
    
    Args:
        file_id: Application file identifier
        room_id: Optional room ID for scoping
        
    Returns:
        True if deletion successful, False otherwise
    """
    if USE_RAILWAY_DOCUMENTS:
        try:
            from src.utils.documents.database import get_document_by_file_id
            document = get_document_by_file_id(file_id, room_id)
            if not document:
                return False
            
            db.session.delete(document)  # Chunks cascade automatically
            db.session.commit()
            current_app.logger.info(f"Railway: Deleted document {file_id}")
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Railway delete error: {e}")
            return False
    else:
        # Railway disabled - Supabase not available
        current_app.logger.error(
            "USE_RAILWAY_DOCUMENTS=false but Supabase not available. "
            "Set USE_RAILWAY_DOCUMENTS=true to enable Library Tool."
        )
        return False


def delete_all_documents(room_id: int = None) -> bool:
    """
    Delete all documents and chunks.
    
    Args:
        room_id: Optional room ID for scoping
        
    Returns:
        True if successful, False otherwise
    """
    if USE_RAILWAY_DOCUMENTS:
        try:
            query = Document.query
            if room_id:
                query = query.filter_by(room_id=room_id)
            
            documents = query.all()
            for doc in documents:
                db.session.delete(doc)  # Chunks cascade
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Railway delete all error: {e}")
            return False
    else:
        # Railway disabled - Supabase not available
        current_app.logger.error(
            "USE_RAILWAY_DOCUMENTS=false but Supabase not available. "
            "Set USE_RAILWAY_DOCUMENTS=true to enable Library Tool."
        )
        return False

