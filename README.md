# AI Voicebot — LiveKit Multilingual Platform

A production-grade AI voicebot built with LiveKit Agents that conducts natural, bilingual (English + Hindi) voice conversations with an Indian English accent.

## Features

| Feature | Status |
|---------|--------|
| LiveKit real-time voice pipeline | ✅ |
| Deepgram STT (English + Hindi, nova-3) | ✅ |
| OpenAI GPT-4o LLM with scenario prompts | ✅ |
| ElevenLabs TTS — Indian accent | ✅ |
| Automatic language detection (Devanagari + heuristics) | ✅ |
| Seamless mid-conversation language switching | ✅ |
| Context preservation across language switches | ✅ |
| Scope enforcement (per scenario) | ✅ |
| Professional tone — never rude or dismissive | ✅ |
| Conversation logging (JSONL + analytics JSON) | ✅ |
| Sentiment analysis (English + Hindi) | ✅ |
| Silero VAD for voice activity detection | ✅ |
| Three business scenarios: Presale / Sales / Marketing | ✅ |

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

### 3. Run the agent

```bash
python -m src.main start
```

### 4. Connect via LiveKit Playground

Open https://agents-playground.livekit.io, enter your LiveKit URL and credentials, join the room — and speak.

---

## Scenarios

Set `SCENARIO` in `.env` to choose the bot's role:

| Scenario | Bot Name | Purpose |
|----------|----------|---------|
| `presale` | Priya | Lead qualification and discovery |
| `sales` | Arjun | Product pitch and objection handling |
| `marketing` | Meera | Lead nurturing and educational content |

---

## Project Structure

```
voicebot-screening-project/
├── src/
│   ├── main.py                  # Entry point + logging setup
│   ├── livekit_manager.py       # LiveKit agent orchestration
│   ├── stt_engine.py            # Deepgram STT configuration
│   ├── tts_engine.py            # ElevenLabs TTS configuration
│   ├── llm_processor.py         # LLM wrapper + scope integration
│   ├── language_detector.py     # Multi-strategy language detection
│   ├── conversation_manager.py  # Full conversation state (spec §3.5)
│   ├── scope_validator.py       # Scenario-specific boundary enforcement
│   ├── sentiment.py             # English + Hindi sentiment analysis
│   └── analytics.py             # Log persistence and summary generation
├── config/
│   ├── settings.py              # Centralised environment variable access
│   ├── scenarios/
│   │   ├── presale_config.yaml
│   │   ├── sales_config.yaml
│   │   └── marketing_config.yaml
│   └── prompts/
│       ├── presale_system_prompt.txt
│       ├── sales_system_prompt.txt
│       └── marketing_system_prompt.txt
├── tests/
│   ├── test_scope_validation.py
│   ├── test_language_switching.py
│   ├── test_llm.py
│   └── test_stt.py
├── logs/                        # Conversation logs written here at runtime
├── docs/
│   ├── ARCHITECTURE.md
│   └── SETUP.md
├── .env.example
├── conftest.py
├── pytest.ini
├── Dockerfile
└── requirements.txt
```

---

## Running Tests

```bash
pytest tests/ -v
```

Tests do not require live API credentials — LiveKit/Deepgram/ElevenLabs plugins are mocked.

---

## Conversation Logs

After each call, two files are written to `logs/`:

- `<conversation_id>.jsonl` — one JSON line per turn (role, content, language, timestamp, sentiment)
- `<conversation_id>.analytics.json` — call summary (duration, turn count, language switches, scope violations, sentiment)

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full pipeline diagram and component descriptions.

## Setup Guide

See [docs/SETUP.md](docs/SETUP.md) for step-by-step credential setup and running instructions.
