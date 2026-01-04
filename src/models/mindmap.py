#!/usr/bin/env python3
"""
mindmap.py
Purpose: MindMap model for Mind Map Tool
Status: [NEW]
Created: 2026-01-XX

Model for storing generated mind maps with hierarchical structure
"""

from datetime import datetime, timezone
from sqlalchemy import JSON
from src.app import db
from typing import Optional, Dict, List


class MindMap(db.Model):
    """Stores a generated mind map with hierarchical node structure."""
    
    __tablename__ = 'mindmap'
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
    size = db.Column(db.String(20), nullable=False)  # 'small', 'medium', 'large'
    
    # Generated mind map data (stored as JSON)
    # Structure: {root: {id, label, explanation}, nodes: [{id, label, explanation, parent, children: [...]}]}
    mind_map_data = db.Column(JSON, nullable=False)
    
    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Relationships
    chat = db.relationship("Chat", backref="mind_maps")
    room = db.relationship("Room", backref="mind_maps")
    creator = db.relationship("User", foreign_keys=[created_by])
    
    def __repr__(self) -> str:
        node_count = 0
        if self.mind_map_data:
            node_count = 1  # root
            if 'nodes' in self.mind_map_data:
                node_count += len(self.mind_map_data.get('nodes', []))
        return f"<MindMap {self.id} chat={self.chat_id} nodes={node_count}>"
    
    def to_dict(self) -> Dict:
        """Convert mind map to dictionary for API responses."""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'room_id': self.room_id,
            'context_mode': self.context_mode,
            'library_doc_ids': self.library_doc_ids or [],
            'instructions': self.instructions,
            'size': self.size,
            'mind_map_data': self.mind_map_data or {},
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
