import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.stream_manager import stream_manager

client = TestClient(app)

def test_browser_state_endpoint():
    # 1. Create a session
    sess_res = client.post("/api/session")
    assert sess_res.status_code == 200
    session_id = sess_res.json()["session_id"]

    # 2. Check initial browser state
    state_res = client.get(f"/api/session/{session_id}/browser-state")
    assert state_res.status_code == 200
    data = state_res.json()
    assert data["session_id"] == session_id
    assert data["status"] == "idle"
    assert isinstance(data["steps"], list)

    # 3. Simulate broadcasting an action step
    stream_manager.broadcast_sync(session_id, "step", {
        "id": "step-test-1",
        "action": "navigate",
        "description": "Opening https://www.example.com",
        "status": "completed",
        "verification_status": "verified",
    })
    stream_manager.broadcast_sync(session_id, "browser_stream", {
        "url": "https://www.example.com",
        "streaming_url": None,
        "title": "Example Domain",
    })

    # 4. Verify updated browser state
    updated_res = client.get(f"/api/session/{session_id}/browser-state")
    assert updated_res.status_code == 200
    updated_data = updated_res.json()
    assert updated_data["current_url"] == "https://www.example.com"
    assert len(updated_data["steps"]) >= 1
    assert updated_data["steps"][-1]["id"] == "step-test-1"

def test_stop_endpoint():
    # 1. Create a session
    sess_res = client.post("/api/session")
    assert sess_res.status_code == 200
    session_id = sess_res.json()["session_id"]

    # 2. Call stop endpoint
    stop_res = client.post(f"/api/session/{session_id}/stop")
    assert stop_res.status_code == 200
    data = stop_res.json()
    assert data["status"] == "stopped"

    # 3. Check that state is cancelled/idle
    state_res = client.get(f"/api/session/{session_id}/browser-state")
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert state_data["status"] == "cancelled"
