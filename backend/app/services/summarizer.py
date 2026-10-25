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

    # Attempt 1: Fast model
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
        logger.warning(f"Fast summarization failed: {e}. Retrying with strong model...")

    # Attempt 2: Strong model fallback
    try:
        retry_prompt = (
            f"User request: {user_request}\n\n"
            f"Findings:\n{findings_str}\n\n"
            'You MUST return ONLY a single valid JSON object:\n'
            '{"reply_text": "Short conversational Hinglish summary", "options": ["1. Choice 1", "2. Choice 2"]}'
        )
        raw_output = call_llm(
            prompt=retry_prompt,
            system_prompt=system_prompt,
            use_strong_model=True,
            json_mode=False,
            temperature=0.1,
            max_tokens=500,
        )
        json_str = extract_json_payload(raw_output)
        data = json.loads(json_str)
        return SummaryOutput(**data)
    except Exception as e2:
        logger.warning(f"Structured summarization retry failed: {e2}. Generating dynamic context fallback.")

    # Context-aware fallback based on actual search results (never hardcode unrelated IRCTC trains)
    if search_results and search_results[0].get("title"):
        first_title = search_results[0].get("title", "").strip()
        first_snippet = search_results[0].get("snippet", "").strip()
        cleaned_snippet = first_snippet[:150] if first_snippet else "Jankari uplabdh hai."
        fallback_text = (
            f"Aapke nirdesh '{user_request}' ke liye hume mila: {first_title}. "
            f"{cleaned_snippet} Kya aap iske baare mein aur detail janna chahenge?"
        )
        opts = [f"1. {first_title[:28]}", "2. Aur jankari dekho", "3. Wapas jao"]
    else:
        fallback_text = (
            f"Aapke nirdesh '{user_request}' ke liye web par jaankari khoji gayi hai. "
            "Aap agla kadam ya vishisht sawaal bol sakte hain."
        )
        opts = ["1. Dobara bolo", "2. Wapas jao"]

    return SummaryOutput(
        reply_text=fallback_text,
        options=opts,
    )
