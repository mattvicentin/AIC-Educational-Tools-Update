"""
Room blueprint initialization.
Registers all room-related routes and services.
"""

from flask import Blueprint
from src.app import csrf

# Create main blueprint
room = Blueprint("room", __name__)

# Import route blueprints to ensure they're registered
from .routes import crud, templates, invitations, api, refine

# Register route blueprints
room.register_blueprint(crud.crud_bp, url_prefix="")
room.register_blueprint(templates.templates_bp, url_prefix="/template")
room.register_blueprint(invitations.invitations_bp, url_prefix="/<int:room_id>")
room.register_blueprint(api.api_bp, url_prefix="/api")
room.register_blueprint(refine.refine_bp, url_prefix="")

# Learning steps management routes (backward-compat)
@room.route('/<int:room_id>/update-learning-steps', methods=['POST', 'OPTIONS'])
@csrf.exempt
def update_learning_steps(room_id: int):
    from flask import request, jsonify, current_app
    from src.models import CustomPrompt, Room
    from src.app import db
    from src.app.access_control import get_current_user
    try:
        # Handle preflight/same-origin OPTIONS
        if request.method == 'OPTIONS':
            return jsonify({"success": True}), 200
        data = request.get_json(silent=True) or {}
        modes = data.get('modes') or data.get('refined_modes')
        
        # Also handle room name and description updates
        room_name = data.get('name', '').strip()
        room_description = data.get('description', '').strip()
        if isinstance(modes, str):
            import json as _json
            try:
                modes = _json.loads(modes)
            except Exception:
                modes = []
        if not isinstance(modes, list):
            return jsonify({"success": False, "error": "Invalid modes payload"}), 400
        
        # Update room fields if provided
        room = Room.query.get(room_id)
        if room:
            if room_name:
                room.name = room_name
            if room_description:
                room.description = room_description
        
        # Replace existing prompts for this room
        CustomPrompt.query.filter_by(room_id=room_id).delete()
        user = get_current_user()
        created_by = getattr(user, 'id', None) or 0
        for m in modes:
            key = m.get('key')
            label = m.get('label')
            prompt = m.get('prompt')
            if key and label and prompt:
                db.session.add(CustomPrompt(
                    mode_key=key,
                    label=label,
                    prompt=prompt,
                    room_id=room_id,
                    created_by=created_by
                ))
        db.session.commit()
        return jsonify({"success": True, "redirect_url": f"/room/{room_id}"})
    except Exception as e:
        current_app.logger.error(f"[learning-steps.update] error: {e}")
        return jsonify({"success": False, "error": "Failed to save changes"}), 500

@room.route('/create/learning-steps', methods=['GET', 'POST', 'OPTIONS'])
@csrf.exempt
def new_learning_steps():
    from flask import render_template, request, redirect, url_for, jsonify, current_app, flash
    from src.models import Room, CustomPrompt
    from src.app import db
    from src.app.access_control import get_current_user
    from .types import RoomCreationData
    from .services.room_service import RoomService
    from src.utils.openai_utils import get_available_templates
    import json as _json

    # Handle CORS preflight if any
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    room = None
    is_editing = False
    room_id = request.args.get('room_id', type=int)

    if request.method == 'POST':
        current_app.logger.info("🔥 REAL ROOM CREATION: /room/create/learning-steps POST")
        try:
            user = get_current_user()
            current_app.logger.info(f"🔥 Creating room for user: {user.username}")
            # Create the room from submitted form/json
            creation_data = RoomCreationData.from_request(request)
            current_app.logger.info(f"🔥 Room data: name='{creation_data.name}', goals='{creation_data.goals[:50]}...'")
            result = RoomService.create_room(creation_data, user)
            current_app.logger.info(f"🔥 RoomService result: success={result.success}, room_id={result.room_id}")
            if not result.success or not result.room_id:
                flash(result.error or 'Failed to create room', 'error')
                return redirect(url_for('room.new_learning_steps'))

            new_room_id = result.room_id

            # Persist refined modes if provided
            refined_modes = None
            # Accept either form field or JSON body
            if request.form.get('refined_modes'):
                refined_modes = request.form.get('refined_modes')
            else:
                body = request.get_json(silent=True) or {}
                refined_modes = body.get('refined_modes')
            if isinstance(refined_modes, str):
                try:
                    refined_modes = _json.loads(refined_modes)
                except Exception:
                    refined_modes = None
            if isinstance(refined_modes, list):
                try:
                    # Upsert refined modes to avoid unique constraint violations
                    for m in refined_modes:
                        key = m.get('key')
                        label = m.get('label')
                        prompt = m.get('prompt')
                        if key and label and prompt:
                            existing = CustomPrompt.query.filter_by(room_id=new_room_id, mode_key=key).first()
                            if existing:
                                existing.label = label
                                existing.prompt = prompt
                            else:
                                db.session.add(CustomPrompt(
                                    mode_key=key,
                                    label=label,
                                    prompt=prompt,
                                    room_id=new_room_id,
                                    created_by=getattr(user, 'id', None) or 0
                                ))
                    db.session.commit()
                except Exception as e:
                    current_app.logger.warning(f"[learning-steps.create] Failed to save refined modes for room {new_room_id}: {e}")

            return redirect(url_for('room.room_crud.view_room', room_id=new_room_id))
        except Exception as e:
            current_app.logger.error(f"[learning-steps.create] error: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('room.new_learning_steps'))

    # GET request
    if room_id:
        room = Room.query.get(room_id)
        is_editing = room is not None

    # Prepare existing modes for editing
    existing_modes = []
    saved_rubrics = {}
    if is_editing and room:
        try:
            from src.utils.openai_utils import get_modes_for_room
            modes_obj = get_modes_for_room(room)
            if hasattr(modes_obj, 'items'):
                for k, v in modes_obj.items():
                    existing_modes.append({"key": k, "label": v.label, "prompt": v.prompt})
        except Exception as e:
            current_app.logger.warning(f"[learning-steps.load] Failed to load modes for room {room_id}: {e}")

        # TODO: Load saved rubrics if available (future enhancement)

    return render_template(
        'room/learning_steps.html',
        room=room,
        is_editing=is_editing,
        existing_modes=existing_modes,
        saved_rubrics=saved_rubrics,
        available_templates=get_available_templates(),
    )

# Import all routes to ensure they're registered
from .routes import crud, templates, invitations, api, refine

# Export the main blueprint
__all__ = ['room']
