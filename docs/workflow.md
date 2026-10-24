# AwaazWeb End-to-End Workflow

## Core Lifecycle
1. **Audio Capture**: User presses the giant talk button (or Space) and speaks in Hindi/Hinglish.
2. **Speech-to-Text**: Groq Whisper (`whisper-large-v3`) converts audio to text transcript.
3. **Intent & Planning**: Groq LLM Planner analyzes request into a structured JSON execution plan.
4. **Autonomous Browsing**: TinyFish engine executes either read-only Fetch/Search or multi-step Action Agent.
5. **Safety Gate**: High-risk actions (transactions, bookings, form submissions) require explicit user voice confirmation.
6. **Conversational Synthesis**: Groq LLM summarizes findings into a concise, numbered Hinglish preview.
7. **Audio Output**: Browser SpeechSynthesis speaks response aloud in natural Hindi accent.
