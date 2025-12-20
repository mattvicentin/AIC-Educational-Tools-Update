"""
API route handlers.
Handles JSON API endpoints for room operations.
"""

from flask import Blueprint, request, jsonify, current_app
from typing import Any, Dict, List, Optional
from datetime import datetime
from src.app import db
from src.models import Room, User, Chat, Message, RoomMember
from ..services.room_service import RoomService
from ..types import RoomCreationData, RoomUpdateData, RoomFilterData
from ..utils.room_utils import get_invitation_count
from src.app.access_control import get_current_user, require_login, require_room_access

api_bp = Blueprint('room_api', __name__)

@api_bp.route("/rooms", methods=["GET"])
@require_login
def get_rooms() -> Any:
    """Get all rooms for the current user."""
    try:
        user = get_current_user()
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        search = request.args.get('search', '').strip()
        template_type = request.args.get('template_type', '').strip()
        group_size = request.args.get('group_size', '').strip()
        
        if search:
            # Use search functionality
            rooms = RoomService.search_user_rooms(search, user, limit)
        else:
            # Use filter functionality
            filters = RoomFilterData(
                template_type=template_type if template_type else None,
                group_size=group_size if group_size else None
            )
            rooms = RoomService.filter_rooms(filters, user, limit)
        
        # Format rooms for API response
        rooms_data = []
        for room in rooms:
            room_data = RoomService.get_room_display_data(room, user)
            rooms_data.append(room_data)
        
        return jsonify({
            "success": True,
            "rooms": rooms_data,
            "count": len(rooms_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting rooms via API: {e}")
        return jsonify({"error": "Failed to get rooms"}), 500

@api_bp.route("/rooms/<int:room_id>", methods=["GET"])
@require_room_access
def get_room(room_id: int) -> Any:
    """Get detailed information about a specific room."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get comprehensive room data
        room_data = RoomService.get_room_display_data(room, user)
        stats = RoomService.get_room_statistics(room)
        activity = RoomService.get_room_activity(room)
        
        return jsonify({
            "success": True,
            "room": room_data,
            "stats": stats,
            "activity": activity
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting room {room_id} via API: {e}")
        return jsonify({"error": "Failed to get room"}), 500

@api_bp.route("/rooms", methods=["POST"])
@require_login
def create_room() -> Any:
    """Create a new room via API."""
    try:
        user = get_current_user()
        
        # Parse JSON data
        data_dict = request.get_json()
        if not data_dict:
            return jsonify({"error": "No data provided"}), 400
        
        # Create room data object
        data = RoomCreationData(
            name=data_dict.get('name', '').strip(),
            description=data_dict.get('description', '').strip(),
            goals=data_dict.get('goals', '').strip(),
            group_size=data_dict.get('group_size', '').strip(),
            template_type=data_dict.get('template_type', '').strip()
        )
        
        # Use service layer
        result = RoomService.create_room(data, user)
        
        if result.success:
            # Get the created room data
            room = RoomService.get_room_by_id(result.room_id, user)
            room_data = RoomService.get_room_display_data(room, user) if room else {}
            
            return jsonify({
                "success": True,
                "message": "Room created successfully",
                "room": room_data,
                "room_id": result.room_id
            }), 201
        else:
            return jsonify({
                "success": False,
                "error": result.error
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error creating room via API: {e}")
        return jsonify({"error": "Failed to create room"}), 500

@api_bp.route("/rooms/<int:room_id>", methods=["PUT"])
@require_room_access
def update_room(room_id: int) -> Any:
    """Update a room via API."""
    try:
        user = get_current_user()
        
        # Parse JSON data
        data_dict = request.get_json()
        if not data_dict:
            return jsonify({"error": "No data provided"}), 400
        
        # Create update data object
        update_data = RoomUpdateData(
            name=data_dict.get('name'),
            description=data_dict.get('description'),
            goals=data_dict.get('goals'),
            group_size=data_dict.get('group_size'),
            is_active=data_dict.get('is_active')
        )
        
        # Use service layer
        result = RoomService.update_room(room_id, update_data, user)
        
        if result.success:
            # Get updated room data
            room = RoomService.get_room_by_id(room_id, user)
            room_data = RoomService.get_room_display_data(room, user) if room else {}
            
            return jsonify({
                "success": True,
                "message": "Room updated successfully",
                "room": room_data
            })
        else:
            return jsonify({
                "success": False,
                "error": result.error
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error updating room {room_id} via API: {e}")
        return jsonify({"error": "Failed to update room"}), 500

@api_bp.route("/rooms/<int:room_id>", methods=["DELETE"])
@require_room_access
def delete_room(room_id: int) -> Any:
    """Delete a room via API."""
    try:
        user = get_current_user()
        
        # Use service layer
        result = RoomService.delete_room(room_id, user)
        
        if result.success:
            return jsonify({
                "success": True,
                "message": "Room deleted successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": result.error
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error deleting room {room_id} via API: {e}")
        return jsonify({"error": "Failed to delete room"}), 500

@api_bp.route("/rooms/<int:room_id>/chats", methods=["GET"])
@require_room_access
def get_room_chats(room_id: int) -> Any:
    """Get chats for a room via API."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get parameters
        limit = request.args.get('limit', 50, type=int)
        
        # Get chats
        chats = RoomService.get_room_chats(room, user, limit)
        
        # Format chats
        chats_data = []
        for chat in chats:
            chats_data.append({
                "id": chat.id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "created_by": chat.created_by,
                "is_active": chat.is_active,
                "room_id": chat.room_id
            })
        
        return jsonify({
            "success": True,
            "chats": chats_data,
            "count": len(chats_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting chats for room {room_id} via API: {e}")
        return jsonify({"error": "Failed to get chats"}), 500

@api_bp.route("/rooms/<int:room_id>/members", methods=["GET"])
@require_room_access
def get_room_members(room_id: int) -> Any:
    """Get members for a room via API."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get members
        members = RoomService.get_room_members(room, user)
        
        # Format members
        members_data = []
        for member in members:
            members_data.append({
                "id": member.id,
                "user_id": member.user_id,
                "display_name": member.display_name,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "accepted_at": member.accepted_at.isoformat() if member.accepted_at else None,
                "can_create_chats": member.can_create_chats,
                "can_invite_members": member.can_invite_members,
                "is_pending": member.accepted_at is None
            })
        
        return jsonify({
            "success": True,
            "members": members_data,
            "count": len(members_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting members for room {room_id} via API: {e}")
        return jsonify({"error": "Failed to get members"}), 500

@api_bp.route("/rooms/<int:room_id>/stats", methods=["GET"])
@require_room_access
def get_room_stats(room_id: int) -> Any:
    """Get statistics for a room via API."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get statistics
        stats = RoomService.get_room_statistics(room)
        
        # Get activity data
        days = request.args.get('days', 7, type=int)
        activity = RoomService.get_room_activity(room, days)
        
        return jsonify({
            "success": True,
            "stats": stats,
            "activity": activity
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting stats for room {room_id} via API: {e}")
        return jsonify({"error": "Failed to get statistics"}), 500

@api_bp.route("/search", methods=["GET"])
@require_login
def search_rooms() -> Any:
    """Search rooms via API."""
    try:
        user = get_current_user()
        
        # Get search parameters
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 20, type=int)
        
        if not query:
            return jsonify({"error": "Search query is required"}), 400
        
        # Search rooms
        rooms = RoomService.search_user_rooms(query, user, limit)
        
        # Format results
        rooms_data = []
        for room in rooms:
            room_data = RoomService.get_room_display_data(room, user)
            rooms_data.append(room_data)
        
        return jsonify({
            "success": True,
            "results": rooms_data,
            "count": len(rooms_data),
            "query": query
        })
        
    except Exception as e:
        current_app.logger.error(f"Error searching rooms via API: {e}")
        return jsonify({"error": "Failed to search rooms"}), 500

@api_bp.route("/user/invitations", methods=["GET"])
@require_login
def get_user_invitations() -> Any:
    """Get pending invitations for the current user via API."""
    try:
        user = get_current_user()
        
        # Get pending invitations
        pending = RoomMember.query.filter_by(
            user_id=user.id,
            accepted_at=None
        ).join(Room).filter(Room.is_active == True).all()
        
        # Format invitations
        invitations_data = []
        for invitation in pending:
            room = Room.query.get(invitation.room_id)
            invitations_data.append({
                "id": invitation.id,
                "room_id": invitation.room_id,
                "room_name": room.name if room else "Unknown Room",
                "room_description": room.description if room else "",
                "display_name": invitation.display_name,
                "joined_at": invitation.joined_at.isoformat() if invitation.joined_at else None,
                "can_create_chats": invitation.can_create_chats,
                "can_invite_members": invitation.can_invite_members
            })
        
        return jsonify({
            "success": True,
            "invitations": invitations_data,
            "count": len(invitations_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user invitations via API: {e}")
        return jsonify({"error": "Failed to get invitations"}), 500

@api_bp.route("/health", methods=["GET"])
def health_check() -> Any:
    """Health check endpoint for the room API."""
    try:
        return jsonify({
            "status": "healthy",
            "service": "room_api",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
