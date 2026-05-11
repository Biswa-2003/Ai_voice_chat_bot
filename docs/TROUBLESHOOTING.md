# Troubleshooting Guide

## Common Issues and Fixes

---

### 1. Agent starts but no audio heard in playground

**Symptom:** Playground shows "Connected" but "Waiting for agent audio track…"

**Causes & Fixes:**
- Agent dispatched before user joined — run `python connect.py` again to get a fresh room
- TTS API key invalid — check `ELEVEN_API_KEY` or `SARVAM_API_KEY` in `.env`
- Check agent logs for `APIError: no audio frames were pushed`

```bash
# Verify Sarvam TTS key works
python -c "
import requests, os; from dotenv import load_dotenv; load_dotenv()
r = requests.post('https://api.sarvam.ai/text-to-speech',
    headers={'api-subscription-key': os.getenv('SARVAM_API_KEY')},
    json={'inputs':['test'],'target_language_code':'en-IN','speaker':'anushka','model':'bulbul:v2'})
print(r.status_code)
"
```

---

### 2. `RuntimeError: Plugins must be registered on the main thread`

**Symptom:** Agent crashes on first job with this error.

**Fix:** All LiveKit plugins must be imported at the top of `src/main.py` before `WorkerOptions` is created. Verify this line exists in [src/main.py](../src/main.py):

```python
from livekit.plugins import openai, deepgram, elevenlabs, silero
```

---

### 3. `ValueError: language detection is not supported in streaming mode`

**Symptom:** STT crashes immediately after user joins.

**Fix:** Remove `detect_language=True` from Deepgram STT config. Use `language="multi"` instead — already set in [src/stt_engine.py](../src/stt_engine.py).

---

### 4. `TypeError: LLM.__init__() got an unexpected keyword argument 'max_tokens'`

**Symptom:** LLM fails to initialise.

**Fix:** Use `max_completion_tokens` not `max_tokens`. Already corrected in [src/llm_processor.py](../src/llm_processor.py).

---

### 5. ElevenLabs returns 401 `missing_permissions`

**Symptom:** TTS silent, logs show 401 from ElevenLabs.

**Fix:** Set `TTS_PROVIDER=sarvam` in `.env` (default). Sarvam AI is confirmed working and provides native Indian voices. If you want ElevenLabs, regenerate your API key at elevenlabs.io with full TTS permissions.

---

### 6. Agent session times out immediately (`entrypoint did not exit in time`)

**Symptom:** Agent joins, saves analytics with 0 turns, then exits.

**Cause:** User was not in the room when agent dispatched — agent waits briefly then exits.

**Fix:** Use `connect.py` — it generates the URL first, then you join, then it dispatches:
```bash
python connect.py
# Open URL in browser → connect → then press Enter
```

Or dispatch manually after connecting:
```bash
python -c "
import asyncio, os
from dotenv import load_dotenv; load_dotenv()
from livekit import api
async def main():
    lkapi = api.LiveKitAPI(os.getenv('LIVEKIT_URL'), os.getenv('LIVEKIT_API_KEY'), os.getenv('LIVEKIT_API_SECRET'))
    await lkapi.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(agent_name='voicebot', room='YOUR_ROOM'))
    await lkapi.aclose()
asyncio.run(main())
"
```

---

### 7. Deepgram STT not transcribing Hindi

**Symptom:** Hindi speech not recognised, only English works.

**Fix:** Ensure `language="multi"` is set (not `language="hi-IN"`). The `nova-3` model with `multi` handles code-switching between English and Hindi in a single stream.

---

### 8. OpenRouter key not working for LLM

**Symptom:** LLM returns 401 or model not found.

**Fix:** OpenRouter keys starting with `sk-or-v1-` are auto-detected. The model defaults to `openai/gpt-4o-mini`. Set explicitly in `.env`:
```
OPENAI_API_KEY=sk-or-v1-your-key
OPENAI_MODEL=openai/gpt-4o-mini
```
Note: OpenRouter does **not** support TTS — use Sarvam AI for TTS.

---

### 9. Scope validation blocking valid queries

**Symptom:** Normal product questions get blocked as out-of-scope.

**Fix:** Check `src/scope_validator.py` — the regex patterns may be too broad. The word `"rate"` for example can match unintentionally. Adjust the pattern for your use case.

---

### 10. `ModuleNotFoundError: No module named 'src'`

**Symptom:** Tests or main.py fail with import errors.

**Fix:** Always run from the project root directory:
```bash
cd voicebot-screening-project
python -m src.main start       # correct
python src/main.py             # incorrect
pytest tests/ -v               # correct (conftest.py handles path)
```

---

### 11. Agent registered but never receives a job

**Symptom:** Logs show `registered worker` but no `received job request`.

**Fix:** The agent needs an explicit dispatch. LiveKit does not auto-dispatch unless configured with room webhooks. Run:
```bash
python connect.py
```

---

### 12. Background noise causing false STT triggers

**Symptom:** Bot responds to background sounds.

**Fix:** Silero VAD is already enabled. For louder environments, increase VAD sensitivity or use noise-cancelling microphone. The playground also has a mic level indicator — ensure it only activates on speech.

---

## Log File Locations

| Log Type | Location |
|----------|----------|
| Conversation turns | `logs/<conversation_id>.jsonl` |
| Analytics summary | `logs/<conversation_id>.analytics.json` |
| Agent worker logs | `logs/worker-<date>.out.log` |
| Agent error logs | `logs/worker-<date>.err.log` |

## Getting Help

- LiveKit Community Slack: https://livekit.io/slack
- Deepgram Discord: https://discord.gg/deepgram
- Stack Overflow tags: `livekit`, `voice-ai`, `speech-to-text`
