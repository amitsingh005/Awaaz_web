import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from app.services.stt import transcribe_audio
from app.services.history import session_manager

logger = logging.getLogger("awaazweb.voice")

router = APIRouter(prefix="/api", tags=["Voice & Text"])

class TextRequest(BaseModel):
    session_id: str
    text: str

class ReplyResponse(BaseModel):
    transcript: str
    reply_text: str
    state: str
    options: List[str] = []
    pending_action: Optional[Dict[str, Any]] = None
    narration: List[str] = []


@router.post("/voice", response_model=ReplyResponse)
async def process_voice(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
):
    """
    Accepts recorded voice audio, transcribes it via Groq Whisper,
    and returns conversational reply for speech synthesis.
    """
    session = session_manager.get_session(session_id)
    if not session:
        session_id = session_manager.create_session()

    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file received")

        # 1. Transcribe with Groq Whisper
        transcript = await transcribe_audio(audio_bytes, filename=audio.filename or "audio.webm")
        if not transcript:
            transcript = "Kuch sunai nahi diya"

        session_manager.log_action(session_id, f"Voice transcribed: {transcript}", "user")

        # In Phase 2: Voice loop echo validation
        reply_text = f"Maine suna: {transcript}."

        session_manager.update_session(session_id, {
            "last_transcript": transcript,
            "last_reply": reply_text,
            "state": "done",
        })

        return ReplyResponse(
            transcript=transcript,
            reply_text=reply_text,
            state="done",
            options=["Delhi se Bhopal train", "Mausam check karo", "Wapas jao"],
            pending_action=None,
            narration=["Audio received", "Whisper transcribed", "Voice loop echoed"],
        )
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        session_manager.log_action(session_id, f"Voice error: {str(e)}", "error")
        return ReplyResponse(
            transcript="",
            reply_text="Thoda ruko, aawaz sunne mein samasya aayi. Dobara koshish karein.",
            state="error",
            options=[],
            pending_action=None,
            narration=[f"Error: {str(e)}"],
        )


@router.post("/text", response_model=ReplyResponse)
async def process_text(request: TextRequest):
    """
    Accepts typed text input for testing the pipeline without a microphone.
    """
    session_id = request.session_id
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    session = session_manager.get_session(session_id)
    if not session:
        session_id = session_manager.create_session()

    session_manager.log_action(session_id, f"Text received: {text}", "user")

    # In Phase 2: Text loop echo validation
    reply_text = f"Maine samjha: {text}."

    session_manager.update_session(session_id, {
        "last_transcript": text,
        "last_reply": reply_text,
        "state": "done",
    })

    return ReplyResponse(
        transcript=text,
        reply_text=reply_text,
        state="done",
        options=["Delhi se Bhopal train", "Mausam check karo", "Wapas jao"],
        pending_action=None,
        narration=["Text input processed", "Loop echoed"],
    )
