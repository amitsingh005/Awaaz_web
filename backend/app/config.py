import os
from pathlib import Path
from dotenv import load_dotenv

# Locate backend/.env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # Check parent directory fallback
    load_dotenv()

# Required credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if not GROQ_API_KEY:
    raise RuntimeError(
        "CRITICAL ERROR: GROQ_API_KEY is missing from backend/.env. "
        "Please provide a valid Groq API key to start the backend."
    )

# Optional credentials
TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "").strip()

# Model configurations
GROQ_LLM_MODEL_FAST = os.getenv("GROQ_LLM_MODEL_FAST", "llama-3.1-8b-instant").strip()
GROQ_LLM_MODEL_STRONG = os.getenv("GROQ_LLM_MODEL_STRONG", "llama-3.3-70b-versatile").strip()
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3").strip()

# Limits and Networking
try:
    MAX_AGENT_RUNS_PER_SESSION = int(os.getenv("MAX_AGENT_RUNS_PER_SESSION", "5"))
except ValueError:
    MAX_AGENT_RUNS_PER_SESSION = 5

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip()

# Data storage paths
DATA_DIR = BASE_DIR / "app" / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
