#!/usr/bin/env python3
"""
analytics.py
Purpose: Analytics models for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Analytics and tracking models for user behavior and achievements
"""

from datetime import datetime, timezone
from src.app import db


class PromptRecord(db.Model):
    """Records student prompts for dashboard analytics."""
    
    __tablename__ = 'prompt_record'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    mode = db.Column(db.String(32), nullable=False)  # The mode when the prompt was sent
    prompt_content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user = db.relationship("User", backref="prompt_records")

    def __repr__(self):
        return f"<PromptRecord {self.id} mode={self.mode}>"


class PageView(db.Model):
    """Track page views for analytics."""
    
    __tablename__ = 'page_view'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(200), nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # Relationship
    user = db.relationship("User", backref="page_views")

    def __repr__(self):
        return f"<PageView {self.id} page={self.page}>"


class UserModeUsage(db.Model):
    """Track which modes each user has used in each room for achievements."""
    
    __tablename__ = 'user_mode_usage'
    __table_args__ = (
        db.UniqueConstraint("user_id", "room_id", "mode", name="unique_user_room_mode"),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    mode = db.Column(db.String(32), nullable=False)  # The mode that was used
    first_used_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_used_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    usage_count = db.Column(
        db.Integer, default=1, nullable=False
    )  # How many times this mode was used

    # Relationships
    user = db.relationship("User", backref="mode_usage")

    def __repr__(self):
        return f"<UserModeUsage user_id={self.user_id} room_id={self.room_id} mode={self.mode}>"


class Achievement(db.Model):
    """Track user achievements/milestones in rooms."""
    
    __tablename__ = 'achievement'
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "room_id",
            "achievement_type",
            name="unique_user_room_achievement",
        ),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    achievement_type = db.Column(
        db.String(50), nullable=False
    )  # 'first_steps', 'explorer', 'collaborator', etc.
    earned_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user = db.relationship("User", backref="achievements")

    def __repr__(self):
        return f"<Achievement {self.achievement_type} for user {self.user_id} in room {self.room_id}>"


class RefinementEvent(db.Model):
    """Track refinement pipeline usage for analytics and monitoring."""

    __tablename__ = 'refinement_event'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=True, index=True)
    event_type = db.Column(db.String(32), nullable=False)  # refine_new, refine_edit, regenerate, revert
    preference = db.Column(db.Text, nullable=True)
    added = db.Column(db.Integer, default=0, nullable=False)
    removed = db.Column(db.Integer, default=0, nullable=False)
    changed = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def __repr__(self):
        return f"<RefinementEvent {self.event_type} room={self.room_id} user={self.user_id}>"


class ProgressSuggestionState(db.Model):
    """Per-chat, per-mode state for next-step suggestion cooldown."""

    __tablename__ = 'progress_suggestion_state'
    __table_args__ = (
        db.UniqueConstraint("chat_id", "mode_key", name="unique_chat_mode_suggest"),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False, index=True)
    mode_key = db.Column(db.String(32), nullable=False)
    shown_once = db.Column(db.Boolean, default=False, nullable=False)
    cooldown = db.Column(db.Integer, default=1, nullable=False)
    since = db.Column(db.Integer, default=0, nullable=False)
    last_confidence = db.Column(db.Float, default=0.0, nullable=False)
    last_shown_message_id = db.Column(db.Integer, db.ForeignKey("message.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<ProgressSuggestionState chat={self.chat_id} mode={self.mode_key} cd={self.cooldown} since={self.since}>"


class ProgressSuggestionEvent(db.Model):
    """Audit events for suggestion show/click/dismiss."""

    __tablename__ = 'progress_suggestion_event'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False, index=True)
    mode_key = db.Column(db.String(32), nullable=False)
    event_type = db.Column(db.String(16), nullable=False)  # shown, clicked, dismissed
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    message_id = db.Column(db.Integer, db.ForeignKey("message.id"), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def __repr__(self):
        return f"<ProgressSuggestionEvent {self.event_type} chat={self.chat_id} mode={self.mode_key}>"
