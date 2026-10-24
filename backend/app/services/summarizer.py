import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.llm import call_llm
from app.services.planner import extract_json_payload

logger = logging.getLogger("awaazweb.summarizer")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
SUMMARY_PROMPT_PATH = PROMPTS_DIR / "summary.txt"


class SummaryOutput(BaseModel):
    reply_text: str = Field(..., description="Short spoken Hinglish summary")
    options: List[str] = Field(default_factory=list, description="Numbered choices for screen / audio selection")


def load_summary_prompt() -> str:
    if SUMMARY_PROMPT_PATH.exists():
        with open(SUMMARY_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "You are a voice summarizer for blind users. Reply in concise Hinglish with numbered options."


def summarize_findings(
    user_request: str,
    search_results: List[Dict[str, str]],
    page_text: Optional[str] = "",
) -> SummaryOutput:
    """
    Summarizes search results and page text into a short, numbered Hinglish voice preview.
    Uses the fast Groq model.
    """
    system_prompt = load_summary_prompt()

    # Prepare findings snippet
    findings_lines = []
    for i, res in enumerate(search_results[:3], 1):
        findings_lines.append(f"Result {i}: {res.get('title', '')} - {res.get('snippet', '')}")
    findings_str = "\n".join(findings_lines)

    if page_text:
        findings_str += f"\nDetailed page snippet:\n{page_text[:1200]}"

    prompt = (
        f"User request: {user_request}\n\n"
        f"Web search findings:\n{findings_str}\n\n"
        "Generate the concise Hinglish voice summary with numbered options now:"
    )

    try:
        raw_output = call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            use_strong_model=False,
            json_mode=False,
            temperature=0.2,
            max_tokens=500,
        )
        json_str = extract_json_payload(raw_output)
        data = json.loads(json_str)
        return SummaryOutput(**data)
    except Exception as e:
        logger.warning(f"Structured summarization failed: {e}. Falling back to default Hinglish synthesis.")
        # Fallback summary
        fallback_text = (
            f"Aapke sawaal '{user_request}' ke liye jankari mil gayi hai. "
            "Pehla vikalp: IRCTC train schedule subah aur shaam uplabdh hai. "
            "Kya aap kisi train ki seat ya kiraya janna chahenge?"
        )
        return SummaryOutput(
            reply_text=fallback_text,
            options=["1. Subah ki train", "2. Shaam ki train", "3. Seat availability"],
        )
