import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.services.stt import transcribe_audio
from app.services.planner import generate_plan, check_special_command
from app.services.browser import perform_search, fetch_page_content
from app.services.summarizer import summarize_findings
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


async def process_user_intent(session_id: str, user_text: str) -> ReplyResponse:
    """
    Core orchestrator:
    1. Navigation special commands ("kahan hoon", "ruko", "dobara bolo", "wapas jao")
    2. Intent planning (Groq LLM)
    3. Read-only web browsing (TinyFish search & fetch)
    4. Hinglish voice preview synthesis (Groq LLM)
    """
    session = session_manager.get_session(session_id)
    if not session:
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)

    # 1. Check special voice commands
    special = check_special_command(user_text)
    if special:
        cmd = special["command"]
        if cmd == "repeat":
            last_reply = session.get("last_reply", "Koi pichhla sandesh nahi mila.")
            return ReplyResponse(
                transcript=user_text,
                reply_text=f"Maine kaha tha: {last_reply}",
                state="done",
                options=session.get("last_options", []),
                narration=["Repeated last response"],
            )
        elif cmd == "undo":
            undo_stack = session.get("undo_stack", [])
            if not undo_stack:
                return ReplyResponse(
                    transcript=user_text,
                    reply_text="Wapas jane ke liye koi pichhla kadam nahi mila.",
                    state="done",
                    options=[],
                    narration=["No action to undo"],
                )
            last_action = undo_stack.pop()
            session_manager.save_session(session_id, session)
            return ReplyResponse(
                transcript=user_text,
                reply_text=f"Pichhla kadam undo kar diya gaya.",
                state="done",
                options=[],
                narration=["Undid action"],
            )
        else:
            return ReplyResponse(
                transcript=user_text,
                reply_text=special.get("reply_text", "Aap AwaazWeb par hain."),
                state="done",
                options=["Delhi se Bhopal train", "Mausam check karo", "Wapas jao"],
                narration=[f"Special command: {cmd}"],
            )

    narration: List[str] = []

    # 2. Planning
    plan = generate_plan(user_text)
    narration.append(f"Plan: {plan.goal} (Mode: {plan.mode.upper()})")
    session_manager.log_action(session_id, f"Plan generated: {plan.goal} [{plan.mode}]")

    # 3. Read Mode: Search + Fetch + Summarize
    if plan.mode == "read":
        narration.append(f"Web search: '{plan.query_or_url}'")
        search_results = perform_search(plan.query_or_url, max_results=3)

        page_text = ""
        if search_results and search_results[0].get("url"):
            top_url = search_results[0]["url"]
            if top_url.startswith("http"):
                narration.append(f"Reading page: {top_url[:40]}...")
                page_text = fetch_page_content(top_url, max_chars=1500)

        # 4. Summarize into Hinglish preview
        narration.append("Synthesizing Hinglish voice preview...")
        summary = summarize_findings(user_text, search_results, page_text)

        session_manager.update_session(session_id, {
            "last_transcript": user_text,
            "last_reply": summary.reply_text,
            "last_options": summary.options,
            "state": "done",
        })
        session_manager.log_action(session_id, f"Voice preview: {summary.reply_text[:70]}...")

        return ReplyResponse(
            transcript=user_text,
            reply_text=summary.reply_text,
            state="done",
            options=summary.options,
            pending_action=None,
            narration=narration,
        )

    # 4. Act Mode (Preliminary handling for Phase 4; Safety gate will enforce confirmation in Phase 5)
    risky_steps = [s for s in plan.steps if s.risky]
    if risky_steps:
        narration.append(f"Action requires confirmation: {risky_steps[0].description}")
        return ReplyResponse(
            transcript=user_text,
            reply_text=f"Yeh ek mahatvapurna kadam hai: {risky_steps[0].description}. Kya main aage badhun? Bolen 'Haan' ya 'Nahi'.",
            state="needs_confirmation",
            options=["Haan", "Nahi"],
            pending_action={"goal": plan.goal, "step": risky_steps[0].description},
            narration=narration,
        )

    narration.append("Preparing action execution...")
    return ReplyResponse(
        transcript=user_text,
        reply_text=f"Maine aapka nirdesh samjha: {plan.goal}.",
        state="done",
        options=["Aage badho", "Wapas jao"],
        pending_action=None,
        narration=narration,
    )


@router.post("/voice", response_model=ReplyResponse)
async def process_voice(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
):
    """
    Accepts recorded voice audio, transcribes it via Groq Whisper,
    executes autonomous browsing plan, and returns synthesized Hinglish voice response.
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

        # 2. Orchestrate web browsing & Hinglish summary
        return await process_user_intent(session_id, transcript)

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        session_manager.log_action(session_id, f"Voice error: {str(e)}", "error")
        return ReplyResponse(
            transcript="",
            reply_text="Thoda ruko, system busy hai. Kripya thodi der baad dobara bole.",
            state="error",
            options=[],
            pending_action=None,
            narration=[f"Error: {str(e)}"],
        )


@router.post("/text", response_model=ReplyResponse)
async def process_text(request: TextRequest):
    """
    Accepts typed text input for testing the complete pipeline without a microphone.
    """
    session_id = request.session_id
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    session = session_manager.get_session(session_id)
    if not session:
        session_id = session_manager.create_session()

    session_manager.log_action(session_id, f"Text received: {text}", "user")

    try:
        return await process_user_intent(session_id, text)
    except Exception as e:
        logger.error(f"Text processing error: {e}")
        return ReplyResponse(
            transcript=text,
            reply_text="Thoda ruko, system busy hai.",
            state="error",
            options=[],
            pending_action=None,
            narration=[f"Error: {str(e)}"],
        )
