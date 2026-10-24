# AwaazWeb Pitch Notes & Judges FAQ

## 🎯 The Vision
AwaazWeb transforms the internet into an interactive, voice-native audio workspace for the visually impaired, allowing them to browse, search, compare, and transact autonomously in Hindi/Hinglish.

---

## 💡 Why Groq & TinyFish?

### 1. Why Groq?
- **Speed is an Accessibility Requirement**: For a blind user who cannot see a loading spinner, a 5-second silence feels like a broken app. Groq's high-throughput LPU inference runs Whisper STT and LLM generation in ~400–800ms, making conversational voice loops feel real-time.
- **Cost & Efficiency**: Groq's accessible pricing tier enables high-volume multilingual processing without heavy cloud GPU overhead.

### 2. Why TinyFish?
- **Modern Web Automation**: 90% of sites rely on dynamic React/Vue/Angular rendering, shadow DOMs, and nested iframes where static scrapers fail. TinyFish drives real headless browser instances capable of interacting with complex Single Page Applications.
- **Browser Context Profiles**: Enables authenticated persistence across sessions so users don't have to re-login every time they check their IRCTC or electricity dashboard.

---

## 📊 Societal Impact
1. **Digital Inclusion**: India has 40M+ visually impaired individuals and over 500M Hindi speakers. AwaazWeb gives them digital self-reliance.
2. **Economic Autonomy**: Blind users can compare prices on Flipkart, book travel on IRCTC, and pay utility bills without having to share sensitive passwords or personal details with third-party helpers.
3. **Government Service Access**: Enables independent access to schemes like PM Kisan, DigiLocker, and Aadhaar update status.

---

## ❓ Anticipated Judge Questions & Strong Answers

### Q1: "Why not just use ChatGPT Voice Mode or Google Gemini?"
**Answer**:
> *"General-purpose voice assistants like Siri, Alexa, or Gemini Voice talk, but they cannot autonomously drive and manipulate arbitrary third-party web pages (e.g. searching a specific regional electricity portal, handling complex form layouts, and navigating multi-step booking flows). Furthermore, they don't have our deterministic, code-enforced Safety Gate that prevents accidental financial transactions."*

### Q2: "What if the LLM hallucinates or approves a transaction without permission?"
**Answer**:
> *"The LLM **cannot** approve a risky step. In AwaazWeb, safety is hardcoded in deterministic Python regexes (`safety.py`). Any step containing words like 'pay', 'book', 'submit', or 'delete' is automatically intercepted before reaching execution. Only an explicit spoken 'Haan' or physical button press from the human user can unlock the gate."*

### Q3: "How do you handle OTPs and passwords?"
**Answer**:
> *"We implement a zero-credential retention policy. If a website asks for an OTP, Captcha, or password, AwaazWeb pauses (`needs_user_input`) and asks the user to provide it directly on their secure device keyboard. We never guess, store, or feed sensitive credentials to the LLM."*

### Q4: "How does AwaazWeb prevent getting stuck on infinite web loops?"
**Answer**:
> *"Three safeguards: (1) Preference for read-only Search/Fetch over active agents, (2) Hard session run caps (`MAX_AGENT_RUNS_PER_SESSION=5`), and (3) Constant user interruption support—saying 'ruko' instantly kills active tasks."*

### Q5: "What is your business model or distribution plan?"
**Answer**:
> *"B2G and B2B accessibility partnerships: Government portals (Digital India, IRCTC) and major enterprise platforms (banks, utilities) can sponsor AwaazWeb API integrations as part of statutory digital accessibility mandates."*
