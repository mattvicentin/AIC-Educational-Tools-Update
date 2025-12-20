"""
Card Comments Model

Comments attached to individual cards (segments) within Card View.
Cards are ephemeral (derived from segmentation), but comments persist
via a stable card_key derived from message_id + segment_index + body hash.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional

from src.app import db


def generate_card_key(message_id: int, segment_index: int, segment_body: str) -> str:
    """
    Generate a stable key for a card based on its source and content.
    
    Args:
        message_id: ID of the source message
        segment_index: Index of the segment (0-based)
        segment_body: First 200 chars of segment body for hash
        
    Returns:
        SHA1 hash string (40 chars) as card key
    """
    content = f"{message_id}:{segment_index}:{segment_body[:200]}"
    return hashlib.sha1(content.encode()).hexdigest()


def generate_body_hash(segment_body: str) -> str:
    """Generate a hash of the segment body for mismatch detection."""
    return hashlib.md5(segment_body.encode()).hexdigest()[:16]


class CardComment(db.Model):
    """
    Comments on individual cards (segments) within Card View.
    
    Cards are ephemeral but card_key provides a stable reference.
    If segmentation changes, segment_body_hash can detect mismatches.
    """
    
    __tablename__ = 'card_comment'
    __table_args__ = (
        db.Index('ix_card_comment_card_key', 'card_key'),
        db.Index('ix_card_comment_chat_card_created', 'chat_id', 'card_key', 'created_at'),
        db.Index('ix_card_comment_user_created', 'user_id', 'created_at'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id", ondelete="CASCADE"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id", ondelete="CASCADE"), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey("message.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    
    # Card identification
    card_key = db.Column(db.String(40), nullable=False)  # SHA1 hex
    segment_index = db.Column(db.Integer, nullable=False)
    
    # For mismatch detection (hash of segment body at comment time)
    segment_body_hash = db.Column(db.String(16), nullable=True)  # MD5 prefix
    
    # Content
    content = db.Column(db.Text, nullable=False)
    
    # Content type: 'user' for human comments, 'ai' for AI-generated replies
    content_type = db.Column(db.String(10), nullable=False, default='user')
    
    # Timestamps
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Soft delete
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship("User", backref=db.backref("card_comments", lazy="dynamic"))
    chat = db.relationship("Chat", backref=db.backref("card_comments", lazy="dynamic"))
    room = db.relationship("Room", backref=db.backref("card_comments", lazy="dynamic"))
    message = db.relationship("Message", backref=db.backref("card_comments", lazy="dynamic"))
    
    def __repr__(self) -> str:
        return f"<CardComment {self.id} on card {self.card_key[:8]}>"
    
    @property
    def is_deleted(self) -> bool:
        """Check if comment is soft-deleted."""
        return self.deleted_at is not None
    
    @property
    def is_ai(self) -> bool:
        """Check if this is an AI-generated comment."""
        return self.content_type == 'ai'
    
    @classmethod
    def count_consecutive_ai_for_user(
        cls, 
        card_key: str, 
        user_id: int, 
        limit: int = 2,
        chat_id: int = None,
    ) -> int:
        """
        Count how many consecutive AI replies the user has made on this card.
        
        Looks at the last `limit` comments by this user on this card (ordered by
        created_at DESC) and counts how many consecutive ones are AI-generated.
        
        Args:
            card_key: The card identifier
            user_id: The user to check
            limit: Max comments to check (default 2)
            chat_id: Optional chat_id for extra isolation (belt-and-suspenders)
            
        Returns:
            Number of consecutive AI comments (0, 1, or 2)
        """
        filters = [
            cls.card_key == card_key,
            cls.user_id == user_id,
            cls.deleted_at.is_(None),
        ]
        
        # Add chat_id filter if provided for extra isolation
        if chat_id is not None:
            filters.append(cls.chat_id == chat_id)
        
        recent = cls.query.filter(*filters).order_by(cls.created_at.desc()).limit(limit).all()
        
        count = 0
        for comment in recent:
            if comment.content_type == 'ai':
                count += 1
            else:
                break  # Streak broken by user comment
        return count
    
    def soft_delete(self) -> None:
        """Soft delete this comment."""
        self.deleted_at = datetime.now(timezone.utc)
    
    def to_dict(self, include_user: bool = True) -> dict:
        """
        Serialize comment to dictionary.
        
        Args:
            include_user: Include user info (name, id)
            
        Returns:
            Dictionary representation
        """
        data = {
            "id": self.id,
            "card_key": self.card_key,
            "segment_index": self.segment_index,
            "content": self.content,
            "content_type": self.content_type,  # 'user' or 'ai'
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_deleted": self.is_deleted,
        }
        
        if include_user and self.user:
            data["user"] = {
                "id": self.user.id,
                "username": self.user.username,
                "display_name": getattr(self.user, 'display_name', None) or self.user.username,
            }
        elif include_user:
            data["user"] = None  # User was deleted
        
        return data
    
    @classmethod
    def create(
        cls,
        chat_id: int,
        room_id: int,
        message_id: int,
        user_id: int,
        card_key: str,
        segment_index: int,
        content: str,
        segment_body: Optional[str] = None,
        content_type: str = 'user',
    ) -> "CardComment":
        """
        Factory method to create a new card comment.
        
        Args:
            chat_id: Chat containing the message
            room_id: Room containing the chat
            message_id: Message containing the card
            user_id: User creating the comment
            card_key: Stable card identifier
            segment_index: Index of the segment (0-based)
            content: Comment text
            segment_body: Optional segment body for hash (mismatch detection)
            content_type: 'user' for human comments, 'ai' for AI-generated
            
        Returns:
            New CardComment instance (not yet committed)
        """
        comment = cls(
            chat_id=chat_id,
            room_id=room_id,
            message_id=message_id,
            user_id=user_id,
            card_key=card_key,
            segment_index=segment_index,
            content=content,
            content_type=content_type,
        )
        
        if segment_body:
            comment.segment_body_hash = generate_body_hash(segment_body)
        
        return comment

