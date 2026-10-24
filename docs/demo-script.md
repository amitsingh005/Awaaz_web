# AwaazWeb 3-Minute Hackathon Demo Script

> **Target Audience**: Hackathon Judges, Accessibility Advocates, Tech Evaluators  
> **Speaker Roles**: Presenter (Voice Operator) & AwaazWeb Voice Assistant  
> **Total Time**: 3 Minutes

---

## ⏱️ Minute 0:00 - 0:45 | The Hook & Problem Statement

**Presenter Speaking**:
> *"Namaste judges. There are over 40 million visually impaired citizens in India. While we book train tickets, pay electricity bills, and check government schemes online in seconds, a blind person today is effectively locked out of 90% of the Indian internet.*
>
> *Screen readers like NVDA read raw DOM code—drowning blind users in 20 minutes of ads, navigation tags, and confusing dropdowns.*
>
> *We built **AwaazWeb**—an autonomous voice-first web navigator that listens in conversational Hindi/Hinglish, drives a real browser for them, and speaks back with short, numbered previews first. Let's see it live."*

---

## ⏱️ Minute 0:45 - 1:45 | Flow 1: Information Search & Preview

**Action**: Presenter presses the big blue Talk button (or taps <kbd>Space</kbd>).

**Presenter (Speaks into mic)**:
> *"Delhi se Bhopal ki kal ki train dhundho"*

**AwaazWeb Visual Feedback**:
- Blue button glows and ripples.
- Audio beep plays.
- `ActivityLog` updates:
  - `[INFO] Whisper transcribed: 'Delhi se Bhopal ki kal ki train dhundho'`
  - `[INFO] Plan: Search trains from Delhi to Bhopal tomorrow (Mode: READ)`
  - `[INFO] TinyFish web search: 'Delhi to Bhopal train schedule tomorrow IRCTC'`
  - `[INFO] Synthesizing Hinglish voice preview...`

**AwaazWeb (Speaks aloud in Hindi voice)**:
> *"Delhi se Bhopal ke liye kal 30 se zyada trains chalti hain. Yahan top 3 vikalp hain:*  
> *Pehli: Vande Bharat Express subah 6 baje, jo sabse tez hai.*  
> *Doosri: Shatabdi Express subah 6:15 par.*  
> *Teesri: Bhopal Express raat 8:55 par.*  
> *Aap konsi train ki detail janna chahte hain?"*

**Presenter Explains to Judges**:
> *"Notice: AwaazWeb didn't read 500 lines of IRCTC markup. It summarized the real-world options into 3 numbered choices."*

---

## ⏱️ Minute 1:45 - 2:30 | Flow 2: The Deterministic Safety Gate

**Action**: Presenter triggers a high-risk booking command.

**Presenter (Speaks into mic)**:
> *"Yeh Shatabdi express ki ticket book kar do"*

**AwaazWeb Feedback**:
- `ActivityLog` flashes in warning amber: `[WARNING] Safety Gate blocked risky step: Book Shatabdi express train ticket`.
- Status Banner turns Red: `Pushti Chahiye (Confirmation Needed)`.
- Green *"✓ Haan (Confirm)"* and Red *"✕ Nahi (Cancel)"* buttons appear.

**AwaazWeb (Speaks aloud)**:
> *"Kripya dhyan dein. Yeh ek mahatvapurna kadam hai: Book Shatabdi express train ticket. Kya main aage badhun? Pushti ke liye 'Haan' bolein, ya radd karne ke liye 'Nahi' bolein."*

**Presenter (Speaks into mic)**:
> *"Haan, confirm karo"*

**AwaazWeb (Speaks aloud)**:
> *"Aapki pushti mil gayi hai. 'Book Shatabdi express train ticket' safalta se pura kiya gaya."*

**Presenter Explains to Judges**:
> *"Notice: The LLM can NEVER approve a financial or booking transaction on its own. The safety gate is hard-coded in Python and requires explicit spoken confirmation."*

---

## ⏱️ Minute 2:30 - 3:00 | Flow 3: Interruptions ("Ruko") & Pitch Wrap-up

**Presenter (Speaks into mic)**:
> *"Electricity bill pay karo"*

**AwaazWeb begins reading confirmation**:
> *"Kripya dhyan dein..."*

**Presenter interrupts immediately**:
> *"Ruko, mat karo"*

**AwaazWeb (Immediately halts and speaks)**:
> *"Thik hai, maine process rok diya hai. Aap naya aadesh de sakte hain."*

**Presenter Closing Pitch**:
> *"With sub-second Groq Whisper transcription, intelligent planning, TinyFish web agents, and strict code safety gates, AwaazWeb doesn't just read the screen—it gives visually impaired users autonomous control of the modern web.*
>
> *Thank you! Team Dead Neurons is ready for your questions."*
