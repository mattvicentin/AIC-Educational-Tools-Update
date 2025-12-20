#!/usr/bin/env python3
"""
pin_helpers.py
Purpose: Helper functions for pinning/unpinning messages and comments
Status: [ACTIVE]
Created: 2025-12-01
Author: AI Collab Team

Provides idempotent pin operations with IntegrityError handling.
"""

from typing import Optional, Dict, Any, Set
from sqlalchemy.exc import IntegrityError
import logging

from src.app import db
from src.models import PinnedItem, Message, Comment, User

logger = logging.getLogger(__name__)


def is_pinned(
    user_id: int, 
    message_id: Optional[int] = None, 
    comment_id: Optional[int] = None
) -> bool:
    """
    Check if a message or comment is pinned by the user.
    
    Args:
        user_id: ID of the user
        message_id: Optional message ID to check
        comment_id: Optional comment ID to check
        
    Returns:
        True if pinned, False otherwise
    """
    try:
        PinnedItem.validate_exactly_one_item(message_id, comment_id)
    except ValueError:
        return False
    
    query = PinnedItem.query.filter_by(user_id=user_id)
    
    if message_id is not None:
        query = query.filter_by(message_id=message_id)
    else:
        query = query.filter_by(comment_id=comment_id)
    
    return query.first() is not None


def pin_item(
    user: User,
    message: Optional[Message] = None,
    comment: Optional[Comment] = None,
    shared: bool = False
) -> Dict[str, Any]:
    """
    Pin a message or comment for the user.
    
    Idempotent: Returns success even if already pinned.
    
    Args:
        user: User object doing the pinning
        message: Optional Message object to pin
        comment: Optional Comment object to pin
        shared: Whether to create as a shared pin (default: personal)
        
    Returns:
        Dict with keys: success (bool), pinned (bool), created (bool), is_shared (bool), error (str)
    """
    try:
        # Validate exactly one item
        message_id = message.id if message else None
        comment_id = comment.id if comment else None
        
        PinnedItem.validate_exactly_one_item(message_id, comment_id)
        
        # Get item details
        if message:
            chat_id = message.chat_id
            room_id = message.chat.room_id
            role = message.role
            content = message.content
        else:  # comment
            chat_id = comment.chat_id
            room_id = comment.chat.room_id
            role = None  # Comments don't have roles
            content = comment.content
        
        # Truncate content
        content_snapshot = PinnedItem.truncate_content(content)
        
        # Create pin
        pin = PinnedItem(
            user_id=user.id,
            room_id=room_id,
            chat_id=chat_id,
            message_id=message_id,
            comment_id=comment_id,
            role=role,
            content=content_snapshot,
            is_shared=shared
        )
        
        db.session.add(pin)
        db.session.commit()
        
        visibility = 'shared' if shared else 'personal'
        logger.info(f"User {user.id} pinned {'message' if message else 'comment'} {message_id or comment_id} ({visibility})")
        
        return {
            'success': True,
            'pinned': True,
            'created': True,
            'is_shared': shared
        }
        
    except ValueError as e:
        # Validation error
        logger.warning(f"Pin validation error: {e}")
        return {
            'success': False,
            'pinned': False,
            'error': str(e)
        }
        
    except IntegrityError as e:
        # Already pinned - rollback and return success anyway (idempotent)
        db.session.rollback()
        logger.debug(f"Pin already exists for user {user.id} - idempotent success")
        
        return {
            'success': True,
            'pinned': True,
            'created': False  # Indicate it already existed
        }
        
    except Exception as e:
        # Other database errors
        db.session.rollback()
        logger.error(f"Error pinning item: {e}")
        
        return {
            'success': False,
            'pinned': False,
            'error': 'Failed to pin item'
        }


def unpin_item(
    user: User,
    message: Optional[Message] = None,
    comment: Optional[Comment] = None
) -> Dict[str, Any]:
    """
    Unpin a message or comment for the user.
    
    Idempotent: Returns success even if not pinned.
    
    Args:
        user: User object doing the unpinning
        message: Optional Message object to unpin
        comment: Optional Comment object to unpin
        
    Returns:
        Dict with keys: success (bool), pinned (bool), deleted (bool), error (str)
    """
    try:
        # Validate exactly one item
        message_id = message.id if message else None
        comment_id = comment.id if comment else None
        
        PinnedItem.validate_exactly_one_item(message_id, comment_id)
        
        # Find and delete pin
        query = PinnedItem.query.filter_by(user_id=user.id)
        
        if message:
            query = query.filter_by(message_id=message_id)
        else:
            query = query.filter_by(comment_id=comment_id)
        
        pin = query.first()
        
        if pin:
            db.session.delete(pin)
            db.session.commit()
            
            logger.info(f"User {user.id} unpinned {'message' if message else 'comment'} {message_id or comment_id}")
            
            return {
                'success': True,
                'pinned': False,
                'deleted': True
            }
        else:
            # Not pinned - return success anyway (idempotent)
            logger.debug(f"Pin doesn't exist for user {user.id} - idempotent success")
            
            return {
                'success': True,
                'pinned': False,
                'deleted': False  # Indicate it didn't exist
            }
        
    except ValueError as e:
        # Validation error
        logger.warning(f"Unpin validation error: {e}")
        return {
            'success': False,
            'pinned': False,
            'error': str(e)
        }
        
    except Exception as e:
        # Database errors
        db.session.rollback()
        logger.error(f"Error unpinning item: {e}")
        
        return {
            'success': False,
            'pinned': False,
            'error': 'Failed to unpin item'
        }


def get_pinned_ids_for_chat(user_id: int, chat_id: int) -> Dict[str, Set[int]]:
    """
    Get all pinned message and comment IDs for a user in a specific chat.
    
    Args:
        user_id: ID of the user
        chat_id: ID of the chat
        
    Returns:
        Dict with 'messages' and 'comments' keys containing sets of IDs
    """
    try:
        pins = PinnedItem.query.filter_by(
            user_id=user_id,
            chat_id=chat_id
        ).all()
        
        message_ids = {
            pin.message_id 
            for pin in pins 
            if pin.message_id is not None
        }
        
        comment_ids = {
            pin.comment_id 
            for pin in pins 
            if pin.comment_id is not None
        }
        
        return {
            'messages': message_ids,
            'comments': comment_ids
        }
        
    except Exception as e:
        logger.error(f"Error getting pinned IDs: {e}")
        # Roll back to recover the session if the table/query failed (e.g., missing table)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {
            'messages': set(),
            'comments': set()
        }


def get_pinned_items_for_chat(user_id: int, chat_id: int) -> list:
    """
    Get all pinned items (with full details) for a user in a specific chat.
    
    Ordered by pin creation time (newest first).
    
    Args:
        user_id: ID of the user
        chat_id: ID of the chat
        
    Returns:
        List of PinnedItem objects
    """
    try:
        return PinnedItem.query.filter_by(
            user_id=user_id,
            chat_id=chat_id
        ).order_by(PinnedItem.created_at.desc()).all()
        
    except Exception as e:
        logger.error(f"Error getting pinned items: {e}")
        # Roll back to recover the session if the table/query failed
        try:
            db.session.rollback()
        except Exception:
            pass
        return []


# =============================================================================
# PHASE B: Shared Pins Functions
# =============================================================================

def get_personal_pins_for_chat(user_id: int, chat_id: int) -> list:
    """
    Get only the user's personal (non-shared) pins for a chat.
    
    Args:
        user_id: ID of the user
        chat_id: ID of the chat
        
    Returns:
        List of PinnedItem objects (personal only)
    """
    try:
        return PinnedItem.query.filter_by(
            user_id=user_id,
            chat_id=chat_id,
            is_shared=False
        ).order_by(PinnedItem.created_at.desc()).all()
        
    except Exception as e:
        logger.error(f"Error getting personal pins: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return []


def get_shared_pins_for_chat(chat_id: int) -> list:
    """
    Get all shared pins for a chat (visible to all room members).
    
    Includes author attribution via the user relationship.
    
    Args:
        chat_id: ID of the chat
        
    Returns:
        List of PinnedItem objects (shared only)
    """
    try:
        return PinnedItem.query.filter_by(
            chat_id=chat_id,
            is_shared=True
        ).order_by(PinnedItem.created_at.desc()).all()
        
    except Exception as e:
        logger.error(f"Error getting shared pins: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return []


def get_shared_pins_for_room(room_id: int) -> list:
    """
    Get all shared pins across a room (all chats).
    
    Useful for room-wide pin views.
    
    Args:
        room_id: ID of the room
        
    Returns:
        List of PinnedItem objects (shared only)
    """
    try:
        return PinnedItem.query.filter_by(
            room_id=room_id,
            is_shared=True
        ).order_by(PinnedItem.created_at.desc()).all()
        
    except Exception as e:
        logger.error(f"Error getting room shared pins: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return []


def get_pins_for_sidebar(user_id: int, chat_id: int) -> Dict[str, list]:
    """
    Get pins organized for sidebar display: personal and shared separately.
    
    Args:
        user_id: ID of the user viewing
        chat_id: ID of the chat
        
    Returns:
        Dict with 'personal' and 'shared' keys containing lists of PinnedItems
    """
    try:
        # Personal: user's own non-shared pins
        personal = PinnedItem.query.filter_by(
            user_id=user_id,
            chat_id=chat_id,
            is_shared=False
        ).order_by(PinnedItem.created_at.desc()).all()
        
        # Shared: all shared pins in the chat
        shared = PinnedItem.query.filter_by(
            chat_id=chat_id,
            is_shared=True
        ).order_by(PinnedItem.created_at.desc()).all()
        
        return {
            'personal': personal,
            'shared': shared
        }
        
    except Exception as e:
        logger.error(f"Error getting sidebar pins: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return {
            'personal': [],
            'shared': []
        }


def share_pin(user: User, pin_id: int) -> Dict[str, Any]:
    """
    Share a personal pin (make it visible to all room members).
    
    Only the pin owner can share their own pin.
    
    Args:
        user: User requesting the share
        pin_id: ID of the pin to share
        
    Returns:
        Dict with success, is_shared, error keys
    """
    try:
        pin = PinnedItem.query.get(pin_id)
        
        if not pin:
            return {'success': False, 'error': 'Pin not found'}
        
        # Only owner can share
        if pin.user_id != user.id:
            return {'success': False, 'error': 'Only the pin owner can share'}
        
        if pin.is_shared:
            # Already shared - idempotent
            return {'success': True, 'is_shared': True, 'changed': False}
        
        pin.is_shared = True
        db.session.commit()
        
        logger.info(f"User {user.id} shared pin {pin_id}")
        
        return {'success': True, 'is_shared': True, 'changed': True}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sharing pin: {e}")
        return {'success': False, 'error': 'Failed to share pin'}


def unshare_pin(user: User, pin_id: int, is_room_owner: bool = False) -> Dict[str, Any]:
    """
    Unshare a shared pin (make it personal again).
    
    Pin owner can always unshare their own pin.
    Room owner can unshare any pin (moderation).
    
    Args:
        user: User requesting the unshare
        pin_id: ID of the pin to unshare
        is_room_owner: Whether the user is the room owner
        
    Returns:
        Dict with success, is_shared, error keys
    """
    try:
        pin = PinnedItem.query.get(pin_id)
        
        if not pin:
            return {'success': False, 'error': 'Pin not found'}
        
        # Owner or room owner can unshare
        if pin.user_id != user.id and not is_room_owner:
            return {'success': False, 'error': 'Only the pin owner or room owner can unshare'}
        
        if not pin.is_shared:
            # Already personal - idempotent
            return {'success': True, 'is_shared': False, 'changed': False}
        
        pin.is_shared = False
        db.session.commit()
        
        logger.info(f"User {user.id} unshared pin {pin_id}")
        
        return {'success': True, 'is_shared': False, 'changed': True}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unsharing pin: {e}")
        return {'success': False, 'error': 'Failed to unshare pin'}


def update_pin_visibility(
    user: User, 
    pin_id: int, 
    shared: bool, 
    is_room_owner: bool = False
) -> Dict[str, Any]:
    """
    Update pin visibility (shared or personal).
    
    Single endpoint for PATCH /pin/<id> to change visibility.
    
    Args:
        user: User requesting the change
        pin_id: ID of the pin
        shared: New visibility state (True=shared, False=personal)
        is_room_owner: Whether the user is the room owner
        
    Returns:
        Dict with success, is_shared, error keys
    """
    if shared:
        return share_pin(user, pin_id)
    else:
        return unshare_pin(user, pin_id, is_room_owner)


def remove_pin_by_id(user: User, pin_id: int, is_room_owner: bool = False) -> Dict[str, Any]:
    """
    Remove a pin by its ID.
    
    Pin owner can always remove their own pin.
    Room owner can remove any pin (moderation).
    
    Args:
        user: User requesting the removal
        pin_id: ID of the pin to remove
        is_room_owner: Whether the user is the room owner
        
    Returns:
        Dict with success, deleted, error keys
    """
    try:
        pin = PinnedItem.query.get(pin_id)
        
        if not pin:
            # Idempotent - return success if pin doesn't exist
            return {'success': True, 'pinned': False, 'deleted': False}
        
        # Only owner or room owner can delete
        if pin.user_id != user.id and not is_room_owner:
            return {'success': False, 'error': 'No permission to remove this pin'}
        
        db.session.delete(pin)
        db.session.commit()
        
        logger.info(f"User {user.id} removed pin {pin_id} (room_owner={is_room_owner})")
        
        return {'success': True, 'pinned': False, 'deleted': True}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing pin: {e}")
        return {'success': False, 'error': 'Failed to remove pin'}


def get_pins_for_ai_context(user_id: int, chat_id: int) -> Dict[str, list]:
    """
    Get pins for AI prompt building with proper isolation.
    
    CRITICAL: Personal pins are ONLY included for the owner.
    Shared pins are included for all users.
    
    Args:
        user_id: ID of the user making the AI request
        chat_id: ID of the chat
        
    Returns:
        Dict with 'personal' (owner only) and 'shared' (all) pins
    """
    try:
        # Personal: ONLY the requesting user's non-shared pins
        personal = PinnedItem.query.filter_by(
            user_id=user_id,
            chat_id=chat_id,
            is_shared=False
        ).order_by(PinnedItem.created_at.desc()).all()
        
        # Shared: all shared pins (safe for any user)
        shared = PinnedItem.query.filter_by(
            chat_id=chat_id,
            is_shared=True
        ).order_by(PinnedItem.created_at.desc()).all()
        
        return {
            'personal': personal,
            'shared': shared
        }
        
    except Exception as e:
        logger.error(f"Error getting AI context pins: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return {
            'personal': [],
            'shared': []
        }
