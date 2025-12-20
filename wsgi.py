#!/usr/bin/env python3
"""
WSGI entry point for production deployment.
This file is used by Gunicorn to serve the Flask application.
Updated for Railway deployment - 2025-08-21
"""

import os
import sys

print("Starting Flask application...")
print(f"FLASK_ENV: {os.getenv('FLASK_ENV', 'not set')}")
print(f"SECRET_KEY: {'set' if os.getenv('SECRET_KEY') else 'not set'}")
print(f"DATABASE_URL: {'set' if os.getenv('DATABASE_URL') else 'not set'}")
print(f"PORT: {os.getenv('PORT', 'not set')}")

try:
    import sys
    import os
    print("🚀🚀🚀 ROOT WSGI.PY BEING USED - LOADING SRC/MAIN.PY 🚀🚀🚀")
    # Add src directory to Python path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from main import app
    print("🚀🚀🚀 ROOT WSGI.PY SUCCESSFULLY LOADED SRC/MAIN.PY 🚀🚀🚀")
    
    print("Creating Flask application...")
    # The Flask application is already created in main.py
    # app is imported from main - Railway deployment ready
    print("Flask app created successfully!")
    
    # Test basic app functionality
    print("Testing app routes...")
    with app.test_client() as client:
        response = client.get('/health')
        print(f"Health check response: {response.status_code}")
    
except Exception as e:
    print(f"Error creating Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    app.run() 