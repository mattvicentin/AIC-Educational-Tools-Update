#!/usr/bin/env python3
"""
room.py
Purpose: Room and RoomMember models for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Room management and membership models for collaborative spaces
"""

from datetime import datetime, timezone
from src.app import db
from typing import Optional, List


class Room(db.Model):
    """A collaborative learning space where users can create and share chats."""
    
    __tablename__ = 'room'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    short_description = db.Column(db.String(300), nullable=True)  # Short narrative description for room list
    goals = db.Column(db.Text, nullable=True)  # Learning goals for the room
    group_size = db.Column(db.String(20), nullable=True)  # Group size: small, medium, large, individual
    owner_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    chats = db.relationship(
        "Chat", backref="room", lazy=True, cascade="all, delete-orphan"
    )
    members = db.relationship(
        "RoomMember", backref="room", lazy=True, cascade="all, delete-orphan"
    )
    custom_prompts = db.relationship(
        "CustomPrompt", backref="room", lazy=True, cascade="all, delete-orphan"
    )
    achievements = db.relationship(
        "Achievement", backref="room", lazy=True, cascade="all, delete-orphan"
    )
    user_mode_usage = db.relationship(
        "UserModeUsage", backref="room", lazy=True, cascade="all, delete-orphan"
    )
    prompt_records = db.relationship(
        "PromptRecord", backref="room", lazy=True, cascade="all, delete-orphan"
    )
    rubric_criteria = db.relationship(
        "RubricCriterion", lazy=True, cascade="all, delete-orphan"
    )
    room_rubrics = db.relationship(
        "RoomRubric", backref="room", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Room {self.id} {self.name!r}>"


class RoomMember(db.Model):
    """Represents a user's membership in a room."""
    
    __tablename__ = 'room_member'
    __table_args__ = (
        db.UniqueConstraint("room_id", "user_id", name="unique_room_user"),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer, db.ForeignKey("room.id"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    joined_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    accepted_at = db.Column(
        db.DateTime, nullable=True
    )  # When user first accessed the room
    can_create_chats = db.Column(db.Boolean, default=True, nullable=False)
    can_invite_members = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<RoomMember room_id={self.room_id} user_id={self.user_id}>"
