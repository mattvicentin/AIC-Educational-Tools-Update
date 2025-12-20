#!/usr/bin/env python3
"""Test script to verify AI API integration (OpenAI or Anthropic)."""

from dotenv import load_dotenv
import os
from src.utils.openai_utils import get_ai_response, MODES
from src.models import Chat, Message
from src.app import create_app, db

load_dotenv()

def test_ai():
    app = create_app()
    with app.app_context():
        # Create a dummy chat and message
        chat = Chat(title="API Test Chat", owner_id=1, mode="explore")
        db.session.add(chat)
        db.session.commit()
        
        msg = Message(chat_id=chat.id, user_id=1, role="user", content="What is the capital of France?")
        db.session.add(msg)
        db.session.commit()
        
        print("Sending test message to AI...")
        from src.utils.openai_utils import get_client_type
        client_type = get_client_type()
        print(f"Using API: {client_type}")
        response = get_ai_response(chat)
        print("AI Response:")
        print(response)
        
        # Clean up
        db.session.delete(msg)
        db.session.delete(chat)
        db.session.commit()
        print("Test complete and cleaned up.")

if __name__ == "__main__":
    test_ai() 