import json
import logging
import time
from typing import Optional, Dict, Any, List
from groq import Groq
from app.config import (
    GROQ_API_KEY,
    GROQ_LLM_MODEL_FAST,
    GROQ_LLM_MODEL_STRONG,
)

logger = logging.getLogger("awaazweb.llm")

# Initialize client singleton
_client: Optional[Groq] = None

def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    use_strong_model: bool = False,
    json_mode: bool = False,
    temperature: float = 0.1,
    max_tokens: int = 1024,
    max_retries: int = 2,
) -> str:
    """
    Central wrapper for all Groq LLM invocations.
    This is the ONLY function in the codebase that calls Groq chat completions.
    """
    client = get_groq_client()
    model = GROQ_LLM_MODEL_STRONG if use_strong_model else GROQ_LLM_MODEL_FAST

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content or ""
            return content.strip()
        except Exception as e:
            last_error = e
            logger.warning(
                f"Groq LLM call failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
            )
            if attempt < max_retries:
                time.sleep(1.0 * (attempt + 1))  # Short backoff

    logger.error(f"Groq LLM call completely failed after {max_retries + 1} attempts: {last_error}")
    raise RuntimeError(f"LLM generation failed: {str(last_error)}")
