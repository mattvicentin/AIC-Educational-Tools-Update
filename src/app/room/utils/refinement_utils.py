"""Utilities for Room Refinement v2: validation, context, AI rewrite, and history.

This module implements:
- validate_and_normalize_modes: strict validator and normalizer for modes
- build_refinement_prompt: constructs system/user prompts per design
- run_ai_refinement: constrained AI call with failover and strict JSON parsing
- record_refinement_history: persistence helper
"""

from __future__ import annotations

import os
import json
import re
from typing import Any, Dict, List, Tuple
import time

from flask import current_app
from src.app import db
from src.models import Room
from src.models.refinement import RoomRefinementHistory
from src.utils.openai_utils import call_anthropic_api, call_openai_api


def _strip_html(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Simple tag remover
    return re.sub(r"<[^>]*>", "", text)


def _normalize_label(label: str, index: int) -> str:
    label = (label or "").strip()
    # Remove leading ordinal if present, we will enforce fresh numbering
    label = re.sub(r"^\s*\d+[\.)\: ]+", "", label)
    return f"{index}. {label}".strip()


def _sequential_key(i: int) -> str:
    return f"step{i}"


def validate_and_normalize_modes(
    modes: List[Dict[str, Any]],
    *,
    min_steps: int = 1,
    max_steps: int = 12,
    max_prompt_len: int = 2000,
) -> Tuple[List[Dict[str, str]], List[str]]:
    """Validate and normalize an array of mode dicts.

    Returns (normalized_modes, warnings). Empty list if irreparable.
    """
    warnings: List[str] = []
    if not isinstance(modes, list):
        return [], ["modes must be a list"]

    cleaned: List[Dict[str, str]] = []
    for m in modes:
        if not isinstance(m, dict):
            continue
        label = (m.get("label") or "").strip()
        prompt = (m.get("prompt") or "").strip()
        if not label or not prompt:
            continue
        # Strip HTML and cap prompt length
        prompt = _strip_html(prompt)[: max_prompt_len]
        cleaned.append({"label": label, "prompt": prompt})

    if not cleaned:
        return [], ["no valid modes"]

    # Enforce bounds
    if len(cleaned) < min_steps:
        warnings.append("below minimum steps; keeping available")
    if len(cleaned) > max_steps:
        cleaned = cleaned[:max_steps]
        warnings.append("truncated to max steps")

    # Renumber keys and labels sequentially
    normalized: List[Dict[str, str]] = []
    for idx, m in enumerate(cleaned, start=1):
        normalized.append({
            "key": _sequential_key(idx),
            "label": _normalize_label(m.get("label", ""), idx),
            "prompt": m.get("prompt", "").strip(),
        })

    return normalized, warnings


def build_refinement_prompt(
    room: Room,
    current_modes: List[Dict[str, Any]],
    preference: str,
) -> Tuple[str, str]:
    """Return (system_prompt, user_prompt) per design skeleton."""
    title = getattr(room, "name", "") or "Room"
    goals = (getattr(room, "goals", None) or getattr(room, "description", "") or "").strip()

    # Summarize current steps (cap to 12)
    lines: List[str] = []
    for i, m in enumerate(current_modes[:12], start=1):
        label = (m.get("label") or "").strip()
        prompt = (m.get("prompt") or "").strip()
        if len(prompt) > 180:
            prompt = prompt[:177] + "…"
        lines.append(f"{i}. {label} — prompt: {prompt}")

    user = (
        f"Room title: \"{title}\"\n"
        f"Room goals: \"{goals}\"\n\n"
        f"Current steps:\n" + ("\n".join(lines) if lines else "(none)") + "\n\n"
        f"Preference: \"{(preference or '').strip()}\"\n\n"
        "Return ONLY JSON as:\n"
        "{\n"
        "  \"modes\": [{ \"key\": \"step1\", \"label\": \"1. …\", \"prompt\": \"…\" }],\n"
        "  \"summary\": \"…\",\n"
        "  \"notes\": [\"optional\"]\n"
        "}"
    )

    system = (
        "You are revising a course/room learning sequence. Produce ONLY JSON with fields "
        "modes, summary, and optional notes. Follow schema strictly. Do not include prose.\n"
        "Each mode: { key, label, prompt }. Keys must be step1..stepN. Labels must start with 'n.'. "
        "Prompts must be plain text."
    )
    return system, user


def _failover_order() -> List[str]:
    order_raw = os.getenv("AI_FAILOVER_ORDER", "anthropic,openai,templates")
    return [p.strip().lower() for p in order_raw.split(',') if p.strip()]


def _parse_strict_json(text: str) -> Dict[str, Any]:
    # Extract first JSON object
    match = re.search(r"\{[\s\S]*\}", text or "")
    if not match:
        raise ValueError("no json in response")
    return json.loads(match.group(0))


def run_ai_refinement(
    room: Room,
    current_modes: List[Dict[str, Any]],
    preference: str,
    *,
    max_tokens: int = 1200,
) -> Dict[str, Any]:
    """Run constrained AI refinement with failover. Returns dict with modes/summary/notes.

    Raises on hard failure; caller should handle fallback.
    """
    system, user = build_refinement_prompt(room, current_modes, preference)

    # Short-lived in-process cache (per worker)
    cached = _cache_get(room, current_modes, preference)
    if cached is not None:
        return cached

    last_err: Exception | None = None
    order = _failover_order()
    for provider in order:
        try:
            if provider == "anthropic":
                text, _ = call_anthropic_api([{"role": "user", "content": user}], system_prompt=system, max_tokens=max_tokens)
            elif provider == "openai":
                text, _ = call_openai_api([{"role": "user", "content": user}], system_prompt=system, max_tokens=max_tokens)
            elif provider == "templates":
                # Fallback: return current modes with a note
                return {
                    "modes": current_modes,
                    "summary": "Used template fallback; kept existing steps.",
                    "notes": ["Template fallback invoked"],
                    "provider": "templates",
                }
            else:
                continue

            parsed = _parse_strict_json(text)
            modes = parsed.get("modes", [])
            summary = (parsed.get("summary") or "").strip()
            notes = parsed.get("notes") or []
            normalized, warnings = validate_and_normalize_modes(modes)
            if not normalized:
                raise ValueError("AI returned invalid modes after normalization")
            # Attach warnings to notes
            if warnings:
                notes = list(notes) + warnings
            result = {"modes": normalized, "summary": summary, "notes": notes, "provider": provider}
            _cache_set(room, current_modes, preference, result)
            return result
        except Exception as e:  # noqa: BLE001
            last_err = e
            try:
                current_app.logger.warning(f"[refine] provider {provider} failed: {e}")
            except Exception:
                pass
            continue

    raise RuntimeError(f"AI refinement failed: {last_err}")


def record_refinement_history(
    room_id: int,
    user_id: int | None,
    preference: str,
    old_modes: List[Dict[str, Any]],
    new_modes: List[Dict[str, Any]],
    summary: str,
) -> None:
    """Insert a history record, swallowing non-critical errors."""
    try:
        rec = RoomRefinementHistory(
            room_id=room_id,
            user_id=user_id,
            preference=(preference or "").strip(),
            old_modes_json=json.dumps(old_modes, ensure_ascii=False),
            new_modes_json=json.dumps(new_modes, ensure_ascii=False),
            summary=(summary or "").strip(),
        )
        db.session.add(rec)
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
        try:
            current_app.logger.warning("[refine] failed to record refinement history")
        except Exception:
            pass


# -----------------
# Caching utilities
# -----------------
_REFINE_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_REFINE_TTL_SECS = 120


def _cache_key(room: Room, current_modes: List[Dict[str, Any]], preference: str) -> str:
    # Build a compact signature
    rid = getattr(room, 'id', 0) or 0
    labels = ":".join([(m.get('label') or '') for m in (current_modes or [])])[:512]
    pref = (preference or '').strip()[:256]
    return f"{rid}|{hash(labels)}|{hash(pref)}"


def _cache_get(room: Room, current_modes: List[Dict[str, Any]], preference: str) -> Dict[str, Any] | None:
    try:
        key = _cache_key(room, current_modes, preference)
        ts, val = _REFINE_CACHE.get(key, (0.0, None))  # type: ignore[assignment]
        if val is None:
            return None
        if (time.time() - ts) <= _REFINE_TTL_SECS:
            return val
        # expired
        _REFINE_CACHE.pop(key, None)
        return None
    except Exception:
        return None


def _cache_set(room: Room, current_modes: List[Dict[str, Any]], preference: str, result: Dict[str, Any]) -> None:
    try:
        key = _cache_key(room, current_modes, preference)
        _REFINE_CACHE[key] = (time.time(), result)
    except Exception:
        pass


# -------------
# Diff utility
# -------------
def compute_modes_diff(before: List[Dict[str, Any]], after: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute a simple diff between two mode lists by label.

    Returns dict with keys: added, removed, changed (list of {from_label,to_label}).
    """
    before_labels = [ (m.get('key'), (m.get('label') or '')) for m in (before or []) ]
    after_labels = [ (m.get('key'), (m.get('label') or '')) for m in (after or []) ]

    bset = set([lbl for _, lbl in before_labels])
    aset = set([lbl for _, lbl in after_labels])

    added = [lbl for lbl in (aset - bset)]
    removed = [lbl for lbl in (bset - aset)]

    # Changed: same index but different label length or content
    changed: List[Dict[str, str]] = []
    for i in range(min(len(before_labels), len(after_labels))):
        b_lbl = before_labels[i][1]
        a_lbl = after_labels[i][1]
        if b_lbl != a_lbl:
            changed.append({"from_label": b_lbl, "to_label": a_lbl})

    return {"added": added, "removed": removed, "changed": changed}


