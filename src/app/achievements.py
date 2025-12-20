from src.app import db
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from src.models import UserModeUsage, Achievement, Message, Comment, Chat, RoomMember
from datetime import datetime
from typing import List


def track_mode_usage(user_id: int, room_id: int, mode: str) -> None:
    """Track that a user has used a specific mode in a room."""
    try:
        # Check if this user has already used this mode in this room
        existing_usage = UserModeUsage.query.filter_by(
            user_id=user_id, room_id=room_id, mode=mode
        ).first()

        if existing_usage:
            # Update existing record
            existing_usage.last_used_at = datetime.utcnow()
            existing_usage.usage_count += 1
        else:
            # Create new record
            new_usage = UserModeUsage(user_id=user_id, room_id=room_id, mode=mode)
            db.session.add(new_usage)

        db.session.commit()

        # Check for achievements after tracking
        check_achievements(user_id, room_id)

    except Exception as e:
        print(f"Error tracking mode usage: {e}")
        db.session.rollback()


def check_achievements(user_id: int, room_id: int) -> None:
    """Check if user has earned any achievements in the room."""
    try:
        # Check "First Steps" achievement
        check_first_steps(user_id, room_id)

        # Check "Explorer" achievement
        check_explorer(user_id, room_id)

        # Check "AI Whisperer" achievement
        check_ai_whisperer(user_id, room_id)

        # Check "Collaborator" achievement
        check_collaborator(user_id, room_id)

        # Check "Learning Master" achievement
        check_learning_master(user_id, room_id)

    except Exception as e:
        print(f"Error checking achievements: {e}")


def check_first_steps(user_id: int, room_id: int) -> None:
    """Check if user has sent their first message in the room."""
    # Check if user has already earned this achievement
    existing = Achievement.query.filter_by(
        user_id=user_id, room_id=room_id, achievement_type="first_steps"
    ).first()

    if existing:
        return

    # Check if user has sent any messages in this room
    message_count = (
        Message.query.join(Chat)
        .filter(Message.user_id == user_id, Chat.room_id == room_id)
        .count()
    )

    if message_count >= 1:
        achievement = Achievement(
            user_id=user_id, room_id=room_id, achievement_type="first_steps"
        )
        db.session.add(achievement)
        db.session.commit()
        print(f"🎉 User {user_id} earned 'First Steps' in room {room_id}")
        flash(
            "🎯 Achievement Unlocked: First Steps! You've sent your first message in this room.",
            "success",
        )


def check_explorer(user_id: int, room_id: int) -> None:
    """Check if user has used 24% or more of the available modes in the room."""
    # Check if user has already earned this achievement
    existing = Achievement.query.filter_by(
        user_id=user_id, room_id=room_id, achievement_type="explorer"
    ).first()

    if existing:
        return

    # Get total number of available modes for this room
    from src.utils.openai_utils import get_modes_for_room
    from src.models import Room

    room = Room.query.get(room_id)
    if not room:
        return

    available_modes = get_modes_for_room(room)
    total_modes = len(available_modes)

    if total_modes == 0:
        return

    # Count unique modes used by this user in this room
    unique_modes = UserModeUsage.query.filter_by(
        user_id=user_id, room_id=room_id
    ).count()

    # Calculate percentage (24% = 0.24)
    percentage_used = unique_modes / total_modes
    required_percentage = 0.24

    if percentage_used >= required_percentage:
        achievement = Achievement(
            user_id=user_id, room_id=room_id, achievement_type="explorer"
        )
        db.session.add(achievement)
        db.session.commit()
        print(f"🎉 User {user_id} earned 'Explorer' in room {room_id}")
        flash(
            f"🗺️ Achievement Unlocked: Explorer! You've used {unique_modes}/{total_modes} modes ({percentage_used:.1%}) in this room.",
            "success",
        )


def check_ai_whisperer(user_id: int, room_id: int) -> None:
    """Check if user has had 10 successful AI conversations in the room."""
    # Check if user has already earned this achievement
    existing = Achievement.query.filter_by(
        user_id=user_id, room_id=room_id, achievement_type="ai_whisperer"
    ).first()

    if existing:
        return

    # Count AI conversations (user messages followed by assistant messages)
    # This is a simplified check - we count user messages in the room
    user_messages = (
        Message.query.join(Chat)
        .filter(
            Message.user_id == user_id, Chat.room_id == room_id, Message.role == "user"
        )
        .count()
    )

    if user_messages >= 10:
        achievement = Achievement(
            user_id=user_id, room_id=room_id, achievement_type="ai_whisperer"
        )
        db.session.add(achievement)
        db.session.commit()
        print(f"🎉 User {user_id} earned 'AI Whisperer' in room {room_id}")
        flash(
            "🤖 Achievement Unlocked: AI Whisperer! You've had 10 successful AI conversations in this room.",
            "success",
        )


def check_collaborator(user_id: int, room_id: int) -> None:
    """Check if user has helped 5 students OR more than 50% of users in the room."""
    # Check if user has already earned this achievement
    existing = Achievement.query.filter_by(
        user_id=user_id, room_id=room_id, achievement_type="collaborator"
    ).first()

    if existing:
        return

    # Count comments given by this user in this room
    comment_count = (
        Comment.query.join(Chat)
        .filter(Comment.user_id == user_id, Chat.room_id == room_id)
        .count()
    )

    # Get total number of users in the room
    total_users = (
        RoomMember.query.filter_by(room_id=room_id).count() + 1
    )  # +1 for room owner

    # Calculate required comments based on percentage (50% = 0.5)
    required_by_percentage = max(1, int(total_users * 0.5))  # At least 1
    required_by_fixed = 5

    # Use whichever is smaller (easier to achieve)
    required_comments = min(required_by_percentage, required_by_fixed)

    if comment_count >= required_comments:
        achievement = Achievement(
            user_id=user_id, room_id=room_id, achievement_type="collaborator"
        )
        db.session.add(achievement)
        db.session.commit()
        print(f"🎉 User {user_id} earned 'Collaborator' in room {room_id}")
        flash(
            f"👥 Achievement Unlocked: Collaborator! You've helped {comment_count} students in this room.",
            "success",
        )


def check_learning_master(user_id: int, room_id: int) -> None:
    """Check if user has used 74% or more of the available modes in the room."""
    # Check if user has already earned this achievement
    existing = Achievement.query.filter_by(
        user_id=user_id, room_id=room_id, achievement_type="learning_master"
    ).first()

    if existing:
        return

    # Get total number of available modes for this room
    from src.utils.openai_utils import get_modes_for_room
    from src.models import Room

    room = Room.query.get(room_id)
    if not room:
        return

    available_modes = get_modes_for_room(room)
    total_modes = len(available_modes)

    if total_modes == 0:
        return

    # Count unique modes used by this user in this room
    unique_modes = UserModeUsage.query.filter_by(
        user_id=user_id, room_id=room_id
    ).count()

    # Calculate percentage (74% = 0.74)
    percentage_used = unique_modes / total_modes
    required_percentage = 0.74

    if percentage_used >= required_percentage:
        achievement = Achievement(
            user_id=user_id, room_id=room_id, achievement_type="learning_master"
        )
        db.session.add(achievement)
        db.session.commit()
        print(f"🎉 User {user_id} earned 'Learning Master' in room {room_id}")
        flash(
            f"🎓 Achievement Unlocked: Learning Master! You've used {unique_modes}/{total_modes} modes ({percentage_used:.1%}) in this room.",
            "success",
        )


def get_user_achievements(user_id: int, room_id: int) -> List[Achievement]:
    """Get all achievements earned by a user in a specific room."""
    return Achievement.query.filter_by(user_id=user_id, room_id=room_id).all()


def get_user_mode_usage(user_id: int, room_id: int) -> List[UserModeUsage]:
    """Get mode usage statistics for a user in a specific room."""
    return UserModeUsage.query.filter_by(user_id=user_id, room_id=room_id).all()
