#!/usr/bin/env python3
"""
quiz.py
Purpose: Quiz and QuizAnswer models for Quiz Tool
Status: [NEW]
Created: 2025-12-20

Models for storing generated quizzes and user answers
"""

from datetime import datetime, timezone
from sqlalchemy import JSON
from src.app import db
from typing import Optional, Dict, List


class Quiz(db.Model):
    """Stores a generated quiz with questions and correct answers."""
    
    __tablename__ = 'quiz'
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
    question_count = db.Column(db.Integer, nullable=False)
    context_mode = db.Column(db.String(20), nullable=False)  # 'chat', 'library', 'both'
    library_doc_ids = db.Column(JSON, nullable=True)  # List of document IDs
    instructions = db.Column(db.Text, nullable=True)
    
    # Generated quiz data (stored as JSON)
    questions = db.Column(JSON, nullable=False)  # List of question objects
    
    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Relationships
    chat = db.relationship("Chat", backref="quizzes")
    room = db.relationship("Room", backref="quizzes")
    creator = db.relationship("User", foreign_keys=[created_by])
    answers = db.relationship(
        "QuizAnswer", 
        backref="quiz", 
        lazy=True, 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Quiz {self.id} chat={self.chat_id} questions={self.question_count}>"
    
    def to_dict(self, include_answers: bool = False) -> Dict:
        """Convert quiz to dictionary for API responses."""
        data = {
            'id': self.id,
            'chat_id': self.chat_id,
            'room_id': self.room_id,
            'question_count': self.question_count,
            'context_mode': self.context_mode,
            'library_doc_ids': self.library_doc_ids or [],
            'instructions': self.instructions,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        
        if include_answers:
            # Include correct answers (for grading)
            data['questions'] = self.questions
        else:
            # Exclude correct answers (for display)
            questions_display = []
            for q in self.questions:
                q_display = {k: v for k, v in q.items() if k != 'correct_answer'}
                questions_display.append(q_display)
            data['questions'] = questions_display
        
        return data


class QuizAnswer(db.Model):
    """Stores a user's answers to a quiz."""
    
    __tablename__ = 'quiz_answer'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(
        db.Integer, 
        db.ForeignKey("quiz.id", ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("user.id", ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Answers stored as JSON: {question_id: selected_choice_index}
    answers = db.Column(JSON, nullable=False)
    
    # Grading results
    score = db.Column(db.Integer, nullable=True)  # Number correct
    total = db.Column(db.Integer, nullable=True)  # Total questions
    graded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    results = db.Column(JSON, nullable=True)  # Per-question results with explanations
    
    # Metadata
    started_at = db.Column(
        db.DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = db.relationship("User", backref="quiz_answers")
    
    def __repr__(self) -> str:
        return f"<QuizAnswer {self.id} quiz={self.quiz_id} user={self.user_id}>"
    
    def to_dict(self) -> Dict:
        """Convert quiz answer to dictionary for API responses."""
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'user_id': self.user_id,
            'answers': self.answers,
            'score': self.score,
            'total': self.total,
            'graded_at': self.graded_at.isoformat() if self.graded_at else None,
            'results': self.results,
            'started_at': self.started_at.isoformat(),
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
        }

