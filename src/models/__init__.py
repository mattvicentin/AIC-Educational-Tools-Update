"""
Database models package for AI Collab Online
Contains SQLAlchemy ORM models
"""

from .user import User
from .room import Room, RoomMember
from .chat import Chat, Message, Comment
from .analytics import (
    PromptRecord,
    UserModeUsage,
    Achievement,
    PageView,
    ProgressSuggestionState,
    ProgressSuggestionEvent,
)
from .google_auth import GoogleAuth
from .custom_prompt import CustomPrompt
from .rubric import RubricCriterion, RubricLevel, RoomRubric
from .refinement import RoomRefinementHistory
from .learning import ChatNotes
from .pin import PinnedItem, PinChatMetadata
from .card_comment import CardComment, generate_card_key, generate_body_hash
from .quiz import Quiz, QuizAnswer
from .flashcards import FlashcardSet, FlashcardSession
from .document import Document, DocumentChunk

__all__ = [
    "User",
    "Room",
    "RoomMember",
    "Chat",
    "Message",
    "Comment",
    "PromptRecord",
    "UserModeUsage",
    "Achievement",
    "PageView",
    "ProgressSuggestionState",
    "ProgressSuggestionEvent",
    "GoogleAuth",
    "CustomPrompt",
    "RubricCriterion",
    "RubricLevel",
    "RoomRubric",
    "RoomRefinementHistory",
    "ChatNotes",
    "PinnedItem",
    "PinChatMetadata",
    "CardComment",
    "generate_card_key",
    "generate_body_hash",
    "Quiz",
    "QuizAnswer",
    "FlashcardSet",
    "FlashcardSession",
    "Document",
    "DocumentChunk",
]
