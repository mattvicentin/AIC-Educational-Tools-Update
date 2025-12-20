#!/usr/bin/env python3
"""Script to help set up the .env file for AI Collab."""

import os
import secrets

def create_env_file():
    """Create a .env file with the required environment variables."""
    
    # Check if .env already exists
    if os.path.exists('.env'):
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Aborted. Your existing .env file is preserved.")
            return
    
    # Generate a secure secret key
    secret_key = secrets.token_hex(32)
    
    # Create the .env content
    env_content = f"""# AI Collab Environment Configuration
# Generated automatically by setup_env.py

# Flask Secret Key (required for sessions and security)
SECRET_KEY={secret_key}

# AI Services (choose one or both)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Google Services (optional - for Google Docs integration)
# Service account file path (default: service-account-key.json)
GOOGLE_SERVICE_ACCOUNT_FILE=service-account-key.json

# Google OAuth (optional - for user Google Docs access)
# Get from: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
"""
    
    # Write the .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created successfully!")
    print(f"🔑 Generated SECRET_KEY: {secret_key}")
    print("\n📝 Next steps:")
    print("1. Edit the .env file to add your API keys")
    print("2. Run: python tests/test_env.py to verify configuration")
    print("3. Run: python run.py to start the application")

def main():
    """Main function."""
    print("🔧 AI Collab Environment Setup")
    print("=" * 40)
    
    create_env_file()

if __name__ == "__main__":
    main() 