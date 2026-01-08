"""
Narrative Tool integration blueprint
Provides narrative generation capabilities
"""

from flask import Blueprint

narrative = Blueprint('narrative', __name__, url_prefix='/api/narrative')

from . import routes

__all__ = ['narrative']
