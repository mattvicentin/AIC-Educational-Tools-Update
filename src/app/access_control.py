"""Access control utilities for room and chat permissions.

This module provides helper methods and decorators for checking
user permissions on rooms and chats in the room-based architecture.
"""

from functools import wraps
import os
from flask import session, redirect, url_for, flash, abort, current_app
from flask import request, jsonify
from src.app import db
from datetime import datetime
from src.models import Chat, User, Room, RoomMember
from typing import Any, Optional


def get_current_user() -> Optional[User]:
    """Get the currently logged-in user from session."""
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None


def is_admin(user: Optional[User]) -> bool:
    """Check if the given user is an admin based on ADMIN_EMAILS env var.

    ADMIN_EMAILS should be a comma-separated list of email addresses.
    Matching is case-insensitive and trimmed.
    """
    if not user or not getattr(user, 'email', None):
        return False
    allowlist = os.getenv('ADMIN_EMAILS', '')
    if not allowlist:
        return False
    emails = [e.strip().lower() for e in allowlist.split(',') if e.strip()]
    return user.email.strip().lower() in emails


def require_admin(f):
    """Decorator to restrict access to admin users (ENV-based allowlist)."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in to access this page.")
            return redirect(url_for("auth.login"))
        if not is_admin(user):
            # Prefer a 403 for APIs; for pages, flash + redirect
            if request.accept_mimetypes.best == 'application/json':
                return jsonify({"error": "forbidden"}), 403
            flash("You don't have permission to access this page.", "error")
            return redirect(url_for("room.room_crud.index"))
        return f(*args, **kwargs)

    return decorated_function


def is_room_member(user: Optional[User], room: Optional[Room]) -> bool:
    """Check if a user is a member of a room.

    Args:
        user: User object or None for anonymous users
        room: Room object to check membership for

    Returns:
        bool: True if user is a member of the room, False otherwise
    """
    if not user or not room:
        return False

    # Room owner is always a member
    if room.owner_id == user.id:
        return True

    # Check if user has a membership record
    membership = RoomMember.query.filter_by(room_id=room.id, user_id=user.id).first()

    return membership is not None


def can_access_room(user: Optional[User], room: Optional[Room]) -> bool:
    """Check if a user can access a room.

    Args:
        user: User object or None for anonymous users
        room: Room object to check access for

    Returns:
        bool: True if user can access the room, False otherwise
    """
    if not room or not room.is_active:
        return False
    # Admins have full access
    if is_admin(user):
        return True
    # Only room members can access
    return is_room_member(user, room)


def can_manage_room(user: Optional[User], room: Optional[Room]) -> bool:
    """Check if a user can manage a room (owner only).

    Args:
        user: User object (must be authenticated)
        room: Room object to check management permissions for

    Returns:
        bool: True if user can manage the room, False otherwise
    """
    if not user or not room:
        return False
    # Admins can manage any room
    if is_admin(user):
        return True
    # Only room owner can manage
    return room.owner_id == user.id


def can_create_chats_in_room(user: Optional[User], room: Optional[Room]) -> bool:
    """Check if a user can create chats in a room.

    Args:
        user: User object (must be authenticated)
        room: Room object to check permissions for

    Returns:
        bool: True if user can create chats in the room, False otherwise
    """
    if not user or not room:
        return False
    # Admins and room owner can always create chats
    if is_admin(user) or room.owner_id == user.id:
        return True

    # Check if user has create_chats permission
    membership = RoomMember.query.filter_by(
        room_id=room.id, user_id=user.id, can_create_chats=True
    ).first()

    return membership is not None


def can_invite_to_room(user: Optional[User], room: Optional[Room]) -> bool:
    """Check if a user can invite others to a room.

    Args:
        user: User object (must be authenticated)
        room: Room object to check permissions for

    Returns:
        bool: True if user can invite to the room, False otherwise
    """
    if not user or not room:
        return False
    # Admins and room owner can always invite
    if is_admin(user) or room.owner_id == user.id:
        return True

    # Check if user has invite permissions
    membership = RoomMember.query.filter_by(
        room_id=room.id, user_id=user.id, can_invite_members=True
    ).first()

    return membership is not None


def can_access_chat(user: Optional[User], chat: Optional[Chat]) -> bool:
    """Check if a user can access a chat within a room.

    Args:
        user: User object or None for anonymous users
        chat: Chat object to check access for

    Returns:
        bool: True if user can access the chat, False otherwise
    """
    if not chat:
        return False
    # Admins have full access
    if is_admin(user):
        return True
    # Check if user can access the room that contains this chat
    return can_access_room(user, chat.room)


def can_edit_chat(user: Optional[User], chat: Optional[Chat]) -> bool:
    """Check if a user can edit a chat.

    Args:
        user: User object (must be authenticated)
        chat: Chat object to check edit permissions for

    Returns:
        bool: True if user can edit the chat, False otherwise
    """
    if not user or not chat:
        return False
    # Admins can edit any chat
    if is_admin(user):
        return True
    # Chat creator can always edit
    if chat.created_by == user.id:
        return True

    # Room owner can edit any chat in their room
    if chat.room.owner_id == user.id:
        return True

    # Room members can edit chats (collaborative environment)
    return is_room_member(user, chat.room)


def can_delete_chat(user: Optional[User], chat: Optional[Chat]) -> bool:
    """Check if a user can delete a chat.

    Args:
        user: User object (must be authenticated)
        chat: Chat object to check delete permissions for

    Returns:
        bool: True if user can delete the chat, False otherwise
    """
    if not user or not chat:
        return False
    # Admins can delete any chat
    if is_admin(user):
        return True
    # Chat creator can delete
    if chat.created_by == user.id:
        return True

    # Room owner can delete any chat in their room
    return chat.room.owner_id == user.id


def require_login(f):
    """Decorator to require user authentication."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in to access this page.")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def require_room_access(f):
    """Decorator to require room access permissions."""

    @wraps(f)
    def decorated_function(room_id, *args, **kwargs):
        from flask import current_app
        
        user = get_current_user()
        
        # First check if user is logged in
        if not user:
            current_app.logger.error(f"🔐 NO USER: Redirecting to login for room {room_id}")
            flash("Please log in to access this room.")
            return redirect(url_for("auth.login"))
        
        current_app.logger.error(f"🔍 LOOKING UP ROOM: {room_id}")
        room = Room.query.get(room_id)  # Don't 404 yet, let's see what we get
        current_app.logger.error(f"🔍 ROOM LOOKUP RESULT: {room.name if room else 'None'} (ID: {room.id if room else 'None'})")
        
        if not room:
            current_app.logger.error(f"🔍 ROOM {room_id} NOT FOUND - RETURNING 404")
            from flask import abort
            abort(404)
        
        # Continue with the original room object

        if not can_access_room(user, room):
            current_app.logger.error(f"🔐 NO ACCESS: User {user.username} denied access to room {room_id}")
            flash("You don't have access to this room.")
            return redirect(url_for("room.room_crud.index"))

        # If the user has a pending invitation (accepted_at is NULL), mark as accepted
        try:
            membership = RoomMember.query.filter_by(room_id=room_id, user_id=user.id).first()
            if membership and getattr(membership, 'accepted_at', None) is None:
                membership.accepted_at = datetime.utcnow()
                db.session.commit()
        except Exception:
            # Don't block access on failure to mark acceptance
            db.session.rollback()

        current_app.logger.error(f"🔐 ACCESS GRANTED: User {user.username} accessing room {room_id} - CALLING FUNCTION")
        return f(room_id, *args, **kwargs)

    return decorated_function


def require_room_management(f):
    """Decorator to require room management permissions (owner only)."""

    @wraps(f)
    def decorated_function(room_id, *args, **kwargs):
        room = Room.query.get_or_404(room_id)
        user = get_current_user()

        if not user:
            flash("Please log in to manage rooms.")
            return redirect(url_for("auth.login"))

        if not can_manage_room(user, room):
            flash("You can only manage rooms you own.")
            return redirect(url_for("room.room_crud.view_room", room_id=room_id))

        return f(room_id, *args, **kwargs)

    return decorated_function


def require_chat_access(f):
    """Decorator to require chat access permissions."""

    @wraps(f)
    def decorated_function(chat_id, *args, **kwargs):
        chat = Chat.query.get_or_404(chat_id)
        user = get_current_user()

        if not can_access_chat(user, chat):
            flash("You don't have access to this chat.")
            return redirect(url_for("room.room_crud.index"))

        # Mark invitation accepted when entering a chat of the room
        try:
            membership = RoomMember.query.filter_by(room_id=chat.room_id, user_id=user.id).first()
            if membership and getattr(membership, 'accepted_at', None) is None:
                # Nested transaction so failures don't poison the main session
                with db.session.begin_nested():
                    membership.accepted_at = datetime.utcnow()
        except Exception:
            db.session.rollback()

        return f(chat_id, *args, **kwargs)

    return decorated_function


def require_chat_edit(f):
    """Decorator to require chat edit permissions."""

    @wraps(f)
    def decorated_function(chat_id, *args, **kwargs):
        chat = Chat.query.get_or_404(chat_id)
        user = get_current_user()

        if not user:
            flash("Please log in to edit chats.")
            return redirect(url_for("auth.login"))

        if not can_edit_chat(user, chat):
            flash("You can only edit chats you created or in rooms you own.")
            return redirect(url_for("chat.view_chat", chat_id=chat_id))

        return f(chat_id, *args, **kwargs)

    return decorated_function


def require_chat_delete(f):
    """Decorator to require chat delete permissions."""

    @wraps(f)
    def decorated_function(chat_id, *args, **kwargs):
        chat = Chat.query.get_or_404(chat_id)
        user = get_current_user()

        if not user:
            flash("Please log in to delete chats.")
            return redirect(url_for("auth.login"))

        if not can_delete_chat(user, chat):
            flash("You can only delete chats you created or in rooms you own.")
            return redirect(url_for("chat.view_chat", chat_id=chat_id))

        return f(chat_id, *args, **kwargs)

    return decorated_function
