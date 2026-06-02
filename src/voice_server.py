"""
WebSocket voice pipeline — replaces the LiveKit agent stack.

Flow per connection:
  Browser mic (webm/opus) → WS → Deepgram streaming STT
  → language detect → scope check → OpenAI LLM → Sarvam/ElevenLabs TTS
  → audio bytes → WS → Browser speaker
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from typing import List

import aiohttp
from fastapi import WebSocket, WebSocketDisconnect

from src.analytics import save_conversation_log
from src.conversation_manager import ConversationManager
from src.language_detector import LanguageDetector
from src.scope_validator import ScopeValidator

logger = logging.getLogger("voice_server")

_GREETINGS = {
    "en": (
        "Namaste and welcome! I'm Priya, your AI assistant. "
        "I'm here to help you today. "
        "You can speak in English or Hindi — whichever is comfortable for you."
    ),
    "hi": (
        "Namaste aur swaagat hai! Main Priya hoon, aapki AI assistant. "
        "Aap Hindi ya English mein baat kar sakte hain — "
        "jo bhi aapko comfortable lage."
    ),
}

_DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?model=nova-3"
    "&language=multi"
    "&punctuate=true"
    "&smart_format=true"
    "&interim_results=true"
    "&endpointing=600"
    "&utterance_end_ms=1500"
    "&vad_events=true"
    "&filler_words=false"
)


# ---------------------------------------------------------------------------
# Main session handler — called once per WebSocket connection
# ---------------------------------------------------------------------------

async def handle_voice_session(ws: WebSocket, scenario: str) -> None:
    cm = ConversationManager(scenario=scenario)
    detector = LanguageDetector()
    scope_validator = ScopeValidator(scenario=scenario)

    system_prompt = cm.get_system_prompt()
    messages: List[dict] = [{"role": "system", "content": system_prompt}]
    current_lang = os.getenv("DEFAULT_LANGUAGE", "en")

    # ── Send greeting ──────────────────────────────────────────────────────
    greeting = _GREETINGS.get(current_lang, _GREETINGS["en"])
    cm.add_turn("assistant", greeting, language=current_lang)
    try:
        greeting_audio = await _tts(greeting, current_lang)
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
            ) as dg_ws:
                await asyncio.gather(
                    _forward_audio(ws, dg_ws),
                    _process_transcripts(
                        ws, dg_ws, cm, detector, scope_validator, messages, current_lang
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
    """Stream browser audio chunks → Deepgram."""
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


async def _process_transcripts(
    ws: WebSocket,
    dg_ws,
    cm: ConversationManager,
    detector: LanguageDetector,
    scope_validator: ScopeValidator,
    messages: List[dict],
    current_lang: str,
) -> None:
    """Receive Deepgram transcripts → LLM → TTS → browser."""
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
                # ── LLM ──────────────────────────────────────────────────
                lang_instruction = (
                    "The user is speaking Hindi. You MUST reply ONLY in Hindi (use Hinglish if needed, but respond in Hindi script or Hindi romanization)."
                    if detected == "hi"
                    else "The user is speaking English. Reply in English."
                )
                messages.append({
                    "role": "user",
                    "content": f"{transcript}\n\n[LANGUAGE INSTRUCTION: {lang_instruction}]"
                })
                reply = await _call_llm(messages)
                messages.append({"role": "assistant", "content": reply})
                # Keep context window manageable: system + last 20 messages
                if len(messages) > 21:
                    messages[1:] = messages[-20:]

            cm.add_turn("assistant", reply, language=current_lang)
            logger.info("Bot  [%s]: %s", current_lang, reply)

            # ── TTS ───────────────────────────────────────────────────────
            await ws.send_json({"type": "bot_text", "text": reply, "lang": current_lang})
            try:
                audio = await _tts(reply, current_lang)
                if audio:
                    await ws.send_bytes(audio)
            except Exception as exc:
                logger.error("TTS error: %s", exc)

        elif msg_type == "Metadata":
            logger.debug("Deepgram metadata: %s", data)

        elif msg_type == "Error":
            logger.error("Deepgram error: %s", data)
            await ws.send_json({"type": "error", "text": "STT error. Please try again."})


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

async def _tts(text: str, lang: str) -> bytes | None:
    provider = os.getenv("TTS_PROVIDER", "edge").lower()
    try:
        if provider == "elevenlabs":
            return await _tts_elevenlabs(text, lang)
        if provider == "openai":
            return await _tts_openai(text)
        if provider == "sarvam":
            return await _tts_sarvam(text, lang)
        # default: edge-tts (free, reliable, works for Hindi + English)
        return await _tts_edge(text, lang)
    except Exception as exc:
        logger.error("TTS [%s] failed: %s — trying edge-tts fallback", provider, exc)
        try:
            return await _tts_edge(text, lang)
        except Exception as exc2:
            logger.error("edge-tts fallback also failed: %s", exc2)
            return None


async def _tts_sarvam(text: str, lang: str) -> bytes:
    api_key = os.getenv("SARVAM_API_KEY", "")
    lang_code = "hi-IN" if lang == "hi" else "en-IN"
    hi_speaker = os.getenv("SARVAM_HI_SPEAKER", "meera")
    en_speaker = os.getenv("SARVAM_EN_SPEAKER", "anushka")
    speaker = hi_speaker if lang == "hi" else en_speaker

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


async def _tts_openai(text: str) -> bytes:
    import openai
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    resp = await client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="shimmer",
        input=text,
        speed=0.95,
    )
    return resp.content


async def _tts_edge(text: str, lang: str) -> bytes:
    """Microsoft Edge TTS — free, no API key, supports Hindi + English."""
    import io
    import edge_tts

    # High-quality Indian voices
    voice = "hi-IN-SwaraNeural" if lang == "hi" else "en-IN-NeerjaNeural"
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
