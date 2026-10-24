# AwaazWeb End-to-End Test Execution Matrix

This matrix documents the verification steps for all primary voice flows, test commands, and expected outputs.

---

## 🧪 Flow Matrix

| Flow ID | Scenario | Input Trigger | Key Steps Executed | Expected State | Validation Criteria |
|---------|----------|---------------|-------------------|----------------|---------------------|
| **F-01** | Read-Only Search | *"Delhi se Bhopal ki kal ki train dhundho"* | Whisper STT -> Planner (`read`) -> TinyFish Search -> Hinglish Summarizer | `done` | Reply contains train overview and at most 3 numbered choices with follow-up prompt. |
| **F-02** | Weather Query | *"Aaj ka mausam kaisa hai Mumbai mein"* | Planner (`read`) -> TinyFish Search -> Weather Summarizer | `done` | Spoken summary of current conditions and temperature in Mumbai. |
| **F-03** | Safety Gate Blocking | *"Electricity bill ₹850 pay kar do"* | Planner (`act`, risky: true) -> `safety.py` intercept | `needs_confirmation` | Action halted; read-back confirmation prompt spoken; pending action stored. |
| **F-04** | Voice Approval | *"Haan, aage badho"* (while confirmation pending) | `parse_spoken_confirmation` -> `approved=True` -> `confirm_action` | `done` | Action executed; undo snapshot created; success message spoken. |
| **F-05** | Voice Cancellation | *"Nahi, cancel karo"* (while confirmation pending) | `parse_spoken_confirmation` -> `approved=False` -> cancel handler | `done` | Action aborted; pending action cleared; cancellation confirmation spoken. |
| **F-06** | Immediate Interruption | *"Ruko, mat karo"* | `check_special_command` -> `cmd: "stop"` | `idle` | Active execution halted instantly; pending action wiped; idle message spoken. |
| **F-07** | Voice Repeat | *"Dobara bolo"* | `check_special_command` -> `cmd: "repeat"` | `done` | Assistant replays previous spoken response verbatim. |
| **F-08** | Multi-Step Undo | *"Wapas jao"* | `check_special_command` -> `session_manager.pop_undo_action` | `done` | Reverts last reversible step and announces undo success. |
| **F-09** | Quota Run Cap | 6th agent action execution | Session check vs `MAX_AGENT_RUNS_PER_SESSION` (5) | `done` / `limit_reached` | Execution blocked; user prompted to start fresh session. |
| **F-10** | Credential Handoff | *"OTP 54321 hai enter karo"* | `requires_user_credentials` regex check | `needs_user_input` | Execution paused; user prompted to enter sensitive code directly. |

---

## 🏃 Test Execution Commands

```bash
# Execute entire 26-test automated backend test suite
cd backend
source venv/bin/activate
pytest tests/ -v
```
