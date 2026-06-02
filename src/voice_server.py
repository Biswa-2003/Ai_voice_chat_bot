"""
WebSocket voice pipeline — replaces the LiveKit agent stack.

Flow per connection:
  Browser mic (webm/opus) → WS → Deepgram streaming STT
  → language detect → scope check → filler word → OpenAI LLM → TTS
  → audio bytes → WS → Browser speaker
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import random
from typing import List

import aiohttp
from fastapi import WebSocket, WebSocketDisconnect

from src.analytics import save_conversation_log
from src.conversation_manager import ConversationManager
from src.language_detector import LanguageDetector
from src.scope_validator import ScopeValidator

logger = logging.getLogger("voice_server")

_GREETINGS = {
    ("en", "female"): (
        "Namaste and welcome! I'm Priya, your AI assistant. "
        "I'm here to help you today. "
        "You can speak in English or Hindi — whichever is comfortable for you."
    ),
    ("en", "male"): (
        "Namaste and welcome! I'm Aryan, your AI assistant. "
        "I'm here to help you today. "
        "You can speak in English or Hindi — whichever is comfortable for you."
    ),
    ("hi", "female"): (
        "Namaste aur swaagat hai! Main Priya hoon, aapki AI assistant. "
        "Aap Hindi ya English mein baat kar sakte hain — "
        "jo bhi aapko comfortable lage."
    ),
    ("hi", "male"): (
        "Namaste aur swaagat hai! Main Aryan hoon, aapka AI assistant. "
        "Aap Hindi ya English mein baat kar sakte hain — "
        "jo bhi aapko comfortable lage."
    ),
}

# Short acknowledgement sounds played while the LLM is thinking.
# These are TTS-synthesised so they match the bot's voice.
_FILLERS = {
    "en": ["Hmm...", "I see.", "Right.", "Okay.", "Sure.", "Let me think..."],
    "hi": ["Hmm...", "Achha.", "Ji haan.", "Theek hai.", "Samjha."],
}

_DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?model=nova-3"
    "&language=multi"
    "&punctuate=true"
    "&smart_format=true"
    "&interim_results=true"
    "&endpointing=300"
    "&utterance_end_ms=1000"
    "&vad_events=true"
    "&filler_words=false"
)
# Deepgram closes connection after ~12s of no audio — send KeepAlive every 8s
_DG_KEEPALIVE_INTERVAL = 8

# Edge-TTS voices by (lang, gender)
_EDGE_VOICES = {
    ("en", "female"): "en-IN-NeerjaNeural",
    ("en", "male"):   "en-IN-PrabhatNeural",
    ("hi", "female"): "hi-IN-SwaraNeural",
    ("hi", "male"):   "hi-IN-MadhurNeural",
}

# Sarvam speakers by (lang, gender)
_SARVAM_SPEAKERS = {
    ("en", "female"): "anushka",
    ("en", "male"):   "amol",
    ("hi", "female"): "meera",
    ("hi", "male"):   "arjun",
}


# ---------------------------------------------------------------------------
# Main session handler — called once per WebSocket connection
# ---------------------------------------------------------------------------

async def handle_voice_session(
    ws: WebSocket,
    scenario: str,
    voice_gender: str = "female",
) -> None:
    cm = ConversationManager(scenario=scenario)
    detector = LanguageDetector()
    scope_validator = ScopeValidator(scenario=scenario)

    system_prompt = cm.get_system_prompt()
    messages: List[dict] = [{"role": "system", "content": system_prompt}]
    current_lang = os.getenv("DEFAULT_LANGUAGE", "en")

    # ── Send bot identity so browser can display correct name ─────────────
    bot_name = "Aryan" if voice_gender == "male" else "Priya"
    await ws.send_json({"type": "bot_info", "name": bot_name, "gender": voice_gender})

    # ── Send greeting ──────────────────────────────────────────────────────
    greeting = _GREETINGS.get((current_lang, voice_gender),
                               _GREETINGS[("en", voice_gender)])
    cm.add_turn("assistant", greeting, language=current_lang)
    try:
        greeting_audio = await _tts(greeting, current_lang, voice_gender)
        await ws.send_json({"type": "bot_text", "text": greeting, "lang": current_lang})
        if greeting_audio:
            await ws.send_bytes(greeting_audio)
    except Exception as exc:
        logger.warning("Greeting TTS failed: %s", exc)
        await ws.send_json({"type": "bot_text", "text": greeting, "lang": current_lang})

    # ── Open Deepgram streaming connection ─────────────────────────────────
    dg_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not dg_key:
        await ws.send_json({"type": "error", "text": "DEEPGRAM_API_KEY not configured."})
        return

    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.ws_connect(
                _DEEPGRAM_URL,
                headers={"Authorization": f"Token {dg_key}"},
                heartbeat=30,
                timeout=aiohttp.ClientTimeout(total=None, connect=10),
            ) as dg_ws:
                await asyncio.gather(
                    _forward_audio(ws, dg_ws),
                    _keepalive_deepgram(dg_ws),
                    _process_transcripts(
                        ws, dg_ws, cm, detector, scope_validator,
                        messages, current_lang, voice_gender,
                    ),
                )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("Voice session error: %s", exc)
    finally:
        log_dir = os.getenv("LOG_DIR", "logs")
        try:
            save_conversation_log(cm.to_context_dict(), log_dir=log_dir)
        except Exception as exc:
            logger.error("Failed to save log: %s", exc)


async def _forward_audio(ws: WebSocket, dg_ws) -> None:
    """Stream browser audio chunks → Deepgram. Runs until browser disconnects."""
    try:
        async for chunk in ws.iter_bytes():
            if dg_ws.closed:
                break
            await dg_ws.send_bytes(chunk)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        try:
            await dg_ws.send_str(json.dumps({"type": "CloseStream"}))
        except Exception:
            pass


async def _keepalive_deepgram(dg_ws) -> None:
    """Send KeepAlive to Deepgram every 8 s to prevent timeout during bot speech."""
    try:
        while not dg_ws.closed:
            await asyncio.sleep(_DG_KEEPALIVE_INTERVAL)
            if not dg_ws.closed:
                await dg_ws.send_str(json.dumps({"type": "KeepAlive"}))
                logger.debug("Deepgram KeepAlive sent")
    except Exception:
        pass


async def _process_transcripts(
    ws: WebSocket,
    dg_ws,
    cm: ConversationManager,
    detector: LanguageDetector,
    scope_validator: ScopeValidator,
    messages: List[dict],
    current_lang: str,
    voice_gender: str,
) -> None:
    """Receive Deepgram transcripts → filler → LLM → TTS → browser."""
    async for msg in dg_ws:
        if msg.type != aiohttp.WSMsgType.TEXT:
            continue
        try:
            data = json.loads(msg.data)
        except Exception:
            continue

        msg_type = data.get("type", "")

        # Final transcript
        if msg_type == "Results" and data.get("is_final"):
            alts = data.get("channel", {}).get("alternatives", [])
            if not alts:
                continue
            transcript = alts[0].get("transcript", "").strip()
            if not transcript:
                continue

            # ── Language detection ────────────────────────────────────────
            detected = detector.detect(transcript)
            if detected != current_lang:
                current_lang = detected
                logger.info("Language: → %s", current_lang)

            logger.info("User [%s]: %s", current_lang, transcript)

            # ── Scope check ───────────────────────────────────────────────
            in_scope, topic = scope_validator.check(transcript)
            cm.add_turn("user", transcript, language=detected, topic=topic or "general")
            await ws.send_json({"type": "user_text", "text": transcript, "lang": detected})

            if not in_scope:
                cm.record_scope_violation(topic or "unknown")
                reply = scope_validator.get_out_of_scope_reply(detected, topic)
            else:
                # ── LLM (start immediately as background task) ────────────
                lang_instruction = (
                    "The user is speaking Hindi. You MUST reply ONLY in Hindi (use Hinglish if needed, but respond in Hindi script or Hindi romanization)."
                    if detected == "hi"
                    else "The user is speaking English. Reply in English."
                )
                messages.append({
                    "role": "user",
                    "content": f"{transcript}\n\n[LANGUAGE INSTRUCTION: {lang_instruction}]"
                })
                llm_task = asyncio.create_task(_call_llm(messages))

                # ── Filler word — plays while LLM thinks ─────────────────
                filler_text = random.choice(_FILLERS.get(detected, _FILLERS["en"]))
                try:
                    filler_audio = await _tts(filler_text, detected, voice_gender)
                    if filler_audio:
                        await ws.send_bytes(filler_audio)
                except Exception as exc:
                    logger.debug("Filler TTS skipped: %s", exc)

                # ── Wait for LLM ──────────────────────────────────────────
                reply = await llm_task
                messages.append({"role": "assistant", "content": reply})
                # Keep context window manageable: system + last 20 messages
                if len(messages) > 21:
                    messages[1:] = messages[-20:]

            cm.add_turn("assistant", reply, language=current_lang)
            logger.info("Bot  [%s]: %s", current_lang, reply)

            # ── Streaming TTS (sentence by sentence) ──────────────────────
            # Send text immediately so user sees it, then stream audio
            # sentence-by-sentence so first audio arrives in ~300ms not 5-6s
            await ws.send_json({"type": "bot_text", "text": reply, "lang": current_lang})
            sentences = _split_sentences(reply)
            first_task = asyncio.create_task(_tts(sentences[0], current_lang, voice_gender))
            try:
                first_audio = await first_task
                if first_audio:
                    await ws.send_bytes(first_audio)
            except Exception as exc:
                logger.error("TTS sentence 1 error: %s", exc)
            for sentence in sentences[1:]:
                try:
                    audio = await _tts(sentence, current_lang, voice_gender)
                    if audio:
                        await ws.send_bytes(audio)
                except Exception as exc:
                    logger.error("TTS sentence error: %s", exc)

        elif msg_type == "Metadata":
            logger.debug("Deepgram metadata: %s", data)

        elif msg_type == "Error":
            logger.error("Deepgram error: %s", data)
            await ws.send_json({"type": "error", "text": "STT error. Please try again."})


# ---------------------------------------------------------------------------
# Sentence splitter for streaming TTS
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split reply into short speakable sentences for low-latency TTS streaming."""
    import re
    # Split on Hindi danda, or English sentence-ending punctuation
    parts = re.split(r'(?<=[।.!?])\s+', text.strip())
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # If still too long (>120 chars), split on comma/semicolon
        if len(part) > 120:
            sub = re.split(r'[,;]\s+', part)
            for s in sub:
                s = s.strip()
                if s:
                    result.append(s)
        else:
            result.append(part)
    return result if result else [text.strip()]


# ---------------------------------------------------------------------------
# LLM — direct OpenAI / OpenRouter call
# ---------------------------------------------------------------------------

async def _call_llm(messages: List[dict]) -> str:
    import openai

    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    if api_key.startswith("sk-or-v1-") and not base_url:
        base_url = "https://openrouter.ai/api/v1"
        if model == "gpt-4o":
            model = "openai/gpt-4o-mini"

    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.65,
            max_tokens=512,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.error("LLM error: %s", exc)
        return "I'm sorry, I had a technical issue. Could you please repeat that?"


# ---------------------------------------------------------------------------
# TTS — edge-tts (free default) / Sarvam / ElevenLabs / OpenAI
# ---------------------------------------------------------------------------

async def _tts(text: str, lang: str, voice_gender: str = "female") -> bytes | None:
    provider = os.getenv("TTS_PROVIDER", "edge").lower()
    try:
        if provider == "elevenlabs":
            return await _tts_elevenlabs(text, lang)
        if provider == "openai":
            return await _tts_openai(text, voice_gender)
        if provider == "sarvam":
            return await _tts_sarvam(text, lang, voice_gender)
        # default: edge-tts (free, reliable, works for Hindi + English)
        return await _tts_edge(text, lang, voice_gender)
    except Exception as exc:
        logger.error("TTS [%s] failed: %s — trying edge-tts fallback", provider, exc)
        try:
            return await _tts_edge(text, lang, voice_gender)
        except Exception as exc2:
            logger.error("edge-tts fallback also failed: %s", exc2)
            return None


async def _tts_sarvam(text: str, lang: str, voice_gender: str = "female") -> bytes:
    api_key = os.getenv("SARVAM_API_KEY", "")
    lang_code = "hi-IN" if lang == "hi" else "en-IN"
    speaker = _SARVAM_SPEAKERS.get((lang, voice_gender), "anushka")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.sarvam.ai/text-to-speech",
            json={
                "inputs": [text],
                "target_language_code": lang_code,
                "speaker": speaker,
                "model": "bulbul:v2",
            },
            headers={"api-subscription-key": api_key},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return base64.b64decode(data["audios"][0])


async def _tts_elevenlabs(text: str, lang: str) -> bytes:
    api_key = os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY", "")
    default_voice = "l7kNoIfnJKPg7779LI2t"
    voice_id = (
        os.getenv("TTS_HI_VOICE_ID", default_voice)
        if lang == "hi"
        else os.getenv("TTS_EN_IN_VOICE_ID", default_voice)
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.55,
                    "similarity_boost": 0.80,
                    "style": 0.15,
                    "use_speaker_boost": True,
                },
            },
            headers={"xi-api-key": api_key},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            resp.raise_for_status()
            return await resp.read()


async def _tts_openai(text: str, voice_gender: str = "female") -> bytes:
    import openai
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    # shimmer/nova = female, echo/onyx = male
    voice = "shimmer" if voice_gender == "female" else "echo"
    resp = await client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        speed=0.95,
    )
    return resp.content


async def _tts_edge(text: str, lang: str, voice_gender: str = "female") -> bytes:
    """Microsoft Edge TTS — free, no API key, supports Hindi + English."""
    import io
    import edge_tts

    voice = _EDGE_VOICES.get((lang, voice_gender), "en-IN-NeerjaNeural")
    communicate = edge_tts.Communicate(text, voice)

    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])

    audio = buf.getvalue()
    if not audio:
        raise RuntimeError("edge-tts returned empty audio")
    logger.info("edge-tts OK: lang=%s voice=%s bytes=%d", lang, voice, len(audio))
    return audio
