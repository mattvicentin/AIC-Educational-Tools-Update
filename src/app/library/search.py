"""Document search endpoint - Railway PostgreSQL version with room scoping"""

from flask import request, jsonify, current_app, session
from functools import wraps

from . import library
from src.utils.documents.indexer import search_indexed_chunks
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


@library.route('/search', methods=['POST'])
@login_required
def search_documents():
    """
    Search indexed documents using Full-Text Search, scoped to room.
    
    Request body:
        {
            "query": "search terms",
            "room_id": 123,  // Required
            "limit": 5,      // optional
            "min_rank": 0.01 // optional
        }
    
    Response:
        {
            "results": [
                {
                    "document_name": "file.pdf",
                    "chunk_text": "...",
                    "chunk_index": 3,
                    "rank": 0.245
                }
            ]
        }
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query'].strip()
        room_id = data.get('room_id', type=int)
        limit = data.get('limit', 5)
        min_rank = data.get('min_rank', 0.01)
        
        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        if not room_id:
            return jsonify({'error': 'room_id is required'}), 400
        
        # Get current user from session
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Verify user has access to room
        if not can_access_room(user.id, room_id):
            current_app.logger.warning(
                f"User {user.id} attempted to search room {room_id} without access"
            )
            return jsonify({
                'error': 'You do not have access to this room.'
            }), 403
        
        current_app.logger.info(f"Searching documents in room {room_id}: '{query}' (limit={limit})")
        
        # Search indexed chunks (scoped to room)
        results = search_indexed_chunks(
            query=query,
            room_id=room_id,
            limit=limit,
            min_rank=min_rank
        )
        
        # Format results
        formatted_results = [
            {
                'document_name': r['document_name'],
                'chunk_text': r['chunk_text'],
                'chunk_index': r['chunk_index'],
                'rank': r['rank']
            }
            for r in results
        ]
        
        current_app.logger.info(f"Found {len(formatted_results)} matching chunks in room {room_id}")
        
        return jsonify({'results': formatted_results}), 200
        
    except Exception as e:
        current_app.logger.error(f"Search error: {e}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

