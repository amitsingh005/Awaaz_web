import json
import logging
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError

from app.services.llm import call_llm

logger = logging.getLogger("awaazweb.planner")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
PLANNER_PROMPT_PATH = PROMPTS_DIR / "planner.txt"


class PlannerStep(BaseModel):
    description: str = Field(..., description="Description of the step")
    risky: bool = Field(False, description="Whether this step requires user confirmation")


class PlannerPlan(BaseModel):
    mode: Literal["read", "act"] = Field(..., description="Read-only search/fetch vs interactive action")
    goal: str = Field(..., description="High-level user objective in English")
    query_or_url: str = Field(..., description="Search query or start URL")
    steps: List[PlannerStep] = Field(default_factory=list, description="Ordered steps to execute")
    needs_login: bool = Field(False, description="Whether authentication is required")


def load_planner_prompt() -> str:
    if PLANNER_PROMPT_PATH.exists():
        with open(PLANNER_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "You are an autonomous web planning agent. Output valid JSON."


def extract_json_payload(text: str) -> str:
    """Extracts JSON payload even if wrapped in markdown codeblocks."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        return cleaned[start : end + 1]
    return cleaned


def check_special_command(text: str) -> Optional[dict]:
    """
    Directly handles always-working navigation commands:
    - 'kahan hoon?' (status / current page)
    - 'ruko' (stop)
    - 'dobara bolo' (repeat)
    - 'wapas jao' (go back / undo)
    """
    normalized = text.lower().strip().rstrip("?.!,")

    if any(cmd in normalized for cmd in ["kahan hoon", "kahan hu", "where am i", "कहाँ हूँ", "कहाँ hu", "कहा हु", "कहाँ हूं"]):
        return {
            "type": "special",
            "command": "where_am_i",
            "reply_text": "Aap AwaazWeb ke mukhya screen par hain. Aap web search ya navigation ke liye bol sakte hain.",
        }

    if any(cmd in normalized for cmd in ["ruko", "rok do", "stop", "ruk jao", "रुको", "रोको", "रोक दो", "रुक जाओ"]):
        return {
            "type": "special",
            "command": "stop",
            "reply_text": "Thik hai, maine process rok diya hai.",
        }

    if any(cmd in normalized for cmd in ["dobara bolo", "fir se bolo", "repeat", "repeat karo", "दोबारा बोलो", "फिर से बोलो"]):
        return {
            "type": "special",
            "command": "repeat",
            "reply_text": None,  # Signals caller to repeat last response
        }

    if any(cmd in normalized for cmd in ["wapas jao", "back jao", "undo", "go back", "वापस जाओ", "पीछे जाओ"]):
        return {
            "type": "special",
            "command": "undo",
            "reply_text": None,  # Handled by undo endpoint
        }

    return None


def generate_plan(user_request: str) -> PlannerPlan:
    """
    Takes a natural Hindi/Hinglish user request and returns a validated PlannerPlan.
    Retries once with the strong model if the first attempt fails validation.
    """
    system_prompt = load_planner_prompt()
    user_prompt = f"User request: {user_request}\n\nGenerate the JSON plan now:"

    # Attempt 1: Fast model
    try:
        raw_output = call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            use_strong_model=False,
            json_mode=False,
            temperature=0.1,
        )
        json_str = extract_json_payload(raw_output)
        parsed = json.loads(json_str)
        return PlannerPlan(**parsed)
    except (json.JSONDecodeError, ValidationError, Exception) as e1:
        logger.warning(f"Fast planner attempt failed: {e1}. Retrying with strong model...")

    # Attempt 2: Strong model fallback
    retry_prompt = (
        f"User request: {user_request}\n"
        f"You MUST return ONLY a single valid JSON object matching the schema:\n"
        f'{{"mode": "read"|"act", "goal": "string", "query_or_url": "string", "steps": [{{"description": "string", "risky": boolean}}], "needs_login": boolean}}'
    )
    raw_output = call_llm(
        prompt=retry_prompt,
        system_prompt=system_prompt,
        use_strong_model=True,
        json_mode=False,
        temperature=0.0,
    )
    json_str = extract_json_payload(raw_output)
    parsed = json.loads(json_str)
    return PlannerPlan(**parsed)
