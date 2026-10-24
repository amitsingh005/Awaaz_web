import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import SESSIONS_DIR

class SessionManager:
    """
    Manages session state, conversation history, and reversible action stack.
    """
    def __init__(self, sessions_dir: Path = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "state": "idle",
            "last_transcript": "",
            "last_reply": "",
            "history": [],
            "action_logs": [],
            "undo_stack": [],
            "agent_runs": 0,
            "pending_action": None,
        }
        self.save_session(session_id, session_data)
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        file_path = self._get_file(session_id)
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        file_path = self._get_file(session_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            session = {
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "history": [],
                "action_logs": [],
                "undo_stack": [],
                "agent_runs": 0,
                "pending_action": None,
            }
        session.update(updates)
        self.save_session(session_id, session)
        return session

    def log_action(self, session_id: str, message: str, log_type: str = "info") -> None:
        session = self.get_session(session_id)
        if not session:
            return
        entry = {
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "message": message,
            "type": log_type,
        }
        session.setdefault("action_logs", []).append(entry)
        self.save_session(session_id, session)

    def get_logs(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.get_session(session_id)
        if not session:
            return []
        return session.get("action_logs", [])

session_manager = SessionManager()
