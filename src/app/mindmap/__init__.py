"""
Mind Map Tool integration blueprint
Provides mind map generation capabilities
"""

from flask import Blueprint

mindmap = Blueprint('mindmap', __name__, url_prefix='/api/mindmap')

from . import routes

__all__ = ['mindmap']
