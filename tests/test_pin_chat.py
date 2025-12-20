#!/usr/bin/env python3
"""
Tests for pin-seeded chat creation endpoint.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestPinChatCreation:
    """Tests for POST /room/<room_id>/chats/from-pins endpoint."""
    
    def test_pin_chat_options_defined(self):
        """Verify all pin chat options are defined."""
        from src.app.room.routes.crud import PIN_CHAT_OPTIONS
        
        expected_options = {
            "explore", "study", "research_essay", "presentation",
            "learning_exercise", "startup", "artistic", "social_impact", "analyze"
        }
        assert PIN_CHAT_OPTIONS == expected_options
    
    def test_min_pins_required(self):
        """Verify minimum pins constant is set."""
        from src.app.room.routes.crud import MIN_PINS_REQUIRED
        
        assert MIN_PINS_REQUIRED == 3
    
    def test_pin_chat_intro_generation(self):
        """Test the intro generation helper."""
        from src.app.room.routes.crud import _generate_pin_chat_intro
        
        # Create mock pins
        mock_pins = []
        for i in range(3):
            pin = MagicMock()
            pin.content = f"Test pin content {i+1} with some details"
            mock_pins.append(pin)
        
        # Create mock room
        mock_room = MagicMock()
        mock_room.goals = "Learn about testing"
        mock_room.name = "Test Room"
        
        # Test explore option
        intro = _generate_pin_chat_intro(mock_pins, "explore", "Explore & Brainstorm", mock_room)
        assert "3 pinned insights" in intro
        assert "explore" in intro.lower() or "brainstorm" in intro.lower()
        
        # Test study option
        intro = _generate_pin_chat_intro(mock_pins, "study", "Study & Master", mock_room)
        assert "3 pinned insights" in intro
        assert "study" in intro.lower() or "master" in intro.lower()
        
        # Test generic option
        intro = _generate_pin_chat_intro(mock_pins, "startup", "Startup Plan", mock_room)
        assert "3 pinned insights" in intro
        assert "Startup Plan" in intro
    
    def test_pin_snapshot_creation(self):
        """Test PinChatMetadata.create_snapshot method."""
        from src.models.pin import PinChatMetadata
        
        # Create mock pins
        mock_pins = []
        for i in range(3):
            pin = MagicMock()
            pin.id = i + 1
            pin.content = f"Content {i+1}"
            pin.role = "assistant" if i % 2 == 0 else "user"
            pin.user = MagicMock()
            pin.user.username = f"user{i+1}"
            pin.chat_id = 100
            pin.created_at = None
            mock_pins.append(pin)
        
        snapshot = PinChatMetadata.create_snapshot(mock_pins)
        data = json.loads(snapshot)
        
        assert len(data) == 3
        assert data[0]["id"] == 1
        assert data[0]["content"] == "Content 1"
        assert data[0]["author"] == "user1"
        assert data[1]["role"] == "user"


class TestPinChatValidation:
    """Tests for validation logic in pin chat creation."""
    
    def test_invalid_option_rejected(self):
        """Verify invalid options are rejected."""
        from src.app.room.routes.crud import PIN_CHAT_OPTIONS
        
        invalid_options = ["invalid", "foobar", "", "EXPLORE"]  # case-sensitive
        for opt in invalid_options:
            assert opt not in PIN_CHAT_OPTIONS
    
    def test_valid_options_accepted(self):
        """Verify all valid options are accepted."""
        from src.app.room.routes.crud import PIN_CHAT_OPTIONS
        
        valid_options = ["explore", "study", "research_essay", "presentation",
                        "learning_exercise", "startup", "artistic", "social_impact", "analyze"]
        for opt in valid_options:
            assert opt in PIN_CHAT_OPTIONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

