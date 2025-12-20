"""
Utility functions for room management.
Pure functions with no side effects for easy testing.
"""

from typing import Optional, Dict, List, Tuple, Any
from src.models import Room, User, RoomMember
from datetime import datetime, timedelta
from ..types import ValidationResult

def get_invitation_count(user: Optional[User]) -> int:
    """Calculate pending invitations for navigation.

    Counts only invitations that are not yet accepted, regardless of age,
    and only for active rooms.
    """
    if not user:
        return 0

    # Exclude cases where the user has already participated in the room
    # (created a chat or posted a message) even if accepted_at wasn't set historically.
    from src.models import Chat, Message
    from sqlalchemy import exists, and_

    membership_q = RoomMember.query.join(Room).filter(
        RoomMember.user_id == user.id,
        Room.is_active == True,
        RoomMember.accepted_at.is_(None),
    )

    # Exists: user created a chat in this room
    has_chat = exists().where(and_(Chat.room_id == RoomMember.room_id, Chat.created_by == user.id))
    # Exists: user posted a message in any chat of this room
    has_message = exists().where(and_(Message.chat_id == Chat.id, Chat.room_id == RoomMember.room_id, Message.user_id == user.id))

    membership_q = membership_q.filter(~has_chat).filter(~exists().where(and_(Chat.room_id == RoomMember.room_id, has_message)))

    return membership_q.count()

def infer_template_type_from_room(room: Room) -> Optional[str]:
    """Infer template type from room characteristics."""
    if not room.goals:
        return None
    
    goals_lower = room.goals.lower()
    room_name_lower = room.name.lower()
    description_lower = (room.description or "").lower()
    
    template_patterns = {
        "academic-essay": [
            "research", "essay", "academic", "writing", "literature review",
            "thesis", "argument", "citation", "academic writing"
        ],
        "study-group": [
            "study", "collaborative", "peer", "group", "learning together",
            "shared", "collective", "team study"
        ],
        "business-hub": [
            "business", "entrepreneur", "startup", "commercial", "market",
            "profit", "enterprise", "corporate"
        ],
        "creative-studio": [
            "creative", "art", "design", "artistic", "visual", "creative process",
            "portfolio", "artwork", "design project"
        ],
        "writing-workshop": [
            "writing", "workshop", "composition", "creative writing", "narrative",
            "story", "poetry", "writing skills"
        ],
        "learning-lab": [
            "lab", "experiment", "hands-on", "practical", "skills", "learning",
            "practice", "experiential"
        ],
        "community-space": [
            "community", "network", "social", "collaboration", "discussion",
            "forum", "group", "community building"
        ]
    }
    
    # Check each template pattern
    for template_type, patterns in template_patterns.items():
        for pattern in patterns:
            if (pattern in goals_lower or 
                pattern in room_name_lower or 
                pattern in description_lower):
                return template_type
    
    return None

def validate_room_name(name: str) -> Tuple[bool, Optional[str]]:
    """Validate room name with detailed error messages."""
    if not name:
        return False, "Room name is required"
    if len(name) > 125:
        return False, "Room name must be 125 characters or less"
    if len(name.strip()) == 0:
        return False, "Room name cannot be empty"
    return True, None

def validate_group_size(group_size: str) -> Tuple[bool, Optional[str]]:
    """Validate group size with detailed error messages."""
    valid_sizes = ["small", "medium", "large", "individual"]
    if group_size and group_size not in valid_sizes:
        return False, f"Invalid group size. Must be one of: {', '.join(valid_sizes)}"
    return True, None

def validate_room_description(description: str) -> Tuple[bool, Optional[str]]:
    """Validate room description with detailed error messages."""
    if description and len(description) > 500:
        return False, "Room description must be 500 characters or less"
    return True, None

def validate_room_goals(goals: str) -> Tuple[bool, Optional[str]]:
    """Validate room goals with detailed error messages."""
    if not goals:
        return False, "Room goals are required"
    if len(goals.strip()) == 0:
        return False, "Room goals cannot be empty"
    if len(goals) > 2000:
        return False, "Room goals must be 2000 characters or less"
    return True, None

def validate_room_data(name: str, description: str, goals: str, group_size: str) -> ValidationResult:
    """Comprehensive validation of room data."""
    errors = []
    warnings = []
    
    # Validate name
    name_valid, name_error = validate_room_name(name)
    if not name_valid:
        errors.append(name_error)
    
    # Validate description
    desc_valid, desc_error = validate_room_description(description)
    if not desc_valid:
        errors.append(desc_error)
    
    # Validate goals
    goals_valid, goals_error = validate_room_goals(goals)
    if not goals_valid:
        errors.append(goals_error)
    
    # Validate group size
    size_valid, size_error = validate_group_size(group_size)
    if not size_valid:
        errors.append(size_error)
    
    # Add warnings for optional improvements
    if len(description) < 10 and description:
        warnings.append("Consider adding a more detailed description")
    
    if len(goals) < 20:
        warnings.append("Consider adding more specific learning goals")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def format_room_name(name: str) -> str:
    """Format room name for consistency."""
    return name.strip()

def format_room_description(description: str) -> str:
    """Format room description for consistency."""
    return description.strip() if description else ""

def format_room_goals(goals: str) -> str:
    """Format room goals for consistency."""
    return goals.strip()

def sanitize_room_data(name: str, description: str, goals: str, group_size: str) -> Dict[str, str]:
    """Sanitize and format room data."""
    return {
        "name": format_room_name(name),
        "description": format_room_description(description),
        "goals": format_room_goals(goals),
        "group_size": group_size.strip() if group_size else None
    }

def get_room_stats(room: Room) -> Dict[str, Any]:
    """Get comprehensive room statistics."""
    from src.models import Chat, Message, RoomMember
    
    # Count members
    total_members = RoomMember.query.filter_by(room_id=room.id).count()
    active_members = RoomMember.query.filter(
        RoomMember.room_id == room.id,
        RoomMember.accepted_at.isnot(None)
    ).count()
    
    # Count chats and messages
    total_chats = Chat.query.filter_by(room_id=room.id).count()
    total_messages = Message.query.join(Chat).filter(Chat.room_id == room.id).count()
    
    # Get last activity
    last_message = Message.query.join(Chat).filter(
        Chat.room_id == room.id
    ).order_by(Message.timestamp.desc()).first()
    
    last_activity = last_message.timestamp if last_message else room.created_at
    
    return {
        "total_members": total_members,
        "active_members": active_members,
        "total_chats": total_chats,
        "total_messages": total_messages,
        "last_activity": last_activity,
        "created_at": room.created_at
    }

def is_room_owner(room: Room, user: User) -> bool:
    """Check if user is the owner of the room."""
    return room.owner_id == user.id

def is_room_member(room: Room, user: User) -> bool:
    """Check if user is a member of the room."""
    return RoomMember.query.filter_by(
        room_id=room.id, 
        user_id=user.id
    ).first() is not None

def can_user_access_room(room: Room, user: User) -> bool:
    """Check if user can access the room."""
    if not room.is_active:
        return False
    return is_room_owner(room, user) or is_room_member(room, user)

def can_user_manage_room(room: Room, user: User) -> bool:
    """Check if user can manage the room."""
    return is_room_owner(room, user)

def can_user_invite_to_room(room: Room, user: User) -> bool:
    """Check if user can invite others to the room."""
    if not can_user_access_room(room, user):
        return False
    
    # Room owner can always invite
    if is_room_owner(room, user):
        return True
    
    # Check member permissions
    member = RoomMember.query.filter_by(
        room_id=room.id, 
        user_id=user.id
    ).first()
    
    return member and member.can_invite_members

def can_user_create_chats_in_room(room: Room, user: User) -> bool:
    """Check if user can create chats in the room."""
    if not can_user_access_room(room, user):
        return False
    
    # Room owner can always create chats
    if is_room_owner(room, user):
        return True
    
    # Check member permissions
    member = RoomMember.query.filter_by(
        room_id=room.id, 
        user_id=user.id
    ).first()
    
    return member and member.can_create_chats

def get_user_room_permissions(room: Room, user: User) -> Dict[str, bool]:
    """Get comprehensive user permissions for a room."""
    return {
        "can_access": can_user_access_room(room, user),
        "can_manage": can_user_manage_room(room, user),
        "can_invite": can_user_invite_to_room(room, user),
        "can_create_chats": can_user_create_chats_in_room(room, user),
        "is_owner": is_room_owner(room, user),
        "is_member": is_room_member(room, user)
    }

def format_room_for_display(room: Room, user: User) -> Dict[str, Any]:
    """Format room data for display in templates."""
    permissions = get_user_room_permissions(room, user)
    stats = get_room_stats(room)
    
    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
        "short_description": room.short_description,
        "goals": room.goals,
        "group_size": room.group_size,
        "is_active": room.is_active,
        "created_at": room.created_at,
        "owner_id": room.owner_id,
        "template_type": infer_template_type_from_room(room),
        "permissions": permissions,
        "stats": stats
    }

def search_rooms(query: str, user: User, limit: int = 20) -> List[Room]:
    """Search rooms accessible to the user."""
    from sqlalchemy import or_
    
    # Get rooms the user owns or is a member of
    owned_rooms = Room.query.filter_by(owner_id=user.id, is_active=True)
    member_rooms = Room.query.join(RoomMember).filter(
        RoomMember.user_id == user.id,
        Room.is_active == True,
        Room.owner_id != user.id
    )
    
    # Combine and search
    all_rooms = owned_rooms.union(member_rooms)
    
    if query:
        search_term = f"%{query}%"
        all_rooms = all_rooms.filter(
            or_(
                Room.name.ilike(search_term),
                Room.description.ilike(search_term),
                Room.goals.ilike(search_term)
            )
        )
    
    return all_rooms.order_by(Room.created_at.desc()).limit(limit).all()

def get_room_activity_summary(room: Room, days: int = 7) -> Dict[str, Any]:
    """Get room activity summary for the specified number of days."""
    from src.models import Message, Chat
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Recent messages
    recent_messages = Message.query.join(Chat).filter(
        Chat.room_id == room.id,
        Message.timestamp >= cutoff_date
    ).order_by(Message.timestamp.desc()).limit(10).all()
    
    # Recent chats
    recent_chats = Chat.query.filter_by(room_id=room.id).filter(
        Chat.created_at >= cutoff_date
    ).order_by(Chat.created_at.desc()).limit(5).all()
    
    # Activity count
    message_count = Message.query.join(Chat).filter(
        Chat.room_id == room.id,
        Message.timestamp >= cutoff_date
    ).count()
    
    chat_count = Chat.query.filter_by(room_id=room.id).filter(
        Chat.created_at >= cutoff_date
    ).count()
    
    return {
        "recent_messages": recent_messages,
        "recent_chats": recent_chats,
        "message_count": message_count,
        "chat_count": chat_count,
        "period_days": days,
        "cutoff_date": cutoff_date
    }
