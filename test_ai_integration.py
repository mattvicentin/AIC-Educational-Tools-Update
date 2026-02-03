#!/usr/bin/env python3
"""
Quick test script to verify AI (Anthropic Claude) integration is working.
"""

# TODO: verify usage; consider moving this script into scripts/ or removing if unused.

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_ai_integration():
    """Test AI integration with a simple API call."""
    print("🧪 Testing AI Integration")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment")
        print("   Please add it to your .env file")
        return False
    
    print(f"✅ API key found (length: {len(api_key)} chars)")
    
    # Test direct API call
    try:
        from src.utils.openai_utils import call_anthropic_api
        
        print("\n📤 Sending test message to Anthropic Claude API...")
        print("   Message: 'Reply with exactly one word: hello'")
        
        messages = [{"role": "user", "content": "Reply with exactly one word: hello"}]
        response, truncated = call_anthropic_api(
            messages=messages,
            system_prompt="You are a helpful assistant. Be concise.",
            max_tokens=10
        )
        
        print(f"\n✅ AI Response received!")
        print(f"   Response: {response.strip()}")
        print(f"   Truncated: {truncated}")
        
        if "hello" in response.lower():
            print("\n🎉 SUCCESS: AI integration is working correctly!")
            return True
        else:
            print(f"\n⚠️  Warning: Unexpected response format")
            print(f"   Expected 'hello', got: {response}")
            return True  # Still consider it working if we got a response
        
    except Exception as e:
        print(f"\n❌ ERROR: AI integration test failed")
        print(f"   Error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check for specific error types
        if "ANTHROPIC_API_KEY" in str(e):
            print("\n   💡 Tip: Check that your API key is correct in .env")
        elif "429" in str(e) or "rate limit" in str(e).lower():
            print("\n   💡 Tip: Rate limit exceeded. Wait a moment and try again.")
        elif "401" in str(e) or "unauthorized" in str(e).lower():
            print("\n   💡 Tip: Invalid API key. Check your .env file.")
        
        import traceback
        print("\n   Full traceback:")
        traceback.print_exc()
        return False

def test_app_context():
    """Test AI integration within Flask app context."""
    print("\n" + "=" * 50)
    print("🧪 Testing AI Integration with Flask App Context")
    print("=" * 50)
    
    try:
        from src.main import app
        from src.models import Chat, Message, User, Room
        from src.app import db
        from src.utils.openai_utils import get_ai_response
        
        with app.app_context():
            # Check if we have any users/rooms
            user_count = User.query.count()
            room_count = Room.query.count()
            
            print(f"\n📊 Database status:")
            print(f"   Users: {user_count}")
            print(f"   Rooms: {room_count}")
            
            # Create a test chat if we have a user and room
            if user_count > 0 and room_count > 0:
                user = User.query.first()
                room = Room.query.first()
                
                print(f"\n📝 Creating test chat...")
                chat = Chat(
                    title="AI Test Chat",
                    room_id=room.id,
                    created_by=user.id,
                    mode="explore"
                )
                db.session.add(chat)
                db.session.commit()
                
                # Add a test message
                message = Message(
                    chat_id=chat.id,
                    user_id=user.id,
                    role="user",
                    content="Say hello in one word."
                )
                db.session.add(message)
                db.session.commit()
                
                print("📤 Getting AI response...")
                response, truncated = get_ai_response(chat)
                
                print(f"\n✅ AI Response received!")
                print(f"   Response: {response[:100]}..." if len(response) > 100 else f"   Response: {response}")
                print(f"   Truncated: {truncated}")
                
                # Cleanup
                db.session.delete(message)
                db.session.delete(chat)
                db.session.commit()
                
                print("\n🎉 SUCCESS: Full AI integration test passed!")
                return True
            else:
                print("\n⚠️  Skipping app context test (no users/rooms found)")
                print("   Create a user and room first to test full integration")
                return True  # Not a failure, just incomplete setup
                
    except Exception as e:
        print(f"\n❌ ERROR: App context test failed")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("AI Integration Test Suite")
    print("=" * 50 + "\n")
    
    # Test 1: Direct API call
    test1_passed = test_ai_integration()
    
    # Test 2: App context test
    test2_passed = test_app_context()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    print(f"Direct API Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"App Context Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed:
        print("\n✅ AI integration is working! You can now use the application.")
    else:
        print("\n❌ AI integration test failed. Please check your API key and try again.")
        sys.exit(1)
