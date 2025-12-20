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
from typing import Any
from src.models import PageView
from datetime import datetime
import json

analytics = Blueprint("analytics", __name__)


@analytics.route("/pageview", methods=["POST"])
def track_pageview() -> Any:
    """Track a page view."""
    try:
        data = request.get_json()

        # Get user ID if logged in
        user_id = None
        if "user_id" in request.session:
            user_id = request.session["user_id"]

        # Create page view record
        pageview = PageView(
            page=data.get("page", ""),
            user_agent=data.get("user_agent", ""),
            ip_address=request.remote_addr,
            user_id=user_id,
        )

        db.session.add(pageview)
        db.session.commit()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analytics.route("/stats", methods=["GET"])
def get_stats() -> Any:
    """Get basic analytics stats."""
    try:
        # Total page views
        total_views = PageView.query.count()

        # Unique visitors (by IP)
        unique_visitors = db.session.query(PageView.ip_address).distinct().count()

        # Most visited pages
        popular_pages = (
            db.session.query(PageView.page, db.func.count(PageView.page).label("count"))
            .group_by(PageView.page)
            .order_by(db.func.count(PageView.page).desc())
            .limit(10)
            .all()
        )

        # Recent activity (last 7 days)
        from datetime import timedelta

        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_views = PageView.query.filter(PageView.timestamp >= week_ago).count()

        return (
            jsonify(
                {
                    "total_page_views": total_views,
                    "unique_visitors": unique_visitors,
                    "recent_views_7_days": recent_views,
                    "popular_pages": [
                        {"page": page, "count": count} for page, count in popular_pages
                    ],
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@analytics.route("/admin-stats", methods=["GET"])
def get_admin_stats() -> Any:
    """Get comprehensive admin analytics."""
    try:
        from src.models import User, Room, Chat, Message, RoomMember

        # User statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()

        # Room statistics
        total_rooms = Room.query.count()
        active_rooms = Room.query.filter_by(is_active=True).count()

        # Chat statistics
        total_chats = Chat.query.count()
        total_messages = Message.query.count()

        # Recent activity (last 7 days)
        from datetime import timedelta

        week_ago = datetime.utcnow() - timedelta(days=7)

        recent_users = User.query.filter(User.created_at >= week_ago).count()
        recent_rooms = Room.query.filter(Room.created_at >= week_ago).count()
        recent_chats = Chat.query.filter(Chat.created_at >= week_ago).count()
        recent_messages = Message.query.filter(Message.timestamp >= week_ago).count()

        # Page view statistics
        recent_page_views = PageView.query.filter(
            PageView.timestamp >= week_ago
        ).count()
        total_page_views = PageView.query.count()

        # Most active users (by message count) - Fixed ambiguous join
        active_users_list = (
            db.session.query(
                User.display_name, db.func.count(Message.id).label("message_count")
            )
            .select_from(User)
            .join(Message, User.id == Message.user_id)
            .group_by(User.id, User.display_name)
            .order_by(db.func.count(Message.id).desc())
            .limit(10)
            .all()
        )

        # Most active rooms (by message count) - Fixed ambiguous join
        active_rooms_list = (
            db.session.query(
                Room.name, db.func.count(Message.id).label("message_count")
            )
            .select_from(Room)
            .join(Chat, Room.id == Chat.room_id)
            .join(Message, Chat.id == Message.chat_id)
            .group_by(Room.id, Room.name)
            .order_by(db.func.count(Message.id).desc())
            .limit(10)
            .all()
        )

        return (
            jsonify(
                {
                    "users": {
                        "total": total_users,
                        "active": active_users,
                        "recent_7_days": recent_users,
                    },
                    "rooms": {
                        "total": total_rooms,
                        "active": active_rooms,
                        "recent_7_days": recent_rooms,
                    },
                    "chats": {"total": total_chats, "recent_7_days": recent_chats},
                    "messages": {
                        "total": total_messages,
                        "recent_7_days": recent_messages,
                    },
                    "page_views": {
                        "total": total_page_views,
                        "recent_7_days": recent_page_views,
                    },
                    "most_active_users": [
                        {"name": name, "messages": count}
                        for name, count in active_users_list
                    ],
                    "most_active_rooms": [
                        {"name": name, "messages": count}
                        for name, count in active_rooms_list
                    ],
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
