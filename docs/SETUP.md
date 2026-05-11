# Setup Guide

## Prerequisites

- Python 3.10 or higher
- `pip` and `venv` (or Poetry)
- Git
- Accounts with credentials for:
  - [LiveKit Cloud](https://cloud.livekit.io) (or self-hosted)
  - [Deepgram](https://console.deepgram.com) — STT
  - [OpenAI](https://platform.openai.com) (or OpenRouter) — LLM
  - [ElevenLabs](https://elevenlabs.io) — TTS

---

## 1. Clone the Repository

```bash
git clone <your-repo-url>
cd voicebot-screening-project
```

## 2. Create a Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxx
LIVEKIT_API_SECRET=your-secret

# OpenAI (or OpenRouter — keys starting sk-or-v1- are auto-detected)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Deepgram
DEEPGRAM_API_KEY=your-deepgram-key

# ElevenLabs
ELEVEN_API_KEY=your-elevenlabs-key
TTS_EN_IN_VOICE_ID=9BWtsMINqrJLrRacOk9x  # Indian English voice
TTS_HI_VOICE_ID=9BWtsMINqrJLrRacOk9x    # Hindi voice (same or different)

# Scenario: presale | sales | marketing
SCENARIO=presale
```

## 5. Get Your LiveKit Credentials

1. Sign up at https://cloud.livekit.io
2. Create a new project
3. Navigate to **Settings → API Keys**
4. Copy `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`

## 6. Get Your ElevenLabs Voice IDs

1. Log in to https://elevenlabs.io
2. Go to **Voice Library**
3. Search for Indian English voices (e.g., "Riya", "Meera")
4. Copy the Voice ID from the voice card
5. Set `TTS_EN_IN_VOICE_ID` in your `.env`

## 7. Run the Agent

```bash
python -m src.main start
```

The agent will connect to LiveKit and wait for a participant to join.

## 8. Connect a Test Client

Use the LiveKit Playground at https://agents-playground.livekit.io to connect to your room and test voice interaction.

Or use the LiveKit CLI:

```bash
lk room join --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET your-room-name
```

## 9. Run Tests

```bash
pytest tests/ -v
```

---

## Switching Scenarios

Set `SCENARIO` in your `.env` to one of:
- `presale` — Lead qualification and discovery
- `sales` — Product features and objection handling
- `marketing` — Lead nurturing and educational content

## Changing the Default Language

Set `DEFAULT_LANGUAGE=hi` in `.env` to greet users in Hindi by default.
