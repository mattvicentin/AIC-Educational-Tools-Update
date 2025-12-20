"""
Learning Context Models

Models for storing and managing learning progression context,
including automatic note generation and cross-chat learning context.
"""

from datetime import datetime
from src.app import db


class ChatNotes(db.Model):
    """
    Model for storing automatically generated notes from completed chats.
    
    This enables cross-chat learning context where new chats can build
    upon insights from all previously completed discussions in the room.
    """
    __tablename__ = 'chat_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False, unique=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    notes_content = db.Column(db.Text, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    message_count = db.Column(db.Integer, nullable=False)
    
    # Relationships
    chat = db.relationship('Chat', backref='stored_notes')
    room = db.relationship('Room', backref='chat_notes')
    
    def __repr__(self):
        return f'<ChatNotes chat_id={self.chat_id} room_id={self.room_id} msgs={self.message_count}>'
