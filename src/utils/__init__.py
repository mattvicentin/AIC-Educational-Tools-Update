"""
Utilities package for AI Collab Online
Contains helper functions and AI integration modules
"""

from .openai_utils import *
from .helpers import *

__all__ = [
    # OpenAI utils exports (simplified for Anthropic only)
    "BASE_MODES",
    "BASE_TEMPLATES",
    "MODES",
    "ChatMode",
    "get_client_type",
    "call_anthropic_api",
    "get_ai_response",
    "get_modes_for_room",
    "generate_room_modes",
    "get_mode_system_prompt",
    "get_available_templates",
    "assess_learning_progression",
    "get_progression_recommendation",
    "get_next_learning_step",
    "generate_chat_introduction",
    # Helper functions
    "generate_room_proposal",
    "refine_room_proposal",
]
