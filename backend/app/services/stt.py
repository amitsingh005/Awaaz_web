import io
import logging
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_STT_MODEL

logger = logging.getLogger("awaazweb.stt")

# Initialize Groq client
_client = None

def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribes audio bytes using Groq Whisper.
    Tolerates Hindi and Hinglish inputs.
    """
    if not audio_bytes:
        raise ValueError("Audio data is empty")

    client = get_groq_client()
    audio_file = (filename, audio_bytes)

    try:
        # Prompt provides contextual hints for Hinglish & navigation keywords
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=GROQ_STT_MODEL,
            prompt="Hindi and Hinglish voice navigation command, e.g., train dhundho, mausam kaisa hai, ticket book karo, wapas jao",
            response_format="json",
            temperature=0.0,
        )
        transcript = transcription.text.strip()
        logger.info(f"Transcription completed (length={len(transcript)})")
        return transcript
    except Exception as e:
        logger.error(f"Groq Whisper transcription failed: {e}")
        raise RuntimeError(f"Speech transcription error: {str(e)}")
