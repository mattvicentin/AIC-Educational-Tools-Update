"""Document storage management - Railway PostgreSQL version with room scoping"""

from flask import request, jsonify, current_app, session
from functools import wraps
import os

from . import library
from src.utils.documents.indexer import delete_document_and_chunks, delete_all_documents, get_all_documents
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


@library.route('/clear', methods=['POST'])
@login_required
def clear_storage():
    """
    Delete documents from storage, scoped to room.
    
    Request body:
        {
            "ids": ["file-id-1", "file-id-2"],  // optional, deletes all in room if omitted
            "room_id": 123  // Required
        }
    """
    try:
        data = request.get_json() or {}
        ids = data.get('ids', None)
        room_id = data.get('room_id')
        if room_id is not None:
            try:
                room_id = int(room_id)
            except (ValueError, TypeError):
                room_id = None
        
        if not room_id:
            return jsonify({'error': 'room_id is required'}), 400
        
        # Get current user from session
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Verify user has access to room
        if not can_access_room(user.id, room_id):
            current_app.logger.warning(
                f"User {user.id} attempted to delete documents in room {room_id} without access"
            )
            return jsonify({
                'error': 'You do not have access to this room.'
            }), 403
        
        deleted_count = 0
        
        if ids and len(ids) > 0:
            # Delete specific documents (scoped to room)
            current_app.logger.info(f"Deleting {len(ids)} documents from room {room_id}")
            for file_id in ids:
                if delete_document_and_chunks(file_id, room_id=room_id):
                    deleted_count += 1
        else:
            # Delete all documents in room
            current_app.logger.info(f"Deleting all documents from room {room_id}")
            if delete_all_documents(room_id=room_id):
                deleted_count = -1  # Indicate "all deleted"
        
        current_app.logger.info(f"Deleted {deleted_count} documents from room {room_id}")
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Clear storage error: {e}")
        return jsonify({'error': f'Failed to clear storage: {str(e)}'}), 500


@library.route('/documents', methods=['GET'])
@login_required
def list_documents():
    """
    Get list of all uploaded documents in a room.
    
    Query parameters:
        room_id: Required - Room ID to list documents for
    
    Returns:
        {
            "documents": [
                {
                    "id": "uuid",
                    "file_id": "uuid",
                    "name": "document.pdf",
                    "uploaded_at": "2025-11-03T...",
                    "chunk_count": 5,
                    "summary": "..."
                }
            ]
        }
    """
    try:
        room_id = request.args.get('room_id', type=int)
        
        if not room_id:
            return jsonify({'error': 'room_id query parameter is required'}), 400
        
        # Get current user from session
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Verify user has access to room
        if not can_access_room(user.id, room_id):
            current_app.logger.warning(
                f"User {user.id} attempted to list documents in room {room_id} without access"
            )
            return jsonify({
                'error': 'You do not have access to this room.'
            }), 403
        
        try:
            documents = get_all_documents(room_id=room_id)
            
            current_app.logger.info(f"Retrieved {len(documents)} documents for room {room_id}")
            
            return jsonify({
                'documents': documents
            }), 200
        except Exception as e:
            current_app.logger.error(f"List documents error: {e}")
            # Return empty list if tables don't exist
            return jsonify({
                'documents': [],
                'error': 'Database tables not initialized. Run migration to enable Library Tool.'
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"List documents error: {e}")
        return jsonify({'error': f'Failed to list documents: {str(e)}'}), 500


@library.route('/storage/stats', methods=['GET'])
@login_required
def get_storage_stats():
    """
    Get storage usage statistics for a room.
    
    Query parameters:
        room_id: Required - Room ID to get stats for
    
    Returns:
        {
            "used_bytes": 1234567,
            "limit_bytes": 10485760,
            "used_mb": 1.18,
            "limit_mb": 10.0,
            "percentage": 11.77,
            "documents_count": 5
        }
    """
    try:
        room_id = request.args.get('room_id', type=int)
        
        if not room_id:
            return jsonify({'error': 'room_id query parameter is required'}), 400
        
        # Get current user from session
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Verify user has access to room
        if not can_access_room(user.id, room_id):
            current_app.logger.warning(
                f"User {user.id} attempted to get storage stats for room {room_id} without access"
            )
            return jsonify({
                'error': 'You do not have access to this room.'
            }), 403
        
        storage_stats = get_room_storage_usage(room_id)
        
        stats = {
            'used_bytes': storage_stats['total_bytes'],
            'limit_bytes': storage_stats['limit_bytes'],
            'used_mb': round(storage_stats['total_bytes'] / (1024 * 1024), 2),
            'limit_mb': round(storage_stats['limit_bytes'] / (1024 * 1024), 2),
            'percentage': storage_stats['percent_used'],
            'documents_count': storage_stats['file_count']
        }
        
        current_app.logger.info(
            f"Storage stats for room {room_id}: {stats['used_mb']}MB / {stats['limit_mb']}MB ({stats['percentage']}%)"
        )
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Get storage stats error: {e}")
        # Return empty stats if tables don't exist (graceful degradation)
        error_msg = str(e)
        if 'no such table' in error_msg.lower() or ('relation' in error_msg.lower() and 'does not exist' in error_msg.lower()):
            return jsonify({
                'used_bytes': 0,
                'limit_bytes': 10 * 1024 * 1024,
                'used_mb': 0,
                'limit_mb': 10.0,
                'percentage': 0,
                'documents_count': 0
            }), 200
        return jsonify({'error': f'Failed to get storage stats: {str(e)}'}), 500

