"""Document upload endpoint - Railway PostgreSQL version with room scoping"""

from flask import request, jsonify, current_app, session
from werkzeug.utils import secure_filename
from uuid import uuid4
import os
from functools import wraps

from . import library
from src.utils.documents.extract_text import extract_text
from src.utils.documents.indexer import index_document
from src.utils.documents.database import get_room_storage_usage
from src.app.access_control import get_current_user

from .access_control import can_access_room_for_library as can_access_room


def login_required(f):
    """Session-based login required decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@library.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """
    Handle file uploads, extract text, chunk, and index in Railway PostgreSQL.
    
    Room ID is extracted from query parameter (canonical source) or chat context (fallback).
    """
    try:
        # Extract room_id from query parameter (canonical source)
        room_id = request.args.get('room_id', type=int)
        
        # Fallback: Try to get from chat context if available
        if not room_id:
            chat_id = request.args.get('chat_id', type=int)
            if chat_id:
                try:
                    from src.models.chat import Chat
                    chat = Chat.query.get(chat_id)
                    if chat and chat.room_id:
                        room_id = chat.room_id
                except Exception:
                    pass
        
        # Fail closed if no room_id
        if not room_id:
            return jsonify({
                'error': 'room_id is required. Please provide room_id query parameter.'
            }), 400
        
        # Get current user from session
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Verify user has access to room
        if not can_access_room(user.id, room_id):
            current_app.logger.warning(
                f"User {user.id} attempted to upload to room {room_id} without access"
            )
            return jsonify({
                'error': 'You do not have access to this room.'
            }), 403
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # VALIDATION: Check file size against storage limit
        STORAGE_LIMIT_BYTES = 10 * 1024 * 1024  # 10 MB
        
        # Get file size
        file.seek(0, os.SEEK_END)
        file_size_bytes = file.tell()
        file.seek(0)  # Reset file pointer to beginning
        
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Get current storage usage for this room
        try:
            storage_stats = get_room_storage_usage(room_id)
            current_usage_bytes = storage_stats['total_bytes']
            available_bytes = storage_stats['remaining_bytes']
            available_mb = available_bytes / (1024 * 1024)
            
            # Check if file would exceed storage limit
            if file_size_bytes > available_bytes:
                current_app.logger.warning(
                    f"Upload rejected: file size {file_size_mb:.2f}MB exceeds "
                    f"available storage {available_mb:.2f}MB for room {room_id}"
                )
                return jsonify({
                    'error': f'File size ({file_size_mb:.2f} MB) exceeds available storage '
                             f'({available_mb:.2f} MB). Please delete some documents to free up space before uploading or choose a smaller document.'
                }), 400
        except Exception as e:
            current_app.logger.error(f"Storage check failed: {e}")
            # Continue with upload if we can't check storage (graceful degradation)
        
        # Generate unique file ID
        file_id = str(uuid4())
        file_name = secure_filename(file.filename) if file.filename else 'unnamed_file'
        
        # Extract text and generate summary
        try:
            extracted = extract_text(file)
            full_text = extracted['fullText']
            first_chunks = extracted['firstChunks']
            summary = extracted['summary']
        except ValueError as e:
            current_app.logger.error(f"Text extraction error: {e}")
            return jsonify({'error': f'Failed to process file: {str(e)}'}), 400
        
        # Index the document (chunk and store)
        chunk_count = 0
        current_app.logger.info(f"Indexing document: {file_name} (file_id: {file_id}) in room {room_id}")
        
        try:
            # Detect chunking method
            is_pdf = file_name.lower().endswith('.pdf')
            has_paragraphs = '\n\n' in full_text
            text_size = len(full_text)
            chunking_method = 'fixed' if (is_pdf or not has_paragraphs or text_size > 50000) else 'paragraph'
            
            current_app.logger.info(f"Using {chunking_method.upper()} chunking method")
            
            index_result = index_document(
                file_id=file_id,
                file_name=file_name,
                full_text=full_text,
                room_id=room_id,  # Pass room_id for scoping
                uploaded_by=user.id,
                chunking_method=chunking_method,
                chunk_size=1000,
                overlap=200,
                file_size_bytes=file_size_bytes,
                summary=summary
            )
            chunk_count = index_result['chunk_count']
            current_app.logger.info(f"✓ Indexed {chunk_count} chunks for {file_name} in room {room_id}")
            
        except Exception as e:
            current_app.logger.error(f"Indexing failed: {e}")
            return jsonify({'error': f'Indexing failed: {str(e)}'}), 500
        
        return jsonify({
            'fileId': file_id,
            'summary': summary,
            'textPreview': first_chunks,
            'chunkCount': chunk_count
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {e}")
        error_msg = str(e)
        # Check if it's a table missing error
        if 'no such table' in error_msg.lower() or ('relation' in error_msg.lower() and 'does not exist' in error_msg.lower()):
            return jsonify({
                'error': 'Database tables not initialized. Please run migration: alembic upgrade head'
            }), 500
        return jsonify({'error': f'Upload failed: {error_msg}'}), 500

