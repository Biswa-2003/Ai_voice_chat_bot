# Architecture

## System Overview

```
User Microphone
      │
      ▼
┌─────────────────────┐
│   LiveKit Room       │  WebRTC real-time audio channel
│  (WebRTC / RTC)      │
└────────┬────────────┘
         │ audio stream
         ▼
┌─────────────────────┐
│  Voice Activity      │  Silero VAD — detects speech boundaries,
│  Detection (VAD)     │  suppresses background noise
└────────┬────────────┘
         │ speech segments
         ▼
┌─────────────────────┐
│  Speech-to-Text      │  Deepgram nova-3, multi-language mode
│  (STT)               │  interim + final transcripts
└────────┬────────────┘
         │ text transcript
         ▼
┌─────────────────────┐
│  Language Detector   │  Devanagari script detection → Deepgram
│                      │  confidence scores → keyword heuristics
│                      │  → langdetect fallback
└────────┬────────────┘
         │ detected language ('en'/'hi')
         ▼
┌─────────────────────┐
│  Scope Validator     │  Regex-based keyword matching per scenario.
│                      │  Returns (in_scope: bool, topic: str).
└────────┬────────────┘
         │ in_scope / redirect message
         ▼
┌─────────────────────┐
│  LLM Processing      │  OpenAI GPT-4o (or compatible).
│  Engine              │  System prompt = scenario prompt from file.
│                      │  Temperature 0.65, max_tokens 512.
└────────┬────────────┘
         │ text response
         ▼
┌─────────────────────┐
│  Text-to-Speech      │  ElevenLabs eleven_multilingual_v2.
│  (TTS)               │  Indian-accented voice; same voice handles
│                      │  English and Hindi.
└────────┬────────────┘
         │ audio stream
         ▼
┌─────────────────────┐
│   LiveKit Room       │  Audio streamed back to user
└─────────────────────┘
         │ (async, side-channel)
         ▼
┌─────────────────────┐
│  Conversation        │  UUID-keyed state: turn history, language
│  Manager             │  history, sentiment, topic categories,
│                      │  scope violations, entities.
└────────┬────────────┘
         │ on disconnect
         ▼
┌─────────────────────┐
│  Analytics Engine    │  Saves .jsonl (turns) + .analytics.json
│  + Logger            │  (summary) to logs/ directory.
└─────────────────────┘
```

## Component Descriptions

| Component | File | Responsibility |
|-----------|------|----------------|
| Entry Point | `src/main.py` | Environment validation, logging setup, LiveKit CLI bootstrap |
| Voice Agent | `src/livekit_manager.py` | Orchestrates STT→Language→Scope→LLM→TTS pipeline |
| STT Engine | `src/stt_engine.py` | Deepgram STT configuration for bilingual Indian speech |
| TTS Engine | `src/tts_engine.py` | ElevenLabs Indian-accent voice configuration |
| LLM Processor | `src/llm_processor.py` | OpenAI LLM wrapper with scope validation integration |
| Language Detector | `src/language_detector.py` | Multi-strategy language detection and switch detection |
| Scope Validator | `src/scope_validator.py` | Scenario-specific content boundary enforcement |
| Conversation Manager | `src/conversation_manager.py` | Full conversation state per spec section 3.5 |
| Sentiment Analyser | `src/sentiment.py` | Keyword-based English/Hindi sentiment scoring |
| Analytics | `src/analytics.py` | Summary generation and log persistence |
| Settings | `config/settings.py` | Centralised environment variable access |

## Language Detection Strategy

```
1. Explicit switch phrase? ("Hindi mein baat kariye" / "speak english")
        ↓ yes → return target language immediately
2. Devanagari characters (U+0900–U+097F) in text?
        ↓ yes → return 'hi'
3. Hindi keyword heuristic score ≥ 2?
        ↓ yes → return 'hi'
4. langdetect library available?
        ↓ yes → use library result (hi/mr/ne/gu/pa → 'hi', else 'en')
5. Fallback → return 'en'
```

## Scope Validation Flow

```
Input text → regex pattern match against scenario's blocked_topics list
    ├── match found → (False, topic_label) → say out-of-scope message → log violation
    └── no match   → (True, None) → pass to LLM for response generation
```

## Conversation State Object (spec §3.5)

```json
{
  "conversation_id": "UUID",
  "current_language": "en | hi",
  "language_history": ["en", "hi", "en"],
  "user_intent": "string",
  "entities_extracted": {},
  "conversation_history": [
    {"role": "user", "content": "...", "language": "en", "timestamp": "...", "sentiment": "neutral"}
  ],
  "scenario": "presale | sales | marketing",
  "conversation_start_time": "ISO timestamp",
  "turn_count": 5,
  "sentiment": "positive | neutral | negative",
  "topic_categories": ["product_capabilities", "meeting_scheduling"],
  "scope_violations": [{"topic": "pricing", "timestamp": "..."}]
}
```

## Latency Budget

| Stage | Target | Acceptable |
|-------|--------|------------|
| STT (speech → text) | < 500 ms | < 800 ms |
| Language detection | < 10 ms | < 50 ms |
| Scope validation | < 5 ms | < 20 ms |
| LLM response | < 800 ms | < 1.2 s |
| TTS synthesis | < 300 ms | < 500 ms |
| **End-to-end** | **< 1.5 s** | **< 2.5 s** |
