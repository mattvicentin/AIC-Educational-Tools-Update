from flask import Blueprint, render_template, Response, redirect, url_for
from src.app.access_control import require_admin
from src.app import db

admin = Blueprint("admin", __name__)


@admin.route("/admin")
@require_admin
def dashboard():
    # Redirect to primary users report for now; KPI page can be added later
    return redirect(url_for('admin.users_report'))


@admin.route("/admin/users")
@require_admin
def users_report():
    from src.models import User, Chat, Room
    from sqlalchemy import func
    from flask import current_app

    try:
        # Aggregate chats per user (avoid cartesian by subquery)
        chats_agg = (
            db.session.query(
                Chat.created_by.label('uid'),
                func.count(Chat.id).label('total_chats'),
                func.max(Chat.created_at).label('last_chat_created_at'),
            )
            .group_by(Chat.created_by)
            .subquery()
        )

        # Aggregate rooms per user (owner)
        rooms_agg = (
            db.session.query(
                Room.owner_id.label('uid'),
                func.count(Room.id).label('total_rooms'),
                func.max(Room.created_at).label('last_room_created_at'),
            )
            .group_by(Room.owner_id)
            .subquery()
        )

        q = (
            db.session.query(
                User.id,
                User.username,
                User.email,
                User.display_name,
                func.coalesce(rooms_agg.c.total_rooms, 0),
                rooms_agg.c.last_room_created_at,
                func.coalesce(chats_agg.c.total_chats, 0),
                chats_agg.c.last_chat_created_at,
            )
            .outerjoin(rooms_agg, rooms_agg.c.uid == User.id)
            .outerjoin(chats_agg, chats_agg.c.uid == User.id)
            .order_by(func.coalesce(chats_agg.c.total_chats, 0).desc())
        )

        rows = q.all()

        # Prepare two tables
        basic = []
        activity = []
        for r in rows:
            user_id, username, email, display_name, total_rooms, last_room_dt, total_chats, last_chat_dt = r
            basic.append({
                'user_id': user_id,
                'username': username,
                'email': email,
                'display_name': display_name,
            })
            activity.append({
                'user_id': user_id,
                'username': username,
                'total_rooms': int(total_rooms or 0),
                'last_room_created_at': last_room_dt.strftime('%Y-%m-%d %H:%M') if last_room_dt else '',
                'total_chats': int(total_chats or 0),
                'last_chat_created_at': last_chat_dt.strftime('%Y-%m-%d %H:%M') if last_chat_dt else '',
            })

        return render_template("admin_users.html", users_basic=basic, users_activity=activity)
    except Exception as e:
        current_app.logger.exception(f"/admin/users render error: {e}")
        # Fallback to CSV if rendering fails
        return users_report_csv()


@admin.route("/admin/users.csv")
@require_admin
def users_report_csv():
    from src.models import User, Chat, Room
    from sqlalchemy import func
    import csv
    from io import StringIO

    chats_agg = (
        db.session.query(
            Chat.created_by.label('uid'),
            func.count(Chat.id).label('total_chats'),
            func.max(Chat.created_at).label('last_chat_created_at'),
        )
        .group_by(Chat.created_by)
        .subquery()
    )

    rooms_agg = (
        db.session.query(
            Room.owner_id.label('uid'),
            func.count(Room.id).label('total_rooms'),
            func.max(Room.created_at).label('last_room_created_at'),
        )
        .group_by(Room.owner_id)
        .subquery()
    )

    rows = (
        db.session.query(
            User.id,
            User.username,
            User.email,
            User.display_name,
            func.coalesce(rooms_agg.c.total_rooms, 0),
            rooms_agg.c.last_room_created_at,
            func.coalesce(chats_agg.c.total_chats, 0),
            chats_agg.c.last_chat_created_at,
        )
        .outerjoin(rooms_agg, rooms_agg.c.uid == User.id)
        .outerjoin(chats_agg, chats_agg.c.uid == User.id)
        .order_by(func.coalesce(chats_agg.c.total_chats, 0).desc())
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "username", "email", "display_name", "total_rooms", "last_room_created_at", "total_chats", "last_chat_created_at"])
    for r in rows:
        writer.writerow([
            r[0], r[1], r[2], r[3], int(r[4] or 0), (r[5].isoformat() if r[5] else ""), int(r[6] or 0), (r[7].isoformat() if r[7] else "")
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=users_chats_report.csv"
        },
    )


@admin.route("/admin/invites/repair", methods=["POST"]) 
@require_admin
def repair_pending_invites():
    """Admin-only: mark accepted_at for memberships where the user already interacted in the room.

    Criteria: user created a chat in the room OR posted a message in any chat of the room.
    """
    from src.models import RoomMember, Chat, Message, Room
    from sqlalchemy import exists, and_, or_
    from datetime import datetime
    from flask import flash

    # Select candidate pending memberships in active rooms
    pending_q = (
        db.session.query(RoomMember)
        .join(Room, RoomMember.room_id == Room.id)
        .filter(Room.is_active == True, RoomMember.accepted_at.is_(None))
    )

    # EXISTS subqueries
    chat_exists = (
        db.session.query(Chat.id)
        .filter(and_(Chat.room_id == RoomMember.room_id, Chat.created_by == RoomMember.user_id))
        .exists()
    )
    msg_exists = (
        db.session.query(Message.id)
        .join(Chat, Message.chat_id == Chat.id)
        .filter(and_(Chat.room_id == RoomMember.room_id, Message.user_id == RoomMember.user_id))
        .exists()
    )

    candidates = pending_q.filter(or_(chat_exists, msg_exists)).all()
    updated = 0
    for m in candidates:
        m.accepted_at = datetime.utcnow()
        updated += 1

    if updated:
        db.session.commit()
    else:
        db.session.rollback()

    flash(f"Repaired {updated} pending invite(s).", "success")
    return redirect(url_for('admin.users_report'))


