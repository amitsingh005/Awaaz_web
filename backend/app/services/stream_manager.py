import asyncio
import json
import logging
from typing import Dict, Any, AsyncGenerator, Set
from datetime import datetime, timezone

logger = logging.getLogger("awaazweb.stream")

class StreamManager:
    """
    Manages in-memory async queues for Server-Sent Events (SSE) per session.
    Allows services (browser agent, planner, safety) to broadcast real-time
    events (timeline steps, live browser streaming URLs, screenshots) to connected frontends.
    """
    def __init__(self):
        # session_id -> Set of asyncio.Queue
        self._listeners: Dict[str, Set[asyncio.Queue]] = {}
        # session_id -> latest state cache (for instant hydration on connect)
        self._latest_state: Dict[str, Dict[str, Any]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue:
        """Subscribes a client to real-time events for a session."""
        if session_id not in self._listeners:
            self._listeners[session_id] = set()
        queue = asyncio.Queue()
        self._listeners[session_id].add(queue)

        # If we have cached state (e.g. active browser stream URL), send immediately
        if session_id in self._latest_state:
            cached = self._latest_state[session_id]
            queue.put_nowait({
                "event": "hydrate",
                "data": cached
            })

        logger.info(f"Client subscribed to session stream: {session_id} (active listeners: {len(self._listeners[session_id])})")
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        """Removes a client queue when connection closes."""
        if session_id in self._listeners:
            self._listeners[session_id].discard(queue)
            if not self._listeners[session_id]:
                del self._listeners[session_id]
        logger.info(f"Client unsubscribed from session stream: {session_id}")

    async def broadcast(self, session_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """
        Broadcasts an event to all connected listeners for the given session.
        Safe to call from async contexts.
        """
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Update cached state for late joiners
        if session_id not in self._latest_state:
            self._latest_state[session_id] = {
                "session_id": session_id,
                "streaming_url": None,
                "current_url": None,
                "screenshot_url": None,
                "status": "idle",
                "original_command": None,
                "current_action": None,
                "steps": [],
                "final_result": None,
                "verification_status": "unverified",
                "preview_reason": None,
                "frame_blocked": False,
                "http_status": None,
            }

        state = self._latest_state[session_id]
        if event_type == "browser_stream":
            state["streaming_url"] = data.get("streaming_url")
            state["current_url"] = data.get("url") or state.get("current_url")
            if data.get("title"):
                state["title"] = data.get("title")
            if "screenshot_url" in data:
                import time
                state["screenshot_url"] = data.get("screenshot_url")
                state["screenshot_for_url"] = state.get("current_url")
                state["screenshot_timestamp"] = data.get("screenshot_timestamp") or time.time()
            if "verification_status" in data:
                state["verification_status"] = data["verification_status"]
            if "reason" in data:
                state["preview_reason"] = data["reason"]
            if "frame_blocked" in data:
                state["frame_blocked"] = data["frame_blocked"]
            if "http_status" in data:
                state["http_status"] = data["http_status"]
        elif event_type == "step":
            step_id = data.get("id")
            existing_idx = next((i for i, s in enumerate(state.get("steps", [])) if s.get("id") == step_id), None) if step_id else None
            if existing_idx is not None:
                state["steps"][existing_idx].update(data)
            else:
                state.setdefault("steps", []).append(data)
        elif event_type == "status":
            state["status"] = data.get("status", "idle")
            if "original_command" in data:
                state["original_command"] = data["original_command"]
            if "current_action" in data:
                state["current_action"] = data["current_action"]
            if "final_result" in data:
                state["final_result"] = data["final_result"]
            if "verification_status" in data:
                state["verification_status"] = data["verification_status"]

        payload = {
            "event": event_type,
            "data": data
        }

        queues = self._listeners.get(session_id, set())
        for q in list(queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning(f"Queue full for session {session_id}, dropping event.")

    def broadcast_sync(self, session_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """Helper to broadcast from synchronous or thread callbacks."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(session_id, event_type, data))
        except RuntimeError:
            # Fallback for background threads
            asyncio.run(self.broadcast(session_id, event_type, data))

    def get_state(self, session_id: str) -> Dict[str, Any]:
        """Returns the current cached browser and agent state for a session."""
        if session_id not in self._latest_state:
            return {
                "session_id": session_id,
                "streaming_url": None,
                "current_url": None,
                "screenshot_url": None,
                "status": "idle",
                "original_command": None,
                "current_action": None,
                "steps": [],
                "final_result": None,
                "verification_status": "unverified",
                "preview_reason": None,
                "frame_blocked": False,
                "http_status": None,
            }
        return dict(self._latest_state[session_id])

    def reset_session(self, session_id: str) -> None:
        """Resets cached stream state for a session."""
        if session_id in self._latest_state:
            del self._latest_state[session_id]

stream_manager = StreamManager()
