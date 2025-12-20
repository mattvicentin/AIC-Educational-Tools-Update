"""
Learning Context Management System

This module provides automatic note generation and cross-chat learning context
for enhanced learning progression in AI Collab Online.

Key Features:
- Automatic note generation when chats reach 5+ messages
- Persistent storage of chat notes for reuse
- Cumulative context loading from all completed chats in a room
- Flexible learning paths (non-linear, skippable, reversible)
"""

from .context_manager import (
    auto_generate_notes_if_needed,
    get_learning_context_for_room,
    get_chat_notes,
    store_chat_notes,
    has_stored_notes,
    get_completion_stats_for_room,
)

from .triggers import (
    trigger_auto_note_generation,
    trigger_context_refresh_for_room,
    should_generate_notes,
)

__all__ = [
    "auto_generate_notes_if_needed",
    "get_learning_context_for_room", 
    "get_chat_notes",
    "store_chat_notes",
    "has_stored_notes",
    "get_completion_stats_for_room",
    "trigger_auto_note_generation",
    "trigger_context_refresh_for_room",
    "should_generate_notes",
]
