"""
Database module for document storage using SQLAlchemy.
Railway PostgreSQL helpers for document operations.
"""

from typing import Optional, List
from src.app import db
from src.models.document import Document, DocumentChunk
from sqlalchemy import func
from flask import current_app

# Synthesis mode configuration constants
SYNTHESIS_MAX_DOCUMENTS = 5
SYNTHESIS_MAX_TOTAL_CHUNKS = 10
SYNTHESIS_CHUNK_TEXT_LIMIT = 400
SYNTHESIS_TOKEN_BUDGET = 1000


def get_document_by_file_id(file_id: str, room_id: Optional[int] = None) -> Optional[Document]:
    """
    Get document by file_id, optionally scoped to room.
    
    Args:
        file_id: Unique file identifier
        room_id: Optional room ID to scope query
        
    Returns:
        Document object or None if not found
    """
    try:
        query = Document.query.filter_by(file_id=file_id)
        if room_id:
            query = query.filter_by(room_id=room_id)
        return query.first()
    except Exception as e:
        # Tables don't exist (migration not run) - return None
        from flask import current_app
        current_app.logger.warning(f"Document tables not found (migration not run): {e}")
        return None


def get_all_documents(room_id: Optional[int] = None) -> List[Document]:
    """
    Get all documents, optionally scoped to room.
    
    Args:
        room_id: Optional room ID to scope query
        
    Returns:
        List of Document objects
    """
    try:
        query = Document.query
        if room_id:
            query = query.filter_by(room_id=room_id)
        return query.order_by(Document.uploaded_at.desc()).all()
    except Exception as e:
        # Tables don't exist (migration not run) - return empty list
        from flask import current_app
        current_app.logger.warning(f"Document tables not found (migration not run): {e}")
        return []


def get_room_storage_usage(room_id: int) -> dict:
    """
    Get storage usage statistics for a room.
    
    Args:
        room_id: Room ID to check
        
    Returns:
        Dict with total_bytes, file_count, limit_bytes, remaining_bytes, percent_used
    """
    STORAGE_LIMIT_BYTES = 10 * 1024 * 1024  # 10MB
    
    try:
        result = db.session.query(
            func.sum(Document.file_size).label('total_bytes'),
            func.count(Document.id).label('file_count')
        ).filter_by(room_id=room_id).first()
        
        total_bytes = int(result.total_bytes or 0)
        file_count = int(result.file_count or 0)
    except Exception as e:
        # Tables don't exist (migration not run) - return empty stats
        from flask import current_app
        current_app.logger.warning(f"Document tables not found (migration not run): {e}")
        total_bytes = 0
        file_count = 0
    
    remaining_bytes = max(0, STORAGE_LIMIT_BYTES - total_bytes)
    percent_used = (total_bytes / STORAGE_LIMIT_BYTES * 100) if STORAGE_LIMIT_BYTES > 0 else 0
    
    return {
        'total_bytes': total_bytes,
        'file_count': file_count,
        'limit_bytes': STORAGE_LIMIT_BYTES,
        'remaining_bytes': remaining_bytes,
        'percent_used': round(percent_used, 2)
    }


def get_representative_chunks_from_all_documents(
    room_id: int,
    chunks_per_doc: int = 2,
    max_documents: int = SYNTHESIS_MAX_DOCUMENTS,
    max_total_chunks: int = SYNTHESIS_MAX_TOTAL_CHUNKS,
    chunk_text_limit: int = SYNTHESIS_CHUNK_TEXT_LIMIT
) -> List[dict]:
    """
    Get representative chunks from each document in the room.
    Useful for synthesis/summarization tasks where you want coverage of all documents.
    
    Args:
        room_id: Room ID to get documents from
        chunks_per_doc: Number of chunks to get from each document (default: 2)
        max_documents: Maximum documents to process (default: 5, most recent)
        max_total_chunks: Hard limit on total chunks returned (default: 10)
        chunk_text_limit: Maximum characters per chunk (default: 400)
        
    Returns:
        List of chunk dicts with document_name, chunk_text (truncated), chunk_index
        Empty list if USE_RAILWAY_DOCUMENTS=false or no documents found
    """
    # Check feature flag
    try:
        from src.utils.documents.indexer import USE_RAILWAY_DOCUMENTS
        if not USE_RAILWAY_DOCUMENTS:
            current_app.logger.warning(
                f"USE_RAILWAY_DOCUMENTS=false. Synthesis mode disabled. "
                f"Set USE_RAILWAY_DOCUMENTS=true to enable Library Tool."
            )
            return []
    except ImportError:
        current_app.logger.error("Could not import USE_RAILWAY_DOCUMENTS feature flag")
        return []
    
    try:
        # Get most recent N documents
        all_documents = get_all_documents(room_id=room_id)
        documents = all_documents[:max_documents]
        
        if not documents:
            current_app.logger.info(f"No documents found in room {room_id}")
            return []
        
        if len(all_documents) > max_documents:
            current_app.logger.info(
                f"Room {room_id} has {len(all_documents)} documents. "
                f"Processing most recent {max_documents} for synthesis."
            )
        
        all_chunks = []
        
        for doc in documents:
            # Stop if we've reached the total chunk limit
            if len(all_chunks) >= max_total_chunks:
                current_app.logger.info(
                    f"Reached max_total_chunks limit ({max_total_chunks}). "
                    f"Stopping chunk collection."
                )
                break
            
            # Get total chunks for this document
            total_chunks = db.session.query(func.count(DocumentChunk.id))\
                .filter_by(document_id=doc.id).scalar() or 0
            
            if total_chunks == 0:
                continue
            
            # Calculate chunk indices to sample - FIXED LOGIC
            if total_chunks <= chunks_per_doc:
                # If document has few chunks, get all
                indices_to_get = list(range(total_chunks))
            elif chunks_per_doc == 2:
                # Explicit: first and last chunk
                indices_to_get = [0, total_chunks - 1]
            elif chunks_per_doc == 3:
                # Explicit: first, middle, last chunk
                indices_to_get = [0, total_chunks // 2, total_chunks - 1]
            else:
                # Evenly distributed: don't truncate after adding
                step = max(1, (total_chunks - 1) // (chunks_per_doc - 1))
                indices_to_get = [i * step for i in range(chunks_per_doc)]
                # Ensure last chunk is included
                if indices_to_get[-1] != total_chunks - 1:
                    indices_to_get[-1] = total_chunks - 1
            
            # Get chunks at these indices
            chunks = db.session.query(DocumentChunk)\
                .filter_by(document_id=doc.id)\
                .filter(DocumentChunk.chunk_index.in_(indices_to_get))\
                .order_by(DocumentChunk.chunk_index)\
                .all()
            
            for chunk in chunks:
                # Stop if we've reached the total chunk limit
                if len(all_chunks) >= max_total_chunks:
                    break
                
                # Truncate chunk text to limit
                chunk_text = chunk.chunk_text[:chunk_text_limit]
                if len(chunk.chunk_text) > chunk_text_limit:
                    chunk_text += "..."
                
                all_chunks.append({
                    'document_name': doc.name,
                    'chunk_text': chunk_text,
                    'chunk_index': chunk.chunk_index,
                    'document_id': doc.id,
                    'rank': 1.0  # All chunks treated equally for synthesis
                })
        
        current_app.logger.info(
            f"Synthesis mode: Retrieved {len(all_chunks)} chunks from {len(documents)} documents "
            f"(max: {max_total_chunks} chunks, {max_documents} docs)"
        )
        
        return all_chunks
        
    except Exception as e:
        current_app.logger.error(f"Error getting representative chunks: {e}", exc_info=True)
        return []


def get_document_summaries_only(room_id: int, max_docs: int = SYNTHESIS_MAX_DOCUMENTS) -> List[dict]:
    """
    Fallback: return document summaries instead of chunks when token budget is exceeded.
    
    Args:
        room_id: Room ID to get documents from
        max_docs: Maximum documents to return (default: 5)
        
    Returns:
        List of dicts with document_name, content (summary), chunk_index, rank
    """
    try:
        from src.utils.documents.indexer import USE_RAILWAY_DOCUMENTS
        if not USE_RAILWAY_DOCUMENTS:
            return []
    except ImportError:
        return []
    
    try:
        documents = get_all_documents(room_id=room_id)[:max_docs]
        summaries = []
        
        for doc in documents:
            summary_text = doc.summary or f"Document: {doc.name} (no summary available)"
            summaries.append({
                'document_name': doc.name,
                'content': summary_text[:500],  # Truncate summaries too
                'chunk_index': 0,
                'rank': 1.0
            })
        
        current_app.logger.info(
            f"Fallback mode: Retrieved summaries from {len(summaries)} documents"
        )
        
        return summaries
        
    except Exception as e:
        current_app.logger.error(f"Error getting document summaries: {e}", exc_info=True)
        return []

