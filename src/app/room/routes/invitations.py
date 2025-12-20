"""
Invitation route handlers.
Handles room invitation system operations.
"""

from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from typing import Any, List, Optional
from datetime import datetime, timedelta
from src.app import db
from src.models import Room, User, RoomMember
from ..services.room_service import RoomService
from ..types import InvitationData, InvitationCreateData, InvitationResponse
from ..utils.room_utils import get_invitation_count, can_user_invite_to_room
from src.app.access_control import get_current_user, require_login, require_room_access

invitations_bp = Blueprint('room_invitations', __name__)

@invitations_bp.route("/invite", methods=["GET", "POST"])
@require_room_access
def invite_members(room_id: int) -> Any:
    """Invite members to a room."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            flash("Room not found or you don't have access to it.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Check if user can invite to this room
        if not can_user_invite_to_room(room, user):
            flash("You don't have permission to invite members to this room.", "error")
            return redirect(url_for('room.room_crud.view_room', room_id=room_id))
        
        if request.method == "POST":
            # Handle invitation creation (email or username)
            invitee_email = (request.form.get('email') or '').strip()
            invitee_username = (request.form.get('username') or '').strip()
            display_name = (request.form.get('display_name') or '').strip()
            can_create_chats = request.form.get('can_create_chats') == 'on'
            can_invite_members = request.form.get('can_invite_members') == 'on'

            # Require at least one identifier
            if not invitee_email and not invitee_username:
                flash("Please enter an email or a username to invite.", "error")
                return redirect(url_for('room.room_invitations.invite_members', room_id=room_id))

            # Resolve invitee by email first, then by username
            invitee: Optional[User] = None
            if invitee_email:
                invitee = User.query.filter_by(email=invitee_email).first()
            if not invitee and invitee_username:
                try:
                    from sqlalchemy import func
                    invitee = User.query.filter(func.lower(User.username) == invitee_username.lower()).first()
                except Exception:
                    invitee = User.query.filter_by(username=invitee_username).first()
            
            if invitee:
                # Check if already a member
                existing_member = RoomMember.query.filter_by(
                    room_id=room_id,
                    user_id=invitee.id
                ).first()
                
                if existing_member:
                    flash("User is already a member of this room.", "warning")
                    return redirect(url_for('room.room_invitations.invite_members', room_id=room_id))
                
                # Create room membership
                member = RoomMember(
                    room_id=room_id,
                    user_id=invitee.id,
                    can_create_chats=can_create_chats,
                    can_invite_members=can_invite_members,
                    joined_at=datetime.utcnow(),
                    accepted_at=None  # Will be set when user accepts
                )
                
                db.session.add(member)
                db.session.commit()
                
                who = invitee.email if invitee_email else f"@{invitee.username}"
                # Send email if an email was provided
                if invitee_email and invitee.email:
                    try:
                        from src.utils.email import send_email
                        room_link = url_for('room.room_crud.view_room', room_id=room_id, _external=True)
                        html = (
                            f"<p>You have been invited to join the room <strong>{room.name}</strong>.</p>"
                            f"<p>Click to view the room: <a href='{room_link}' target='_blank'>{room_link}</a></p>"
                        )
                        send_email(invitee.email, f"Invitation to join '{room.name}'", html, f"Join the room: {room_link}")
                    except Exception as _e:
                        current_app.logger.warning(f"[email] Failed to send invitation email: {_e}")
                flash(f"Invitation sent to {who}!", "success")
                
            else:
                if invitee_username:
                    flash(f"No user found with username '@{invitee_username}'. Please check the spelling and try again.", "error")
                else:
                    flash("User not found. They need to register first.", "error")
            
            return redirect(url_for('room.room_invitations.invite_members', room_id=room_id))
        
        # GET request - show invite form
        members = RoomService.get_room_members(room, user)
        
        return render_template(
            "room/invite.html",
            room=room,
            members=members,
            user=user,
            invitation_count=get_invitation_count(user)
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in invite members for room {room_id}: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('room.room_crud.view_room', room_id=room_id))

@invitations_bp.route("/accept/<int:invitation_id>", methods=["POST"])
@require_login
def accept_invitation(invitation_id: int) -> Any:
    """Accept a room invitation."""
    try:
        user = get_current_user()
        
        # Find the invitation
        invitation = RoomMember.query.filter_by(
            id=invitation_id,
            user_id=user.id,
            accepted_at=None
        ).first()
        
        if not invitation:
            flash("Invitation not found or already processed.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Accept the invitation
        invitation.accepted_at = datetime.utcnow()
        db.session.commit()
        
        flash("Invitation accepted! Welcome to the room.", "success")
        return redirect(url_for('room.room_crud.view_room', room_id=invitation.room_id))
        
    except Exception as e:
        current_app.logger.error(f"Error accepting invitation {invitation_id}: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('room.room_crud.index'))

@invitations_bp.route("/decline/<int:invitation_id>", methods=["POST"])
@require_login
def decline_invitation(invitation_id: int) -> Any:
    """Decline a room invitation."""
    try:
        user = get_current_user()
        
        # Find the invitation
        invitation = RoomMember.query.filter_by(
            id=invitation_id,
            user_id=user.id,
            accepted_at=None
        ).first()
        
        if not invitation:
            flash("Invitation not found or already processed.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Remove the invitation
        db.session.delete(invitation)
        db.session.commit()
        
        flash("Invitation declined.", "info")
        return redirect(url_for('room.room_crud.index'))
        
    except Exception as e:
        current_app.logger.error(f"Error declining invitation {invitation_id}: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('room.room_crud.index'))

@invitations_bp.route("/pending")
@require_login
def pending_invitations() -> Any:
    """View pending invitations for the current user."""
    try:
        user = get_current_user()
        
        # Get pending invitations
        pending = RoomMember.query.filter_by(
            user_id=user.id,
            accepted_at=None
        ).join(Room).filter(Room.is_active == True).all()
        
        return render_template(
            "room/invitations/pending.html",
            pending_invitations=pending,
            user=user,
            invitation_count=len(pending)
        )
        
    except Exception as e:
        current_app.logger.error(f"Error getting pending invitations: {e}")
        flash("Failed to load pending invitations. Please try again.", "error")
        return redirect(url_for('room.room_crud.index'))

@invitations_bp.route("/manage")
@require_room_access
def manage_invitations(room_id: int) -> Any:
    """Manage invitations for a room."""
    try:
        user = get_current_user()
        room = RoomService.get_room_by_id(room_id, user)
        
        if not room:
            flash("Room not found or you don't have access to it.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Check if user can manage invitations
        permissions = RoomService.get_room_permissions(room, user)
        if not permissions["can_manage"]:
            flash("You don't have permission to manage invitations for this room.", "error")
            return redirect(url_for('room.room_crud.view_room', room_id=room_id))
        
        # Get all members and pending invitations
        all_members = RoomMember.query.filter_by(room_id=room_id).all()
        
        accepted_members = [m for m in all_members if m.accepted_at is not None]
        pending_invitations = [m for m in all_members if m.accepted_at is None]
        
        return render_template(
            "room/invitations/manage.html",
            room=room,
            accepted_members=accepted_members,
            pending_invitations=pending_invitations,
            user=user,
            invitation_count=get_invitation_count(user)
        )
        
    except Exception as e:
        current_app.logger.error(f"Error managing invitations for room {room_id}: {e}")
        flash("Failed to load invitation management. Please try again.", "error")
        return redirect(url_for('room.room_crud.view_room', room_id=room_id))

@invitations_bp.route("/revoke/<int:invitation_id>", methods=["POST"])
@require_login
def revoke_invitation(invitation_id: int) -> Any:
    """Revoke a pending invitation."""
    try:
        user = get_current_user()
        
        # Find the invitation
        invitation = RoomMember.query.get(invitation_id)
        
        if not invitation:
            flash("Invitation not found.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Check if user can manage this room
        room = RoomService.get_room_by_id(invitation.room_id, user)
        if not room:
            flash("Room not found or you don't have access to it.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        permissions = RoomService.get_room_permissions(room, user)
        if not permissions["can_manage"]:
            flash("You don't have permission to revoke invitations for this room.", "error")
            return redirect(url_for('room.room_crud.view_room', room_id=invitation.room_id))
        
        # Remove the invitation
        db.session.delete(invitation)
        db.session.commit()
        
        flash("Invitation revoked successfully.", "success")
        return redirect(url_for('room.room_invitations.manage_invitations', room_id=invitation.room_id))
        
    except Exception as e:
        current_app.logger.error(f"Error revoking invitation {invitation_id}: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('room.room_crud.index'))

@invitations_bp.route("/update/<int:member_id>", methods=["POST"])
@require_login
def update_member_permissions(member_id: int) -> Any:
    """Update member permissions."""
    try:
        user = get_current_user()
        
        # Find the member
        member = RoomMember.query.get(member_id)
        
        if not member:
            flash("Member not found.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Check if user can manage this room
        room = RoomService.get_room_by_id(member.room_id, user)
        if not room:
            flash("Room not found or you don't have access to it.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        permissions = RoomService.get_room_permissions(room, user)
        if not permissions["can_manage"]:
            flash("You don't have permission to update member permissions.", "error")
            return redirect(url_for('room.room_crud.view_room', room_id=member.room_id))
        
        # Update permissions
        member.can_create_chats = request.form.get('can_create_chats') == 'on'
        member.can_invite_members = request.form.get('can_invite_members') == 'on'
        
        db.session.commit()
        
        flash("Member permissions updated successfully.", "success")
        return redirect(url_for('room.room_invitations.manage_invitations', room_id=member.room_id))
        
    except Exception as e:
        current_app.logger.error(f"Error updating member permissions {member_id}: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('room.room_crud.index'))

@invitations_bp.route("/remove/<int:member_id>", methods=["POST"])
@require_login
def remove_member(member_id: int) -> Any:
    """Remove a member from the room."""
    try:
        user = get_current_user()
        
        # Find the member
        member = RoomMember.query.get(member_id)
        
        if not member:
            flash("Member not found.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        # Check if user can manage this room
        room = RoomService.get_room_by_id(member.room_id, user)
        if not room:
            flash("Room not found or you don't have access to it.", "error")
            return redirect(url_for('room.room_crud.index'))
        
        permissions = RoomService.get_room_permissions(room, user)
        if not permissions["can_manage"]:
            flash("You don't have permission to remove members from this room.", "error")
            return redirect(url_for('room.room_crud.view_room', room_id=member.room_id))
        
        # Don't allow removing the room owner
        if member.user_id == room.owner_id:
            flash("Cannot remove the room owner.", "error")
            return redirect(url_for('room.room_invitations.manage_invitations', room_id=member.room_id))
        
        # Remove the member
        db.session.delete(member)
        db.session.commit()
        
        flash("Member removed from room successfully.", "success")
        return redirect(url_for('room.room_invitations.manage_invitations', room_id=member.room_id))
        
    except Exception as e:
        current_app.logger.error(f"Error removing member {member_id}: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('room.room_crud.index'))
