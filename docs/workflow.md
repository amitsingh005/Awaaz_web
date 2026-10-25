# AwaazWeb End-to-End Workflow Specification

This document details the complete end-to-end lifecycle of an AwaazWeb voice interaction, from user speech capture to web execution and speech synthesis.

---

## 🔁 Complete Request Lifecycle

```
[User Speaks]
      │
      ▼
1. Audio Capture (MediaRecorder in browser -> WebM audio blob)
      │
      ▼
2. Multipart Upload (POST /api/voice -> FastAPI)
      │
      ▼
3. Speech-to-Text (Sarvam AI Saaras 'saaras:v4' with native Hindi/Hinglish codemix)
      │
      ▼
4. Special Command Check (ruko / kahan hoon / dobara bolo / wapas jao)
      │
      ├──> Special Command -> Instant execution & audio response
      │
      ▼
5. Strategic Intent Planning (Groq LLM 'qwen/qwen3.8-27b')
      │  Produces JSON: { mode: "read"|"act", goal, query_or_url, steps, needs_login }
      │
      ▼
6. Deterministic Safety Gate Check (safety.py)
      │
      ├──> Contains risky step (payment / booking / delete / submit / OTP)
      │         │
      │         ▼
      │    Blocks action -> Speaks exact read-back prompt -> Awaits "Haan" or "Nahi"
      │
      └──> Safe Read Operation (mode: "read")
                │
                ▼
7. Autonomous Web Browsing (TinyFish Search & Fetch API)
      │  - Searches Google/IRCTC/Portals via TinyFish
      │  - Fetches target page content
      │  - Strips HTML tags and trims text to ~1,500-3,000 characters
      │
      ▼
8. Conversational Hinglish Synthesis (Groq LLM)
      │  - Overview summary first
      │  - At most 2 to 3 numbered options
      │  - Guiding question for next spoken response
      │
      ▼
9. Audio Delivery & Speech Output
      - Sarvam AI Bulbul ('bulbul:v3') synthesizes native Hindi/Hinglish audio
      - Frontend plays high-fidelity WAV audio response
      - Real-time ActivityLog updates for sighted judges
```

---

## 🔍 Detailed Walkthrough Example

### User Input:
> *"Delhi se Bhopal ki kal ki train dhundho"*

### Step 1: Capture & Transcription
- Audio recorded at 44.1kHz WebM format.
- Groq Whisper decodes audio:
  ```json
  {
    "transcript": "Delhi se Bhopal ki kal ki train dhundho"
  }
  ```

### Step 2: Planning Phase
- Planner LLM analyzes intent:
  ```json
  {
    "mode": "read",
    "goal": "Search trains from Delhi to Bhopal tomorrow",
    "query_or_url": "Delhi to Bhopal train schedule tomorrow IRCTC",
    "steps": [
      {"description": "Search train schedule and fares", "risky": false}
    ],
    "needs_login": false
  }
  ```

### Step 3: Web Execution
- TinyFish Search queries IRCTC schedules.
- Top 3 results extracted:
  1. *Vande Bharat Express (20172)* - 06:00 AM New Delhi -> 13:36 PM Bhopal
  2. *Shatabdi Express (12002)* - 06:15 AM New Delhi -> 14:40 PM Bhopal
  3. *Bhopal Express (12156)* - 20:55 PM Hazrat Nizamuddin -> 07:05 AM Bhopal

### Step 4: Voice Synthesis
- Summarizer LLM creates accessible audio script:
  ```json
  {
    "reply_text": "Delhi se Bhopal ke liye kal 30 se zyada trains uplabdh hain. Pehli: Vande Bharat Express subah 6 baje. Doosri: Shatabdi Express subah 6:15 par. Teesri: Bhopal Express raat 8:55 par. Aap konsi train ki ticket price ya seat availability janna chahte hain?",
    "options": [
      "1. Vande Bharat Express (6:00 AM)",
      "2. Shatabdi Express (6:15 AM)",
      "3. Bhopal Express (8:55 PM)"
    ]
  }
  ```

### Step 5: Follow-Up Action
- User replies: *"Doosri wali ki detail batao"*
- AwaazWeb immediately pulls detailed seat status for Shatabdi Express.
