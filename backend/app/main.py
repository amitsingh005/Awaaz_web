import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import FRONTEND_ORIGIN
from app.routes.session import router as session_router
from app.routes.voice import router as voice_router

# Configure logging without leaking secrets
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("awaazweb")

app = FastAPI(
    title="AwaazWeb API",
    description="Voice-first web navigator for visually impaired users",
    version="0.1.0",
)

# CORS configuration
origins = [
    FRONTEND_ORIGIN,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(session_router)
app.include_router(voice_router)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint to verify backend service status."""
    return {"status": "ok"}


@app.get("/", tags=["System"])
async def root():
    return {
        "app": "AwaazWeb",
        "description": "Voice-first web assistant for the visually impaired",
        "status": "online"
    }
