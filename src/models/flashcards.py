#!/usr/bin/env python3
"""
flashcards.py
Purpose: FlashcardSet and FlashcardSession models for Flashcards Tool
Status: [NEW]
Created: 2026-01-02

Models for storing generated flashcard sets and infinite mode sessions
"""

from datetime import datetime, timezone
from sqlalchemy import JSON
from src.app import db
from typing import Optional, Dict, List


class FlashcardSet(db.Model):
    """Stores a generated flashcard set."""
    
    __tablename__ = 'flashcard_set'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(
        db.Integer, 
        db.ForeignKey("chat.id", ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    room_id = db.Column(
        db.Integer, 
        db.ForeignKey("room.id", ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    created_by = db.Column(
        db.Integer, 
        db.ForeignKey("user.id", ondelete='SET NULL'), 
        nullable=True, 
        index=True
    )
    
    # Configuration
    context_mode = db.Column(db.String(20), nullable=False)  # 'chat', 'library', 'both'
    library_doc_ids = db.Column(JSON, nullable=True)  # List of document IDs
    instructions = db.Column(db.Text, nullable=True)
    display_mode = db.Column(db.String(20), nullable=False)  # 'grid', 'single'
    grid_size = db.Column(db.String(10), nullable=True)  # '1x2', '2x2', '2x3', '3x3'
    is_infinite = db.Column(db.Boolean, nullable=False, default=False)
    
    # Generated flashcard data (stored as JSON)
    cards = db.Column(JSON, nullable=False)  # List of {front, back, id, hash}
    
    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Relationships
    chat = db.relationship("Chat", backref="flashcard_sets")
    room = db.relationship("Room", backref="flashcard_sets")
    creator = db.relationship("User", foreign_keys=[created_by])
    sessions = db.relationship(
        "FlashcardSession", 
        backref="flashcard_set", 
        lazy=True, 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<FlashcardSet {self.id} chat={self.chat_id} cards={len(self.cards) if self.cards else 0}>"
    
    def to_dict(self) -> Dict:
        """Convert flashcard set to dictionary for API responses."""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'room_id': self.room_id,
            'context_mode': self.context_mode,
            'library_doc_ids': self.library_doc_ids or [],
            'instructions': self.instructions,
            'display_mode': self.display_mode,
            'grid_size': self.grid_size,
            'is_infinite': self.is_infinite,
            'cards': self.cards or [],
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class FlashcardSession(db.Model):
    """Tracks infinite mode sessions to prevent repeats."""
    
    __tablename__ = 'flashcard_session'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    flashcard_set_id = db.Column(
        db.Integer, 
        db.ForeignKey("flashcard_set.id", ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("user.id", ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Session tracking
    session_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    cursor_state = db.Column(JSON, nullable=False)  # {normalizedFrontHashes: List, totalGenerated, lastContextHash}
    
    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    last_accessed_at = db.Column(
        db.DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    
    # Relationships
    user = db.relationship("User", backref="flashcard_sessions")
    
    def __repr__(self) -> str:
        return f"<FlashcardSession {self.id} session_id={self.session_id}>"
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary for API responses."""
        return {
            'id': self.id,
            'flashcard_set_id': self.flashcard_set_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'cursor_state': self.cursor_state,
            'created_at': self.created_at.isoformat(),
            'last_accessed_at': self.last_accessed_at.isoformat(),
        }
