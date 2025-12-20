#!/usr/bin/env python3
"""
rubric.py
Purpose: Rubric models for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Rubric assessment models for learning step evaluation
"""

from datetime import datetime, timezone
from src.app import db


class RubricCriterion(db.Model):
    """Rubric criteria for assessing learning step progress."""
    
    __tablename__ = 'rubric_criterion'
    __table_args__ = (
        db.UniqueConstraint(
            "room_id", "step_key", "name", name="unique_room_step_criterion"
        ),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    step_key = db.Column(
        db.String(32), nullable=False
    )  # 'explore', 'focus', 'context', etc.
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    weight = db.Column(
        db.Float, default=1.0, nullable=False, info={"check": "weight >= 0.0"}
    )
    order = db.Column(db.Integer, nullable=False)

    # Relationships
    room = db.relationship("Room", lazy=True, overlaps="rubric_criteria")
    levels = db.relationship(
        "RubricLevel", backref="criterion", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<RubricCriterion {self.name} for {self.step_key} in room {self.room_id}>"
        )


class RubricLevel(db.Model):
    """Individual levels within a rubric criterion."""
    
    __tablename__ = 'rubric_level'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    criterion_id = db.Column(
        db.Integer, db.ForeignKey("rubric_criterion.id"), nullable=False
    )
    level = db.Column(
        db.String(50), nullable=False
    )  # 'Emerging', 'Developing', 'Proficient', 'Exemplary'
    score = db.Column(
        db.Integer, nullable=False, info={"check": "score >= 1 AND score <= 4"}
    )  # 1, 2, 3, 4
    description = db.Column(db.Text, nullable=False)
    examples = db.Column(db.Text, nullable=True)  # JSON array of examples

    def __repr__(self):
        return f"<RubricLevel {self.level} (score {self.score}) for criterion {self.criterion_id}>"


class RoomRubric(db.Model):
    """Overall rubric configuration for a learning step in a room."""
    
    __tablename__ = 'room_rubric'
    __table_args__ = (
        db.UniqueConstraint("room_id", "step_key", name="unique_room_step_rubric"),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    step_key = db.Column(db.String(32), nullable=False)
    progression_threshold = db.Column(db.Float, default=2.5, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships

    def __repr__(self):
        return f"<RoomRubric for {self.step_key} in room {self.room_id}>"
