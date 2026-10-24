from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.history import session_manager

router = APIRouter(prefix="/api/session", tags=["Session"])


class SessionCreateResponse(BaseModel):
    session_id: str


class ReplyResponse(BaseModel):
    transcript: str
    reply_text: str
    state: str
    options: List[str] = []
    pending_action: Optional[Dict[str, Any]] = None
    narration: List[str] = []


@router.post("", response_model=SessionCreateResponse)
async def create_session():
    """Create a new conversational session."""
    session_id = session_manager.create_session()
    session_manager.log_action(
        session_id,
        "Session initialized",
        log_type="info",
        before_state=None,
        after_state={"state": "idle", "agent_runs": 0},
    )
    return {"session_id": session_id}


@router.get("/{session_id}/log")
async def get_session_log(session_id: str):
    """Retrieve logged actions and state transitions for a session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "agent_runs": session.get("agent_runs", 0),
        "undo_available": len(session.get("undo_stack", [])) > 0,
        "logs": session_manager.get_logs(session_id),
    }


@router.post("/{session_id}/undo", response_model=ReplyResponse)
async def undo_last_action(session_id: str):
    """Undo the last reversible action in the session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    last_action = session_manager.pop_undo_action(session_id)
    if not last_action:
        return ReplyResponse(
            transcript="wapas jao",
            reply_text="Wapas jane ke liye koi pichhla kadam nahi mila.",
            state="done",
            options=["Delhi se Bhopal train", "Mausam check karo"],
            pending_action=None,
            narration=["No reversible action to undo"],
        )

    desc = last_action.get("description", "previous action")
    before_state = last_action.get("before_state")

    # Restore before_state if available
    if before_state:
        session_manager.update_session(session_id, before_state)

    session_manager.log_action(
        session_id,
        f"Undid action: {desc}",
        log_type="warning",
        before_state=last_action.get("after_state"),
        after_state=before_state,
    )

    reply_text = f"Pichhla kadam undo kar diya gaya: {desc}."
    return ReplyResponse(
        transcript="wapas jao",
        reply_text=reply_text,
        state="done",
        options=["Nayi request bolein", "Status dekho"],
        pending_action=None,
        narration=[f"Reverted action: {desc}"],
    )
