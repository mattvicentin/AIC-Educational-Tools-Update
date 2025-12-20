"""
Library Tool integration blueprint
Provides document upload, chunking, and search capabilities
"""

from flask import Blueprint

library = Blueprint('library', __name__, url_prefix='/api/library')

from . import upload, search, storage, access_control

__all__ = ['library']

