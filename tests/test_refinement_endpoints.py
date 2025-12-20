import os
import json

# Use in-memory DB for tests before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from src.main import app as flask_app


def test_refine_edit_requires_access(monkeypatch):
    monkeypatch.setenv("AI_FAILOVER_ORDER", "templates")
    with flask_app.app_context():
        flask_app.config.update(TESTING=True, DEBUG=True, REFINE_V2_ENABLED=True)
        client = flask_app.test_client()

        # Create a dummy room and user, then attempt refine as anonymous -> redirected/login
        # For simplicity of this integration test, just call endpoint and expect redirect
        resp = client.post("/room/1/refine-room-proposal", data=json.dumps({}), content_type="application/json")
        # require_room_access should redirect to login for anonymous
        assert resp.status_code in (302, 303, 401, 403)


