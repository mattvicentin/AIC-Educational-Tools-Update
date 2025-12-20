#!/usr/bin/env python3
"""
google_auth.py
Purpose: Google OAuth model for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Google OAuth token storage for Docs API access
"""

from datetime import datetime, timezone
from src.app import db


class GoogleAuth(db.Model):
    """Stores Google OAuth tokens for Docs API access."""
    
    __tablename__ = 'google_auth'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True, index=True
    )
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<GoogleAuth user_id={self.user_id}>"
