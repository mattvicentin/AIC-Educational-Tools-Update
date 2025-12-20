"""
Learning Context Manager

Handles automatic note generation, storage, and retrieval for enhanced
learning progression across multiple chats within a room.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from flask import current_app
from src.app import db

logger = logging.getLogger(__name__)


def ensure_chat_notes_table_exists() -> bool:
    """Ensure the chat_notes table exists, create it if missing."""
    try:
        from src.models import ChatNotes
        # Try to query the table to see if it exists
        ChatNotes.query.first()
        logger.debug("chat_notes table exists")
        return True
    except Exception as e:
        logger.warning(f"chat_notes table may not exist: {e}")
        try:
            # Try to create the table directly
            db.engine.execute("""
                CREATE TABLE IF NOT EXISTS chat_notes (
                    id SERIAL PRIMARY KEY,
                    chat_id INTEGER NOT NULL UNIQUE REFERENCES chat(id),
                    room_id INTEGER NOT NULL REFERENCES room(id),
                    notes_content TEXT NOT NULL,
                    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_chat_notes_room_id ON chat_notes(room_id);
                CREATE INDEX IF NOT EXISTS ix_chat_notes_generated_at ON chat_notes(generated_at);
            """)
            logger.info("✅ Created chat_notes table directly")
            return True
        except Exception as create_error:
            logger.error(f"❌ Failed to create chat_notes table: {create_error}")
            return False


def auto_generate_notes_if_needed(chat_id: int) -> bool:
    """
    Automatically generate or update notes for a chat if:
    1. Chat has reached a 5-message milestone (5, 10, 15, 20...)
    2. This milestone is newer than the last generated notes
    
    Notes are iteratively refined - each milestone updates the same note record
    with a more comprehensive understanding of the entire conversation.
    
    Returns True if notes were generated/updated, False otherwise.
    """
    try:
        # Ensure table exists before proceeding
        if not ensure_chat_notes_table_exists():
            logger.error("Cannot proceed without chat_notes table")
            return False
            
        from src.models import Chat, Message
        
        # Get current message count
        message_count = Message.query.filter_by(chat_id=chat_id).count()
        
        # Only generate at 5-message milestones
        if message_count < 5 or message_count % 5 != 0:
            logger.debug(f"Chat {chat_id} has {message_count} messages, not at 5-message milestone")
            return False
            
        # Check if notes already exist and if they're up to date
        from src.models import ChatNotes
        
        logger.info(f"🔍 Checking notes status: chat_id={chat_id}, message_count={message_count}")
        
        try:
            existing_notes = ChatNotes.query.filter_by(chat_id=chat_id).first()
        except Exception as db_error:
            logger.error(f"❌ Database error checking notes (table may not exist): {db_error}")
            return False
        
        # If notes exist and are up-to-date, skip generation
        if existing_notes and existing_notes.message_count >= message_count:
            logger.debug(f"Notes already up-to-date for chat {chat_id} (stored: {existing_notes.message_count}, current: {message_count})")
            return False
            
        logger.info(f"📝 Generating/updating iterative notes for chat {chat_id} at {message_count} messages")
            
        # Get chat and messages
        chat = Chat.query.get(chat_id)
        if not chat:
            logger.error(f"Chat {chat_id} not found")
            return False
            
        messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
        
        # Generate notes using existing document generation logic
        logger.info(f"📝 Generating notes for chat {chat_id} with {len(messages)} messages")
        
        try:
            from src.app.documents import generate_document_content
            notes_content = generate_document_content(messages, chat, "notes")
            logger.info(f"✅ Notes generated successfully, length: {len(notes_content)} chars")
        except Exception as gen_error:
            logger.error(f"❌ Note generation failed: {gen_error}")
            return False
        
        # Store the notes
        success = store_chat_notes(chat_id, chat.room_id, notes_content, message_count)
        
        if success:
            logger.info(f"✅ Auto-generated notes for chat {chat_id} ({message_count} messages)")
            return True
        else:
            logger.error(f"❌ Failed to store notes for chat {chat_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error auto-generating notes for chat {chat_id}: {e}")
        return False


def store_chat_notes(chat_id: int, room_id: int, notes_content: str, message_count: int) -> bool:
    """
    Store notes for a chat in the database.
    
    Returns True if successful, False otherwise.
    """
    try:
        from src.models import ChatNotes
        
        # Update existing notes or create new ones (iterative refinement)
        from src.models import ChatNotes
        existing = ChatNotes.query.filter_by(chat_id=chat_id).first()
        
        if existing:
            # Update existing notes with refined understanding
            existing.notes_content = notes_content
            existing.message_count = message_count
            existing.generated_at = datetime.utcnow()
            logger.info(f"🔄 Updated iterative notes for chat {chat_id} (was {existing.message_count} msgs, now {message_count} msgs)")
        else:
            # Create new notes record
            chat_notes = ChatNotes(
                chat_id=chat_id,
                room_id=room_id,
                notes_content=notes_content,
                message_count=message_count
            )
            db.session.add(chat_notes)
            logger.info(f"📝 Created initial notes for chat {chat_id} at {message_count} messages")
        
        db.session.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error storing notes for chat {chat_id}: {e}")
        db.session.rollback()
        return False


def has_stored_notes(chat_id: int) -> bool:
    """Check if notes exist for a chat (simplified for iterative approach)."""
    try:
        from src.models import ChatNotes
        return ChatNotes.query.filter_by(chat_id=chat_id).first() is not None
            
    except Exception as e:
        logger.error(f"Error checking for existing notes for chat {chat_id}: {e}")
        return False


def get_chat_notes(chat_id: int) -> Optional[str]:
    """Get stored notes for a chat (simplified for iterative approach)."""
    try:
        from src.models import ChatNotes
        notes = ChatNotes.query.filter_by(chat_id=chat_id).first()
        return notes.notes_content if notes else None
        
    except Exception as e:
        logger.error(f"Error retrieving notes for chat {chat_id}: {e}")
        return None


def get_learning_context_for_room(room_id: int, exclude_chat_id: Optional[int] = None) -> Optional[str]:
    """
    Get cumulative learning context from all completed chats in a room.
    
    This combines notes from all chats with stored notes, providing rich
    context for new chats to build upon previous discussions.
    
    Args:
        room_id: The room to get context for
        exclude_chat_id: Optional chat ID to exclude (e.g., current chat)
        
    Returns:
        Combined notes content or None if no completed chats found
    """
    try:
        from src.models import ChatNotes
        
        # Get notes for all chats in this room (one note record per chat)
        from src.models import ChatNotes
        
        query = ChatNotes.query.filter_by(room_id=room_id)
        
        if exclude_chat_id:
            query = query.filter(ChatNotes.chat_id != exclude_chat_id)
            
        completed_chats = query.order_by(ChatNotes.generated_at).all()
        
        if not completed_chats:
            logger.debug(f"No completed chats found for room {room_id}")
            return None
            
        # Combine all notes into comprehensive context
        context_parts = []
        
        for i, chat_notes in enumerate(completed_chats, 1):
            # Get chat info for context
            from src.models import Chat
            chat = Chat.query.get(chat_notes.chat_id)
            chat_mode = chat.mode if chat else "unknown"
            
            context_parts.append(f"""
## Discussion {i}: {chat_mode.title()} Mode
*Generated from {chat_notes.message_count} messages*

{chat_notes.notes_content}

---
""")
        
        combined_context = "\n".join(context_parts)
        
        logger.info(f"✅ Generated learning context from {len(completed_chats)} completed chats for room {room_id}")
        
        return combined_context.strip()
        
    except Exception as e:
        logger.error(f"Error getting learning context for room {room_id}: {e}")
        return None


def get_completion_stats_for_room(room_id: int) -> Dict[str, Any]:
    """
    Get statistics about completed chats in a room.
    
    Returns information about how many chats have notes, modes covered, etc.
    """
    try:
        from src.models import Chat, ChatNotes
        
        completed_chats = db.session.query(ChatNotes, Chat).join(
            Chat, ChatNotes.chat_id == Chat.id
        ).filter(ChatNotes.room_id == room_id).all()
        
        if not completed_chats:
            return {"total_completed": 0, "modes_covered": [], "total_messages": 0}
            
        modes_covered = []
        total_messages = 0
        
        for chat_notes, chat in completed_chats:
            if chat.mode and chat.mode not in modes_covered:
                modes_covered.append(chat.mode)
            total_messages += chat_notes.message_count
            
        return {
            "total_completed": len(completed_chats),
            "modes_covered": modes_covered,
            "total_messages": total_messages,
            "average_messages": total_messages // len(completed_chats) if completed_chats else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting completion stats for room {room_id}: {e}")
        return {"total_completed": 0, "modes_covered": [], "total_messages": 0}
