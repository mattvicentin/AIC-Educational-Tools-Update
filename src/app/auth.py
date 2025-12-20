#!/usr/bin/env python3
"""
auth.py
Purpose: User authentication and session management blueprint
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Handles user registration, login, logout, password management, and session handling
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
)
from src.app import db
from src.app.access_control import get_current_user, require_login
from typing import Any
import datetime
import secrets
import traceback

# Removed incorrect flask_login import

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register() -> Any:
    if request.method == "POST":
        try:
            # Required fields
            username = request.form["username"].strip()
            email = request.form["email"].strip()
            full_name = request.form["full_name"].strip()
            display_name = request.form["display_name"].strip()
            password = request.form["password"]

            # Optional fields
            institution = request.form.get("institution", "").strip()
            department = request.form.get("department", "").strip()
            research_area = request.form.get("research_area", "").strip()
            role = request.form.get("role", "").strip()
            primary_use_case = request.form.get("primary_use_case", "").strip()
            team_size = request.form.get("team_size", "").strip()
            heard_from = request.form.get("heard_from", "").strip()
            receive_updates = request.form.get("receive_updates") == "1"
            contact_for_research = request.form.get("contact_for_research") == "1"

        except Exception as e:
            flash("Invalid form data. Please try again.", "error")
            return render_template("register.html"), 400

        # Import User model directly to avoid conflicts
        from src.models.user import User
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return render_template(
                "register.html",
                username=username,
                email=email,
                full_name=full_name,
                display_name=display_name,
                institution=institution,
                department=department,
                research_area=research_area,
                role=role,
                primary_use_case=primary_use_case,
                team_size=team_size,
                heard_from=heard_from,
                receive_updates=receive_updates,
                contact_for_research=contact_for_research,
            )

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template(
                "register.html",
                username=username,
                email=email,
                full_name=full_name,
                display_name=display_name,
                institution=institution,
                department=department,
                research_area=research_area,
                role=role,
                primary_use_case=primary_use_case,
                team_size=team_size,
                heard_from=heard_from,
                receive_updates=receive_updates,
                contact_for_research=contact_for_research,
            )
        
        # Validate required input
        if not all([username, email, full_name, display_name, password]):
            flash(
                "All required fields (Username, Email, Full Name, Display Name, and Password) are needed.",
                "error",
            )
            return render_template(
                "register.html",
                username=username,
                email=email,
                full_name=full_name,
                display_name=display_name,
                institution=institution,
                department=department,
                research_area=research_area,
                role=role,
                primary_use_case=primary_use_case,
                team_size=team_size,
                heard_from=heard_from,
                receive_updates=receive_updates,
                contact_for_research=contact_for_research,
            )

        # Validate username format (alphanumeric and underscores only)
        if not username.replace("_", "").isalnum():
            flash(
                "Username can only contain letters, numbers, and underscores.", "error"
            )
            return render_template(
                "register.html",
                username=username,
                email=email,
                full_name=full_name,
                display_name=display_name,
                institution=institution,
                department=department,
                research_area=research_area,
                role=role,
                primary_use_case=primary_use_case,
                team_size=team_size,
                heard_from=heard_from,
                receive_updates=receive_updates,
                contact_for_research=contact_for_research,
            )

        # Validate email format
        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "error")
            return render_template(
                "register.html",
                username=username,
                email=email,
                full_name=full_name,
                display_name=display_name,
                institution=institution,
                department=department,
                research_area=research_area,
                role=role,
                primary_use_case=primary_use_case,
                team_size=team_size,
                heard_from=heard_from,
                receive_updates=receive_updates,
                contact_for_research=contact_for_research,
            )

        # Validate password strength
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template(
                "register.html",
                username=username,
                email=email,
                full_name=full_name,
                display_name=display_name,
                institution=institution,
                department=department,
                research_area=research_area,
                role=role,
                primary_use_case=primary_use_case,
                team_size=team_size,
                heard_from=heard_from,
                receive_updates=receive_updates,
                contact_for_research=contact_for_research,
            )

        try:
            # Create new user
            user = User()
            user.username = username
            user.email = email
            user.full_name = full_name
            user.display_name = display_name
            user.institution = institution
            user.department = department
            user.research_area = research_area
            user.role = role
            user.primary_use_case = primary_use_case
            user.team_size = team_size
            user.heard_from = heard_from
            user.receive_updates = receive_updates
            user.contact_for_research = contact_for_research
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            # Log in the user
            session["user_id"] = user.id
            session["username"] = user.username
            # Mark this as a new registration to avoid "welcome back" message
            session["just_registered"] = True

            flash("Registration successful! Welcome to AI Collab.", "success")
            return redirect(url_for("room.room_crud.index"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {str(e)}")
            current_app.logger.error(
                f"Registration traceback: {traceback.format_exc()}"
            )
            flash("An error occurred during registration. Please try again.", "error")
            return render_template(
                "register.html",
                username=username,
                email=email,
                full_name=full_name,
                display_name=display_name,
                institution=institution,
                department=department,
                research_area=research_area,
                role=role,
                primary_use_case=primary_use_case,
                team_size=team_size,
                heard_from=heard_from,
                receive_updates=receive_updates,
                contact_for_research=contact_for_research,
            )

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if request.method == "POST":
        # Import User model directly to avoid conflicts
        from src.models.user import User
        
        username = request.form["username"].strip()
        password = request.form["password"]

        # Debug logging
        # print(f"Login attempt for username: {username}")

        # Validate input
        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("login.html", username=username)

        # Check if user exists and password is correct
        # First try exact case match, then fall back to case-insensitive
        try:
            user = User.query.filter_by(username=username).first()  # Exact match first
            if not user:
                # Fall back to case-insensitive search if no exact match
                user = User.query.filter(User.username.ilike(username)).first()

            # print(f"User found: {user.username if user else 'None'}")

            if user and user.check_password(password):
                if not user.is_active:
                    flash(
                        "Your account has been deactivated. Please contact support.",
                        "error",
                    )
                    return render_template("login.html", username=username)

                # Set session (original session-based authentication)
                session["user_id"] = user.id
                session["username"] = user.username  # For easier access

                # Only show "welcome back" for returning users, not new registrations
                if not session.pop("just_registered", False):
                    flash(f"Welcome back, {user.display_name}!", "success")
                return redirect(url_for("room.room_crud.index"))
            else:
                # Don't reveal whether username or password was wrong for security
                flash("Invalid username or password.", "error")
                return render_template("login.html", username=username)
        except Exception as e:
            # Log the error for debugging
            current_app.logger.error(f"Login error for username '{username}': {str(e)}")
            flash("An error occurred during login. Please try again.", "error")
            return render_template("login.html", username=username)

    return render_template("login.html")


@auth.route("/logout")
def logout() -> Any:
    session.pop("user_id", None)
    flash("You have been logged out.")
    return redirect(url_for("room.room_crud.index"))


@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password() -> Any:
    if request.method == "POST":
        # Import User model directly to avoid conflicts
        from src.models.user import User
        
        email = request.form["email"].strip()

        if not email:
            flash("Please enter your email address.", "error")
            return render_template("forgot_password.html", email=email)

        # Find user by email
        user = User.query.filter_by(email=email).first()

        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            db.session.commit()

            # Create reset URL
            reset_url = url_for("auth.reset_password", token=token, _external=True)

            # Send email via helper
            try:
                from src.utils.email import send_email
                html = (
                    f"<p>You requested a password reset.</p>"
                    f"<p>Click the link below to reset your password:</p>"
                    f"<p><a href='{reset_url}' target='_blank'>{reset_url}</a></p>"
                    f"<p>If you did not request this, you can ignore this email.</p>"
                )
                sent = send_email(user.email, "Reset your password", html, f"Reset your password: {reset_url}")
                if sent:
                    flash("Password reset email sent. Please check your inbox.", "success")
                else:
                    # Fallback to logging for visibility
                    print(f"=== PASSWORD RESET LINK FOR {user.email} ===")
                    print(f"Reset URL: {reset_url}")
                    print(f"Token: {token}")
                    print("=== END PASSWORD RESET LINK ===")
                    flash("Password reset link generated. Email not configured; link logged on server.", "info")
            except Exception as _e:
                print(f"[email] Failed to send reset email: {_e}")
                print(f"=== PASSWORD RESET LINK FOR {user.email} ===")
                print(f"Reset URL: {reset_url}")
                print(f"Token: {token}")
                print("=== END PASSWORD RESET LINK ===")
                flash("Password reset link generated. Email send failed; link logged on server.", "info")
        else:
            flash(
                "If an account with that email exists, a reset link has been sent.",
                "info",
            )

        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str) -> Any:
    # Import User model directly to avoid conflicts
    from src.models.user import User
    
    # Find user by reset token
    user = User.query.filter_by(reset_token=token).first()

    if not user or user.reset_token_expiry < datetime.datetime.utcnow():
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("reset_password.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("reset_password.html")

        # Update password and clear reset token
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()

        flash("Password has been reset successfully. You can now login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")


@auth.route("/profile")
@require_login
def profile() -> Any:
    user = get_current_user()
    # Get invitation count for navigation
    from src.app.room.utils.room_utils import get_invitation_count
    invitation_count = get_invitation_count(user)
    return render_template("profile.html", user=user, invitation_count=invitation_count)


@auth.route("/edit-profile", methods=["GET", "POST"])
@require_login
def edit_profile() -> Any:
    user = get_current_user()

    if request.method == "POST":
        # Get form data
        full_name = request.form.get("full_name", "").strip()
        display_name = request.form.get("display_name", "").strip()
        email = request.form.get("email", "").strip()
        institution = request.form.get("institution", "").strip()
        department = request.form.get("department", "").strip()
        research_area = request.form.get("research_area", "").strip()
        role = request.form.get("role", "").strip()
        primary_use_case = request.form.get("primary_use_case", "").strip()
        team_size = request.form.get("team_size", "").strip()
        heard_from = request.form.get("heard_from", "").strip()
        receive_updates = request.form.get("receive_updates") == "1"
        contact_for_research = request.form.get("contact_for_research") == "1"

        # Get invitation count for navigation
        from src.app.room.utils.room_utils import get_invitation_count
        invitation_count = get_invitation_count(user)
        
        # Validate required fields
        if not all([display_name, email]):
            flash("Display Name and Email are required.", "error")
            return render_template("edit_profile.html", user=user, invitation_count=invitation_count)

        # Import User model directly to avoid conflicts
        from src.models.user import User
        
        # Check if email is already taken by another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            flash("Email is already registered by another user.", "error")
            return render_template("edit_profile.html", user=user, invitation_count=invitation_count)

        try:
            # Update user information
            user.full_name = full_name
            user.display_name = display_name
            user.email = email
            user.institution = institution
            user.department = department
            user.research_area = research_area
            user.role = role
            user.primary_use_case = primary_use_case
            user.team_size = team_size
            user.heard_from = heard_from
            user.receive_updates = receive_updates
            user.contact_for_research = contact_for_research

            db.session.commit()
            flash("Profile updated successfully!", "success")
            return redirect(url_for("auth.profile"))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while updating your profile: {str(e)}", "error")
            return render_template("edit_profile.html", user=user, invitation_count=invitation_count)

    # Get invitation count for navigation
    from src.app.room.utils.room_utils import get_invitation_count
    invitation_count = get_invitation_count(user)
    return render_template("edit_profile.html", user=user, invitation_count=invitation_count)


@auth.route("/change-password", methods=["GET", "POST"])
@require_login
def change_password() -> Any:
    user = get_current_user()
    
    # Get invitation count for navigation
    from src.app.room.utils.room_utils import get_invitation_count
    invitation_count = get_invitation_count(user)

    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validate current password
        if not user.check_password(current_password):
            flash("Current password is incorrect.", "error")
            return render_template("change_password.html", invitation_count=invitation_count)

        # Validate new password
        if len(new_password) < 6:
            flash("New password must be at least 6 characters long.", "error")
            return render_template("change_password.html", invitation_count=invitation_count)

        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return render_template("change_password.html", invitation_count=invitation_count)

        try:
            # Update password
            user.set_password(new_password)
            db.session.commit()
            flash("Password updated successfully!", "success")
            return redirect(url_for("auth.profile"))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while updating your password: {str(e)}", "error")
            return render_template("change_password.html", invitation_count=invitation_count)

    return render_template("change_password.html", invitation_count=invitation_count)
