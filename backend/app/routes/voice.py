import logging
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from pydantic import BaseModel

from app.services.stt import transcribe_audio
from app.services.tts import synthesize_speech, synthesize_speech_base64
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
from app.services.stream_manager import stream_manager
from app.routes.confirm import confirm_action, ConfirmRequest

logger = logging.getLogger("awaazweb.voice")

router = APIRouter(prefix="/api", tags=["Voice & Text"])


class TextRequest(BaseModel):
    session_id: Optional[str] = None
    text: str


class ReplyResponse(BaseModel):
    transcript: str
    reply_text: str
    state: str
    options: List[str] = []
    pending_action: Optional[Dict[str, Any]] = None
    narration: List[str] = []
    audio_base64: Optional[str] = None
    session_id: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    language_code: Optional[str] = "hi-IN"
    speaker: Optional[str] = None
    pace: Optional[float] = 1.0
    format: Optional[str] = "audio"  # "audio" -> audio/wav, "json" -> {"audio_base64": ...}


class STTResponse(BaseModel):
    transcript: str
    language_code: str = "hi-IN"


async def _attach_audio(resp: ReplyResponse) -> ReplyResponse:
    """Attaches Sarvam TTS generated audio to the response if reply_text is present."""
    if resp.reply_text and not resp.audio_base64:
        try:
            resp.audio_base64 = await synthesize_speech_base64(resp.reply_text)
        except Exception as e:
            logger.warning(f"Voice synthesis in response failed (non-fatal): {e}")
    return resp


async def _orchestrate_intent(session_id: str, user_text: str) -> ReplyResponse:
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

    # 1. Check special voice commands (Interrupts 'ruko', 'kahan hoon', 'dobara bolo', 'wapas jao')
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
        elif cmd == "stop":
            session_manager.update_session(session_id, {
                "state": "idle",
                "pending_action": None,
                "last_reply": "Thik hai, maine process rok diya hai.",
            })
            session_manager.log_action(session_id, "User interrupted with 'ruko'", "warning")
            return ReplyResponse(
                transcript=user_text,
                reply_text="Thik hai, maine process rok diya hai. Aap naya aadesh de sakte hain.",
                state="idle",
                options=["Delhi se Bhopal train", "Mausam check karo"],
                narration=["Interrupted by user ('ruko')", "Process halted"],
            )
        elif cmd == "undo":
            last_action = session_manager.pop_undo_action(session_id)
            if not last_action:
                return ReplyResponse(
                    transcript=user_text,
                    reply_text="Wapas jane ke liye koi pichhla kadam nahi mila.",
                    state="done",
                    options=["Delhi se Bhopal train", "Mausam check karo"],
                    narration=["No action to undo"],
                )
            desc = last_action.get("description", "previous action")
            if last_action.get("before_state"):
                session_manager.update_session(session_id, last_action["before_state"])
            session_manager.log_action(session_id, f"Undid action via voice command: {desc}", "warning")
            return ReplyResponse(
                transcript=user_text,
                reply_text=f"Pichhla kadam undo kar diya gaya: {desc}.",
                state="done",
                options=["Nayi request bolein", "Status dekho"],
                narration=[f"Undid action: {desc}"],
            )
        else:
            return ReplyResponse(
                transcript=user_text,
                reply_text=special.get("reply_text", "Aap AwaazWeb par hain."),
                state="done",
                options=["Delhi se Bhopal train", "Mausam check karo", "Wapas jao"],
                narration=[f"Special command: {cmd}"],
            )

    # 2. Spoken confirmation resolution if pending action exists
    if session.get("pending_action") and session.get("state") == "needs_confirmation":
        decision = parse_spoken_confirmation(user_text)
        if decision is True:
            # approval path
            confirm_req = ConfirmRequest(session_id=session_id, approved=True)
            confirm_res = await confirm_action(confirm_req)
            return ReplyResponse(
                transcript=user_text,
                reply_text=confirm_res.reply_text,
                state=confirm_res.state,
                options=confirm_res.options,
                pending_action=None,
                narration=[
                    f"Spoken response detected: '{user_text}'",
                    "Safety decision: APPROVED",
                ],
            )
        elif decision is False:
            # rejection path
            confirm_req = ConfirmRequest(session_id=session_id, approved=False)
            confirm_res = await confirm_action(confirm_req)
            return ReplyResponse(
                transcript=user_text,
                reply_text=confirm_res.reply_text,
                state=confirm_res.state,
                options=confirm_res.options,
                pending_action=None,
                narration=[
                    f"Spoken response detected: '{user_text}'",
                    "Safety decision: CANCELLED",
                ],
            )
        else:
            # ambiguous – re‑prompt for explicit confirmation
            prompt = session.get("last_reply") or format_confirmation_prompt(session["pending_action"]["step"])
            return ReplyResponse(
                transcript=user_text,
                reply_text=prompt,
                state="needs_confirmation",
                options=["Haan", "Nahi"],
                pending_action=session["pending_action"],
                narration=["Awaiting clear confirmation (Haan/Nahi)"],
            )

    narration: List[str] = []
    task_id = str(uuid.uuid4())[:8]

    stream_manager.broadcast_sync(session_id, "status", {
        "status": "working",
        "task_id": task_id,
        "original_command": user_text,
        "current_action": "Analyzing intent & generating plan",
        "verification_status": "unverified",
    })

    # 3. Planning
    plan = generate_plan(user_text)
    narration.append(f"Plan: {plan.goal} (Mode: {plan.mode.upper()})")
    session_manager.log_action(session_id, f"Plan generated: {plan.goal} [{plan.mode}]")

    stream_manager.broadcast_sync(session_id, "step", {
        "id": f"step-{task_id}-plan",
        "action": "plan",
        "description": f"Plan: {plan.goal} (Mode: {plan.mode.upper()})",
        "status": "completed",
        "verification_status": "verified",
    })

    # 4. Deterministic Safety Gate Check
    # Check both plan steps and goal for risky or sensitive actions
    risky_step = next((s for s in plan.steps if s.risky or is_action_risky(s.description)), None)
    if not risky_step and is_action_risky(plan.goal):
        risky_step = plan.steps[0] if plan.steps else None

    # Check for OTP / Captcha / Passwords
    if requires_user_credentials(user_text) or (risky_step and requires_user_credentials(risky_step.description)):
        session_manager.update_session(session_id, {"state": "needs_user_input"})
        session_manager.log_action(session_id, "Handoff: User credentials/OTP required", "warning")

        stream_manager.broadcast_sync(session_id, "status", {
            "status": "needs_user_input",
            "task_id": task_id,
            "original_command": user_text,
            "current_action": "Paused for manual OTP / Captcha entry",
            "verification_status": "held_for_credentials",
        })
        stream_manager.broadcast_sync(session_id, "step", {
            "id": f"step-{task_id}-creds",
            "action": "credentials_handoff",
            "description": "Sensitive credentials / OTP detected - paused for user screen input",
            "status": "pending",
            "verification_status": "held_for_credentials",
        })

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
            "pending_action": {"goal": plan.goal, "step": action_name, "query_or_url": plan.query_or_url},
            "last_reply": confirmation_prompt,
            "last_options": ["Haan (Pushti)", "Nahi (Cancel)"],
        })
        session_manager.log_action(session_id, f"Safety Gate blocked action: {action_name}", "warning")
        narration.append(f"SAFETY GATE BLOCKED: Awaiting voice confirmation for '{action_name}'")

        stream_manager.broadcast_sync(session_id, "status", {
            "status": "needs_confirmation",
            "task_id": task_id,
            "original_command": user_text,
            "current_action": f"Safety Gate Held: Requires confirmation to execute '{action_name}'",
            "verification_status": "held_by_safety",
        })
        stream_manager.broadcast_sync(session_id, "step", {
            "id": f"step-{task_id}-gate",
            "action": "safety_gate",
            "description": f"Safety Gate Held: Requires confirmation for '{action_name}'",
            "status": "pending",
            "verification_status": "held_by_safety",
        })

        return ReplyResponse(
            transcript=user_text,
            reply_text=confirmation_prompt,
            state="needs_confirmation",
            options=["Haan", "Nahi"],
            pending_action={"goal": plan.goal, "step": action_name, "query_or_url": plan.query_or_url},
            narration=narration,
        )

    # 5. Read Mode Execution (Search + Fetch + Hinglish Summarize)
    narration.append(f"Web search: '{plan.query_or_url}'")
    stream_manager.broadcast_sync(session_id, "status", {
        "status": "working",
        "task_id": task_id,
        "original_command": user_text,
        "current_action": f"Web search for: {plan.query_or_url}",
        "verification_status": "in_progress",
    })
    stream_manager.broadcast_sync(session_id, "step", {
        "id": f"step-{task_id}-search",
        "action": "search",
        "description": f"Searching: '{plan.query_or_url}'",
        "status": "completed",
        "verification_status": "verified",
    })

    search_results = perform_search(plan.query_or_url, max_results=3)

    page_text = ""
    if search_results and search_results[0].get("url"):
        top_url = search_results[0]["url"]
        if top_url.startswith("http"):
            narration.append(f"Reading page: {top_url[:40]}...")
            stream_manager.broadcast_sync(session_id, "browser_stream", {
                "url": top_url,
                "streaming_url": None,
                "title": search_results[0].get("title", top_url),
            })
            stream_manager.broadcast_sync(session_id, "step", {
                "id": f"step-{task_id}-read",
                "action": "navigate",
                "description": f"Navigating to {top_url}",
                "status": "completed",
                "verification_status": "verified",
            })
            # Trigger fresh screenshot capture of the actual rendered website
            try:
                import asyncio
                from app.routes.session import capture_verified_screenshot
                asyncio.create_task(capture_verified_screenshot(session_id, top_url))
            except Exception as e_shot:
                logger.debug(f"Async screenshot trigger skipped: {e_shot}")

            page_text = fetch_page_content(top_url, max_chars=1500)
    elif plan.query_or_url.startswith("http"):
        direct_url = plan.query_or_url
        stream_manager.broadcast_sync(session_id, "browser_stream", {
            "url": direct_url,
            "streaming_url": None,
            "title": direct_url,
        })
        try:
            import asyncio
            from app.routes.session import capture_verified_screenshot
            asyncio.create_task(capture_verified_screenshot(session_id, direct_url))
        except Exception:
            pass

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

    stream_manager.broadcast_sync(session_id, "status", {
        "status": "completed",
        "task_id": task_id,
        "original_command": user_text,
        "current_action": "Completed",
        "final_result": summary.reply_text,
    })

    return ReplyResponse(
        transcript=user_text,
        reply_text=summary.reply_text,
        state="done",
        options=summary.options,
        pending_action=None,
        narration=narration,
    )


async def process_user_intent(session_id: str, user_text: str) -> ReplyResponse:
    """
    Executes intent orchestration and attaches Sarvam AI synthesized TTS audio.
    """
    res = await _orchestrate_intent(session_id, user_text)
    res.session_id = session_id
    return await _attach_audio(res)


@router.post("/stt", response_model=STTResponse)
async def process_stt(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    language_code: Optional[str] = Form("hi-IN"),
):
    """
    Accepts recorded voice audio and converts speech to text using Sarvam AI Saaras model.
    Supports Hindi and Hinglish.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received")

    transcript = await transcribe_audio(
        audio_bytes,
        filename=audio.filename or "audio.webm",
        language_code=language_code or "hi-IN",
    )
    if session_id:
        session_manager.log_action(session_id, f"STT transcript: {transcript}", "user")

    return STTResponse(transcript=transcript, language_code=language_code or "hi-IN")


@router.post("/tts")
async def process_tts(request: TTSRequest):
    """
    Synthesizes speech from text using Sarvam AI Bulbul model.
    Returns either raw audio/wav binary or JSON payload with base64 audio.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if request.format == "json":
        audio_b64 = await synthesize_speech_base64(
            text=text,
            language_code=request.language_code or "hi-IN",
            speaker=request.speaker,
            pace=request.pace or 1.0,
        )
        return {"audio_base64": audio_b64, "text": text}
    else:
        audio_bytes = await synthesize_speech(
            text=text,
            language_code=request.language_code or "hi-IN",
            speaker=request.speaker,
            pace=request.pace or 1.0,
        )
        return Response(content=audio_bytes, media_type="audio/wav")


@router.get("/tts")
async def stream_tts(
    text: str,
    language_code: Optional[str] = "hi-IN",
    speaker: Optional[str] = None,
    pace: Optional[float] = 1.0,
):
    """
    GET endpoint to stream synthesized audio directly in browser audio elements.
    """
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    audio_bytes = await synthesize_speech(
        text=clean_text,
        language_code=language_code or "hi-IN",
        speaker=speaker,
        pace=pace or 1.0,
    )
    return Response(content=audio_bytes, media_type="audio/wav")


@router.post("/voice", response_model=ReplyResponse)
async def process_voice(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
):
    """
    Accepts recorded voice audio, transcribes it via Sarvam AI Saaras STT,
    executes autonomous browsing plan with safety gate protection,
    and returns synthesized Hindi/Hinglish voice response with Sarvam AI Bulbul TTS.
    """
    if not session_id or not session_manager.get_session(session_id):
        session_id = session_manager.create_session()

    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file received")

        # 1. Transcribe with Sarvam AI Saaras (with built-in retry on empty)
        try:
            transcript = await transcribe_audio(audio_bytes, filename=audio.filename or "audio.webm")
        except RuntimeError as stt_err:
            # STT failed after retries — respond gracefully in Hindi
            logger.warning(f"STT failed with RuntimeError: {stt_err}")
            stt_fail_msg = str(stt_err) if str(stt_err).strip() else \
                "Sarvam AI aawaz nahi pehchaan paya. Kripya dobara bolein."
            err_reply = ReplyResponse(
                transcript="",
                reply_text=stt_fail_msg,
                state="error",
                options=["Dobara bolein", "Text mein likho"],
                pending_action=None,
                narration=[f"STT fallback: {str(stt_err)}"],
                session_id=session_id,
            )
            return await _attach_audio(err_reply)

        if not transcript or len(transcript) < 2:
            transcript = "Kuch sunai nahi diya"

        session_manager.log_action(session_id, f"Voice transcribed: {transcript}", "user")

        # 2. Orchestrate web browsing, safety gate, & Hinglish summary + Sarvam TTS
        return await process_user_intent(session_id, transcript)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        session_manager.log_action(session_id, f"Voice error: {str(e)}", "error")
        err_reply = ReplyResponse(
            transcript="",
            reply_text="Thoda ruko, system busy hai. Kripya thodi der baad dobara bole.",
            state="error",
            options=["Dobara bolein"],
            pending_action=None,
            narration=[f"Error: {str(e)}"],
        )
        return await _attach_audio(err_reply)


@router.post("/text", response_model=ReplyResponse)
async def process_text(request: TextRequest):
    """
    Accepts typed text input for testing the complete pipeline without a microphone.
    """
    session_id = request.session_id
    if not session_id or not session_manager.get_session(session_id):
        session_id = session_manager.create_session()
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
        err_reply = ReplyResponse(
            transcript=text,
            reply_text="Thoda ruko, system busy hai.",
            state="error",
            options=[],
            pending_action=None,
            narration=[f"Error: {str(e)}"],
        )
        return await _attach_audio(err_reply)

