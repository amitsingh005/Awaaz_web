import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_session_lifecycle():
    # 1. Create session
    create_res = client.post("/api/session")
    assert create_res.status_code == 200
    data = create_res.json()
    assert "session_id" in data
    session_id = data["session_id"]

    # 2. Process text input
    text_res = client.post("/api/text", json={"session_id": session_id, "text": "Delhi se Bhopal train dhundho"})
    assert text_res.status_code == 200
    text_data = text_res.json()
    assert text_data["transcript"] == "Delhi se Bhopal train dhundho"
    assert "Maine samjha" in text_data["reply_text"]
    assert text_data["state"] == "done"

    # 3. Check session log
    log_res = client.get(f"/api/session/{session_id}/log")
    assert log_res.status_code == 200
    logs = log_res.json().get("logs", [])
    assert len(logs) >= 2
