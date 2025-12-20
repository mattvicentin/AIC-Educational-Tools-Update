import os
import pytest

# Ensure tests use in-memory database before app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from src.main import app as flask_app  # noqa: E402
from src.app import db  # noqa: E402
from src.models import User, Room, Chat  # noqa: E402


@pytest.fixture
def test_client(monkeypatch):
    """Return a Flask test client with a fresh in-memory database."""
    with flask_app.app_context():
        flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        db.drop_all()
        db.create_all()

        # Patch expensive side effects triggered during chat creation
        monkeypatch.setattr(
            "src.utils.learning.triggers.trigger_context_refresh_for_room",
            lambda room_id: None,
            raising=False,
        )
        monkeypatch.setattr(
            "src.utils.openai_utils.generate_chat_introduction",
            lambda *args, **kwargs: "Welcome to your next step!",
            raising=False,
        )

        client = flask_app.test_client()
        yield client

        db.session.remove()
        db.drop_all()


def _create_user_and_room():
    """Helper to create a logged-in owner and their room."""
    user = User(
        username="owner",
        email="owner@example.com",
        display_name="Owner Tester",
        password_hash="hashed-password",
    )
    db.session.add(user)
    db.session.commit()

    room = Room(
        name="Progression Room",
        description="Testing next-step creation",
        owner_id=user.id,
    )
    db.session.add(room)
    db.session.commit()
    return user.id, room.id


def test_next_step_creation_deduplicates(test_client):
    """Ensure JSON next-step creation reuses existing chats and marks completion."""
    with flask_app.app_context():
        user_id, room_id = _create_user_and_room()

    with test_client.session_transaction() as session:
        session["user_id"] = user_id

    # First request should create a brand-new chat for the mode
    resp1 = test_client.post(
        f"/room/{room_id}/chat/create",
        json={"mode": "explore", "title": "Initial Step", "source": "next_step"},
    )
    assert resp1.status_code == 200
    data1 = resp1.get_json()
    assert data1["success"] is True
    created_chat_id = data1["chat_id"]

    with flask_app.app_context():
        assert Chat.query.filter_by(room_id=room_id, mode="explore").count() == 1

    # Second request for the same mode should reuse the existing chat
    resp2 = test_client.post(
        f"/room/{room_id}/chat/create",
        json={"mode": "explore", "title": "Duplicate Step", "source": "next_step"},
    )
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2["success"] is True
    assert data2.get("existing") is True
    assert data2["chat_id"] == created_chat_id

    with flask_app.app_context():
        # Still only one chat, so no duplicates were created
        assert Chat.query.filter_by(room_id=room_id, mode="explore").count() == 1
