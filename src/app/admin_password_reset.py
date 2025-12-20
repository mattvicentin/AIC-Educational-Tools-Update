"""
Admin-only password reset endpoint.
Allows admins to reset user passwords via web interface.
"""

from flask import Blueprint, request, jsonify, render_template_string
from flask_wtf.csrf import generate_csrf
from src.app import db
from src.models import User
from src.app.access_control import require_admin
import secrets

admin_reset_bp = Blueprint('admin_password_reset', __name__)


RESET_FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Password Reset</title>
    <style>
        body { font-family: system-ui; max-width: 600px; margin: 50px auto; padding: 20px; }
        .form-group { margin: 20px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #3b82f6; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #2563eb; }
        .success { background: #dcfce7; border: 1px solid #86efac; padding: 15px; border-radius: 4px; margin: 20px 0; }
        .error { background: #fee2e2; border: 1px solid #fca5a5; padding: 15px; border-radius: 4px; margin: 20px 0; }
        .info { background: #f0f9ff; border: 1px solid #93c5fd; padding: 15px; border-radius: 4px; margin: 20px 0; }
        pre { background: #f3f4f6; padding: 15px; border-radius: 4px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>🔐 Admin Password Reset</h1>
    
    {% if message %}
    <div class="{{ message_type }}">{{ message|safe }}</div>
    {% endif %}
    
    <form method="POST">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
        
        <div class="form-group">
            <label for="email">User Email:</label>
            <input type="email" id="email" name="email" required 
                   value="{{ email or '' }}" 
                   placeholder="user@example.com">
        </div>
        
        <div class="form-group">
            <label for="password">Temporary Password:</label>
            <input type="text" id="password" name="password" required 
                   value="{{ suggested_password }}" 
                   placeholder="TempPass2024!">
            <small>User will be asked to change this on first login</small>
        </div>
        
        <button type="submit">Reset Password</button>
    </form>
    
    <p style="margin-top: 40px; color: #666;">
        <strong>Note:</strong> This will immediately reset the user's password and clear any pending reset tokens.
        Send the temporary password to the user via email or message.
    </p>
</body>
</html>
"""


@admin_reset_bp.route('/admin/reset-user-password', methods=['GET', 'POST'])
@require_admin
def admin_reset_password():
    """Admin endpoint to reset user passwords."""
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()
        
        if not email or not new_password:
            return render_template_string(
                RESET_FORM_HTML,
                message="Email and password are required",
                message_type="error",
                email=email,
                suggested_password=secrets.token_urlsafe(12),
                csrf_token=generate_csrf
            )
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return render_template_string(
                RESET_FORM_HTML,
                message=f"❌ No user found with email: {email}",
                message_type="error",
                email=email,
                suggested_password=secrets.token_urlsafe(12),
                csrf_token=generate_csrf
            )
        
        # Reset password
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        # Generate message for user
        user_message = f"""
<strong>✅ Password reset successful!</strong><br><br>

<strong>User Details:</strong><br>
• Email: {user.email}<br>
• Username: {user.username}<br>
• Display Name: {user.display_name}<br>
• New Password: <code>{new_password}</code><br><br>

<strong>📧 Message to send to {user.display_name}:</strong>
<pre>
Hi {user.display_name},

Your password has been reset to: {new_password}

Please login at: https://collab.up.railway.app/auth/login
  • Username: {user.username}
  • Password: {new_password}

After logging in, please immediately:
1. Click on 'Profile' in the top menu
2. Select 'Change Password'
3. Set your own secure password

Let me know if you have any issues!
</pre>
"""
        
        return render_template_string(
            RESET_FORM_HTML,
            message=user_message,
            message_type="success",
            suggested_password=secrets.token_urlsafe(12),
            csrf_token=generate_csrf
        )
    
    # GET request - show form
    return render_template_string(
        RESET_FORM_HTML,
        suggested_password=secrets.token_urlsafe(12),
        csrf_token=generate_csrf
    )

