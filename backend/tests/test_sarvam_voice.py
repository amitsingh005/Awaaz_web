import io
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.tts import clean_text_for_speech, synthesize_speech_base64
from app.services.stt import transcribe_audio

client = TestClient(app)


def test_clean_text_for_speech():
    raw = "Here is the result: **[Google Search](https://google.com)** for `#train` tickets!"
    cleaned = clean_text_for_speech(raw)
    assert "https://" not in cleaned
    assert "**" not in cleaned
    assert "#" not in cleaned
    assert "Google Search" in cleaned
    assert "train" in cleaned


@pytest.mark.anyio
async def test_transcribe_audio_empty():
    with pytest.raises(ValueError, match="Audio data is empty"):
        await transcribe_audio(b"")


def test_api_tts_json_endpoint():
    res = client.post("/api/tts", json={"text": "Namaste", "format": "json"})
    assert res.status_code == 200
    data = res.json()
    assert "audio_base64" in data
    assert len(data["audio_base64"]) > 100
    assert data["text"] == "Namaste"


def test_api_tts_audio_endpoint():
    res = client.post("/api/tts", json={"text": "Namaste", "format": "audio"})
    assert res.status_code == 200
    assert res.headers.get("content-type") == "audio/wav"
    assert len(res.content) > 100


def test_api_tts_get_stream_endpoint():
    res = client.get("/api/tts?text=Mausam+kaisa+hai")
    assert res.status_code == 200
    assert res.headers.get("content-type") == "audio/wav"
    assert len(res.content) > 100


def test_api_stt_endpoint():
    # 1. Synthesize audio via Sarvam TTS to get valid audio bytes
    tts_res = client.post("/api/tts", json={"text": "Delhi se Bhopal train", "format": "audio"})
    assert tts_res.status_code == 200
    audio_wav = tts_res.content

    # 2. Send to STT endpoint
    files = {"audio": ("sample.wav", io.BytesIO(audio_wav), "audio/wav")}
    stt_res = client.post("/api/stt", files=files)
    assert stt_res.status_code == 200
    data = stt_res.json()
    assert "transcript" in data
    assert len(data["transcript"]) > 0
    assert data["language_code"] == "hi-IN"


def test_api_voice_full_pipeline_mocked():
    """Verify multipart voice form processing and response with Sarvam AI audio_base64."""
    # 1. Create session
    s_res = client.post("/api/session")
    assert s_res.status_code == 200
    sid = s_res.json()["session_id"]

    # 2. Mock STT transcript
    with patch("app.routes.voice.transcribe_audio", new_callable=AsyncMock) as mock_stt:
        mock_stt.return_value = "Delhi se Bhopal train dhundho"

        files = {"audio": ("input.webm", io.BytesIO(b"RIFFdummywavecontent1234"), "audio/webm")}
        data = {"session_id": sid}

        res = client.post("/api/voice", data=data, files=files)
        assert res.status_code == 200
        reply = res.json()
        assert reply["transcript"] == "Delhi se Bhopal train dhundho"
        assert len(reply["reply_text"]) > 0
        assert reply["state"] == "done"
        assert "audio_base64" in reply
        # Audio is synthesized with Sarvam Bulbul
        assert reply["audio_base64"] is not None
        assert len(reply["audio_base64"]) > 100
