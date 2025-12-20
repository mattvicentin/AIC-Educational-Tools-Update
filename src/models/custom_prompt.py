#!/usr/bin/env python3
"""
custom_prompt.py
Purpose: CustomPrompt model for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Custom system instructions model for AI prompts
"""

from datetime import datetime, timezone
from src.app import db


class CustomPrompt(db.Model):
    """Custom system instructions created by instructors for specific modes and rooms."""
    
    __tablename__ = 'custom_prompt'
    __table_args__ = (
        db.UniqueConstraint("room_id", "mode_key", name="unique_room_mode"),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer, db.ForeignKey("room.id"), nullable=True
    )  # null for global prompts
    mode_key = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    creator = db.relationship(
        "User", backref="custom_prompts", foreign_keys=[created_by]
    )

    def __repr__(self):
        return f"<CustomPrompt {self.mode_key} for room {self.room_id}>"
