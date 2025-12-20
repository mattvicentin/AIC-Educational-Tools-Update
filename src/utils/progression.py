#!/usr/bin/env python3
"""
progression.py
Purpose: Helpers for learning progression suggestions with exponential cooldown.
"""

from typing import Any, Dict, Optional
import os

from flask import url_for


def build_next_step_descriptor(chat: Any) -> Optional[Dict[str, str]]:
    """Return {key,label,link} for the next learning step in this chat's room.

    Uses the room's configured modes (custom prompts first), then falls back to
    base modes. Link points to the learning steps editor for this room.
    """
    try:
        from src.utils.openai_utils import get_modes_for_room
        modes = get_modes_for_room(chat.room) if getattr(chat, "room", None) else {}
        mode_keys = list(modes.keys())
        current_key = getattr(chat, "mode", "") or (mode_keys[0] if mode_keys else "")
        if current_key in mode_keys:
            idx = mode_keys.index(current_key)
            if idx + 1 < len(mode_keys):
                next_key = mode_keys[idx + 1]
                mode_info = modes.get(next_key)
                label = getattr(mode_info, "label", str(mode_info)) or next_key
                link = url_for("room.new_learning_steps", room_id=chat.room_id)
                return {"key": next_key, "label": label, "link": link}
    except Exception:
        pass
    return None


def compute_suggestion(chat: Any) -> Optional[Dict[str, Any]]:
    """Compute suggestion payload with discussion context, based on rubric confidence and next step.

    Returns None if no next step or confidence below threshold.
    """
    try:
        from src.utils.openai_utils import get_progression_recommendation_with_rubric
    except Exception:
        return None

    rec = get_progression_recommendation_with_rubric(chat) or {}
    confidence = float(rec.get("confidence") or 0.0)
    # Default to 0.80 because current heuristics/rubric helper tops near ~0.85
    threshold = float(os.getenv("MODE_SUGGEST_THRESHOLD", "0.80"))
    next_step = rec.get("next_step")
    if not next_step:
        # Fallback: compute directly
        next_step = build_next_step_descriptor(chat)

    if confidence >= threshold and next_step:
        suggestion = {
            "confidence": confidence,
            "next_key": next_step.get("key"),
            "next_label": next_step.get("label"),
            "link": next_step.get("link"),
        }
        
        # Add discussion context if 5+ messages available
        try:
            from src.models import Message
            message_count = Message.query.filter_by(chat_id=chat.id).count()
            
            if message_count >= 5:
                # Generate summary context using existing document generation
                messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp).all()
                
                # Use existing document generation logic
                from src.app.documents import generate_document_content
                summary_notes = generate_document_content(messages, chat, "notes")
                
                # Extract key insights for banner context
                context_lines = summary_notes.split('\n')
                context_preview = None
                
                # Look for key sections in summary
                for i, line in enumerate(context_lines):
                    if any(keyword in line for keyword in ["Key Insights", "Original Ideas", "Technical Solutions"]):
                        # Take next few lines as context
                        preview_lines = []
                        for j in range(i+1, min(i+4, len(context_lines))):
                            if context_lines[j].strip() and not context_lines[j].startswith('#'):
                                preview_lines.append(context_lines[j].strip())
                        context_preview = " ".join(preview_lines)[:250]
                        break
                
                if not context_preview:
                    # Fallback: use first meaningful content
                    meaningful_lines = [line.strip() for line in context_lines 
                                      if line.strip() and not line.startswith('#') and len(line.strip()) > 20]
                    context_preview = " ".join(meaningful_lines[:2])[:250] if meaningful_lines else "your discussion"
                
                suggestion["context"] = context_preview
                suggestion["has_context"] = True
            else:
                suggestion["has_context"] = False
                
        except Exception as e:
            # Context generation failed - continue without context
            suggestion["has_context"] = False
            
        return suggestion
    
    return None


def should_show_with_exponential_cooldown(state: Dict[str, Any], chat: Any) -> bool:
    """Exponential cooldown gating.

    state shape (per chat_id):
    {
      "mode": str,
      "shown_once": bool,
      "cooldown": int,   # current cooldown window in assistant replies
      "since": int       # assistant replies since last suggestion
    }
    """
    mode = getattr(chat, "mode", "")
    # Reset state when mode changes
    if state.get("mode") != mode:
        state.clear()
        state.update({"mode": mode, "shown_once": False, "cooldown": 1, "since": 0})

    # If never shown in this mode, show now
    if not state.get("shown_once"):
        state["shown_once"] = True
        state["cooldown"] = 2  # next window doubles from here
        state["since"] = 0
        return True

    # Otherwise, require since >= cooldown
    if int(state.get("since", 0)) >= int(state.get("cooldown", 1)):
        # Show and double cooldown
        state["cooldown"] = max(1, int(state.get("cooldown", 1))) * 2
        state["since"] = 0
        return True

    # Not ready; increment since for the next time this function is called
    state["since"] = int(state.get("since", 0)) + 1
    return False


