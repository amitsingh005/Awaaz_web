import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def test_voice_endpoint_mock():
    # 1. Create a session
    sess_res = client.post("/api/session")
    assert sess_res.status_code == 200
    session_id = sess_res.json()["session_id"]

    # 2. Mock transcribe_audio to verify multipart form handler and response contract
    with patch("app.routes.voice.transcribe_audio") as mock_stt:
        mock_stt.return_value = "Delhi se Bhopal train"

        audio_content = b"RIFF....WAVEfmt ...."
        files = {
            "audio": ("input.webm", io.BytesIO(audio_content), "audio/webm")
        }
        data = {
            "session_id": session_id
        }

        res = client.post("/api/voice", data=data, files=files)
        assert res.status_code == 200
        reply = res.json()
        assert reply["transcript"] == "Delhi se Bhopal train"
        assert len(reply["reply_text"]) > 0
        assert "Bhopal" in reply["reply_text"]
        assert reply["state"] == "done"
        assert len(reply["options"]) > 0
