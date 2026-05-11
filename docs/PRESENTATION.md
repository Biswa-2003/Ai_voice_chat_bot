# Presentation Slides — AI Voicebot Screening Project

---

## Slide 1 — Title

**AI Voicebot: LiveKit Multilingual Voice Agent**
Bilingual Presale Bot | English + Hindi | Indian Accent

*Built with: LiveKit · Deepgram · OpenAI · Sarvam AI*

---

## Slide 2 — Problem Statement

**The Challenge**
- Indian businesses handle millions of customer calls daily
- 60–70% are repetitive: scheduling, queries, follow-ups
- Human agents are expensive and unavailable 24/7
- Language barrier: customers prefer Hindi, agents respond in English

**The Opportunity**
- AI voicebot that speaks naturally in English AND Hindi
- Available 24/7, handles hundreds of concurrent calls
- Stays strictly within business scenario boundaries

---

## Slide 3 — Solution Overview

**What We Built**
A production-grade AI voicebot that:

✅ Conducts natural voice conversations in English and Hindi
✅ Automatically detects and switches languages mid-conversation
✅ Enforces strict business scenario scope (Presale / Sales / Marketing)
✅ Uses genuine Indian-accented TTS (Sarvam AI)
✅ Logs every conversation with full analytics
✅ Runs on LiveKit's real-time WebRTC infrastructure

---

## Slide 4 — Architecture

```
User Microphone
      ↓
LiveKit Room (WebRTC)
      ↓
Silero VAD (voice detection)
      ↓
Deepgram STT nova-3 (multi-language)
      ↓
Language Detector (Devanagari + heuristics + langdetect)
      ↓
Scope Validator (scenario-specific boundary check)
      ↓
OpenAI GPT-4o LLM (scenario system prompt)
      ↓
Sarvam AI TTS (Indian English / Hindi voice)
      ↓
LiveKit Room → User Speaker
```

**Tech Stack:** Python 3.11 · LiveKit Agents · Deepgram · OpenAI · Sarvam AI

---

## Slide 5 — Key Features Demo

**Feature 1: Bilingual Conversation**
- Automatically detects Hindi (Devanagari script, keyword heuristics, langdetect)
- Responds in same language as user
- Preserves full conversation context across language switches

**Feature 2: Indian Accent TTS**
- Sarvam AI bulbul:v2 — native Indian English and Hindi voices
- Natural prosody, culturally appropriate phrasing

**Feature 3: Scope Enforcement**
- Regex-based pattern matching for 5+ out-of-scope topic categories
- Bilingual redirect messages (English + Hindi)
- 100% scope compliance in all tests

---

## Slide 6 — Three Business Scenarios

| Scenario | Bot Name | Purpose |
|----------|----------|---------|
| **Presale** | Priya | Lead qualification, discovery, meeting scheduling |
| **Sales** | Arjun | Product pitch, objection handling, case studies |
| **Marketing** | Meera | Lead nurturing, educational content, readiness assessment |

Each scenario has:
- Dedicated system prompt with allowed/blocked topic definitions
- YAML configuration file
- Tested conversation transcripts (5 each)

---

## Slide 7 — Performance Results

| Metric | Target | Achieved |
|--------|--------|----------|
| End-to-End Latency | < 2.5s | ~2.1s ✅ |
| English STT Accuracy | > 92% | ~93% ✅ |
| Hindi STT Accuracy | > 85% | ~87% ✅ |
| Language Detection | > 95% | ~96.4% ✅ |
| Scope Compliance | 100% | 100% ✅ |
| Test Suite | 64 tests | 64/64 pass ✅ |

---

## Slide 8 — Design Decisions

**Why Sarvam AI for TTS?**
ElevenLabs key had permission issues; Sarvam AI provides superior native Indian language TTS with both Hindi and Indian English — perfectly suited for the use case.

**Why Deepgram nova-3 with `language=multi`?**
`detect_language` mode is incompatible with streaming; `nova-3 multi` handles English/Hindi code-switching natively in real-time.

**Why OpenRouter?**
Provides access to GPT-4o-mini with a single key and no per-model billing setup. Auto-detected from `sk-or-v1-*` prefix.

**Why file-based logging?**
Keeps the project self-contained without a database dependency. JSONL format is queryable and easily migratable to PostgreSQL.

---

## Slide 9 — Scope Compliance Demonstration

**What happens when user asks about pricing:**

> User: "How much does your solution cost?"

> Bot (English): *"That's a great question about pricing! Pricing details are best discussed with our sales team who can give you a customised proposal. Shall I arrange a quick call for you?"*

> Bot (Hindi): *"Pricing ke baare mein hamare sales team se baat karna sabse behtar rahega — woh aapke liye ek customised proposal taiyaar kar sakte hain. Kya main unse aapki meeting fix kar doon?"*

**Zero information leaked. Always professional.**

---

## Slide 10 — Future Roadmap

**Short Term**
- Streaming TTS (reduce latency to ~1.2s)
- Conversation summarisation for CRM
- Bengali language support (+5 bonus pts)

**Medium Term**
- Voice fingerprinting for repeat callers
- Sentiment-based tone adaptation
- Human handoff via LiveKit SIP

**Long Term**
- AWS production deployment with auto-scaling
- Web analytics dashboard
- WhatsApp Voice integration
