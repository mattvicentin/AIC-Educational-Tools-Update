"""
Quiz Tool integration blueprint
Provides quiz generation and grading capabilities
"""

from flask import Blueprint

quiz = Blueprint('quiz', __name__, url_prefix='/api/quiz')

from . import routes

__all__ = ['quiz']


