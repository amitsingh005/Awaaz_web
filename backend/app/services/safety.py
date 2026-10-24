import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("awaazweb.safety")

# Deterministic keywords that require explicit user voice confirmation
RISKY_PATTERNS = [
    r"\bpay\b",
    r"\bpayment\b",
    r"\bcheckout\b",
    r"\bbuy\b",
    r"\bpurchase\b",
    r"\bbook\b",
    r"\bbooking\b",
    r"\bsubmit\b",
    r"\bdelete\b",
    r"\bremove\b",
    r"\bsend\b",
    r"\btransfer\b",
    r"\bdebit\b",
    r"\bcredit card\b",
    r"\bupi\b",
    r"\brefund\b",
]

USER_INPUT_PATTERNS = [
    r"\botp\b",
    r"\bcaptcha\b",
    r"\bpassword\b",
    r"\bpin\b",
    r"\bpasscode\b",
    r"\b2fa\b",
]

CONFIRM_YES_PATTERNS = [
    r"\bhaan\b",
    r"\bha\b",
    r"\byes\b",
    r"\btheek hai\b",
    r"\bkar do\b",
    r"\bkardo\b",
    r"\bconfirm\b",
    r"\baage badho\b",
    r"\bok\b",
    r"\bokay\b",
    r"\byep\b",
]

CONFIRM_NO_PATTERNS = [
    r"\bnahi\b",
    r"\bna\b",
    r"\bno\b",
    r"\bmat karo\b",
    r"\bcancel\b",
    r"\broko\b",
    r"\bruko\b",
    r"\bstop\b",
    r"\bchhod do\b",
]


def is_action_risky(action_description: str) -> bool:
    """
    Deterministic code safety check.
    The LLM can NEVER override or bypass this check.
    """
    desc_lower = action_description.lower()
    return any(re.search(pat, desc_lower) for pat in RISKY_PATTERNS)


def requires_user_credentials(action_description: str) -> bool:
    """
    Checks if an action requires sensitive user input like OTP, Captcha, or Password.
    AwaazWeb NEVER guesses, stores, or logs these.
    """
    desc_lower = action_description.lower()
    return any(re.search(pat, desc_lower) for pat in USER_INPUT_PATTERNS)


def format_confirmation_prompt(action_description: str) -> str:
    """
    Constructs an explicit spoken read-back prompt for the blind user.
    """
    return (
        f"Kripya dhyan dein. Yeh ek mahatvapurna kadam hai: {action_description}. "
        "Kya main ise aage badhaun? Pushti ke liye 'Haan' bolein, ya radd karne ke liye 'Nahi' bolein."
    )


def parse_spoken_confirmation(user_text: str) -> Optional[bool]:
    """
    Parses spoken Hindi/Hinglish yes/no response.
    Returns:
      True  -> Confirmed ('Haan', 'Yes', 'Theek hai', 'Kar do')
      False -> Cancelled ('Nahi', 'No', 'Mat karo', 'Cancel')
      None  -> Ambiguous or unrelated input
    """
    text_lower = user_text.lower().strip()

    # Check for NO first (safety-biased)
    if any(re.search(pat, text_lower) for pat in CONFIRM_NO_PATTERNS):
        return False

    # Check for YES
    if any(re.search(pat, text_lower) for pat in CONFIRM_YES_PATTERNS):
        return True

    return None
