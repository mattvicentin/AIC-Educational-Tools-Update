"""
Flashcards Tool integration blueprint
Provides flashcard generation capabilities
"""

from flask import Blueprint

flashcards = Blueprint('flashcards', __name__, url_prefix='/api/flashcards')

from . import routes

__all__ = ['flashcards']
