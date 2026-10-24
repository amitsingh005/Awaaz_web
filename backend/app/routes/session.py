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
    session_manager.log_action(session_id, "Session initialized")
    return {"session_id": session_id}

@router.get("/{session_id}/log")
async def get_session_log(session_id: str):
    """Retrieve logged actions and traces for a session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"logs": session_manager.get_logs(session_id)}

@router.post("/{session_id}/undo", response_model=ReplyResponse)
async def undo_last_action(session_id: str):
    """Undo the last reversible action in the session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    undo_stack = session.get("undo_stack", [])
    if not undo_stack:
        return ReplyResponse(
            transcript="wapas jao",
            reply_text="Wapas jane ke liye koi pichhla kadam nahi mila.",
            state="done",
            options=[],
            pending_action=None,
            narration=["No reversible action to undo"]
        )

    last_action = undo_stack.pop()
    session_manager.save_session(session_id, session)
    session_manager.log_action(session_id, f"Undid action: {last_action.get('description', 'previous action')}", "warning")

    return ReplyResponse(
        transcript="wapas jao",
        reply_text=f"Pichhla kadam undo kar diya gaya: {last_action.get('description', '')}.",
        state="done",
        options=[],
        pending_action=None,
        narration=["Undid previous action"]
    )
