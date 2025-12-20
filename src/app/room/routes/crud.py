"""
Room CRUD route handlers.
Handles HTTP requests for room operations.
"""

from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from typing import Any, Tuple, List
from src.app import db
from src.models import Room, User, Chat, RoomMember, Message, PinnedItem, PinChatMetadata
from ..services.room_service import RoomService
from ..types import RoomCreationData, RoomUpdateData
from ..utils.room_utils import get_invitation_count
from src.app.access_control import get_current_user, require_login, require_room_access
from src.utils.title_generator import get_display_title
from src.utils.openai_utils import get_modes_for_room, get_available_templates
from src.app import csrf

crud_bp = Blueprint('room_crud', __name__)


@crud_bp.route("/test-route")
def test_route():
    return "CRUD BLUEPRINT WORKING"

@crud_bp.route("/generate-room-proposal-v2", methods=["POST"], endpoint="legacy_generate_room_proposal")
@require_login
@csrf.exempt
def legacy_generate_room_proposal() -> Any:
    """Compatibility endpoint for non-template room creation.
    Returns fields expected by the new UI (title/description/modes/conversation_id/ai_message),
    with safe fallbacks when AI mode generation is not used.
    """
    current_app.logger.info("🔥 ROUTE HIT: /generate-room-proposal-v2")
    
    try:
        from uuid import uuid4
        import json as _json
        from src.utils.openai_utils import generate_room_modes, BASE_TEMPLATES
        current_app.logger.info("🔥 IMPORTS SUCCESSFUL")
        
        # Parse goals from JSON body
        data = request.get_json(silent=True)
        current_app.logger.info(f"🔥 REQUEST DATA: {data}")
        if data is None:
            try:
                data = _json.loads(request.data or b"{}")
            except Exception:
                data = {}
        if not isinstance(data, dict):
            data = {}
        goals_text = (data.get("goals") or "").strip()

        # AI title generation with working fallback
        first_line = (goals_text.splitlines() or [""])[0].strip()
        
        # Try AI first using the exact same pattern as working learning modes
        try:
            from src.utils.openai_utils import call_anthropic_api
            
            prompt = f"Create ONE clear and concise title for this learning room. Respond with ONLY the title, nothing else. Maximum 5 words. Goals: {goals_text}"
            
            # Use exact same call pattern as working learning modes (line 300 in openai_utils.py)
            ai_response, _ = call_anthropic_api(
                [{"role": "user", "content": prompt}],
                max_tokens=50
            )
            
            if ai_response and ai_response.strip():
                suggested_title = ai_response.strip()
                # Auto-truncate if too long (prevent validation failures)
                if len(suggested_title) > 125:
                    suggested_title = suggested_title[:122].strip() + "..."
            else:
                raise Exception("AI returned empty response")
                
        except Exception:
            # Fallback to working string extraction
            if first_line:
                words = first_line.lower().replace("to learn about", "").replace("to study", "").replace("to learn", "").strip().split()
                key_words = [w.capitalize() for w in words[:4] if len(w) > 2]
                suggested_title = " ".join(key_words) if key_words else "New Learning Room"
            else:
                suggested_title = "New Learning Room"
        
        # Generate modes separately (keep existing working logic)
        modes_list = []

        # Use modes from the combined AI call, or fallback if needed
        if not modes_list:
            # Fallback to separate mode generation if combined call failed
            try:
                from src.utils.openai_utils import generate_room_modes, BASE_TEMPLATES
                temp_room = type('obj', (object,), {
                    'id': 0,
                    'name': suggested_title or 'New Room',
                    'goals': goals_text,
                    'description': ''
                })
                modes_obj = generate_room_modes(temp_room)
                if modes_obj:
                    modes_list = [
                        {"key": key, "label": mode.label, "prompt": mode.prompt}
                        for key, mode in modes_obj.items()
                    ]
                else:
                    modes_list = []
            except Exception:
                # Final fallback to base template
                from src.utils.openai_utils import BASE_TEMPLATES
                modes_list = [
                    {"key": key, "label": mode.label, "prompt": mode.prompt}
                    for key, mode in (BASE_TEMPLATES.get("academic_essay", {}).get("modes", {}).items())
                ]

        ai_message = (
            "I drafted a starter proposal based on your goals. You can refine the title, "
            "description, or add learning steps now."
        )

        return jsonify({
            "success": True,
            "room_title": suggested_title,
            "room_description": "",
            "modes": modes_list,
            "conversation_id": str(uuid4()),
            "ai_message": ai_message
        })
    except Exception as e:
        current_app.logger.error(f"[legacy_generate_room_proposal] error: {e}")
        return jsonify({
            "success": True,
            "room_title": "New Learning Room",
            "room_description": "",
            "modes": [],
            "conversation_id": str(uuid4()),
            "ai_message": "Let's refine your room details."
        })



@crud_bp.route("/")
@require_login
def index() -> Any:
    """Redirect to enhanced V2 dashboard."""
    current_app.logger.info("🔄 HOME REDIRECT: Redirecting /room/ to /room/v2/")
    from flask import redirect, url_for
    return redirect(url_for('room_v2.index'))

@crud_bp.route("/create", methods=["GET", "POST"])
@require_login
@csrf.exempt
def create_room() -> Any:
    """Create a new room."""
    try:
        user = get_current_user()
        
        if request.method == "POST":
            # Extract and validate data
            data = RoomCreationData.from_request(request)
            
            # Use service layer
            result = RoomService.create_room(data, user)
            
            if result.success:
                # Redirect directly to learning steps management for newly created room
                return redirect(url_for('room.room_crud.view_room', room_id=result.room_id))
            else:
                flash(f"Error: {result.error}", "error")
                return redirect(url_for("room.room_crud.create_room"))
        
        # GET request - redirect to the unified learning steps editor (creation mode)
        return redirect(url_for('room.new_learning_steps'))
        
    except Exception as e:
        current_app.logger.error(f"Error in create room: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for("room.room_crud.create_room"))

@crud_bp.route("/<int:room_id>/mountain")
@require_room_access
def view_room_mountain(room_id: int) -> Any:
    """Mountain view is now the default - redirect to main room route."""
    current_app.logger.info(f"🔄 REDIRECT: /mountain route redirecting to main room view for {room_id}")
    return redirect(url_for('room.room_crud.view_room', room_id=room_id))

@crud_bp.route("/<int:room_id>")
@require_room_access
def view_room(room_id: int) -> Any:
    """View a specific room (overview) - SAFE MOUNTAIN VIEW WITH FALLBACK."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            flash("Room not found or you don't have access to it.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Get room data (same for both templates)
        chats = RoomService.get_room_chats(room, user)
        members = RoomService.get_room_members(room, user)
        room_data = RoomService.get_room_display_data(room, user)
        
        # Get pin chat metadata for grouping
        pin_chat_ids = set()
        pin_chat_info = {}
        try:
            from src.models import PinChatMetadata
            if chats:
                pin_metas = PinChatMetadata.query.filter(
                    PinChatMetadata.chat_id.in_([c.id for c in chats])
                ).all()
                for meta in pin_metas:
                    pin_chat_ids.add(meta.chat_id)
                    pin_chat_info[meta.chat_id] = {
                        'pin_count': meta.pin_count,
                        'option': meta.option
                    }
        except Exception as e:
            current_app.logger.warning(f"Could not load pin chat metadata: {e}")
        
        # Get learning modes for mountain view
        modes = {}
        try:
            modes_obj = get_modes_for_room(room)
            if hasattr(modes_obj, 'items'):
                for k, v in modes_obj.items():
                    modes[k] = v
        except Exception as e:
            current_app.logger.warning(f"Failed to load modes for room {room_id}: {e}")
            modes = {}

        # Try mountain view with fallback
        try:
            return render_template(
                "room/view_mountain_simple.html",
                room=room,
                room_data=room_data,
                chats=chats,
                members=members,
                modes=modes,
                user=user,
                pin_chat_ids=pin_chat_ids,
                pin_chat_info=pin_chat_info
            )
            
        except Exception as mountain_error:
            # Fallback to standard view
            print(f"🔄 STEP 9: Falling back to standard view for room {room_id}")
            current_app.logger.error(f"🚨 MOUNTAIN VIEW FAILED for room {room_id}: {mountain_error}")
            current_app.logger.info(f"🔄 FALLBACK: Using standard view for room {room_id}")
            
            return render_template(
                "room/view.html",
                room=room,
                room_data=room_data,
                chats=chats,
                members=members,
                user=user,
                invitation_count=get_invitation_count(user),
                get_display_title=get_display_title,
                pin_chat_ids=pin_chat_ids,
                pin_chat_info=pin_chat_info
            )
            
    except Exception as e:
        current_app.logger.error(f"Error viewing room {room_id}: {e}")
        flash("Failed to load room. Please try again.", "error")
        return redirect(url_for('room.room_crud.index'))

@crud_bp.route("/<int:room_id>/edit", methods=["GET", "POST"])
@require_room_access
def edit_room(room_id: int) -> Any:
    """Redirect legacy edit route to the unified learning steps editor."""
    try:
        # Preserve authorization check and then redirect
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        if not room:
            flash("Room not found or you don't have access to it.", "error")
            return redirect(url_for('room.room_crud.index'))

        permissions = RoomService.get_room_permissions(room, user)
        if not permissions.get("can_manage"):
            flash("You don't have permission to edit this room.", "error")
            return redirect(url_for('room.room_crud.view_room', room_id=room_id))

        # Redirect to unified editor with rubrics
        return redirect(url_for('room.new_learning_steps', room_id=room_id))
    except Exception as e:
        current_app.logger.error(f"Error redirecting edit room {room_id}: {e}")
        return redirect(url_for('room.room_crud.view_room', room_id=room_id))

@crud_bp.route("/<int:room_id>/delete", methods=["GET", "POST"])
@require_room_access
def delete_room(room_id: int) -> Any:
    """Delete a room."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            flash("Room not found or you don't have access to it.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Check if user can manage the room
        permissions = RoomService.get_room_permissions(room, user)
        if not permissions["can_manage"]:
            flash("You don't have permission to delete this room.", "error")
            return redirect(url_for('room.room_crud.view_room', room_id=room_id))
        
        if request.method == "POST":
            # Use service layer to delete
            result = RoomService.delete_room(room_id, user)
            
            if result.success:
                flash("Room deleted successfully!", "success")
                return redirect(url_for('room.room_crud.index'))
            else:
                flash(f"Error: {result.error}", "error")
                return redirect(url_for('room.room_crud.view_room', room_id=room_id))
        else:
            # GET request - show confirmation page
            return render_template(
                "room/delete.html",
                room=room,
                user=user,
                invitation_count=get_invitation_count(user)
            )
            
    except Exception as e:
        current_app.logger.error(f"Error deleting room {room_id}: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('room.room_crud.view_room', room_id=room_id))

@crud_bp.route("/search")
@require_login
def search_rooms() -> Any:
    """Search rooms."""
    try:
        user = get_current_user()
        query = request.args.get('q', '').strip()
        
        if not query:
            return redirect(url_for('room.room_crud.index'))
        
        # Use service layer
        rooms = RoomService.search_user_rooms(query, user)
        
        return render_template(
            "room/search.html",
            rooms=rooms,
            query=query,
            user=user,
            invitation_count=get_invitation_count(user)
        )
        
    except Exception as e:
        current_app.logger.error(f"Error searching rooms: {e}")
        flash("Failed to search rooms. Please try again.", "error")
        return redirect(url_for('room.room_crud.index'))

@crud_bp.route("/<int:room_id>/stats")
@require_room_access
def room_stats(room_id: int) -> Any:
    """Get room statistics."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get statistics
        stats = RoomService.get_room_statistics(room)
        activity = RoomService.get_room_activity(room)
        
        return jsonify({
            "success": True,
            "stats": stats,
            "activity": activity
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting room stats {room_id}: {e}")
        return jsonify({"error": "Failed to get room statistics"}), 500

@crud_bp.route("/<int:room_id>/activity")
@require_room_access
def room_activity(room_id: int) -> Any:
    """Get room activity."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get activity data
        days = request.args.get('days', 7, type=int)
        activity = RoomService.get_room_activity(room, days)
        
        return jsonify({
            "success": True,
            "activity": activity
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting room activity {room_id}: {e}")
        return jsonify({"error": "Failed to get room activity"}), 500

@crud_bp.route("/<int:room_id>/members")
@require_room_access
def room_members(room_id: int) -> Any:
    """Get room members."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get members
        members = RoomService.get_room_members(room, user)
        
        return jsonify({
            "success": True,
            "members": [
                {
                    "id": member.id,
                    "user_id": member.id,
                    "display_name": member.display_name,
                    "email": member.email,
                    "joined_at": None,  # User objects don't have joined_at
                    "accepted_at": None,  # User objects don't have accepted_at
                    "can_create_chats": False,  # These would need to be fetched separately
                    "can_invite_members": False
                }
                for member in members
            ]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting room members {room_id}: {e}")
        return jsonify({"error": "Failed to get room members"}), 500

@crud_bp.route("/<int:room_id>/chats")
@require_room_access
def room_chats(room_id: int) -> Any:
    """Get room chats."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get chats
        limit = request.args.get('limit', 50, type=int)
        chats = RoomService.get_room_chats(room, user, limit)
        
        return jsonify({
            "success": True,
            "chats": [
                {
                    "id": chat.id,
                    "title": chat.title,
                    "created_at": chat.created_at.isoformat() if chat.created_at else None,
                    "created_by": chat.created_by,
                    "is_active": chat.is_active
                }
                for chat in chats
            ]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting room chats {room_id}: {e}")
        return jsonify({"error": "Failed to get room chats"}), 500

@crud_bp.route("/<int:room_id>/chat/create", methods=["GET", "POST"])
@require_login
@csrf.exempt
def create_chat(room_id: int) -> Any:
    """Create a new chat within a room."""
    # ABSOLUTE FIRST LINE DEBUG - before ANY imports or logic
    print(f"\n\n=== CRUD ROUTE DEFINITELY HIT: room_id={room_id} ===")
    
    # CRITICAL DEBUG: Log that this route is being hit
    try:
        from flask import current_app
        current_app.logger.error(f"🚨 CRUD ROUTE HIT: create_chat room_id={room_id}, method={request.method}")
    except Exception as e:
        print(f"CRUD ROUTE HIT: create_chat room_id={room_id}, logger error: {e}")
    
    from src.models import Chat, Message
    from src.app.access_control import can_create_chats_in_room
    from src.utils.openai_utils import get_modes_for_room
    from src.app.google_docs import validate_google_docs_url, get_document_content
    from src.utils.openai_utils import get_ai_response, generate_chat_introduction
    from ..utils.room_utils import infer_template_type_from_room
    
    room = Room.query.get_or_404(room_id)
    user = get_current_user()

    if not can_create_chats_in_room(user, room):
        flash("You don't have permission to create chats in this room.")
        return redirect(url_for("room.room_crud.view_room", room_id=room.id))

    # Enforce per-room chat cap
    try:
        from flask import current_app as _ca
        max_chats = int((_ca.config.get('ROOM_MAX_CHATS') or 25))
    except Exception:
        max_chats = 25
    from src.models import Chat as _Chat
    existing_count = _Chat.query.filter_by(room_id=room.id).count()
    if existing_count >= max_chats:
        flash(f"Chat limit reached for this room (max {max_chats}). Please create a new room to continue.", "error")
        return redirect(url_for("room.room_crud.view_room", room_id=room.id))

    if request.method == "POST":
        is_json = request.is_json or request.headers.get('Content-Type', '').startswith('application/json')
        payload = request.get_json(silent=True) if is_json else None

        if payload is not None:
            title = (payload.get("title") or "").strip()
            mode = payload.get("mode", "explore")
            google_doc_url = (payload.get("google_doc_url") or "").strip()
        else:
            title = (request.form.get("title") or "").strip()
            mode = request.form.get("mode", "explore")
            google_doc_url = request.form.get("google_doc_url", "").strip()

        if not title:
            title = f"New {mode.title()} Chat"
            if not title.strip():
                if payload is not None:
                    return jsonify({"success": False, "error": "Chat title is required."}), 400
                flash("Chat title is required.")
                return redirect(url_for("room.room_crud.create_chat", room_id=room.id))

        if payload is not None and payload.get("source") == "next_step":
            existing_chat = (
                Chat.query.filter_by(room_id=room.id, mode=mode)
                .order_by(Chat.created_at.desc())
                .first()
            )
            if existing_chat:
                return jsonify({"success": True, "chat_id": existing_chat.id, "existing": True})

        # Validate Google Doc URL if provided
        if google_doc_url:
            is_valid, doc_id_or_error = validate_google_docs_url(google_doc_url)
            if not is_valid:
                flash(f"Google Doc URL error: {doc_id_or_error}")
                return redirect(url_for("room.room_crud.create_chat", room_id=room.id))

        chat_obj = Chat(title=title, room_id=room.id, created_by=user.id, mode=mode)
        db.session.add(chat_obj)
        db.session.commit()

        print(f"\n=== STEP 1: About to generate notes for room {room_id} ===")
        
        # FIRST: Generate notes for any previous completed chats in this room
        # This must happen BEFORE the AI introduction so context is available
        try:
            from src.utils.learning.triggers import trigger_context_refresh_for_room
            print(f"=== STEP 2: Imported trigger_context_refresh_for_room ===")
            trigger_context_refresh_for_room(room_id)
            print(f"=== STEP 3: Completed trigger_context_refresh_for_room ===")
            current_app.logger.info(f"✅ Generated/updated notes for existing chats in room {room_id}")
        except Exception as e:
            print(f"=== ERROR in note generation: {e} ===")
            current_app.logger.error(f"Error generating context for new chat: {e}")

        # THEN: Generate and add AI introduction message with learning context
        try:
            # Infer template type from room characteristics
            template_type = infer_template_type_from_room(chat_obj.room)
            learning_step = "step1"  # Default to step 1 for new chats
            
            current_app.logger.info(f"🔍 Chat introduction params: template_type={template_type}, learning_step={learning_step}, room_id={chat_obj.room.id}, chat_id={chat_obj.id}")
            current_app.logger.info(f"🔍 Room goals: {chat_obj.room.goals[:100]}...")
            
            introduction = generate_chat_introduction(
                chat_obj.room.goals, 
                template_type=template_type, 
                learning_step=learning_step, 
                room_id=chat_obj.room.id,
                chat_id=chat_obj.id  # Pass chat_id for context loading
            )
            
            current_app.logger.info(f"✅ Introduction generated successfully, length: {len(introduction)} chars")

            # Add the AI introduction as the first message
            intro_message = Message(
                chat_id=chat_obj.id,
                role="assistant",
                content=introduction,
                is_truncated=False,
            )
            db.session.add(intro_message)
            db.session.commit()
        except Exception as e:
            # If introduction generation fails, add a simple fallback
            current_app.logger.error(f"Failed to generate chat introduction: {e}")
            fallback_intro = Message(
                chat_id=chat_obj.id,
                role="assistant",
                content="Hello! I'm here to help you with your learning. What would you like to work on today?",
                is_truncated=False,
            )
            db.session.add(fallback_intro)
            db.session.commit()

        # If Google Doc URL provided, import the content
        if google_doc_url:
            doc_id = doc_id_or_error  # This is the doc_id from validation
            content, error = get_document_content(doc_id)

            if error:
                flash(f"Could not access Google Doc: {error}")
                return redirect(url_for("chat.view_chat", chat_id=chat_obj.id))

            if content:
                # Add the Google Doc content as the first user message
                doc_message = Message(
                    chat_id=chat_obj.id,
                    user_id=user.id,
                    role="user",
                    content=f"[Google Doc Content]\n\n{content}",
                )
                db.session.add(doc_message)

                # Get AI response to the imported content
                ai_content = get_ai_response(chat_obj)
                ai_msg = Message(
                    chat_id=chat_obj.id, role="assistant", content=ai_content
                )
                db.session.add(ai_msg)
                db.session.commit()

                flash("Google Doc content imported successfully!")

        if payload is not None:
            return jsonify({"success": True, "chat_id": chat_obj.id})

        return redirect(url_for("chat.view_chat", chat_id=chat_obj.id))

    # Get dynamic modes for this room
    modes = get_modes_for_room(room)

    return render_template(
        "room/create_chat.html",
        room=room,
        modes=modes,
        user=user,
        invitation_count=get_invitation_count(user)
    )


# =============================================================================
# PIN-SEEDED CHAT CREATION (Phase D)
# =============================================================================

# Valid pin chat options
PIN_CHAT_OPTIONS = {
    "explore", "study", "research_essay", "presentation", 
    "learning_exercise", "startup", "artistic", "social_impact", "analyze"
}

# Minimum pins required (configurable)
MIN_PINS_REQUIRED = 3


@crud_bp.route("/<int:room_id>/chats/from-pins", methods=["POST"])
@require_login
@csrf.exempt
def create_chat_from_pins(room_id: int) -> Any:
    """
    Create a new chat seeded with shared pins.
    
    POST body (JSON):
    {
        "pin_ids": [1, 2, 3, ...],  // Must be ≥3 shared pins from this room
        "option": "explore",         // One of PIN_CHAT_OPTIONS
        "include_summary": false     // Optional, for future use
    }
    
    Returns:
    - 201: {"success": true, "chat_id": <id>}
    - 400: {"success": false, "error": "<message>"}
    - 403: {"success": false, "error": "Access denied"}
    """
    from src.app.access_control import can_create_chats_in_room
    
    user = get_current_user()
    room = Room.query.get_or_404(room_id)
    
    # Check room access and permission to create chats
    if not can_create_chats_in_room(user, room):
        return jsonify({
            "success": False, 
            "error": "You don't have permission to create chats in this room."
        }), 403
    
    # Enforce per-room chat cap
    try:
        max_chats = int(current_app.config.get('ROOM_MAX_CHATS') or 25)
    except Exception:
        max_chats = 25
    
    existing_count = Chat.query.filter_by(room_id=room.id).count()
    if existing_count >= max_chats:
        return jsonify({
            "success": False,
            "error": f"Chat limit reached for this room (max {max_chats})."
        }), 400
    
    # Parse request body
    data = request.get_json(silent=True) or {}
    pin_ids = data.get("pin_ids", [])
    option = (data.get("option") or "").strip().lower()
    
    # Validate option
    if option not in PIN_CHAT_OPTIONS:
        return jsonify({
            "success": False,
            "error": f"Invalid option. Must be one of: {', '.join(sorted(PIN_CHAT_OPTIONS))}"
        }), 400
    
    # Validate pin_ids is a list
    if not isinstance(pin_ids, list):
        return jsonify({
            "success": False,
            "error": "pin_ids must be a list of integers."
        }), 400
    
    # Validate minimum pins
    if len(pin_ids) < MIN_PINS_REQUIRED:
        return jsonify({
            "success": False,
            "error": f"At least {MIN_PINS_REQUIRED} pins are required."
        }), 400
    
    # Fetch and validate pins
    pins = PinnedItem.query.filter(PinnedItem.id.in_(pin_ids)).all()
    
    # Check all requested pins were found
    if len(pins) != len(pin_ids):
        found_ids = {p.id for p in pins}
        missing_ids = set(pin_ids) - found_ids
        return jsonify({
            "success": False,
            "error": f"Pins not found: {list(missing_ids)}"
        }), 400
    
    # Validate all pins belong to this room and are shared
    for pin in pins:
        if pin.room_id != room_id:
            return jsonify({
                "success": False,
                "error": f"Pin {pin.id} does not belong to this room."
            }), 400
        if not pin.is_shared:
            return jsonify({
                "success": False,
                "error": f"Pin {pin.id} is not shared. Only shared pins can be used."
            }), 400
    
    # Generate title
    option_labels = {
        "explore": "Explore & Brainstorm",
        "study": "Study & Master",
        "research_essay": "Research Essay",
        "presentation": "Presentation",
        "learning_exercise": "Learning Exercise",
        "startup": "Startup Plan",
        "artistic": "Artistic Creation",
        "social_impact": "Social Impact",
        "analyze": "Analysis"
    }
    option_label = option_labels.get(option, option.title())
    title = f"Pinned Insights — {option_label} — {room.name}"
    
    # Truncate title if too long
    if len(title) > 120:
        title = title[:117] + "..."
    
    try:
        # Create the chat
        chat_obj = Chat(
            title=title,
            room_id=room.id,
            created_by=user.id,
            mode=f"pins_{option}"  # Use pins_ prefix to distinguish from regular modes
        )
        db.session.add(chat_obj)
        db.session.flush()  # Get chat ID
        
        # Create pin metadata with snapshot
        pin_snapshot = PinChatMetadata.create_snapshot(pins)
        metadata = PinChatMetadata(
            chat_id=chat_obj.id,
            option=option,
            pin_snapshot=pin_snapshot
        )
        db.session.add(metadata)
        
        # Generate AI introduction using pin_synthesis module
        try:
            from src.utils.pin_synthesis import generate_pin_chat_introduction
            
            # Convert PinnedItem objects to dicts for the function
            pins_data = [
                {
                    "id": p.id,
                    "content": p.content,
                    "role": p.role,
                    "author": p.user.username if p.user else "Unknown"
                }
                for p in pins
            ]
            
            intro_content = generate_pin_chat_introduction(
                pins=pins_data,
                option=option,
                room_goals=room.goals,
                room_name=room.name
            )
        except Exception as intro_error:
            current_app.logger.warning(f"AI intro failed, using fallback: {intro_error}")
            intro_content = _generate_pin_chat_intro(pins, option, option_label, room)
        
        intro_message = Message(
            chat_id=chat_obj.id,
            role="assistant",
            content=intro_content,
            is_truncated=False
        )
        db.session.add(intro_message)
        
        db.session.commit()
        
        current_app.logger.info(
            f"✅ Pin chat created: chat_id={chat_obj.id}, option={option}, pins={len(pins)}, user={user.id}"
        )
        
        return jsonify({
            "success": True,
            "chat_id": chat_obj.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Failed to create pin chat: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to create chat. Please try again."
        }), 500


def _generate_pin_chat_intro(pins: list, option: str, option_label: str, room) -> str:
    """
    Generate introduction message for a pin-seeded chat.
    
    This is a template-based fallback. Phase 3 will add full AI-generated intros
    via the pin_synthesis module.
    """
    pin_count = len(pins)
    
    # Build pin summary (first 3 pins, truncated)
    pin_summaries = []
    for i, pin in enumerate(pins[:3]):
        content_preview = pin.content[:100] + "..." if len(pin.content) > 100 else pin.content
        pin_summaries.append(f"• {content_preview}")
    
    if pin_count > 3:
        pin_summaries.append(f"• ...and {pin_count - 3} more pins")
    
    pins_text = "\n".join(pin_summaries)
    
    # Option-specific intro templates
    intro_templates = {
        "explore": f"""Welcome! Let's explore and brainstorm together using these **{pin_count} pinned insights** from your room.

📌 **Your Pinned Context:**
{pins_text}

I'm here to help you discover connections, generate new ideas, and explore possibilities based on these insights.

**How would you like to begin?**
• Tell me what connections or patterns you notice
• Ask me to find themes across these pins
• Share a question or idea you'd like to explore""",
        
        "study": f"""Welcome! I'll help you study and master the content in these **{pin_count} pinned insights**.

📌 **Study Material:**
{pins_text}

I'll guide you through understanding these concepts deeply, testing your knowledge, and building mastery.

**Ready to begin?**
• Ask me to explain any concept in depth
• Request a quiz or practice questions
• Tell me what you'd like to focus on first""",
        
        "research_essay": f"""Welcome! Let's work on drafting a research essay using these **{pin_count} pinned insights** as source material.

📌 **Source Material:**
{pins_text}

I'll help you synthesize these insights into a well-structured essay with clear arguments and evidence.

**Where would you like to start?**
• Identify the main thesis or argument
• Create an outline structure
• Summarize the key points from each pin""",
        
        "analyze": f"""Welcome! Let's analyze and synthesize these **{pin_count} pinned insights** together.

📌 **Content to Analyze:**
{pins_text}

I'll help you identify patterns, draw conclusions, and create actionable insights.

**What would you like to explore?**
• Find common themes and patterns
• Identify gaps or contradictions
• Create a summary of key takeaways"""
    }
    
    # Use specific template or generic fallback
    if option in intro_templates:
        return intro_templates[option]
    
    # Generic fallback for other options
    return f"""Welcome! I'm here to help you with **{option_label}** using these **{pin_count} pinned insights** from your room.

📌 **Your Pinned Context:**
{pins_text}

🎯 **Room Goals:** {room.goals[:200] + '...' if room.goals and len(room.goals) > 200 else room.goals or 'Not specified'}

Let me know how you'd like to proceed, and I'll help you make the most of these insights!"""


def _generate_title_and_modes(goals_text: str) -> Tuple[str, List]:
    """
    Generate both room title and learning modes in single AI call.
    Uses simplified prompt approach as requested.
    """
    current_app.logger.info(f"🤖 AI Title Generation: Starting with goals: '{goals_text}'")
    
    try:
        from src.utils.openai_utils import call_anthropic_api
        
        prompt = f"""Based on these learning goals: "{goals_text}"

Please provide:
1. A clear and concise title for this learning room. It should be no longer than five words.
2. 8-10 learning steps that follow a logical progression for achieving these goals.

Return as JSON with this exact format:
{{
    "title": "Short Room Title",
    "modes": [
        {{
            "key": "step1",
            "label": "1. Step Name", 
            "prompt": "Detailed prompt for this step"
        }}
    ]
}}"""

        current_app.logger.info(f"🤖 AI Title: Calling Anthropic API...")
        
        response = call_anthropic_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3
        )
        
        current_app.logger.info(f"🤖 AI Title: Response received: {len(response) if response else 0} chars")
        
        if response and response.strip():
            import json
            try:
                current_app.logger.info(f"🤖 AI Title: Parsing JSON response...")
                data = json.loads(response.strip())
                title = data.get("title", "").strip()
                modes = data.get("modes", [])
                
                current_app.logger.info(f"✅ AI SUCCESS: Generated title: '{title}' and {len(modes)} modes")
                return title, modes
                
            except json.JSONDecodeError as e:
                current_app.logger.error(f"❌ AI JSON Parse Error: {e}")
                current_app.logger.error(f"❌ Raw AI Response: {response[:500]}")
                
    except Exception as e:
        current_app.logger.error(f"❌ AI Call Exception: {e}")
        import traceback
        current_app.logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    # Fallback
    current_app.logger.warning("⚠️ AI FAILED: Using fallback title 'New Learning Room'")
    return "", []
