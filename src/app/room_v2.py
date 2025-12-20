"""
Room V2 - Clean Enhanced Dashboard Implementation
Step 1: Basic route with room links and activity sorting
"""

from flask import Blueprint, render_template, current_app
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.app import db
from src.models import Room, Chat, Message, User
from src.app.access_control import get_current_user, require_login
from src.app.room.services.room_service import RoomService
from src.utils.title_generator import get_display_title

# Create independent blueprint
room_v2 = Blueprint("room_v2", __name__)


def get_room_statistics(room: Room, user: User) -> Dict[str, Any]:
    """
    Step 3: Enhanced room statistics with unread message detection.
    Returns comprehensive room activity, member data, and unread counts.
    """
    try:
        from src.models import RoomMember
        
        # Look at last 7 days for recent activity
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        
        # Look at last 48 hours for unread messages
        unread_cutoff = datetime.utcnow() - timedelta(hours=48)
        
        # Count all-time activity
        total_chats = Chat.query.filter_by(room_id=room.id).count()
        total_messages = Message.query.join(Chat).filter(Chat.room_id == room.id).count()
        
        # Count recent activity
        recent_chats = Chat.query.filter(
            Chat.room_id == room.id,
            Chat.created_at >= recent_cutoff
        ).count()
        
        recent_messages = Message.query.join(Chat).filter(
            Chat.room_id == room.id,
            Message.timestamp >= recent_cutoff
        ).count()
        
        # Count unread messages (messages from last 24 hours that aren't from this user)
        unread_messages = Message.query.join(Chat).filter(
            Chat.room_id == room.id,
            Message.timestamp >= unread_cutoff,
            Message.user_id != user.id  # Don't count user's own messages as unread
        ).count()
        
        # Get member count
        try:
            member_count = RoomMember.query.filter_by(room_id=room.id).count() + 1  # +1 for owner
        except Exception:
            member_count = 1  # Fallback if RoomMember table issues
        
        # Get last activity
        last_message = Message.query.join(Chat).filter(
            Chat.room_id == room.id
        ).order_by(Message.timestamp.desc()).first()
        
        last_activity = last_message.timestamp if last_message else room.created_at
        
        # Calculate base activity score
        activity_score = (recent_chats * 10) + recent_messages
        
        # New room boost: Give newly created rooms a boost so they appear at top
        room_age_hours = (datetime.utcnow() - room.created_at).total_seconds() / 3600
        if room_age_hours <= 6:    # Very new (6 hours)
            activity_score += 100
            current_app.logger.info(f"Room {room.id} gets very new boost (+100): {room_age_hours:.1f}h old")
        elif room_age_hours <= 24: # New (1 day)  
            activity_score += 50
            current_app.logger.info(f"Room {room.id} gets new boost (+50): {room_age_hours:.1f}h old")
        elif room_age_hours <= 72: # Recent (3 days)
            activity_score += 25
            current_app.logger.info(f"Room {room.id} gets recent boost (+25): {room_age_hours:.1f}h old")
        
        # Enhanced sorting: unread messages get top priority boost
        if unread_messages > 0:
            activity_score += 1000  # Boost unread rooms to very top
        
        return {
            "total_chats": total_chats,
            "total_messages": total_messages,
            "recent_chats": recent_chats,
            "recent_messages": recent_messages,
            "unread_messages": unread_messages,
            "has_unread": unread_messages > 0,
            "member_count": member_count,
            "last_activity": last_activity,
            "activity_score": activity_score,
            "has_recent_activity": activity_score > 0,
            "room_age_hours": room_age_hours,
            "is_very_new": room_age_hours <= 6,
            "is_new": room_age_hours <= 24,
            "is_recent": room_age_hours <= 72
        }
        
    except Exception as e:
        current_app.logger.warning(f"Statistics error for room {room.id}: {e}")
        return {
            "total_chats": 0,
            "total_messages": 0,
            "recent_chats": 0,
            "recent_messages": 0,
            "member_count": 1,
            "last_activity": room.created_at,
            "activity_score": 0,
            "has_recent_activity": False
        }


@room_v2.route("/")
@require_login
def index() -> Any:
    """Step 1: Basic activity-sorted room dashboard."""
    current_app.logger.info("🚀 ROOM V2 STEP 1: Basic activity sorting")
    
    try:
        user = get_current_user()
        current_app.logger.info(f"🚀 V2 User: {user.username}")
        
        # Get rooms using proven RoomService
        rooms_data = RoomService.get_user_rooms(user)
        owned_rooms = rooms_data["owned"]
        member_rooms = rooms_data["member"]
        
        # Combine and score all rooms
        all_rooms = []
        
        # Process owned rooms with enhanced statistics
        for room in owned_rooms:
            stats = get_room_statistics(room, user)
            all_rooms.append({
                "room": room,
                "is_owner": True,
                "stats": stats
            })
        
        # Process member rooms with enhanced statistics
        for room in member_rooms:
            stats = get_room_statistics(room, user)
            all_rooms.append({
                "room": room,
                "is_owner": False,
                "stats": stats
            })
        
        # Sort by activity (highest first)
        all_rooms.sort(key=lambda x: -x["stats"]["activity_score"])
        
        # Count rooms with unread messages
        rooms_with_unread = sum(1 for room_data in all_rooms if room_data["stats"]["has_unread"])
        
        current_app.logger.info(f"🚀 V2 STEP 4: Sorted {len(all_rooms)} rooms with collapsible details ({rooms_with_unread} with unread)")
        
        # Log top 3 for verification with short titles
        for i, room_data in enumerate(all_rooms[:3]):
            room = room_data["room"]
            stats = room_data["stats"]
            display_title = get_display_title(room)
            unread_info = f", {stats['unread_messages']} unread" if stats['has_unread'] else ""
            goals_info = f", has goals" if room.goals else ", no goals"
            current_app.logger.info(f"🚀 V2 #{i+1}: '{display_title}' (was: {room.name[:20]}...) - {stats['total_chats']} chats, {stats['total_messages']} messages{unread_info}{goals_info} (Score: {stats['activity_score']})")
        
        return render_template(
            "room_v2_step5_fixed.html",
            sorted_rooms=all_rooms,
            user=user,
            total_rooms=len(all_rooms),
            get_display_title=get_display_title  # Make function available in template
        )
        
    except Exception as e:
        current_app.logger.error(f"V2 Step 1 error: {e}")
        import traceback
        current_app.logger.error(f"V2 Traceback: {traceback.format_exc()}")
        from flask import flash, redirect, url_for
        flash("V2 dashboard failed. Please try the original.", "error")
        return redirect(url_for('room.room_crud.index'))
