import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.browser import execute_agent_action
from app.services.history import session_manager
from app.config import MAX_AGENT_RUNS_PER_SESSION

client = TestClient(app)

def test_agent_action_streaming_narration():
    session_id = session_manager.create_session()
    result = execute_agent_action(
        goal="Open booking form and fill name",
        start_url="https://example.com/booking",
        session_id=session_id,
    )
    assert result["status"] == "done"
    assert len(result["narration"]) >= 2
    assert any("site khol raha hoon" in n for n in result["narration"])

def test_agent_run_cap_enforcement():
    session_id = session_manager.create_session()
    session = session_manager.get_session(session_id)

    # Set session agent_runs directly to the maximum cap
    session["agent_runs"] = MAX_AGENT_RUNS_PER_SESSION
    session_manager.save_session(session_id, session)

    # Attempting another agent run must be capped
    capped_result = execute_agent_action(
        goal="Submit additional form",
        start_url="https://example.com",
        session_id=session_id,
    )
    assert capped_result["status"] == "limit_reached"
    assert "limit" in capped_result["reply_text"].lower() or "limit" in capped_result["narration"][0].lower()

def test_otp_captcha_handoff():
    session_id = session_manager.create_session()
    otp_result = execute_agent_action(
        goal="Enter OTP received on phone",
        start_url="https://example.com/verify",
        session_id=session_id,
    )
    assert otp_result["status"] == "needs_user_input"
    assert "otp" in otp_result["reply_text"].lower() or "captcha" in otp_result["reply_text"].lower()

def test_e2e_confirmation_and_agent_action_flow():
    # 1. Create session
    sess_res = client.post("/api/session")
    session_id = sess_res.json()["session_id"]

    # 2. Issue risky request
    client.post(
        "/api/text",
        json={"session_id": session_id, "text": "Train ticket book kar do"},
    )

    # 3. Confirm via /api/confirm
    confirm_res = client.post(
        "/api/confirm",
        json={"session_id": session_id, "approved": True},
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["state"] == "done"
    assert len(confirm_data["narration"]) >= 2
