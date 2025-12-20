#!/usr/bin/env python3
"""
chat.py
Purpose: Chat, Message, and Comment models for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Chat conversation and messaging models
"""

from datetime import datetime, timezone
from src.app import db
from typing import Optional, List


class Chat(db.Model):
    """A conversation within a room that can be accessed by all room members."""
    
    __tablename__ = 'chat'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    room_id = db.Column(
        db.Integer, db.ForeignKey("room.id"), nullable=False, index=True
    )
    created_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    mode = db.Column(
        db.String(32),  # Dynamic modes based on room goals
        default="explore",
        nullable=False,
    )

    # Relationships
    messages = db.relationship(
        "Message", backref="chat", lazy=True, cascade="all, delete-orphan"
    )
    prompt_records = db.relationship(
        "PromptRecord", backref="chat", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="chat", lazy=True, cascade="all, delete-orphan"
    )
    creator = db.relationship(
        "User", backref="created_chats", foreign_keys=[created_by]
    )

    def __repr__(self) -> str:
        return f"<Chat {self.id} {self.title!r}>"


class Message(db.Model):
    """A single turn in the conversation (user or assistant)."""
    
    __tablename__ = 'message'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(
        db.Integer, db.ForeignKey("chat.id"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True, index=True
    )  # null for assistant messages
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    parent_message_id = db.Column(
        db.Integer, db.ForeignKey("message.id"), nullable=True, default=None
    )
    is_truncated = db.Column(db.Boolean, default=False, nullable=False)

    # Relationship
    user = db.relationship("User", backref="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id} role={self.role}>"


class Comment(db.Model):
    """Comments on specific dialogue items in a chat."""
    
    __tablename__ = 'comment'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    dialogue_number = db.Column(
        db.Integer, nullable=False
    )  # Which prompt/response (1, 2, 3, etc.)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    # Relationships
    user = db.relationship("User", backref="comments")
    

    def __repr__(self) -> str:
        return f"<Comment {self.id} on dialogue {self.dialogue_number}>"
