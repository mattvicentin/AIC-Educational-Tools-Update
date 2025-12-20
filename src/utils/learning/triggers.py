"""
Learning Context Triggers

Handles automatic triggering of note generation when messages are added to chats.
This module integrates with the message creation process to automatically generate
and store notes when chats reach the 5+ message threshold.
"""

import logging
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)


def trigger_auto_note_generation(message: Any) -> None:
    """
    Trigger automatic note generation after a message is added.
    
    This should be called after every message creation to check if
    the chat has reached the threshold for automatic note generation.
    
    Args:
        message: The message that was just created
    """
    try:
        if not message or not hasattr(message, 'chat_id'):
            logger.debug("Invalid message object for auto note generation")
            return
            
        chat_id = message.chat_id
        
        # Import here to avoid circular imports
        from .context_manager import auto_generate_notes_if_needed
        
        # Attempt to auto-generate notes
        notes_generated = auto_generate_notes_if_needed(chat_id)
        
        if notes_generated:
            logger.info(f"🎓 Auto-generated learning notes for chat {chat_id}")
        else:
            logger.debug(f"No notes generated for chat {chat_id} (may not meet criteria)")
            
    except Exception as e:
        logger.error(f"Error in auto note generation trigger for message {getattr(message, 'id', 'unknown')}: {e}")
        # Don't re-raise - note generation failure shouldn't break message creation


def trigger_context_refresh_for_room(room_id: int) -> None:
    """
    Generate missing notes for all chats in a room that need them.
    
    This scans all chats in the room and generates notes for any chat
    that has reached 5+ message milestones but doesn't have notes yet.
    
    Args:
        room_id: The room ID to refresh context for
    """
    try:
        from src.models import Chat, Message
        from .context_manager import auto_generate_notes_if_needed
        
        # Get all chats in this room
        room_chats = Chat.query.filter_by(room_id=room_id).all()
        
        notes_generated = 0
        for chat in room_chats:
            # Get message count for this chat
            message_count = Message.query.filter_by(chat_id=chat.id).count()
            
            if message_count >= 5:
                # Check if notes already exist for this chat
                from .context_manager import has_stored_notes
                
                if has_stored_notes(chat.id):
                    logger.debug(f"Notes already exist for chat {chat.id} ({message_count} messages)")
                else:
                    # Generate notes for the most recent milestone
                    most_recent_milestone = (message_count // 5) * 5  # e.g., 7 msgs → milestone 5
                    logger.info(f"📝 Generating notes for chat {chat.id} at milestone {most_recent_milestone} (chat has {message_count} messages)")
                    
                    try:
                        if generate_notes_for_milestone(chat.id, most_recent_milestone):
                            notes_generated += 1
                            logger.info(f"✅ Generated notes for chat {chat.id} at {most_recent_milestone} messages")
                    except Exception as e:
                        logger.error(f"Failed to generate notes for chat {chat.id}: {e}")
        
        logger.info(f"🎓 Generated {notes_generated} note versions for room {room_id}")
        
        # Get final stats
        from .context_manager import get_completion_stats_for_room
        stats = get_completion_stats_for_room(room_id)
        logger.info(f"🔄 Room {room_id} final stats: {stats['total_completed']} completed chats, "
                   f"{len(stats['modes_covered'])} modes covered")
                   
    except Exception as e:
        logger.error(f"Error refreshing context for room {room_id}: {e}")


def should_generate_notes(chat_id: int) -> bool:
    """
    Check if a chat should have notes generated/updated.
    
    Returns True if:
    - Chat has reached a 5-message milestone (5, 10, 15, 20...)
    - Notes need to be created or updated for this milestone
    
    Args:
        chat_id: The chat to check
        
    Returns:
        True if notes should be generated/updated, False otherwise
    """
    try:
        from src.models import Message, ChatNotes
        
        # Get current message count
        message_count = Message.query.filter_by(chat_id=chat_id).count()
        
        # Check if we're at a 5-message milestone
        if message_count < 5 or message_count % 5 != 0:
            return False
            
        # Check if notes need updating (don't exist or are outdated)
        existing_notes = ChatNotes.query.filter_by(chat_id=chat_id).first()
        
        if not existing_notes:
            logger.info(f"📝 Chat {chat_id} reached {message_count}-message milestone, creating initial notes")
            return True
        elif existing_notes.message_count < message_count:
            logger.info(f"🔄 Chat {chat_id} reached {message_count}-message milestone, updating notes (was {existing_notes.message_count})")
            return True
        else:
            logger.debug(f"Notes already up-to-date for chat {chat_id} at {message_count} messages")
            return False
        
    except Exception as e:
        logger.error(f"Error checking if notes should be generated for chat {chat_id}: {e}")
        return False




def generate_notes_for_milestone(chat_id: int, milestone_count: int) -> bool:
    """Generate notes for a specific milestone (e.g., 5 messages from a 7-message chat)."""
    try:
        from src.models import Chat, Message
        
        # Get chat
        chat = Chat.query.get(chat_id)
        if not chat:
            logger.error(f"Chat {chat_id} not found")
            return False
            
        # Get first N messages for this milestone
        messages = Message.query.filter_by(chat_id=chat_id)\
                                .order_by(Message.timestamp)\
                                .limit(milestone_count)\
                                .all()
        
        if len(messages) < milestone_count:
            logger.error(f"Chat {chat_id} doesn't have {milestone_count} messages")
            return False
            
        # Generate notes
        from src.app.documents import generate_document_content
        notes_content = generate_document_content(messages, chat, "notes")
        
        # Store notes
        from .context_manager import store_chat_notes
        return store_chat_notes(chat_id, chat.room_id, notes_content, milestone_count)
        
    except Exception as e:
        logger.error(f"Error generating milestone notes for chat {chat_id}: {e}")
        return False
