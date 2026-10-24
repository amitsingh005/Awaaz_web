import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.safety import (
    is_action_risky,
    requires_user_credentials,
    parse_spoken_confirmation,
)

client = TestClient(app)

def test_deterministic_safety_rules():
    # Risky actions must always return True
    assert is_action_risky("Pay electricity bill of 850 INR") is True
    assert is_action_risky("Book Shatabdi express train ticket") is True
    assert is_action_risky("Submit government subsidy application form") is True
    assert is_action_risky("Delete my user profile and stored history") is True
    assert is_action_risky("Send confirmation email to applicant") is True

    # Safe read-only actions must always return False
    assert is_action_risky("Search trains from Delhi to Bhopal") is False
    assert is_action_risky("Read current weather in Mumbai") is False
    assert is_action_risky("Compare prices for headphones on Flipkart") is False
    assert is_action_risky("View train seat availability") is False

def test_credentials_detection():
    assert requires_user_credentials("Enter OTP received on phone") is True
    assert requires_user_credentials("Solve captcha on screen") is True
    assert requires_user_credentials("Enter bank password") is True
    assert requires_user_credentials("Check train timing") is False

def test_spoken_confirmation_parser():
    # Affirmatives
    assert parse_spoken_confirmation("Haan") is True
    assert parse_spoken_confirmation("ha, aage badho") is True
    assert parse_spoken_confirmation("yes, please proceed") is True
    assert parse_spoken_confirmation("kar do") is True
    assert parse_spoken_confirmation("theek hai") is True

    # Negatives
    assert parse_spoken_confirmation("Nahi") is False
    assert parse_spoken_confirmation("no, cancel it") is False
    assert parse_spoken_confirmation("mat karo") is False
    assert parse_spoken_confirmation("cancel") is False
    assert parse_spoken_confirmation("ruko, mat karo") is False

    # Ambiguous
    assert parse_spoken_confirmation("Delhi train schedule") is None

def test_safety_gate_blocking_and_voice_confirmation_flow():
    # 1. Create a fresh session
    sess_res = client.post("/api/session")
    session_id = sess_res.json()["session_id"]

    # 2. Issue a risky command
    risky_res = client.post(
        "/api/text",
        json={"session_id": session_id, "text": "Electricity bill ₹850 pay kar do"},
    )
    assert risky_res.status_code == 200
    risky_data = risky_res.json()

    # The safety gate MUST block execution
    assert risky_data["state"] == "needs_confirmation"
    assert risky_data["pending_action"] is not None
    assert "Pushti" in risky_data["reply_text"] or "Kripya" in risky_data["reply_text"]

    # 3. User says spoken "Haan" to approve
    approve_res = client.post(
        "/api/text",
        json={"session_id": session_id, "text": "Haan, aage badho"},
    )
    assert approve_res.status_code == 200
    approve_data = approve_res.json()
    assert approve_data["state"] == "done"
    assert approve_data["pending_action"] is None
    assert "pushti" in approve_data["reply_text"].lower()

def test_safety_gate_cancellation_flow():
    # 1. Create a fresh session
    sess_res = client.post("/api/session")
    session_id = sess_res.json()["session_id"]

    # 2. Issue a risky command
    client.post(
        "/api/text",
        json={"session_id": session_id, "text": "Ticket book kar do"},
    )

    # 3. User cancels via /api/confirm with approved=False
    cancel_res = client.post(
        "/api/confirm",
        json={"session_id": session_id, "approved": False},
    )
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["state"] == "done"
    assert cancel_data["pending_action"] is None
    assert "cancel" in cancel_data["reply_text"].lower()
