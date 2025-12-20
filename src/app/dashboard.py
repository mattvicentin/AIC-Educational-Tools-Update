from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.app import db
from typing import Any
from src.models import (
    PromptRecord,
    User,
    Chat,
    Room,
    RoomMember,
    Message,
    Comment,
    CustomPrompt,
)
from .access_control import get_current_user, require_login
from sqlalchemy import func
from collections import defaultdict
from src.utils.openai_utils import BASE_MODES, get_modes_for_room
from datetime import datetime

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/")
@require_login
def index() -> Any:
    """Instructor/Team Leader Dashboard - Room Overview."""
    user = get_current_user()

    # Get rooms owned by the user
    owned_rooms = (
        Room.query.filter_by(owner_id=user.id, is_active=True)
        .order_by(Room.created_at.desc())
        .all()
    )

    # Get rooms where user is a member (for team leaders who might not own all rooms)
    member_rooms = (
        Room.query.join(RoomMember)
        .filter(RoomMember.user_id == user.id, Room.is_active == True)
        .order_by(Room.created_at.desc())
        .all()
    )

    # Combine and remove duplicates (rooms should never be None from queries)
    all_rooms = list({room.id: room for room in owned_rooms + member_rooms}.values())

    # Get room statistics
    room_stats = {}
    for room in all_rooms:
        # Count members (including owner)
        member_count = RoomMember.query.filter_by(room_id=room.id).count() + 1

        # Count chats
        chat_count = Chat.query.filter_by(room_id=room.id).count()

        # Count total messages
        message_count = (
            db.session.query(func.count(Message.id))
            .join(Chat)
            .filter(Chat.room_id == room.id)
            .scalar()
        )

        # Get last activity (latest message timestamp)
        last_activity = (
            db.session.query(func.max(Message.timestamp))
            .join(Chat)
            .filter(Chat.room_id == room.id)
            .scalar()
        )

        # Count prompts in this room
        prompt_count = PromptRecord.query.filter_by(room_id=room.id).count()

        # Count comments in this room
        comment_count = (
            db.session.query(func.count(Comment.id))
            .join(Chat)
            .filter(Chat.room_id == room.id)
            .scalar()
        )

        room_stats[room.id] = {
            "member_count": member_count,
            "chat_count": chat_count,
            "message_count": message_count or 0,
            "last_activity": last_activity,
            "prompt_count": prompt_count,
            "comment_count": comment_count or 0,
        }

    return render_template(
        "dashboard/index.html", user=user, rooms=all_rooms, room_stats=room_stats
    )


@dashboard.route("/system-instructions")
@require_login
def system_instructions() -> Any:
    """Manage system instructions for AI modes."""
    user = get_current_user()

    # Get all rooms the user has access to
    user_room_ids = []

    # Rooms owned by user
    owned_rooms = Room.query.filter_by(owner_id=user.id).all()
    user_room_ids.extend([room.id for room in owned_rooms if room is not None])

    # Rooms where user is a member
    member_rooms = (
        Room.query.join(RoomMember).filter(RoomMember.user_id == user.id).all()
    )
    user_room_ids.extend([room.id for room in member_rooms if room is not None])

    # Get all rooms for mode selection
    rooms = Room.query.filter(Room.id.in_(user_room_ids)).all()

    # Get base modes
    base_modes = BASE_MODES

    # Get room-specific modes if a room is selected
    selected_room_id = request.args.get("room", "")
    room_specific_modes = {}
    selected_room = None

    if selected_room_id:
        selected_room = Room.query.get(selected_room_id)
        if selected_room and selected_room.id in user_room_ids:
            # Use the same function that chat creation uses for consistency
            room_specific_modes = get_modes_for_room(selected_room)

    # Get custom prompts for the selected room (or global if no room selected)
    custom_prompts = {}
    if selected_room_id:
        custom_prompts = CustomPrompt.query.filter_by(
            room_id=selected_room_id, is_active=True
        ).all()
    else:
        # Get global custom prompts (room_id is null)
        custom_prompts = CustomPrompt.query.filter_by(
            room_id=None, is_active=True
        ).all()

    # Convert custom prompts to a dictionary for easy lookup
    custom_prompts_dict = {cp.mode_key: cp for cp in custom_prompts}

    return render_template(
        "dashboard/system_instructions.html",
        user=user,
        rooms=rooms,
        room_specific_modes=room_specific_modes,
        selected_room_id=selected_room_id,
        selected_room=selected_room,
        custom_prompts=custom_prompts_dict,
    )


@dashboard.route("/system-instructions/edit", methods=["POST"])
@require_login
def edit_system_instructions() -> Any:
    """Edit system instructions for a specific mode."""
    user = get_current_user()

    mode_key = request.form.get("mode_key")
    new_prompt = request.form.get("prompt", "").strip()
    label = request.form.get("label", "").strip()
    room_id = request.form.get("room_id", "")

    if not mode_key or not new_prompt or not label:
        flash("Please provide mode key, label, and prompt content.")
        return redirect(url_for("dashboard.system_instructions"))

    # Convert room_id to integer or None
    room_id = int(room_id) if room_id else None

    # Check if user has access to this room
    if room_id:
        room = Room.query.get(room_id)
        if not room or (
            room.owner_id != user.id
            and not RoomMember.query.filter_by(room_id=room_id, user_id=user.id).first()
        ):
            flash("You don't have permission to edit prompts for this room.")
            return redirect(url_for("dashboard.system_instructions"))

    # Check if a custom prompt already exists for this mode and room
    existing_prompt = CustomPrompt.query.filter_by(
        mode_key=mode_key, room_id=room_id
    ).first()

    if existing_prompt:
        # Update existing prompt
        existing_prompt.prompt = new_prompt
        existing_prompt.label = label
        existing_prompt.updated_at = datetime.utcnow()
        flash(f"System instructions for '{mode_key}' updated successfully!")
    else:
        # Create new custom prompt
        custom_prompt = CustomPrompt(
            mode_key=mode_key,
            label=label,
            prompt=new_prompt,
            room_id=room_id,
            created_by=user.id,
        )
        db.session.add(custom_prompt)
        flash(f"System instructions for '{mode_key}' created successfully!")

    db.session.commit()

    # Redirect back to the same room selection
    if room_id:
        return redirect(url_for("dashboard.system_instructions", room=room_id))
    else:
        return redirect(url_for("dashboard.system_instructions"))


@dashboard.route("/system-instructions/regenerate", methods=["POST"])
@require_login
def regenerate_room_modes() -> Any:
    """Regenerate contextual modes for a room based on its goals."""
    user = get_current_user()

    room_id = request.form.get("room_id")
    if not room_id:
        flash("Room ID is required.")
        return redirect(url_for("dashboard.system_instructions"))

    room = Room.query.get(room_id)
    if not room:
        flash("Room not found.")
        return redirect(url_for("dashboard.system_instructions"))

    # Check if user has access to this room
    if (
        room.owner_id != user.id
        and not RoomMember.query.filter_by(room_id=room_id, user_id=user.id).first()
    ):
        flash("You don't have permission to edit prompts for this room.")
        return redirect(url_for("dashboard.system_instructions"))

    if not room.goals:
        flash("Room must have learning goals to generate contextual modes.")
        return redirect(url_for("dashboard.system_instructions", room=room_id))

    try:
        from src.utils.openai_utils import generate_room_modes

        # Delete existing custom prompts for this room
        CustomPrompt.query.filter_by(room_id=room_id).delete()

        # Generate new contextual modes
        contextual_modes = generate_room_modes(room)

        # Save generated modes as custom prompts
        for mode_key, mode_info in contextual_modes.items():
            custom_prompt = CustomPrompt(
                mode_key=mode_key,
                label=mode_info.label,
                prompt=mode_info.prompt,
                room_id=room_id,
                created_by=user.id,
            )
            db.session.add(custom_prompt)

        db.session.commit()
        flash(f"Generated {len(contextual_modes)} contextual modes for '{room.name}'!")

    except Exception as e:
        db.session.rollback()
        flash(f"Error generating modes: {str(e)}")

    return redirect(url_for("dashboard.system_instructions", room=room_id))


@dashboard.route("/room/<int:room_id>")
@require_login
def room_detail(room_id: int) -> Any:
    """LEGACY ROUTE - Redirect to new room view."""
    current_app.logger.error(f"🚨🚨🚨 LEGACY ROUTE HIT: Dashboard room route intercepting room {room_id} - REDIRECTING TO NEW ROUTE 🚨🚨🚨")
    return redirect(url_for('room.room_crud.view_room', room_id=room_id))

    # Check if user has access to this room
    if (
        room.owner_id != user.id
        and not RoomMember.query.filter_by(room_id=room.id, user_id=user.id).first()
    ):
        flash("You don't have access to this room.")
        return redirect(url_for("dashboard.index"))

    # Get room members
    members = RoomMember.query.filter_by(room_id=room.id).all()
    member_users = [User.query.get(member.user_id) for member in members]

    # Add room owner to member list
    owner = User.query.get(room.owner_id)
    if owner not in member_users:
        member_users.append(owner)

    # Get chats in this room
    chats = Chat.query.filter_by(room_id=room.id).order_by(Chat.created_at.desc()).all()

    # Get prompt analytics for this room
    prompts = (
        PromptRecord.query.filter_by(room_id=room.id)
        .order_by(PromptRecord.timestamp.desc())
        .all()
    )

    # Mode usage statistics for this room
    mode_stats = (
        db.session.query(PromptRecord.mode, func.count(PromptRecord.id).label("count"))
        .filter(PromptRecord.room_id == room.id)
        .group_by(PromptRecord.mode)
        .all()
    )

    mode_counts = {mode: count for mode, count in mode_stats}

    # User activity in this room
    user_activity = (
        db.session.query(
            PromptRecord.user_id,
            User.display_name,
            func.count(PromptRecord.id).label("prompt_count"),
        )
        .join(User)
        .filter(PromptRecord.room_id == room.id)
        .group_by(PromptRecord.user_id, User.display_name)
        .all()
    )

    # Comment statistics for this room
    comment_count = (
        db.session.query(func.count(Comment.id))
        .join(Chat)
        .filter(Chat.room_id == room.id)
        .scalar()
        or 0
    )

    # Comments by user in this room
    user_comments = (
        db.session.query(
            Comment.user_id,
            User.display_name,
            func.count(Comment.id).label("comment_count"),
        )
        .join(User)
        .join(Chat)
        .filter(Chat.room_id == room.id)
        .group_by(Comment.user_id, User.display_name)
        .all()
    )

    return render_template(
        "dashboard/room_detail.html",
        user=user,
        room=room,
        members=member_users,
        chats=chats,
        prompts=prompts,
        mode_counts=mode_counts,
        user_activity=user_activity,
        comment_count=comment_count,
        user_comments=user_comments,
    )


@dashboard.route("/prompts")
@require_login
def view_prompts() -> Any:
    """View all prompts with room-based filtering."""
    user = get_current_user()

    # Get filter parameters
    room_filter = request.args.get("room", "")
    mode_filter = request.args.get("mode", "")
    user_filter = request.args.get("user", "")

    # Build query - only show prompts from rooms the user has access to
    user_room_ids = []

    # Rooms owned by user
    owned_rooms = Room.query.filter_by(owner_id=user.id).all()
    user_room_ids.extend([room.id for room in owned_rooms if room is not None])

    # Rooms where user is a member
    member_rooms = (
        Room.query.join(RoomMember).filter(RoomMember.user_id == user.id).all()
    )
    user_room_ids.extend([room.id for room in member_rooms if room is not None])

    query = (
        PromptRecord.query.join(User)
        .join(Chat)
        .filter(PromptRecord.room_id.in_(user_room_ids))
    )

    if room_filter:
        query = query.filter(PromptRecord.room_id == room_filter)

    if mode_filter:
        query = query.filter(PromptRecord.mode == mode_filter)

    if user_filter:
        query = query.filter(User.username == user_filter)

    # Get unique rooms, modes, and users for filter dropdowns
    rooms = Room.query.filter(Room.id.in_(user_room_ids)).all()

    # Get modes - if a room is selected, only show modes for that room
    if room_filter:
        modes = (
            db.session.query(PromptRecord.mode)
            .filter(PromptRecord.room_id == room_filter)
            .distinct()
            .all()
        )
    else:
        modes = (
            db.session.query(PromptRecord.mode)
            .filter(PromptRecord.room_id.in_(user_room_ids))
            .distinct()
            .all()
        )

    users = (
        db.session.query(User.username, User.display_name)
        .join(PromptRecord)
        .filter(PromptRecord.room_id.in_(user_room_ids))
        .distinct()
        .all()
    )

    # Get filtered results
    prompts = query.order_by(PromptRecord.timestamp.desc()).all()

    return render_template(
        "dashboard/prompts.html",
        user=user,
        prompts=prompts,
        rooms=rooms,
        modes=modes,
        users=users,
        current_room=room_filter,
        current_mode=mode_filter,
        current_user=user_filter,
    )
