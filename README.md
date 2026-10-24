# AwaazWeb 🎙️🌐

> **Voice-first web navigator enabling visually impaired individuals to access any website autonomously via Hindi/Hinglish speech.**

Built for Hackathon by team **Dead Neurons**.

---

## 💡 Overview
AwaazWeb bridges the digital divide for blind and visually impaired users. Rather than relying on rigid screen readers or pre-programmed site scripts, AwaazWeb listens to natural Hindi/Hinglish voice requests, autonomously browses, reads, and navigates web pages using TinyFish Web Agents and Groq LLMs, and synthesizes short, numbered conversational previews back to the user.

---

## 🧱 Project Structure
```
awaaz2/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py          # FastAPI entrypoint, CORS, routes
│   │   ├── config.py        # Environment validation & constants
│   │   ├── routes/          # Voice, session, confirmation APIs
│   │   ├── services/        # LLM, STT, Planner, Browser, Safety, History
│   │   ├── prompts/         # System prompts (Planner, Summary, Safety)
│   │   └── data/sessions/   # Persistent session state & logs
│   ├── tests/               # Pytest suite & test specs
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment template
├── frontend/                 # Vite + React Accessible Frontend
│   ├── src/
│   │   ├── components/      # Accessible Talk Button, Status Banner, Activity Log
│   │   ├── hooks/           # Voice recorder and Web Speech speaker
│   │   └── services/        # Backend API integration
│   └── public/sounds/       # Audio cues for screenless feedback
└── docs/                     # Architecture, workflow, and pitch documentation
```

---

## ⚡ Quick Start

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Accessible UI available at `http://localhost:5173`.
