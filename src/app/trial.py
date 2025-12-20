"""Lightweight trial mode scaffolding.

This module provides minimal, non-persistent counters for anonymous users using
Flask's server-side session to enforce refinement limits when TRIAL_ENABLED is
true. It is designed to be safe and reversible without DB migrations.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime, timedelta, timezone

from flask import session, current_app


TRIAL_SESSION_KEY = "trial_state"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_trial_session() -> Dict[str, Any]:
    """Ensure a trial session dict exists in Flask session and return it."""
    state = session.get(TRIAL_SESSION_KEY)
    if not isinstance(state, dict):
        state = {}
    created_at = state.get("created_at")
    if not created_at:
        state["created_at"] = _now().isoformat()
    # expiry
    ttl_days = int(current_app.config.get("TRIAL_TTL_DAYS", 7) or 7)
    state["expires_at"] = (
        datetime.fromisoformat(state["created_at"]).replace(tzinfo=timezone.utc)
        + timedelta(days=ttl_days)
    ).isoformat()
    # counters bucket
    counters = state.get("counters")
    if not isinstance(counters, dict):
        counters = {}
    state["counters"] = counters
    session[TRIAL_SESSION_KEY] = state
    session.modified = True
    return state


def _expired(state: Dict[str, Any]) -> bool:
    try:
        exp = datetime.fromisoformat(state.get("expires_at"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return _now() > exp
    except Exception:
        return False


def can_consume_event(state: Dict[str, Any], event: str, max_allowed: int) -> bool:
    """Check if the given event can be consumed under trial limits.

    For refinement integration, event == 'refine'.
    """
    if _expired(state):
        return False
    counters: Dict[str, int] = state.get("counters", {})
    used = int(counters.get(event, 0) or 0)
    return used < int(max_allowed or 0)


def consume_event(state: Dict[str, Any], event: str) -> None:
    """Increment a trial event counter and persist back to session."""
    counters: Dict[str, int] = state.get("counters", {})
    counters[event] = int(counters.get(event, 0) or 0) + 1
    state["counters"] = counters
    session[TRIAL_SESSION_KEY] = state
    session.modified = True


