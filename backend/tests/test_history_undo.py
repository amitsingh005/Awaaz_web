import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.history import session_manager
from app.services.browser import get_or_create_browser_profile

client = TestClient(app)

def test_action_log_with_state_snapshots():
    session_id = session_manager.create_session()
    session_manager.log_action(
        session_id=session_id,
        message="Search triggered",
        log_type="info",
        before_state={"state": "idle"},
        after_state={"state": "working"},
    )
    logs = session_manager.get_logs(session_id)
    assert len(logs) >= 1
    last_log = logs[-1]
    assert last_log["message"] == "Search triggered"
    assert last_log["before_state"] == {"state": "idle"}
    assert last_log["after_state"] == {"state": "working"}

def test_undo_stack_and_reversal():
    session_id = session_manager.create_session()
    # Push an action to undo stack
    session_manager.push_undo_action(
        session_id=session_id,
        action_type="fill_form",
        description="Filled passenger details",
        before_state={"state": "idle", "last_field": ""},
        after_state={"state": "done", "last_field": "passenger_name"},
    )

    # 1. Test via endpoint
    undo_res = client.post(f"/api/session/{session_id}/undo")
    assert undo_res.status_code == 200
    undo_data = undo_res.json()
    assert undo_data["state"] == "done"
    assert "undo kar diya gaya" in undo_data["reply_text"]
    assert "Filled passenger details" in undo_data["reply_text"]

    # 2. Second undo when stack is empty
    empty_undo_res = client.post(f"/api/session/{session_id}/undo")
    assert empty_undo_res.status_code == 200
    assert "koi pichhla kadam nahi mila" in empty_undo_res.json()["reply_text"]

def test_voice_interruption_ruko():
    session_id = session_manager.create_session()
    # Set session in working / confirmation state
    session_manager.update_session(session_id, {
        "state": "needs_confirmation",
        "pending_action": {"goal": "Test goal", "step": "Test step"},
    })

    # User says 'ruko'
    res = client.post(
        "/api/text",
        json={"session_id": session_id, "text": "ruko, mat karo"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["state"] == "idle"
    assert "rok diya hai" in data["reply_text"]

    # Verify pending action was cleared
    session = session_manager.get_session(session_id)
    assert session["pending_action"] is None
    assert session["state"] == "idle"

def test_browser_context_profiles():
    session_id = session_manager.create_session()
    p1 = get_or_create_browser_profile("IRCTC", session_id)
    assert p1 is not None
    assert "irctc" in p1

    # Calling again for same service in same session returns same profile ID
    p2 = get_or_create_browser_profile("IRCTC", session_id)
    assert p1 == p2

    # Session log API returns profile info
    log_res = client.get(f"/api/session/{session_id}/log")
    assert log_res.status_code == 200
    log_data = log_res.json()
    assert "session_id" in log_data
    assert "logs" in log_data
