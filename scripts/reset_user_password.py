#!/usr/bin/env python3
"""
Reset a user's password directly (admin tool)

Usage:
    python reset_user_password.py elisehafskjold@gmail.com TempPass123!
    
Or run interactively without arguments.
"""

import sys
import os

# Ensure we can import from src by adding project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import create_app, db
from src.models import User


def reset_user_password(email: str, new_password: str):
    """Reset a user's password and clear any pending reset tokens."""
    
    app = create_app()
    
    with app.app_context():
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ User not found with email: {email}")
            return False
        
        # Reset password
        user.set_password(new_password)
        
        # Clear any pending reset tokens
        user.reset_token = None
        user.reset_token_expiry = None
        
        db.session.commit()
        
        print("="*60)
        print(f"✅ Password reset successful!")
        print(f"Email: {user.email}")
        print(f"Username: {user.username}")
        print(f"Display Name: {user.display_name}")
        print(f"New Password: {new_password}")
        print("="*60)
        print("\n📧 Message to send to user:")
        print("-"*60)
        print(f"""
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

Best regards
        """.strip())
        print("-"*60)
        
        return True


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # Command line arguments provided
        email = sys.argv[1]
        password = sys.argv[2]
    else:
        # Interactive mode
        print("Password Reset Tool")
        print("="*60)
        email = input("Enter user email: ").strip()
        password = input("Enter temporary password: ").strip()
        
        if not email or not password:
            print("❌ Email and password are required")
            sys.exit(1)
    
    # Confirm before proceeding
    print(f"\n⚠️  You are about to reset password for: {email}")
    print(f"New password will be: {password}")
    confirm = input("Continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Cancelled")
        sys.exit(0)
    
    success = reset_user_password(email, password)
    sys.exit(0 if success else 1)




