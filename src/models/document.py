#!/usr/bin/env python3
"""
document.py
Purpose: Document and DocumentChunk models for Library Tool
Status: [NEW - Railway PostgreSQL Migration]
Created: 2024-11-06
Author: writeian

Document storage models for Railway PostgreSQL using SQLAlchemy ORM
"""

from datetime import datetime, timezone
from sqlalchemy import Index, func, text, String
from sqlalchemy.dialects import postgresql
from src.app import db
from typing import Optional


class Document(db.Model):
    """Stores document metadata and full text."""
    
    __tablename__ = 'document'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(255), nullable=False, index=True)
    name = db.Column(db.String(500), nullable=False)
    full_text = db.Column(db.Text, nullable=True)  # Store full text for reference
    file_size = db.Column(db.Integer, default=0, nullable=False)
    room_id = db.Column(
        db.Integer, 
        db.ForeignKey("room.id", ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    uploaded_at = db.Column(
        db.DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        index=True
    )
    summary = db.Column(db.Text, nullable=True)

    # Relationships
    room = db.relationship("Room", backref="documents")
    user = db.relationship("User", foreign_keys=[uploaded_by])
    chunks = db.relationship(
        "DocumentChunk", 
        backref="document", 
        lazy=True, 
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index"
    )

    def __repr__(self) -> str:
        return f"<Document {self.id} {self.name!r}>"


class DocumentChunk(db.Model):
    """Stores document chunks with Full-Text Search support."""
    
    __tablename__ = 'document_chunk'
    # Note: GIN index on search_vector is PostgreSQL-specific, created manually in main.py
    __table_args__ = (
        Index('ix_document_chunk_doc_created_at', 'document_id', 'created_at'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer,
        db.ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_index = db.Column(db.Integer, nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)
    start_char = db.Column(db.Integer, nullable=True)
    end_char = db.Column(db.Integer, nullable=True)
    token_count = db.Column(db.Integer, nullable=True)
    
    # Full-text search vector (TSVECTOR for PostgreSQL, TEXT/VARCHAR for SQLite)
    # Using String() for SQLite compatibility - TSVECTOR handled in manual table creation
    search_vector = db.Column(
        String(),  # SQLite-compatible default
        nullable=True
    )
    
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk {self.id} doc={self.document_id} idx={self.chunk_index}>"

