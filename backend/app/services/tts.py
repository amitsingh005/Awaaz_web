import re
import base64
import logging
import httpx
from typing import Optional, Dict, Any, Tuple
from app.config import SARVAM_API_KEY, SARVAM_TTS_MODEL, SARVAM_TTS_SPEAKER

logger = logging.getLogger("awaazweb.tts")

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


def clean_text_for_speech(text: str) -> str:
    """
    Strips markdown formatting, code snippets, URLs, and noisy symbols
    to ensure natural spoken narration in Hindi/Hinglish.
    """
    if not text:
        return ""

    # Replace markdown links [title](url) with title
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove raw URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove markdown asterisks, backticks, underscores, hash headers
    cleaned = re.sub(r"[*`_#~>]+", " ", cleaned)
    # Normalize multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Limit to 2000 characters to safely respect Sarvam limits (max 2500)
    if len(cleaned) > 2000:
        cleaned = cleaned[:1997] + "..."

    return cleaned


async def synthesize_speech_base64(
    text: str,
    language_code: str = "hi-IN",
    speaker: Optional[str] = None,
    model: Optional[str] = None,
    pace: float = 1.0,
) -> str:
    """
    Calls Sarvam AI Text-to-Speech (Bulbul model) and returns the base64-encoded audio string.
    Supports Hindi and code-mixed Hinglish.
    """
    clean_text = clean_text_for_speech(text)
    if not clean_text:
        raise ValueError("Cannot synthesize empty text")

    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not configured in backend/.env")

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "text": clean_text,
        "language_code": language_code,
        "speaker": speaker or SARVAM_TTS_SPEAKER or "shubh",
        "model": model or SARVAM_TTS_MODEL or "bulbul:v3",
        "pace": pace,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                SARVAM_TTS_URL,
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            logger.error(f"Sarvam TTS failed ({response.status_code}): {response.text}")
            raise RuntimeError(f"Sarvam TTS failed with status {response.status_code}: {response.text}")

        res_json = response.json()
        audios = res_json.get("audios", [])
        if not audios or not audios[0]:
            raise RuntimeError("Sarvam TTS returned an empty audio list")

        audio_base64 = audios[0]
        logger.info(f"Sarvam TTS generated audio successfully (b64_len={len(audio_base64)})")
        return audio_base64

    except httpx.RequestError as e:
        logger.error(f"Sarvam TTS network error: {e}")
        raise RuntimeError(f"Sarvam TTS network error: {str(e)}")
    except Exception as e:
        logger.error(f"Sarvam TTS error: {e}")
        raise


async def synthesize_speech(
    text: str,
    language_code: str = "hi-IN",
    speaker: Optional[str] = None,
    model: Optional[str] = None,
    pace: float = 1.0,
) -> bytes:
    """
    Synthesizes speech using Sarvam AI Bulbul and returns raw audio bytes (WAV format).
    """
    b64_audio = await synthesize_speech_base64(
        text=text,
        language_code=language_code,
        speaker=speaker,
        model=model,
        pace=pace,
    )
    return base64.b64decode(b64_audio)
