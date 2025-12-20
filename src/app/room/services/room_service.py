"""
Room business logic service layer.
Handles all room-related business operations.
"""

from typing import Optional, Dict, Any, List
from flask import current_app
from src.app import db
from src.models import Room, User, RoomMember, CustomPrompt, Chat
from ..types import RoomCreationData, RoomServiceResult, RoomUpdateData, RoomFilterData
from ..utils.room_utils import (
    validate_room_name, 
    validate_group_size, 
    validate_room_description,
    validate_room_goals,
    sanitize_room_data,
    get_user_room_permissions,
    format_room_for_display,
    search_rooms,
    get_room_stats,
    get_room_activity_summary
)
from src.utils.room_descriptions import generate_unique_room_name, generate_room_short_description
from src.utils.openai_utils import generate_room_modes
from src.app.room.utils.refinement_utils import record_refinement_history
from src.models import Chat as _Chat

class RoomService:
    """Service class for room operations."""
    
    @staticmethod
    def create_room(data: RoomCreationData, user: User) -> RoomServiceResult:
        """Create a new room with comprehensive error handling."""
        try:
            current_app.logger.info(
                f"[RoomService.create_room] user_id={getattr(user, 'id', None)} name={data.name!r} group_size={data.group_size!r} template_type={data.template_type!r}"
            )
            # Validate input
            name_valid, name_error = validate_room_name(data.name)
            if not name_valid:
                return RoomServiceResult(success=False, error=name_error)
            
            size_valid, size_error = validate_group_size(data.group_size)
            if not size_valid:
                return RoomServiceResult(success=False, error=size_error)
            
            desc_valid, desc_error = validate_room_description(data.description or "")
            if not desc_valid:
                return RoomServiceResult(success=False, error=desc_error)
            
            goals_valid, goals_error = validate_room_goals(data.goals)
            if not goals_valid:
                return RoomServiceResult(success=False, error=goals_error)
            
            # Sanitize data
            sanitized_data = sanitize_room_data(
                data.name, 
                data.description or "", 
                data.goals, 
                data.group_size or ""
            )
            
            # Generate unique name
            unique_name = generate_unique_room_name(sanitized_data["name"], user.id)
            
            # Generate description
            short_description = generate_room_short_description(
                template_type=data.template_type or "general",
                room_name=sanitized_data["name"],
                group_size=sanitized_data["group_size"],
                goals=sanitized_data["goals"]
            )
            
            # Create room
            room = Room(
                name=unique_name,
                description=sanitized_data["description"],
                short_description=short_description,
                goals=sanitized_data["goals"],
                group_size=sanitized_data["group_size"],
                owner_id=user.id,
                is_active=True
            )
            
            db.session.add(room)
            db.session.flush()  # Get the room ID
            
            # Generate modes
            try:
                current_app.logger.info(
                    f"[RoomService.create_room] generating modes for room_id={room.id} template_type={data.template_type!r}"
                )
                modes = generate_room_modes(room, template_name=data.template_type)
                if modes:
                    for mode_key, mode_info in modes.items():
                        custom_prompt = CustomPrompt(
                            mode_key=mode_key,
                            label=mode_info.label,
                            prompt=mode_info.prompt,
                            room_id=room.id,
                            created_by=user.id,
                        )
                        db.session.add(custom_prompt)
                current_app.logger.info(
                    f"[RoomService.create_room] modes_saved={len(modes) if modes else 0} for room_id={room.id}"
                )
            except Exception as mode_error:
                current_app.logger.warning(f"Mode generation failed for room {room.id}: {mode_error}")
            
            db.session.commit()
            
            current_app.logger.info(f"Room created successfully: {room.name} (ID: {room.id}) by user {user.id}")
            
            # Baseline snapshot: record initial modes as history (non-blocking)
            try:
                baseline_modes = []
                try:
                    # Reconstruct modes saved to CustomPrompt
                    from src.models import CustomPrompt as _CP
                    cps = _CP.query.filter_by(room_id=room.id).all()
                    baseline_modes = [
                        {"key": cp.mode_key, "label": cp.label, "prompt": cp.prompt}
                        for cp in cps
                    ]
                except Exception:
                    baseline_modes = []
                record_refinement_history(
                    room_id=room.id,
                    user_id=user.id,
                    preference="baseline",
                    old_modes=[],
                    new_modes=baseline_modes,
                    summary="Initial learning steps saved",
                )
            except Exception:
                pass

            return RoomServiceResult(
                success=True,
                data={
                    "room_id": room.id,
                    "room_name": room.name,
                    "original_name": data.name,
                },
                room_id=room.id
            )
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[RoomService.create_room] error: {e}")
            return RoomServiceResult(
                success=False,
                error="Failed to create room. Please try again."
            )
    
    @staticmethod
    def get_user_rooms(user: User) -> Dict[str, List[Room]]:
        """Get all rooms for a user with proper error handling."""
        try:
            owned_rooms = Room.query.filter_by(
                owner_id=user.id, 
                is_active=True
            ).order_by(Room.created_at.desc()).all()
            
            member_rooms = Room.query.join(RoomMember).filter(
                RoomMember.user_id == user.id,
                Room.is_active == True,
                Room.owner_id != user.id
            ).order_by(Room.created_at.desc()).all()
            
            return {
                "owned": owned_rooms,
                "member": member_rooms
            }
        except Exception as e:
            current_app.logger.error(f"Error fetching user rooms: {e}")
            return {"owned": [], "member": []}
    
    @staticmethod
    def get_room_by_id(room_id: int, user: User) -> Optional[Room]:
        """Get a room by ID with access control."""
        try:
            room = Room.query.get(room_id)
            if not room:
                return None
            
            # Check if user can access the room
            permissions = get_user_room_permissions(room, user)
            if not permissions["can_access"]:
                return None
            
            return room
        except Exception as e:
            current_app.logger.error(f"Error fetching room {room_id}: {e}")
            return None
    
    @staticmethod
    def update_room(room_id: int, data: RoomUpdateData, user: User) -> RoomServiceResult:
        """Update a room with comprehensive validation."""
        try:
            room = Room.query.get(room_id)
            if not room:
                return RoomServiceResult(success=False, error="Room not found")
            
            # Check if user can manage the room
            permissions = get_user_room_permissions(room, user)
            if not permissions["can_manage"]:
                return RoomServiceResult(success=False, error="You don't have permission to edit this room")
            
            # Validate updates
            if data.name is not None:
                name_valid, name_error = validate_room_name(data.name)
                if not name_valid:
                    return RoomServiceResult(success=False, error=name_error)
                room.name = data.name.strip()
            
            if data.description is not None:
                desc_valid, desc_error = validate_room_description(data.description)
                if not desc_valid:
                    return RoomServiceResult(success=False, error=desc_error)
                room.description = data.description.strip()
            
            if data.goals is not None:
                goals_valid, goals_error = validate_room_goals(data.goals)
                if not goals_valid:
                    return RoomServiceResult(success=False, error=goals_error)
                room.goals = data.goals.strip()
            
            if data.group_size is not None:
                size_valid, size_error = validate_group_size(data.group_size)
                if not size_valid:
                    return RoomServiceResult(success=False, error=size_error)
                room.group_size = data.group_size
            
            if data.is_active is not None:
                room.is_active = data.is_active
            
            db.session.commit()
            
            current_app.logger.info(f"Room {room_id} updated by user {user.id}")
            
            return RoomServiceResult(
                success=True,
                data={"room_id": room.id},
                room_id=room.id
            )
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating room {room_id}: {e}")
            return RoomServiceResult(
                success=False,
                error="Failed to update room. Please try again."
            )
    
    @staticmethod
    def delete_room(room_id: int, user: User) -> RoomServiceResult:
        """Delete a room (soft delete by setting is_active=False)."""
        try:
            room = Room.query.get(room_id)
            if not room:
                return RoomServiceResult(success=False, error="Room not found")
            
            # Check if user can manage the room
            permissions = get_user_room_permissions(room, user)
            if not permissions["can_manage"]:
                return RoomServiceResult(success=False, error="You don't have permission to delete this room")
            
            # Soft delete
            room.is_active = False
            db.session.commit()
            
            current_app.logger.info(f"Room {room_id} deleted (soft) by user {user.id}")
            
            return RoomServiceResult(
                success=True,
                data={"room_id": room.id},
                room_id=room.id
            )
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting room {room_id}: {e}")
            return RoomServiceResult(
                success=False,
                error="Failed to delete room. Please try again."
            )
    
    @staticmethod
    def search_user_rooms(query: str, user: User, limit: int = 20) -> List[Room]:
        """Search rooms accessible to the user."""
        try:
            return search_rooms(query, user, limit)
        except Exception as e:
            current_app.logger.error(f"Error searching rooms: {e}")
            return []
    
    @staticmethod
    def get_room_display_data(room: Room, user: User) -> Dict[str, Any]:
        """Get formatted room data for display."""
        try:
            return format_room_for_display(room, user)
        except Exception as e:
            current_app.logger.error(f"Error formatting room data: {e}")
            return {}
    
    @staticmethod
    def get_room_statistics(room: Room) -> Dict[str, Any]:
        """Get room statistics."""
        try:
            return get_room_stats(room)
        except Exception as e:
            current_app.logger.error(f"Error getting room stats: {e}")
            return {}
    
    @staticmethod
    def get_room_activity(room: Room, days: int = 7) -> Dict[str, Any]:
        """Get room activity summary."""
        try:
            return get_room_activity_summary(room, days)
        except Exception as e:
            current_app.logger.error(f"Error getting room activity: {e}")
            return {}
    
    @staticmethod
    def get_room_chats(room: Room, user: User, limit: int = 50) -> List[Chat]:
        """Get chats in a room."""
        try:
            # Check if user can access the room
            permissions = get_user_room_permissions(room, user)
            if not permissions["can_access"]:
                return []
            
            return Chat.query.filter_by(room_id=room.id).order_by(
                Chat.created_at.desc()
            ).limit(limit).all()
            
        except Exception as e:
            current_app.logger.error(f"Error getting room chats: {e}")
            return []

    @staticmethod
    def get_room_chat_count(room: Room) -> int:
        try:
            return _Chat.query.filter_by(room_id=room.id).count()
        except Exception:
            return 0
    
    @staticmethod
    def get_room_members(room: Room, user: User) -> List[User]:
        """Get room members as User objects."""
        try:
            # Check if user can access the room
            permissions = get_user_room_permissions(room, user)
            if not permissions["can_access"]:
                return []
            
            # Get room members and convert to User objects
            members = RoomMember.query.filter_by(room_id=room.id).all()
            member_users = [User.query.get(member.user_id) for member in members]
            
            # Add room owner to member list if not already included
            owner = User.query.get(room.owner_id)
            if owner and owner not in member_users:
                member_users.append(owner)
            
            return member_users
            
        except Exception as e:
            current_app.logger.error(f"Error getting room members: {e}")
            return []
    
    @staticmethod
    def filter_rooms(filters: RoomFilterData, user: User, limit: int = 50) -> List[Room]:
        """Filter rooms based on criteria."""
        try:
            query = Room.query.filter(Room.is_active == True)
            
            # Apply filters
            if filters.owner_id:
                query = query.filter(Room.owner_id == filters.owner_id)
            
            if filters.template_type:
                # This would need to be implemented based on how template types are stored
                pass
            
            if filters.group_size:
                query = query.filter(Room.group_size == filters.group_size)
            
            if filters.search_query:
                from sqlalchemy import or_
                search_term = f"%{filters.search_query}%"
                query = query.filter(
                    or_(
                        Room.name.ilike(search_term),
                        Room.description.ilike(search_term),
                        Room.goals.ilike(search_term)
                    )
                )
            
            # Filter to only rooms user can access
            owned_rooms = query.filter(Room.owner_id == user.id)
            member_rooms = query.join(RoomMember).filter(RoomMember.user_id == user.id)
            
            all_rooms = owned_rooms.union(member_rooms)
            
            return all_rooms.order_by(Room.created_at.desc()).limit(limit).all()
            
        except Exception as e:
            current_app.logger.error(f"Error filtering rooms: {e}")
            return []
    
    @staticmethod
    def get_room_permissions(room: Room, user: User) -> Dict[str, bool]:
        """Get user permissions for a room."""
        try:
            return get_user_room_permissions(room, user)
        except Exception as e:
            current_app.logger.error(f"Error getting room permissions: {e}")
            return {
                "can_access": False,
                "can_manage": False,
                "can_invite": False,
                "can_create_chats": False,
                "is_owner": False,
                "is_member": False
            }
