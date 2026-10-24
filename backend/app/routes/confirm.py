import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.history import session_manager
from app.services.browser import execute_agent_action

logger = logging.getLogger("awaazweb.confirm")

router = APIRouter(prefix="/api/confirm", tags=["Confirmation"])


class ConfirmRequest(BaseModel):
    session_id: str
    approved: bool


class ReplyResponse(BaseModel):
    transcript: str
    reply_text: str
    state: str
    options: List[str] = []
    pending_action: Optional[Dict[str, Any]] = None
    narration: List[str] = []


@router.post("", response_model=ReplyResponse)
async def confirm_action(request: ConfirmRequest):
    """
    Explicit safety confirmation gate.
    Executes or cancels the pending risky action based on user decision.
    """
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    pending = session.get("pending_action")
    if not pending:
        return ReplyResponse(
            transcript="haan" if request.approved else "nahi",
            reply_text="Pushti ke liye koi pending action nahi mila. Aap nayi request bol sakte hain.",
            state="done",
            options=["Delhi se Bhopal train", "Mausam check karo"],
            pending_action=None,
            narration=["No pending action in session"],
        )

    action_desc = pending.get("step") or pending.get("goal") or "Action"
    start_url = pending.get("query_or_url") or "https://www.google.com"

    if request.approved:
        logger.info(f"User approved risky action: {action_desc}")
        session_manager.log_action(
            request.session_id,
            f"Voice confirmed: {action_desc}",
            "warning",
        )

        # Execute agent action
        exec_res = execute_agent_action(
            goal=action_desc,
            start_url=start_url,
            session_id=request.session_id,
        )

        narration = [
            f"Approved by user: {action_desc}",
            "Safety gate passed",
        ] + exec_res.get("narration", [])

        if exec_res.get("status") == "needs_user_input":
            session["state"] = "needs_user_input"
            session["pending_action"] = None
            session_manager.save_session(request.session_id, session)
            return ReplyResponse(
                transcript="haan",
                reply_text=exec_res.get("reply_text", "OTP ya Captcha darj karein."),
                state="needs_user_input",
                options=["OTP enter kar diya", "Cancel"],
                pending_action=None,
                narration=narration,
            )

        if exec_res.get("status") == "limit_reached":
            session["state"] = "done"
            session["pending_action"] = None
            session_manager.save_session(request.session_id, session)
            return ReplyResponse(
                transcript="haan",
                reply_text=exec_res.get("reply_text"),
                state="done",
                options=["Naya session shuru karein"],
                pending_action=None,
                narration=narration,
            )

        # Record into undo stack if reversible
        undo_entry = {
            "type": "browser_action",
            "description": action_desc,
            "data": pending,
        }
        session.setdefault("undo_stack", []).append(undo_entry)
        session["pending_action"] = None
        session["state"] = "done"

        reply_text = f"Aapki pushti mil gayi hai. '{action_desc}' safalta se pura kiya gaya."
        session["last_reply"] = reply_text
        session_manager.save_session(request.session_id, session)

        return ReplyResponse(
            transcript="haan",
            reply_text=reply_text,
            state="done",
            options=["Nayi khoj karo", "Wapas jao"],
            pending_action=None,
            narration=narration,
        )
    else:
        logger.info(f"User rejected risky action: {action_desc}")
        session_manager.log_action(
            request.session_id,
            f"Action cancelled by user: {action_desc}",
            "info",
        )

        session["pending_action"] = None
        session["state"] = "done"
        reply_text = f"Theek hai, maine '{action_desc}' cancel kar diya hai. Kuch aur karna ho toh bolein."
        session["last_reply"] = reply_text
        session_manager.save_session(request.session_id, session)

        return ReplyResponse(
            transcript="nahi",
            reply_text=reply_text,
            state="done",
            options=["Delhi se Bhopal train", "Wapas jao"],
            pending_action=None,
            narration=[
                f"Cancelled by user: {action_desc}",
                "Safety gate closed action",
            ],
        )
