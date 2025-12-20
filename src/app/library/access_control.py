"""
Access control helper for Library Tool.
Wraps existing can_access_room function for Library Tool use.
"""

from flask import current_app
from typing import Optional


def can_access_room_for_library(user_id: int, room_id: int) -> bool:
    """
    Verify user has access to room for Library Tool operations.
    
    This function wraps the existing can_access_room from src.app.access_control
    but accepts user_id and room_id as integers (for Library Tool convenience).
    
    Args:
        user_id: User ID to check
        room_id: Room ID to check
        
    Returns:
        True if user can access room, False otherwise
    """
    try:
        from src.app.access_control import can_access_room
        from src.models.room import Room
        from src.models.user import User
        
        # Get user and room objects
        user = User.query.get(user_id)
        room = Room.query.get(room_id)
        
        if not user or not room:
            return False
        
        # Use existing access control function
        return can_access_room(user, room)
    except Exception as e:
        current_app.logger.error(f"Error checking room access: {e}")
        return False

