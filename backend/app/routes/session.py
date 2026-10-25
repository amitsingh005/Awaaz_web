import asyncio
import json
import logging
import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.history import session_manager
from app.services.stream_manager import stream_manager

logger = logging.getLogger("awaazweb.session")
router = APIRouter(prefix="/api/session", tags=["Session"])


def validate_external_url(url: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validates that a URL is a legitimate external HTTP/HTTPS web address.
    Protects against SSRF and private network probing.
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid"

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return False, "Only HTTP and HTTPS URLs are allowed"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must include a valid hostname"

    lower_host = hostname.lower()
    if (
        lower_host in ("localhost", "127.0.0.1", "0.0.0.0", "::1")
        or lower_host.endswith(".local")
        or lower_host.endswith(".internal")
    ):
        return False, "Access to local network services is restricted"

    try:
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            addr_info = socket.getaddrinfo(hostname, None)
            if not addr_info:
                return False, "Could not resolve hostname"
            ip = ipaddress.ip_address(addr_info[0][4][0])

        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, "Access to private or local network addresses is restricted"
    except Exception as e:
        return False, f"Invalid or unresolvable hostname: {e}"

    return True, None


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


@router.get("/{session_id}/browser-state")
async def get_browser_state(session_id: str):
    """Retrieve the current browser preview and agent activity timeline state."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return stream_manager.get_state(session_id)


class ActionRequest(BaseModel):
    action: str  # "scroll_down", "scroll_up", "click", "refresh"
    target: Optional[str] = None


async def capture_verified_screenshot(
    session_id: str,
    url: str,
    action: Optional[str] = None,
    action_target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Uses Playwright to navigate, optionally execute a permitted browser action
    (scrolling or clicking), verify page state, and capture an actual rendered screenshot.
    Broadcasts results to connected SSE clients and caches state in stream_manager.
    """
    import time
    now = time.time()

    # 1. SSRF & URL Validation
    is_valid, err_msg = validate_external_url(url)
    if not is_valid:
        res = {
            "screenshot_url": None,
            "source": "validation",
            "verification_status": "failed",
            "reason": "restricted_url",
            "message": err_msg or "Invalid or restricted URL.",
            "url": url,
            "screenshot_timestamp": now,
        }
        await stream_manager.broadcast(session_id, "browser_stream", res)
        return res

    try:
        import base64
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            try:
                resp = await page.goto(url, timeout=12000, wait_until="domcontentloaded")
                status_code = resp.status if resp else 0
                headers = resp.headers if resp else {}
                page_title = (await page.title()) or ""
                x_frame = headers.get("x-frame-options", "").lower()
                csp = headers.get("content-security-policy", "").lower()
                frame_blocked = ("deny" in x_frame or "sameorigin" in x_frame or "frame-ancestors" in csp)

                # Wait briefly for dynamic assets to settle
                try:
                    await page.wait_for_load_state("load", timeout=3000)
                except Exception:
                    pass

                content_sample = ""
                try:
                    content_sample = (await page.content())[:2000].lower()
                except Exception:
                    pass

                # A. Detect Access Denied / WAF / Anti-bot restriction
                is_access_denied = (
                    status_code == 403
                    or "access denied" in page_title.lower()
                    or "403 forbidden" in page_title.lower()
                    or "errors.edgesuite.net" in content_sample
                    or ("access denied" in content_sample and ("cloudflare" in content_sample or "akamai" in content_sample or "security" in content_sample or "perimeterx" in content_sample))
                )

                # B. Detect Authentication / Login Required
                is_auth_required = (
                    status_code == 401
                    or (status_code == 403 and "login" in page_title.lower())
                    or ("login" in page_title.lower() and "sign in" in content_sample and "password" in content_sample)
                )

                if is_access_denied:
                    result = {
                        "screenshot_url": None,
                        "source": "playwright",
                        "verification_status": "access_denied",
                        "reason": "server_security_access_denied",
                        "http_status": status_code,
                        "title": page_title or "Access Denied",
                        "frame_blocked": True,
                        "url": url,
                        "message": "Website server returned Access Denied (automated or embedded access blocked by server security policy).",
                        "screenshot_timestamp": now,
                    }
                    await stream_manager.broadcast(session_id, "browser_stream", result)
                    return result

                if is_auth_required:
                    result = {
                        "screenshot_url": None,
                        "source": "playwright",
                        "verification_status": "auth_required",
                        "reason": "authentication_required",
                        "http_status": status_code,
                        "title": page_title or "Authentication Required",
                        "frame_blocked": frame_blocked,
                        "url": url,
                        "message": "Website requires login or user authentication in a browser tab.",
                        "screenshot_timestamp": now,
                    }
                    await stream_manager.broadcast(session_id, "browser_stream", result)
                    return result

                if status_code >= 400:
                    result = {
                        "screenshot_url": None,
                        "source": "playwright",
                        "verification_status": "failed",
                        "reason": f"http_error_{status_code}",
                        "http_status": status_code,
                        "title": page_title,
                        "frame_blocked": frame_blocked,
                        "url": url,
                        "message": f"Website returned HTTP {status_code} error.",
                        "screenshot_timestamp": now,
                    }
                    await stream_manager.broadcast(session_id, "browser_stream", result)
                    return result

                # C. Execute supported browser action if specified
                action_executed = None
                if action == "scroll_down":
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_timeout(400)
                    action_executed = "scroll_down"
                elif action == "scroll_up":
                    await page.evaluate("window.scrollBy(0, -500)")
                    await page.wait_for_timeout(400)
                    action_executed = "scroll_up"
                elif action == "click" and action_target:
                    try:
                        await page.click(action_target, timeout=3000)
                        await page.wait_for_load_state("domcontentloaded", timeout=4000)
                        action_executed = f"click: {action_target}"
                        url = page.url
                        page_title = (await page.title()) or page_title
                    except Exception as e_click:
                        logger.warning(f"Click action failed on '{action_target}': {e_click}")

                # D. Capture fresh screenshot (JPEG at 85 quality for fast render & compact footprint)
                screenshot_bytes = await page.screenshot(type="jpeg", quality=85, full_page=False)
                b64 = base64.b64encode(screenshot_bytes).decode()
                screenshot_data_url = f"data:image/jpeg;base64,{b64}"

                final_url = page.url or url
                result = {
                    "screenshot_url": screenshot_data_url,
                    "source": "playwright",
                    "verification_status": "verified",
                    "reason": "loaded_successfully",
                    "http_status": status_code,
                    "title": page_title,
                    "frame_blocked": frame_blocked,
                    "url": final_url,
                    "action_executed": action_executed,
                    "screenshot_timestamp": now,
                }
                await stream_manager.broadcast(session_id, "browser_stream", result)
                return result
            finally:
                await browser.close()
    except Exception as e:
        logger.warning(f"Browser navigation/screenshot failed for {url}: {e}")
        result = {
            "screenshot_url": None,
            "source": "playwright",
            "verification_status": "failed",
            "reason": "navigation_failed",
            "message": f"Could not load website: {str(e)}",
            "url": url,
            "screenshot_timestamp": now,
        }
        await stream_manager.broadcast(session_id, "browser_stream", result)
        return result


@router.post("/{session_id}/action")
async def execute_browser_action(session_id: str, request: ActionRequest):
    """
    Executes a permitted browser action (scrolling, clicking, or refreshing)
    and captures a new screenshot immediately.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    state = stream_manager.get_state(session_id)
    current_url = state.get("current_url")
    if not current_url:
        raise HTTPException(status_code=400, detail="No active URL in session")

    return await capture_verified_screenshot(
        session_id=session_id,
        url=current_url,
        action=request.action,
        action_target=request.target,
    )


@router.get("/{session_id}/screenshot")
async def get_session_screenshot(session_id: str, url: Optional[str] = None, refresh: bool = False):
    """
    Returns a verified screenshot or access status of the current URL the agent is viewing.
    Checks memory cache first (valid for 30s for the same URL).
    Uses Playwright for a real browser render and validates HTTP status and anti-bot blocks.
    Distinguishes: verified, access_denied, auth_required, blocked_embedding, failed.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = stream_manager.get_state(session_id)
    current_url = url or state.get("current_url")

    if not current_url:
        return {
            "screenshot_url": None,
            "source": "none",
            "verification_status": "unverified",
            "message": "No active URL to display.",
        }

    # If new URL was specified, update session stream
    if url and url != state.get("current_url"):
        await stream_manager.broadcast(session_id, "browser_stream", {"url": url, "title": url})

    cached_screenshot = state.get("screenshot_url")
    cached_for_url = state.get("screenshot_for_url")
    cached_time = state.get("screenshot_timestamp", 0)
    cached_status = state.get("verification_status")

    import time
    now = time.time()

    # Return cached result if fresh (<30s) for the same URL and not forced refresh
    if (
        not refresh
        and cached_for_url == current_url
        and (now - cached_time) < 30
        and cached_status in ("verified", "access_denied", "auth_required", "failed")
    ):
        return {
            "screenshot_url": cached_screenshot,
            "source": "cached",
            "verification_status": cached_status,
            "reason": state.get("preview_reason"),
            "frame_blocked": state.get("frame_blocked", False),
            "http_status": state.get("http_status"),
            "title": state.get("title"),
            "url": current_url,
            "screenshot_timestamp": cached_time,
        }

    return await capture_verified_screenshot(session_id=session_id, url=current_url)


@router.get("/{session_id}/stream")
async def session_event_stream(session_id: str, request: Request):
    """
    Server-Sent Events (SSE) endpoint providing real-time timeline,
    status updates, and browser streaming URLs.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        queue = stream_manager.subscribe(session_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    yield f"event: {event_type}\ndata: {event_data}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat to keep SSE connection alive
                    yield ": heartbeat\n\n"
        finally:
            stream_manager.unsubscribe(session_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/stop")
async def stop_session_task(session_id: str):
    """
    Cancels any active or pending browser task in the session and resets to idle.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    pending = session.get("pending_action")
    action_desc = (pending.get("step") or pending.get("goal") or "task") if pending else "task"

    session_manager.update_session(session_id, {
        "state": "idle",
        "pending_action": None,
        "last_reply": "Process ruk gaya hai. Aap naya aadesh de sakte hain.",
    })
    session_manager.log_action(session_id, f"Session stopped by user: {action_desc}", "warning")

    await stream_manager.broadcast(session_id, "status", {
        "status": "cancelled",
        "current_action": "Stopped by user",
        "final_result": "Process stopped by user request.",
        "verification_status": "cancelled_by_user",
    })
    await stream_manager.broadcast(session_id, "step", {
        "id": f"stop-{session_id[:6]}",
        "action": "stop",
        "description": "User requested task halt (Stop)",
        "status": "failed",
        "verification_status": "cancelled_by_user",
    })

    return {
        "status": "stopped",
        "message": "Process halted successfully.",
        "session_id": session_id,
    }

