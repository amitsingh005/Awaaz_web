import os
from pathlib import Path
from dotenv import load_dotenv

# Locate backend/.env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Required credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if not GROQ_API_KEY:
    raise RuntimeError(
        "CRITICAL ERROR: GROQ_API_KEY is missing from backend/.env. "
        "Please provide a valid Groq API key to start the backend."
    )

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
if not SARVAM_API_KEY:
    raise RuntimeError(
        "CRITICAL ERROR: SARVAM_API_KEY is missing from backend/.env. "
        "Please provide a valid Sarvam API key to start the backend voice services."
    )

# Optional credentials
TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "").strip()

# Model configurations
GROQ_LLM_MODEL_FAST = os.getenv("GROQ_LLM_MODEL_FAST", "qwen/qwen3.8-27b").strip()
GROQ_LLM_MODEL_STRONG = os.getenv("GROQ_LLM_MODEL_STRONG", "openai/gpt-oss-120b").strip()
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3").strip()
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v4").strip()
SARVAM_TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3").strip()
SARVAM_TTS_SPEAKER = os.getenv("SARVAM_TTS_SPEAKER", "shubh").strip()

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
