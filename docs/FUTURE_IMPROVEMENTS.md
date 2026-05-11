# Future Improvement Roadmap

## Phase 1 — Short Term (Weeks 1–4)

### 1.1 Streaming TTS
**Why:** Current Sarvam AI TTS makes a full HTTP request per response, adding ~400-500ms latency. Streaming TTS would return audio chunks as they are generated.
**How:** Migrate to ElevenLabs streaming API (once permissions issue resolved) or implement Sarvam AI chunked streaming when available.
**Expected impact:** End-to-end latency drops from ~2.1s to ~1.2s.

### 1.2 Conversation Summarisation
**Why:** After each call, generate a structured summary (customer name, intent, outcome, follow-up action) for the sales team's CRM.
**How:** Post-call LLM call with conversation history → structured JSON summary saved alongside `.analytics.json`.
**Expected impact:** +3 bonus points in evaluation; practical CRM value.

### 1.3 Real-Time Transcription Display
**Why:** Evaluators and agents can see what the bot heard in real time — improves trust and debugging.
**How:** LiveKit data channel messages with interim Deepgram transcripts displayed in a simple web UI.

### 1.4 Third Language Support — Bengali
**Why:** +5 bonus points in evaluation; ~100M Bengali speakers in India.
**How:** Add `"bn"` to language detector, add Sarvam AI `bn-IN` TTS, create Bengali system prompt files.

---

## Phase 2 — Medium Term (Months 1–2)

### 2.1 Voice Fingerprinting for Repeat Callers
**Why:** Identify returning customers by voice and personalise the greeting ("Welcome back, Rajesh!").
**How:** Integrate a speaker embedding model (e.g., SpeechBrain or Resemblyzer) to generate voice prints stored per customer ID.

### 2.2 Conversation Quality Scoring
**Why:** Automatically grade each conversation on relevance, tone, scope compliance, and resolution.
**How:** Post-call LLM evaluation prompt that scores the bot's performance 0–10 on each dimension.

### 2.3 Advanced Sentiment-Based Tone Adaptation
**Why:** If a user expresses frustration (negative sentiment), the bot should shift to a more empathetic, slower-paced tone automatically.
**How:** Sentiment score from `sentiment.py` feeds a tone modifier in the system prompt per turn.

### 2.4 Human Handoff Integration
**Why:** For escalations, route the live call to a human agent without dropping the customer.
**How:** LiveKit SIP integration → transfer call to agent queue with conversation summary pre-filled.

---

## Phase 3 — Long Term (Months 3–6)

### 3.1 Production Deployment on AWS
**Why:** Move from local to cloud-hosted agent for 99.9% uptime, auto-scaling, and monitoring.
**How:** ECS Fargate + CloudWatch + ALB. Auto-scale worker pool based on active room count.

### 3.2 Dashboard & Analytics UI
**Why:** Business users need a web interface to view call logs, analytics, and sentiment trends.
**How:** FastAPI backend + React frontend. Charts for call volume, language distribution, scope violation rates, sentiment trends.

### 3.3 A/B Testing Framework
**Why:** Test different system prompt variations to find which gives better conversion outcomes.
**How:** Randomly assign incoming calls to prompt variant A or B; track conversion metrics per variant.

### 3.4 Custom Vocabulary and Pronunciation Guide
**Why:** Industry-specific terms (drug names, legal terms, product names) may be mispronounced.
**How:** ElevenLabs pronunciation dictionary or Sarvam AI custom vocabulary list per scenario.

### 3.5 WhatsApp Voice Integration
**Why:** Many Indian users prefer WhatsApp — extending the voicebot to WhatsApp Voice Notes would 10x reach.
**How:** Meta WhatsApp Business API → audio transcription → same LLM pipeline → audio response.

---

## Technical Debt to Address

| Item | Priority | Effort |
|------|----------|--------|
| Replace OpenRouter with direct OpenAI key for lower LLM latency | High | Low |
| Fix ElevenLabs API key permissions for premium Indian voice | Medium | Low |
| Add database persistence (PostgreSQL) instead of file-based logs | Medium | Medium |
| Add rate limiting to prevent API quota exhaustion | High | Low |
| Add unit tests for `sarvam_tts.py` and `livekit_manager.py` | Medium | Medium |
| Add integration test that mocks LiveKit room end-to-end | Low | High |
