#!/usr/bin/env python3
"""
user.py
Purpose: User model for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

User model with authentication, profile, and relationship management
"""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from src.app import db
from typing import Optional, List


class User(db.Model):
    """A registered user of the application."""
    
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Registration questions (optional fields)
    full_name = db.Column(db.String(100), nullable=True)
    institution = db.Column(db.String(200), nullable=True)
    department = db.Column(db.String(200), nullable=True)
    research_area = db.Column(db.String(200), nullable=True)
    role = db.Column(
        db.String(50), nullable=True
    )  # Student, Professor, Researcher, etc.
    primary_use_case = db.Column(db.String(100), nullable=True)
    team_size = db.Column(db.String(50), nullable=True)
    heard_from = db.Column(db.String(100), nullable=True)
    receive_updates = db.Column(db.Boolean, default=False, nullable=True)
    contact_for_research = db.Column(db.Boolean, default=False, nullable=True)

    # Password reset fields
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    # Relationships
    owned_rooms = db.relationship(
        "Room", backref="owner", lazy=True, foreign_keys="Room.owner_id"
    )
    room_memberships = db.relationship("RoomMember", backref="user", lazy=True)
    google_auth = db.relationship("GoogleAuth", backref="user", uselist=False)

    def set_password(self, password: str) -> None:
        # Use pbkdf2:sha256 instead of scrypt (scrypt requires OpenSSL 1.1+, not available on macOS with LibreSSL)
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def validate_email(self) -> bool:
        """Validate email format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, self.email) is not None

    def validate_username(self) -> bool:
        """Validate username format."""
        import re

        # Username should be 3-20 characters, alphanumeric and underscores only
        pattern = r"^[a-zA-Z0-9_]{3,20}$"
        return re.match(pattern, self.username) is not None

    def __repr__(self) -> str:
        return f"<User {self.username}>"
