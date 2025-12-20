"""
Refinement and regeneration routes for learning steps.
"""

from flask import Blueprint, request, jsonify, current_app
import re
from src.app import db, csrf, limiter
from src.models import Room, CustomPrompt
from src.app.access_control import get_current_user, require_login, require_room_access
from src.utils.openai_utils import generate_room_modes
from ..utils.refinement_utils import (
    validate_and_normalize_modes,
    run_ai_refinement,
    record_refinement_history,
    compute_modes_diff,
)
from src.app.access_control import require_room_management

refine_bp = Blueprint('room_refine', __name__)


def _normalize_modes(modes):
    """Ensure modes is a list of dicts with keys: key,label,prompt."""
    if not isinstance(modes, list):
        return []
    out = []
    for m in modes:
        if isinstance(m, dict):
            key = m.get('key')
            label = m.get('label')
            prompt = m.get('prompt')
            if key and label and prompt:
                out.append({'key': key, 'label': label, 'prompt': prompt})
    return out


def _reindex_modes(modes):
    """Reindex mode keys as step1.. and optionally renumber leading label indices."""
    reindexed = []
    for idx, m in enumerate(modes, start=1):
        new_key = f"step{idx}"
        label = m.get('label', '')
        # If label starts with a number. or number) or number:
        new_label = label
        m_num = re.match(r"^\s*(\d+)([\.)\:]?\s+)(.*)$", label)
        if m_num:
            new_label = f"{idx}{m_num.group(2)}{m_num.group(3)}".strip()
        reindexed.append({'key': new_key, 'label': new_label, 'prompt': m.get('prompt', '')})
    return reindexed


def _parse_target_count(text):
    """Extract target count like 'reduce to 6' or 'six steps'."""
    if not text:
        return None
    m = re.search(r"\b(?:to\s*)?(\d{1,2})\b", text)
    if m:
        try:
            n = int(m.group(1))
            if 1 <= n <= 30:
                return n
        except Exception:
            pass
    # word numbers simple mapping
    words = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
        'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
    }
    for w, n in words.items():
        if re.search(rf"\b{w}\b", text):
            return n
    return None


def _parse_remove_hint(text):
    """Return a removal hint: by step number or label substring.
    Examples: 'remove step 9', 'remove the 9 historical patterns step'
    """
    if not text:
        return {}
    # step number
    m = re.search(r"remove\s+step\s*(\d{1,2})", text, re.I)
    if m:
        try:
            return {'step_number': int(m.group(1))}
        except Exception:
            pass
    # label substring between remove and step
    m2 = re.search(r"remove\s+(.*?)\s+step", text, re.I)
    if m2:
        sub = m2.group(1).strip("'\"").strip()
        if sub:
            return {'label_contains': sub.lower()}
    # generic remove <phrase>
    m3 = re.search(r"remove\s+(.+)$", text, re.I)
    if m3:
        sub = m3.group(1).strip()
        if sub:
            return {'label_contains': sub.lower()}
    return {}


def _apply_refinements(message: str, current_modes: list):
    """Apply simple deterministic refinements to the provided modes.
    Supports: reduce to N steps; remove step N; remove by label substring.
    Returns (new_modes, summary_message) or (None, None) if no change.
    """
    modes = _normalize_modes(current_modes)
    original_len = len(modes)
    if not modes:
        return None, None

    changed = False
    feedbacks = []
    text = (message or '').strip()

    # Reduce to N steps
    target = _parse_target_count(text)
    if target and target < len(modes):
        modes = modes[:target]
        changed = True
        feedbacks.append(f"reduced to {target} steps")

    # Remove specific step
    hint = _parse_remove_hint(text)
    if hint:
        before = len(modes)
        if 'step_number' in hint:
            num = hint['step_number']
            modes = [m for m in modes if not m.get('key', '').lower() == f'step{num}']
            if len(modes) != before:
                changed = True
                feedbacks.append(f"removed step {num}")
        elif 'label_contains' in hint:
            substr = hint['label_contains']
            modes = [m for m in modes if substr not in m.get('label', '').lower()]
            if len(modes) != before:
                changed = True
                feedbacks.append(f"removed step matching '{substr}'")

    if changed:
        modes = _reindex_modes(modes)
        msg = "; ".join(feedbacks) if feedbacks else "applied your changes"
        return modes, msg
    return None, None


@refine_bp.route("/refine-room-proposal", methods=["POST"]) 
@csrf.exempt
@limiter.limit("10/minute")
def refine_room_proposal_new():
    """Refine proposal during new-room flow (no room_id yet).
    Regenerates modes based on current title/description hints; returns updates for UI.
    """
    current_app.logger.info("🔥 REFINE ROUTE HIT: /refine-room-proposal (REAL ROUTE)")
    try:
        from uuid import uuid4
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        current_modes = data.get("current_modes") or []
        title = (data.get("current_room_title") or "").strip()
        description = (data.get("current_room_description") or "").strip()
        
        # AI TITLE GENERATION (if no title provided)
        if not title and description:
            current_app.logger.info(f"🤖 GENERATING AI TITLE from description: '{description}'")
            try:
                from src.utils.openai_utils import call_anthropic_api
                
                prompt = f"Create a clear and concise title for this learning room. It should be no longer than five words. Goals: {description}"
                
                ai_response = call_anthropic_api(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,
                    temperature=0.3
                )
                
                if ai_response and ai_response.strip():
                    title = ai_response.strip()
                    current_app.logger.info(f"✅ AI TITLE SUCCESS: '{title}'")
                else:
                    current_app.logger.warning("❌ AI returned empty title response")
                    
            except Exception as e:
                current_app.logger.error(f"❌ AI TITLE ERROR: {e}")
        
        current_app.logger.info(f"🎯 FINAL TITLE: '{title}' (from AI or user input)")

        # Auth/trial guard: allow anonymous only when TRIAL_ENABLED; otherwise require login
        user = get_current_user()
        if not user and not current_app.config.get('TRIAL_ENABLED'):
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))

        # Create a temporary room-like object for mode generation
        tmp = type('obj', (object,), {
            'id': 0,
            'name': title or 'New Room',
            'goals': description or '',
            'description': description or ''
        })
        # If feature flag enabled, run AI refinement v2 with strict validation
        if current_app.config.get('REFINE_V2_ENABLED'):
            try:
                base_modes = current_modes
                if not isinstance(base_modes, list) or not base_modes:
                    try:
                        modes_obj = generate_room_modes(tmp)
                        base_modes = [
                            {"key": k, "label": v.label, "prompt": v.prompt}
                            for k, v in (modes_obj.items() if hasattr(modes_obj, 'items') else [])
                        ]
                    except Exception:
                        base_modes = []

                # Trial counters: if anonymous and TRIAL_ENABLED, enforce max refines
                try:
                    if current_app.config.get('TRIAL_ENABLED'):
                        user = get_current_user()
                        if not user:
                            from src.app.trial import ensure_trial_session, can_consume_event, consume_event
                            sess = ensure_trial_session()
                            if not can_consume_event(sess, 'refine', current_app.config.get('TRIAL_MAX_REFINES', 3)):
                                return jsonify({"success": False, "error": "Trial limit reached for refinements"}), 403
                except Exception:
                    pass

                ai_out = run_ai_refinement(tmp, base_modes, message)
                modes = ai_out.get("modes", [])
                summary = (ai_out.get("summary") or "").strip()
                diff = compute_modes_diff(base_modes, modes)
                provider = ai_out.get("provider")
                ai_message = (
                    f"Applied your feedback. {('Summary: ' + summary) if summary else ''}"
                )
                resp = {
                    "success": True,
                    "room_title": title or 'New Room',
                    "room_description": description or '',
                    "modes": modes,
                    "conversation_id": str(uuid4()),
                    "ai_message": ai_message,
                    "changes_applied": True,
                    "diff": diff,
                    "provider": provider
                }
                # Consume trial event on success
                try:
                    if current_app.config.get('TRIAL_ENABLED'):
                        user = get_current_user()
                        if not user:
                            from src.app.trial import ensure_trial_session, consume_event
                            sess = ensure_trial_session()
                            consume_event(sess, 'refine')
                except Exception:
                    pass
                return jsonify(resp)
            except Exception:
                # Fall through to deterministic path
                pass

        # Deterministic fast path (pre-pass + generation fallback)
        modes, summary = _apply_refinements(message, current_modes)
        if modes is None:
            try:
                modes_obj = generate_room_modes(tmp)
                modes = [
                    {"key": k, "label": v.label, "prompt": v.prompt}
                    for k, v in (modes_obj.items() if hasattr(modes_obj, 'items') else [])
                ]
                summary = None
            except Exception:
                modes = current_modes if isinstance(current_modes, list) else []
                summary = None

        ai_message = (
            f"I {summary}. Save changes to persist." if summary else
            "Updated your proposal. Adjust further or save when ready."
        )

        return jsonify({
            "success": True,
            "room_title": title or 'New Room',
            "room_description": description or '',
            "modes": modes,
            "conversation_id": str(uuid4()),
            "ai_message": ai_message,
            "changes_applied": True
        })
    except Exception as e:
        current_app.logger.error(f"[refine.new] error: {e}")
        return jsonify({"success": False, "error": "Failed to refine"}), 500


@refine_bp.route("/<int:room_id>/refine-room-proposal", methods=["POST"]) 
@require_room_access
@csrf.exempt
@limiter.limit("10/minute")
def refine_room_proposal_edit(room_id: int):
    """Refine proposal for an existing room. Returns updated modes, not persisted."""
    try:
        room = Room.query.get_or_404(room_id)
        data = request.get_json(silent=True) or {}
        current_modes = data.get("current_modes") or []
        title = (data.get("current_room_title") or room.name or "").strip()
        description = (data.get("current_room_description") or room.description or "").strip()

        tmp = type('obj', (object,), {
            'id': room.id,
            'name': title or room.name,
            'goals': room.goals or description or '',
            'description': description or room.description or ''
        })
        # If feature flag enabled, use AI refinement pipeline with history
        if current_app.config.get('REFINE_V2_ENABLED'):
            try:
                # Build base_modes from current custom prompts if current_modes missing
                base_modes = current_modes
                if not isinstance(base_modes, list) or not base_modes:
                    cps = CustomPrompt.query.filter_by(room_id=room_id).all()
                    base_modes = [
                        {"key": cp.mode_key, "label": cp.label, "prompt": cp.prompt}
                        for cp in cps
                    ]
                if not base_modes:
                    try:
                        modes_obj = generate_room_modes(tmp)
                        base_modes = [
                            {"key": k, "label": v.label, "prompt": v.prompt}
                            for k, v in (modes_obj.items() if hasattr(modes_obj, 'items') else [])
                        ]
                    except Exception:
                        base_modes = []

                # Save old modes snapshot before update
                old_modes_snapshot = list(base_modes)

                # Trial counters for anonymous users only
                try:
                    if current_app.config.get('TRIAL_ENABLED'):
                        user = get_current_user()
                        if not user:
                            from src.app.trial import ensure_trial_session, can_consume_event
                            sess = ensure_trial_session()
                            if not can_consume_event(sess, 'refine', current_app.config.get('TRIAL_MAX_REFINES', 3)):
                                return jsonify({"success": False, "error": "Trial limit reached for refinements"}), 403
                except Exception:
                    pass

                ai_out = run_ai_refinement(tmp, base_modes, data.get("message", ""))
                modes = ai_out.get("modes", [])
                summary = (ai_out.get("summary") or "").strip()
                diff = compute_modes_diff(base_modes, modes)
                provider = ai_out.get("provider")

                # Persist transactionally
                try:
                    CustomPrompt.query.filter_by(room_id=room_id).delete()
                    user = get_current_user()
                    created_by = getattr(user, 'id', None) or 0
                    for m in modes:
                        if m.get('key') and m.get('label') and m.get('prompt'):
                            db.session.add(CustomPrompt(
                                mode_key=m['key'],
                                label=m['label'],
                                prompt=m['prompt'],
                                room_id=room_id,
                                created_by=created_by,
                            ))
                    db.session.commit()
                    persisted = True
                except Exception as persist_err:
                    db.session.rollback()
                    current_app.logger.error(f"[refine.edit] persist error: {persist_err}")
                    persisted = False

                # Record history (non-blocking)
                try:
                    user = get_current_user()
                    record_refinement_history(
                        room_id=room_id,
                        user_id=getattr(user, 'id', None),
                        preference=(data.get("message") or ""),
                        old_modes=old_modes_snapshot,
                        new_modes=modes,
                        summary=summary,
                    )
                    # Analytics event
                    try:
                        from src.models.analytics import RefinementEvent
                        ev = RefinementEvent(
                            user_id=getattr(user, 'id', None),
                            room_id=room_id,
                            event_type='refine_edit',
                            preference=(data.get("message") or ""),
                            added=len(diff.get('added', [])),
                            removed=len(diff.get('removed', [])),
                            changed=len(diff.get('changed', [])),
                        )
                        db.session.add(ev)
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                except Exception:
                    pass

                ai_message = (
                    f"Applied your feedback. {('Summary: ' + summary) if summary else ''}"
                )

                resp = {
                    "success": True,
                    "room_title": title,
                    "room_description": description,
                    "modes": modes,
                    "ai_message": ai_message,
                    "changes_applied": True,
                    "persisted": persisted,
                    "diff": diff,
                    "provider": provider
                }
                # Consume trial event on success
                try:
                    if current_app.config.get('TRIAL_ENABLED'):
                        user = get_current_user()
                        if not user:
                            from src.app.trial import ensure_trial_session, consume_event
                            sess = ensure_trial_session()
                            consume_event(sess, 'refine')
                except Exception:
                    pass
                return jsonify(resp)
            except Exception:
                # Fall through to deterministic path
                pass

        # Deterministic path (pre-pass + generate fallback, then persist)
        modes, summary = _apply_refinements(data.get("message"), current_modes)
        if modes is None:
            try:
                modes_obj = generate_room_modes(tmp)
                modes = [
                    {"key": k, "label": v.label, "prompt": v.prompt}
                    for k, v in (modes_obj.items() if hasattr(modes_obj, 'items') else [])
                ]
                summary = None
            except Exception:
                modes = current_modes if isinstance(current_modes, list) else []
                summary = None

        # Persist immediately for edit flow so changes are reflected without requiring an extra Save click
        try:
            CustomPrompt.query.filter_by(room_id=room_id).delete()
            user = get_current_user()
            created_by = getattr(user, 'id', None) or 0
            for m in modes:
                if m.get('key') and m.get('label') and m.get('prompt'):
                    db.session.add(CustomPrompt(
                        mode_key=m['key'],
                        label=m['label'],
                        prompt=m['prompt'],
                        room_id=room_id,
                        created_by=created_by,
                    ))
            db.session.commit()
            persisted = True
        except Exception as persist_err:
            db.session.rollback()
            current_app.logger.error(f"[refine.edit] persist error: {persist_err}")
            persisted = False

        ai_message = (
            f"I {summary}. Changes have been saved." if summary else
            ("Applied your feedback and saved the changes." if persisted else
             "Applied your feedback to the learning steps.")
        )

        return jsonify({
            "success": True,
            "room_title": title,
            "room_description": description,
            "modes": modes,
            "ai_message": ai_message,
            "changes_applied": True,
            "persisted": persisted
        })
    except Exception as e:
        current_app.logger.error(f"[refine.edit] error: {e}")
        return jsonify({"success": False, "error": "Failed to refine"}), 500


@refine_bp.route("/<int:room_id>/regenerate-learning-steps", methods=["POST"]) 
@require_room_access
@csrf.exempt
@limiter.limit("6/minute")
def regenerate_learning_steps(room_id: int):
    """Generate a fresh set of modes for the room and replace existing CustomPrompt rows."""
    try:
        room = Room.query.get_or_404(room_id)
        modes_obj = generate_room_modes(room)
        new_modes = [
            {"key": k, "label": v.label, "prompt": v.prompt}
            for k, v in (modes_obj.items() if hasattr(modes_obj, 'items') else [])
        ]

        # Replace existing prompts transactionally
        CustomPrompt.query.filter_by(room_id=room_id).delete()
        user = get_current_user()
        created_by = getattr(user, 'id', None) or 0
        for m in new_modes:
            if m.get('key') and m.get('label') and m.get('prompt'):
                db.session.add(CustomPrompt(
                    mode_key=m['key'],
                    label=m['label'],
                    prompt=m['prompt'],
                    room_id=room_id,
                    created_by=created_by,
                ))
        db.session.commit()

        return jsonify({"success": True, "new_modes": new_modes})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[regenerate] error: {e}")
        return jsonify({"success": False, "error": "Failed to regenerate steps"}), 500


@refine_bp.route("/<int:room_id>/history", methods=["GET"]) 
@require_room_management
def list_refinement_history(room_id: int):
    """Return recent refinement history entries for a room (management only)."""
    try:
        from src.models.refinement import RoomRefinementHistory
        rows = (
            RoomRefinementHistory.query
            .filter_by(room_id=room_id)
            .order_by(RoomRefinementHistory.created_at.desc())
            .limit(20)
            .all()
        )
        items = []
        for r in rows:
            items.append({
                "id": r.id,
                "summary": r.summary or "",
                "preference": r.preference or "",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return jsonify({"success": True, "history": items, "count": len(items)})
    except Exception as e:
        current_app.logger.error(f"[history] error: {e}")
        return jsonify({"success": False, "error": "Failed to load history"}), 500


@refine_bp.route("/<int:room_id>/revert/<int:history_id>", methods=["POST"]) 
@require_room_management
@csrf.exempt
@limiter.limit("6/minute")
def revert_learning_steps(room_id: int, history_id: int):
    """Revert room's learning steps to a history record's new_modes snapshot."""
    try:
        if not current_app.config.get('REFINE_V2_ENABLED'):
            return jsonify({"success": False, "error": "Refine v2 disabled"}), 400

        from src.models.refinement import RoomRefinementHistory
        room = Room.query.get_or_404(room_id)
        hist = RoomRefinementHistory.query.filter_by(id=history_id, room_id=room_id).first()
        if not hist:
            return jsonify({"success": False, "error": "History not found"}), 404

        import json as _json
        try:
            target_modes = _json.loads(hist.new_modes_json or '[]')
        except Exception:
            target_modes = []

        # Validate and normalize before writing
        normalized, _ = validate_and_normalize_modes(target_modes)
        if not normalized:
            return jsonify({"success": False, "error": "Invalid target modes"}), 400

        # Persist transactionally
        try:
            CustomPrompt.query.filter_by(room_id=room_id).delete()
            user = get_current_user()
            created_by = getattr(user, 'id', None) or 0
            for m in normalized:
                db.session.add(CustomPrompt(
                    mode_key=m['key'],
                    label=m['label'],
                    prompt=m['prompt'],
                    room_id=room_id,
                    created_by=created_by,
                ))
            db.session.commit()
        except Exception as persist_err:
            db.session.rollback()
            current_app.logger.error(f"[revert] persist error: {persist_err}")
            return jsonify({"success": False, "error": "Failed to persist revert"}), 500

        # Record revert as history
        try:
            # Capture current (post-revert) snapshot for completeness
            cps = CustomPrompt.query.filter_by(room_id=room_id).all()
            new_snapshot = [
                {"key": cp.mode_key, "label": cp.label, "prompt": cp.prompt}
                for cp in cps
            ]
            user = get_current_user()
            record_refinement_history(
                room_id=room_id,
                user_id=getattr(user, 'id', None),
                preference=f"revert:{history_id}",
                old_modes=[],
                new_modes=new_snapshot,
                summary="Reverted learning steps to a previous version",
            )
        except Exception:
            pass

        # Analytics event
        try:
            from src.models.analytics import RefinementEvent
            user = get_current_user()
            ev = RefinementEvent(
                user_id=getattr(user, 'id', None),
                room_id=room_id,
                event_type='revert',
                preference=f"revert:{history_id}",
                added=0,
                removed=0,
                changed=0,
            )
            db.session.add(ev)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return jsonify({"success": True, "modes": normalized})

    except Exception as e:
        current_app.logger.error(f"[revert] error: {e}")
        return jsonify({"success": False, "error": "Failed to revert"}), 500

