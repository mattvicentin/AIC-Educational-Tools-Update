#!/usr/bin/env python3
"""
refinement.py
Purpose: Track room learning-step refinements for audit and revert
Status: [ACTIVE]
Created: 2025-09-11
Author: writeian

Model for recording refinement operations with before/after modes and summary.
"""

from datetime import datetime, timezone
from src.app import db


class RoomRefinementHistory(db.Model):
    """History of room learning-step refinements.

    Stores user preference text, old/new modes JSON (as text payloads), and a
    human-readable summary. Enables preview, audit, and one-click reverts.
    """

    __tablename__ = "room_refinement_history"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)

    # Free-text user instruction that prompted the refinement
    preference = db.Column(db.Text, nullable=True)

    # JSON-serialized arrays of mode dicts (stored as TEXT for cross-DB compatibility)
    old_modes_json = db.Column(db.Text, nullable=True)
    new_modes_json = db.Column(db.Text, nullable=True)

    # Short natural-language summary returned to the UI
    summary = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<RoomRefinementHistory id={self.id} room_id={self.room_id}>"


