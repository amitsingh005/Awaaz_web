import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.services.stt import transcribe_audio
from app.services.planner import generate_plan, check_special_command
from app.services.browser import perform_search, fetch_page_content
from app.services.summarizer import summarize_findings
from app.services.safety import (
    is_action_risky,
    requires_user_credentials,
    format_confirmation_prompt,
    parse_spoken_confirmation,
)
from app.services.history import session_manager
from app.routes.confirm import confirm_action, ConfirmRequest

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
    1. Check pending confirmation state & spoken Yes/No
    2. Navigation special commands ("kahan hoon", "ruko", "dobara bolo", "wapas jao")
    3. Intent planning (Groq LLM)
    4. Deterministic Safety Gate check (Blocks payment, booking, delete, send, submit)
    5. Read-only web browsing (TinyFish search & fetch)
    6. Hinglish voice preview synthesis
    """
    session = session_manager.get_session(session_id)
    if not session:
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)

    # 1. Spoken confirmation resolution if pending action exists
    if session.get("pending_action") and session.get("state") == "needs_confirmation":
        decision = parse_spoken_confirmation(user_text)
        if decision is not None:
            # Delegate directly to confirmation handler
            confirm_req = ConfirmRequest(session_id=session_id, approved=decision)
            confirm_res = await confirm_action(confirm_req)
            return ReplyResponse(
                transcript=user_text,
                reply_text=confirm_res.reply_text,
                state=confirm_res.state,
                options=confirm_res.options,
                pending_action=None,
                narration=[
                    f"Spoken response detected: '{user_text}'",
                    f"Safety decision: {'APPROVED' if decision else 'CANCELLED'}",
                ],
            )

    # 2. Check special voice commands
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
                reply_text="Pichhla kadam undo kar diya gaya.",
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

    # 3. Planning
    plan = generate_plan(user_text)
    narration.append(f"Plan: {plan.goal} (Mode: {plan.mode.upper()})")
    session_manager.log_action(session_id, f"Plan generated: {plan.goal} [{plan.mode}]")

    # 4. Deterministic Safety Gate Check
    # Check both plan steps and goal for risky or sensitive actions
    risky_step = next((s for s in plan.steps if s.risky or is_action_risky(s.description)), None)
    if not risky_step and is_action_risky(plan.goal):
        risky_step = plan.steps[0] if plan.steps else None

    # Check for OTP / Captcha / Passwords
    if requires_user_credentials(user_text) or (risky_step and requires_user_credentials(risky_step.description)):
        session_manager.update_session(session_id, {"state": "needs_user_input"})
        session_manager.log_action(session_id, "Handoff: User credentials/OTP required", "warning")
        return ReplyResponse(
            transcript=user_text,
            reply_text="Yeh process OTP ya password maang raha hai. Suraksha ke liye, ise aap khud darj karein.",
            state="needs_user_input",
            options=["OTP enter kar diya", "Cancel karo"],
            pending_action=None,
            narration=["Paused for user OTP/captcha input", "Safety handoff active"],
        )

    # If action is risky, BLOCK IT and hold for explicit confirmation
    if risky_step or plan.mode == "act":
        action_name = risky_step.description if risky_step else plan.goal
        confirmation_prompt = format_confirmation_prompt(action_name)

        session_manager.update_session(session_id, {
            "state": "needs_confirmation",
            "pending_action": {"goal": plan.goal, "step": action_name},
            "last_reply": confirmation_prompt,
            "last_options": ["Haan (Pushti)", "Nahi (Cancel)"],
        })
        session_manager.log_action(session_id, f"Safety Gate blocked action: {action_name}", "warning")
        narration.append(f"SAFETY GATE BLOCKED: Awaiting voice confirmation for '{action_name}'")

        return ReplyResponse(
            transcript=user_text,
            reply_text=confirmation_prompt,
            state="needs_confirmation",
            options=["Haan", "Nahi"],
            pending_action={"goal": plan.goal, "step": action_name},
            narration=narration,
        )

    # 5. Read Mode Execution (Search + Fetch + Hinglish Summarize)
    narration.append(f"Web search: '{plan.query_or_url}'")
    search_results = perform_search(plan.query_or_url, max_results=3)

    page_text = ""
    if search_results and search_results[0].get("url"):
        top_url = search_results[0]["url"]
        if top_url.startswith("http"):
            narration.append(f"Reading page: {top_url[:40]}...")
            page_text = fetch_page_content(top_url, max_chars=1500)

    # 6. Summarize into Hinglish preview
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


@router.post("/voice", response_model=ReplyResponse)
async def process_voice(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
):
    """
    Accepts recorded voice audio, transcribes it via Groq Whisper,
    executes autonomous browsing plan with safety gate protection,
    and returns synthesized Hinglish voice response.
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

        # 2. Orchestrate web browsing, safety gate, & Hinglish summary
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
