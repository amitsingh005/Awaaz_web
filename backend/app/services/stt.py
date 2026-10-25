import logging
import httpx
from typing import Optional, Dict, Any
from app.config import SARVAM_API_KEY, SARVAM_STT_MODEL

logger = logging.getLogger("awaazweb.stt")

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


def _guess_content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".wav"):
        return "audio/wav"
    elif lower.endswith(".mp3"):
        return "audio/mpeg"
    elif lower.endswith(".aac"):
        return "audio/aac"
    elif lower.endswith(".ogg") or lower.endswith(".opus"):
        return "audio/ogg"
    elif lower.endswith(".flac"):
        return "audio/flac"
    elif lower.endswith(".m4a") or lower.endswith(".mp4"):
        return "audio/mp4"
    return "audio/webm"


async def _call_sarvam_stt(
    audio_bytes: bytes,
    filename: str,
    language_code: str,
    model: str,
    mode: Optional[str],
) -> str:
    """
    Single attempt to Sarvam STT API. Returns transcript string or raises on failure.
    """
    content_type = _guess_content_type(filename)
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
    }
    files = {"file": (filename, audio_bytes, content_type)}
    data: Dict[str, Any] = {
        "model": model,
        "language_code": language_code,
    }
    if mode:
        data["mode"] = mode

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SARVAM_STT_URL,
            headers=headers,
            files=files,
            data=data,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Sarvam STT returned {response.status_code}: {response.text[:300]}"
        )

    res_json = response.json()
    transcript = res_json.get("transcript", "").strip()
    return transcript


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language_code: str = "hi-IN",
    model: Optional[str] = None,
    mode: Optional[str] = "codemix",
) -> str:
    """
    Transcribes audio bytes using Sarvam AI Speech-to-Text (Saaras model family).
    Supports Hindi and Hinglish (codemix).

    Retry strategy:
    - Primary: requested language_code + codemix mode.
    - If empty result: retry with hi-IN + codemix (catches cases where Sarvam
      misidentifies language or returns empty on short utterances).
    - If still empty: raises RuntimeError with a user-friendly Hindi message.
    """
    if not audio_bytes:
        raise ValueError("Audio data is empty — no audio was recorded.")

    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not configured in backend/.env")

    resolved_model = model or SARVAM_STT_MODEL or "saaras:v4"
    transcript = ""

    # ── Primary attempt ──────────────────────────────────────────────────────
    try:
        transcript = await _call_sarvam_stt(
            audio_bytes, filename, language_code, resolved_model, mode
        )
        logger.info(f"Sarvam STT primary succeeded (chars={len(transcript)})")
    except Exception as e:
        logger.warning(f"Sarvam STT primary attempt failed: {e}")

    # ── Retry if transcript is empty / suspiciously short (< 3 chars) ────────
    if not transcript or len(transcript) < 3:
        logger.info(
            "Sarvam STT: transcript empty or too short — retrying with hi-IN codemix"
        )
        try:
            transcript = await _call_sarvam_stt(
                audio_bytes, filename, "hi-IN", "saaras:v4", "codemix"
            )
            logger.info(f"Sarvam STT retry succeeded (chars={len(transcript)})")
        except Exception as e:
            logger.warning(f"Sarvam STT retry also failed: {e}")

    # ── Final guard ──────────────────────────────────────────────────────────
    if not transcript:
        raise RuntimeError(
            "Sarvam AI aawaz ko samajh nahi paya. "
            "Kripya saaf awaaz mein Hindi ya Hinglish mein bolein aur dobara try karein."
        )

    logger.info(f"Final transcript: {transcript[:80]}")
    return transcript
