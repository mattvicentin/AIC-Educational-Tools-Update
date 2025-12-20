import os
import json

# Ensure SQLite in-memory for tests before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from src.main import app as flask_app
from src.app.room.utils.refinement_utils import validate_and_normalize_modes


def test_validate_and_normalize_modes_basic():
    modes = [
        {"label": "Step A", "prompt": "<b>Do A</b>"},
        {"label": "2) Step B", "prompt": "Do B"},
    ]
    normalized, warnings = validate_and_normalize_modes(modes)
    assert normalized and isinstance(normalized, list)
    assert normalized[0]["key"] == "step1"
    assert normalized[0]["label"].startswith("1.")
    assert "<" not in normalized[0]["prompt"]
    assert not warnings or isinstance(warnings, list)


def test_refine_new_trial_limit(monkeypatch):
    # Force templates-only fallback to avoid external API calls
    monkeypatch.setenv("AI_FAILOVER_ORDER", "templates")

    with flask_app.app_context():
        flask_app.config.update(
            TESTING=True,
            DEBUG=True,
            REFINE_V2_ENABLED=True,
            TRIAL_ENABLED=True,
            TRIAL_MAX_REFINES=1,
        )

        client = flask_app.test_client()

        payload = {
            "message": "reduce to one step",
            "current_modes": [
                {"key": "step1", "label": "1. Explore", "prompt": "Explore prompt"},
                {"key": "step2", "label": "2. Focus", "prompt": "Focus prompt"},
            ],
            "current_room_title": "Room",
            "current_room_description": "Goals",
        }

        # First refinement should succeed for anonymous session
        resp1 = client.post(
            "/room/refine-room-proposal",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp1.status_code in (200, 303)
        data1 = resp1.get_json()
        assert data1.get("success") is True

        # Second refinement should hit trial limit (HTTP 403)
        resp2 = client.post(
            "/room/refine-room-proposal",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp2.status_code == 403
        data2 = resp2.get_json()
        assert data2.get("success") is False
        assert "limit" in (data2.get("error") or "").lower()


