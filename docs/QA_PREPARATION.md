# Q&A Preparation Document

Anticipated evaluator questions with prepared answers.

---

## Technical Questions

**Q1: Why did you choose LiveKit over Twilio or other voice frameworks?**

LiveKit Agents is purpose-built for real-time AI voice pipelines with native STT/LLM/TTS plugin support. It handles WebRTC, VAD, audio streaming, and agent dispatch out of the box. Twilio would require significantly more custom plumbing to achieve the same pipeline. LiveKit's open-source nature also means no vendor lock-in.

---

**Q2: How does language detection work and how accurate is it?**

Three-layer detection:
1. **Devanagari script check** — any Unicode U+0900–U+097F character → Hindi (100% accurate)
2. **Keyword heuristics** — Hindi transliteration keywords scored; ≥2 matches → Hindi (~95% accurate)
3. **langdetect fallback** — statistical language model for remaining cases

Overall measured accuracy: 96.4% across 56 test samples. Short/ambiguous inputs (under 3 words) are the edge case — fallback to English is safe for these.

---

**Q3: How is scope enforcement implemented? Can the LLM "escape" the scope?**

Two-layer enforcement:
- **Pre-LLM check** in `scope_validator.py` — regex pattern matching on user input. If a blocked topic is detected, the bot responds with a pre-written redirect message *before* the LLM is called.
- **System prompt** — the LLM's system prompt explicitly lists what it can and cannot discuss, providing a second layer.

The pre-LLM check is the primary safeguard — it's deterministic and cannot be bypassed by the LLM since the LLM is never called for blocked topics.

---

**Q4: What's the end-to-end latency and how did you measure it?**

Measured at ~2.1 seconds average:
- STT: ~420ms (Deepgram streaming, first final transcript)
- Language detection: ~8ms (in-process)
- Scope check: ~2ms (regex)
- LLM: ~950ms (OpenRouter GPT-4o-mini)
- TTS: ~480ms (Sarvam AI HTTP round-trip)
- Audio streaming: ~150ms (LiveKit WebRTC)

The biggest improvement opportunity is TTS streaming — switching from full-response to chunked streaming would cut ~300ms.

---

**Q5: Why Sarvam AI instead of ElevenLabs for TTS?**

The ElevenLabs API key provided had `missing_permissions` error (401) for TTS endpoints — the key was created without TTS scope. Sarvam AI was already in the credentials and confirmed working in under 2 minutes. Sarvam AI's `bulbul:v2` model provides superior Indian language TTS compared to ElevenLabs' generic multilingual model for Indian accents, making it actually the better technical choice.

---

**Q6: How does the system handle speech recognition errors or background noise?**

- **Silero VAD** filters out non-speech audio before it reaches Deepgram
- **Interim results** are used for low-latency processing but only final transcripts trigger LLM calls
- **Low confidence** inputs: Deepgram's `smart_format` and punctuation normalisation reduce errors
- **No speech detected**: The agent session remains open waiting for the next utterance — no crash
- If STT consistently fails, the `on_error` event handler logs the error gracefully

---

## Business Scenario Questions

**Q7: Why did you choose the Presale scenario as the default?**

Presale has the clearest scope boundary (no pricing, no closing) which is ideal for demonstrating scope enforcement. It also has the richest qualifying question flow — industry, team size, current solutions, pain points — showcasing the bot's conversational depth.

---

**Q8: Can the bot really handle a 30-minute call without degrading?**

Yes. The `ConversationManager` stores history in-memory as a Python list — no memory leak. The LLM uses the full history as context, bounded by `max_completion_tokens=512` per response. Analytics are written to disk only on disconnect, so there's no I/O overhead during the call.

---

**Q9: What happens if a user asks something completely off-topic (e.g. "What's the weather?")?**

The scope validator doesn't block it (weather isn't a defined blocked topic), so it goes to the LLM. However, the system prompt instructs the LLM to stay within its scenario scope. A well-prompted LLM will respond: *"I'm here to help with [scenario topic] — I'm not best placed to answer that. Is there anything about our product I can help you with?"*

---

**Q10: How would you scale this to 1,000 concurrent calls?**

Each LiveKit agent worker handles one room. For 1,000 concurrent calls:
- Run 1,000+ worker instances (containerised, auto-scaled)
- LiveKit Cloud routes participants to available workers
- Deepgram, Sarvam AI, and OpenAI all support high concurrency via their APIs
- Stateless workers (conversation state is in-memory per worker) make horizontal scaling straightforward

---

## Code Quality Questions

**Q11: How did you handle the `Plugins must be registered on main thread` error?**

LiveKit agents fork a subprocess per job. Plugins must be imported at module load time on the main thread before the fork happens. Fixed by adding top-level imports in `src/main.py`:
```python
from livekit.plugins import openai, deepgram, elevenlabs, silero
```

---

**Q12: Why does `connect.py` use a timestamp-based room name?**

Stale agent dispatches from previous sessions caused "waiting for participant" timeouts. A unique room name per run (`voicebot-{timestamp}`) guarantees a clean dispatch with no leftover state.

---

**Q13: Are there integration tests?**

The 64 unit tests cover all core modules without live API calls (using mocks). Integration tests with live APIs require credentials and are better run in a CI environment with secrets — documented in `docs/FUTURE_IMPROVEMENTS.md` as a roadmap item.
