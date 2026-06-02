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
    "&endpointing=1200"
    "&utterance_end_ms=1500"
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
    ("en", "male"):   "abhilash",
    ("hi", "female"): "anushka",
    ("hi", "male"):   "abhilash",
}


# Cache to hold synthesized filler audio bytes for instant playback
_FILLER_AUDIO_CACHE = {}


async def prewarm_cache():
    logger.info("Pre-warming Voicebot TTS Cache in background...")
    # Languages to pre-warm
    langs = ["en", "hi"]
    genders = ["female", "male"]
    
    for lang in langs:
        for gender in genders:
            # 1. Warm Greeting
            greeting = _GREETINGS.get((lang, gender), _GREETINGS[("en", gender)])
            cache_key = ("greeting", lang, gender)
            try:
                audio = await _tts(greeting, lang, gender)
                if audio:
                    _FILLER_AUDIO_CACHE[cache_key] = audio
                    logger.info("Pre-warmed greeting for lang=%s, gender=%s", lang, gender)
            except Exception as exc:
                logger.warning("Failed to pre-warm greeting for lang=%s, gender=%s: %s", lang, gender, exc)
                
            # 2. Warm Fillers (first two)
            fillers = _FILLERS.get(lang, _FILLERS["en"])[:2]
            for filler in fillers:
                cache_key = (filler, lang, gender)
                try:
                    audio = await _tts(filler, lang, gender)
                    if audio:
                        _FILLER_AUDIO_CACHE[cache_key] = audio
                        logger.info("Pre-warmed filler '%s' for lang=%s, gender=%s", filler, lang, gender)
                except Exception as exc:
                    logger.warning("Failed to pre-warm filler '%s': %s", filler, exc)
                    
    logger.info("Voicebot TTS Cache pre-warming completed!")



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
        cache_key = ("greeting", current_lang, voice_gender)
        if cache_key in _FILLER_AUDIO_CACHE:
            greeting_audio = _FILLER_AUDIO_CACHE[cache_key]
            logger.info("Greeting cache HIT: lang=%s, gender=%s", current_lang, voice_gender)
        else:
            greeting_audio = await _tts(greeting, current_lang, voice_gender)
            if greeting_audio:
                _FILLER_AUDIO_CACHE[cache_key] = greeting_audio
                logger.info("Greeting cache MISS, cached: lang=%s, gender=%s", current_lang, voice_gender)
                
        if greeting_audio:
            import base64
            audio_b64 = base64.b64encode(greeting_audio).decode("utf-8")
            await ws.send_json({
                "type": "bot_text_audio",
                "text": greeting,
                "audio": audio_b64,
                "lang": current_lang
            })
        else:
            await ws.send_json({"type": "bot_text", "text": greeting, "lang": current_lang})
    except Exception as exc:
        logger.warning("Greeting TTS failed: %s", exc)
        await ws.send_json({"type": "bot_text", "text": greeting, "lang": current_lang})

    # ── Open Deepgram streaming connection ─────────────────────────────────
    dg_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not dg_key:
        await ws.send_json({"type": "error", "text": "DEEPGRAM_API_KEY not configured."})
        return

    interrupt_event = asyncio.Event()
    text_input_queue = asyncio.Queue()

    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.ws_connect(
                _DEEPGRAM_URL,
                headers={"Authorization": f"Token {dg_key}"},
                heartbeat=30,
                timeout=aiohttp.ClientTimeout(total=None, connect=10),
            ) as dg_ws:
                await asyncio.gather(
                    _forward_audio(ws, dg_ws, interrupt_event, text_input_queue),
                    _keepalive_deepgram(dg_ws),
                    _process_transcripts(
                        ws, dg_ws, cm, detector, scope_validator,
                        messages, current_lang, voice_gender, interrupt_event
                    ),
                    _process_text_inputs(
                        ws, cm, detector, scope_validator,
                        messages, current_lang, voice_gender, interrupt_event,
                        text_input_queue
                    )
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


async def _forward_audio(ws: WebSocket, dg_ws, interrupt_event: asyncio.Event, text_input_queue: asyncio.Queue) -> None:
    """Stream browser audio chunks → Deepgram, and user text suggestions → text queue."""
    try:
        while True:
            msg = await ws.receive()
            if "bytes" in msg:
                chunk = msg["bytes"]
                if len(chunk) == 4 and list(chunk) == [9, 9, 9, 9]:
                    logger.info("Interrupt signal received from client!")
                    interrupt_event.set()
                    try:
                        await ws.send_json({"type": "interrupted", "interrupted": True})
                    except Exception as e:
                        logger.warning("Could not send interrupted confirmation to client: %s", e)
                else:
                    if not dg_ws.closed:
                        await dg_ws.send_bytes(chunk)
            elif "text" in msg:
                text_str = msg["text"]
                try:
                    data = json.loads(text_str)
                    if data.get("type") == "user_text_input":
                        text = data.get("text", "")
                        if text:
                            logger.info("Enqueuing suggestion chip text: %s", text)
                            await text_input_queue.put(text)
                except Exception as e:
                    logger.warning("Failed to parse text message: %s", e)
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
    interrupt_event: asyncio.Event,
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
            
            try:
                await ws.send_json({
                    "type": "analytics_update",
                    "sentiment": cm.sentiment,
                    "detected_lang": current_lang,
                    "turn_count": cm.turn_count,
                    "scope_violations": len(cm.scope_violations),
                    "screening_goals": cm.get_screening_goals()
                })
            except Exception as e:
                logger.debug("Failed sending user analytics update: %s", e)

            if not in_scope:
                cm.record_scope_violation(topic or "unknown")
                reply = scope_validator.get_out_of_scope_reply(detected, topic)
                cm.add_turn("assistant", reply, language=current_lang)
                logger.info("Bot  [%s]: %s", current_lang, reply)
                
                try:
                    await ws.send_json({
                        "type": "analytics_update",
                        "sentiment": cm.sentiment,
                        "detected_lang": current_lang,
                        "turn_count": cm.turn_count,
                        "scope_violations": len(cm.scope_violations),
                        "screening_goals": cm.get_screening_goals()
                    })
                except Exception as e:
                    logger.debug("Failed sending out-of-scope analytics update: %s", e)
                
                try:
                    audio = await _tts(reply, current_lang, voice_gender)
                    if audio:
                        import base64
                        audio_b64 = base64.b64encode(audio).decode("utf-8")
                        await ws.send_json({
                            "type": "bot_text_audio",
                            "text": reply,
                            "audio": audio_b64,
                            "lang": current_lang
                        })
                    else:
                        await ws.send_json({"type": "bot_text", "text": reply, "lang": current_lang})
                except Exception as exc:
                    logger.error("TTS out-of-scope error: %s", exc)
                    await ws.send_json({"type": "bot_text", "text": reply, "lang": current_lang})
            else:
                # ── LLM streaming + sentence-by-sentence TTS ────────────
                lang_instruction = (
                    "Respond in Hindi"
                    if detected == "hi"
                    else "Respond in English"
                )
                messages.append({
                    "role": "user",
                    "content": f"{transcript}\n\n[LANGUAGE INSTRUCTION: {lang_instruction}]"
                })

                # ── Filler word — plays while LLM thinks ─────────────────
                filler_text = random.choice(_FILLERS.get(detected, _FILLERS["en"]))
                try:
                    cache_key = (filler_text, detected, voice_gender)
                    if cache_key in _FILLER_AUDIO_CACHE:
                        filler_audio = _FILLER_AUDIO_CACHE[cache_key]
                        logger.info("Filler cache HIT: %s", filler_text)
                    else:
                        filler_audio = await _tts(filler_text, detected, voice_gender)
                        if filler_audio:
                            _FILLER_AUDIO_CACHE[cache_key] = filler_audio
                            logger.info("Filler cache MISS, cached: %s", filler_text)
                    
                    if filler_audio and not interrupt_event.is_set():
                        await ws.send_bytes(filler_audio)
                except Exception as exc:
                    logger.debug("Filler TTS skipped: %s", exc)

                # ── Stream LLM and synthesize sentence-by-sentence ──────
                full_reply_sentences = []
                interrupt_event.clear() # Reset at start of speaking turn
                
                async for sentence in _stream_llm_sentences(messages):
                    if interrupt_event.is_set():
                        logger.info("Bot speech interrupted during LLM generation!")
                        break
                        
                    full_reply_sentences.append(sentence)
                    logger.info("Sentence streamed: %s", sentence)
                    
                    # Synthesize audio and send
                    try:
                        audio = await _tts(sentence, current_lang, voice_gender)
                        if interrupt_event.is_set():
                            logger.info("Bot speech interrupted after TTS synthesis!")
                            break
                        if audio:
                            import base64
                            audio_b64 = base64.b64encode(audio).decode("utf-8")
                            await ws.send_json({
                                "type": "bot_text_audio",
                                "text": sentence,
                                "audio": audio_b64,
                                "lang": current_lang
                            })
                        else:
                            await ws.send_json({"type": "bot_text", "text": sentence, "lang": current_lang})
                    except Exception as exc:
                        logger.error("TTS sentence stream error: %s", exc)

                if full_reply_sentences:
                    reply = " ".join(full_reply_sentences)
                    messages.append({"role": "assistant", "content": reply})
                    # Keep context window manageable: system + last 20 messages
                    if len(messages) > 21:
                        messages[1:] = messages[-20:]

                    cm.add_turn("assistant", reply, language=current_lang)
                    logger.info("Bot complete [%s]: %s", current_lang, reply)
                    try:
                        await ws.send_json({
                            "type": "analytics_update",
                            "sentiment": cm.sentiment,
                            "detected_lang": current_lang,
                            "turn_count": cm.turn_count,
                            "scope_violations": len(cm.scope_violations),
                            "screening_goals": cm.get_screening_goals()
                        })
                    except Exception as e:
                        logger.debug("Failed sending assistant complete analytics update: %s", e)

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


async def _stream_llm_sentences(messages: List[dict]):
    import openai
    import re

    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    if api_key.startswith("sk-or-v1-") and not base_url:
        base_url = "https://openrouter.ai/api/v1"
        if model == "gpt-4o":
            model = "openai/gpt-4o-mini"

    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.65,
            max_tokens=512,
            stream=True,
        )
        
        buffer = ""
        sentence_end_pat = re.compile(r'([^.!?।\n]+[.!?।\n]+)(?:\s+|$)')
        
        async for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            if not content:
                continue
            buffer += content
            
            while True:
                match = sentence_end_pat.match(buffer)
                if not match:
                    break
                sentence = match.group(1).strip()
                buffer = buffer[match.end():]
                if sentence:
                    yield sentence

        final_text = buffer.strip()
        if final_text:
            yield final_text
            
    except Exception as exc:
        logger.error("LLM stream error: %s", exc)
        err_detail = str(exc)
        if len(err_detail) > 150:
            err_detail = err_detail[:150] + "..."
        yield f"I'm sorry, I had a technical issue ({type(exc).__name__}: {err_detail}). Could you please repeat that?"


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
        # default: edge-tts
        return await _tts_edge(text, lang, voice_gender)
    except Exception as exc:
        logger.warning("TTS [%s] failed: %s — trying edge-tts fallback", provider, exc)
        try:
            # Fallback to edge-tts if premium provider fails (maintains gender-awareness)
            return await _tts_edge(text, lang, voice_gender)
        except Exception as exc2:
            logger.warning("edge-tts fallback also failed: %s — trying gTTS", exc2)
            try:
                # gTTS (Google TTS) — free, no API key, different servers than edge-tts
                return await _tts_gtts(text, lang)
            except Exception as exc3:
                logger.error("gTTS fallback also failed: %s", exc3)
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
    # Increase speed from 0.95 to 1.12 for snappier conversation pacing
    resp = await client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        speed=1.12,
    )
    return resp.content


async def _tts_edge(text: str, lang: str, voice_gender: str = "female") -> bytes:
    """Microsoft Edge TTS — free, no API key, supports Hindi + English."""
    import io
    import edge_tts

    voice = _EDGE_VOICES.get((lang, voice_gender), "en-IN-NeerjaNeural")
    # Increase rate to +15% for faster, snappier replies
    communicate = edge_tts.Communicate(text, voice, rate="+15%")

    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])

    audio = buf.getvalue()
    if not audio:
        raise RuntimeError("edge-tts returned empty audio")
    logger.info("edge-tts OK: lang=%s voice=%s bytes=%d", lang, voice, len(audio))
    return audio


async def _tts_gtts(text: str, lang: str) -> bytes:
    """Google TTS — free, no API key, good Hindi + English support."""
    import io
    from gtts import gTTS

    lang_code = "hi" if lang == "hi" else "en"

    def _generate() -> bytes:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()

    loop = asyncio.get_event_loop()
    audio = await loop.run_in_executor(None, _generate)
    if not audio:
        raise RuntimeError("gTTS returned empty audio")
    logger.info("gTTS OK: lang=%s bytes=%d", lang_code, len(audio))
    return audio


async def _process_text_inputs(
    ws: WebSocket,
    cm: ConversationManager,
    detector: LanguageDetector,
    scope_validator: ScopeValidator,
    messages: List[dict],
    current_lang: str,
    voice_gender: str,
    interrupt_event: asyncio.Event,
    text_input_queue: asyncio.Queue,
) -> None:
    """Worker task that consumes user text suggestions, processes them via LLM, and streams speech back."""
    try:
        while True:
            transcript = await text_input_queue.get()
            text_input_queue.task_done()
            
            # ── Language detection ────────────────────────────────────────
            detected = detector.detect(transcript)
            if detected != current_lang:
                current_lang = detected
                logger.info("Language (Text Input): → %s", current_lang)

            logger.info("User Text Suggestion [%s]: %s", current_lang, transcript)

            # ── Scope check ───────────────────────────────────────────────
            in_scope, topic = scope_validator.check(transcript)
            cm.add_turn("user", transcript, language=detected, topic=topic or "general")
            await ws.send_json({"type": "user_text", "text": transcript, "lang": detected})
            
            try:
                await ws.send_json({
                    "type": "analytics_update",
                    "sentiment": cm.sentiment,
                    "detected_lang": current_lang,
                    "turn_count": cm.turn_count,
                    "scope_violations": len(cm.scope_violations),
                    "screening_goals": cm.get_screening_goals()
                })
            except Exception:
                pass

            if not in_scope:
                cm.record_scope_violation(topic or "unknown")
                reply = scope_validator.get_out_of_scope_reply(detected, topic)
                cm.add_turn("assistant", reply, language=current_lang)
                logger.info("Bot (Text Out-of-Scope) [%s]: %s", current_lang, reply)
                
                try:
                    audio = await _tts(reply, current_lang, voice_gender)
                    if audio:
                        import base64
                        audio_b64 = base64.b64encode(audio).decode("utf-8")
                        await ws.send_json({
                            "type": "bot_text_audio",
                            "text": reply,
                            "audio": audio_b64,
                            "lang": current_lang
                        })
                    else:
                        await ws.send_json({"type": "bot_text", "text": reply, "lang": current_lang})
                except Exception as exc:
                    logger.error("TTS out-of-scope error: %s", exc)
                    await ws.send_json({"type": "bot_text", "text": reply, "lang": current_lang})
            else:
                lang_instruction = (
                    "Respond in Hindi"
                    if detected == "hi"
                    else "Respond in English"
                )
                messages.append({
                    "role": "user",
                    "content": f"{transcript}\n\n[LANGUAGE INSTRUCTION: {lang_instruction}]"
                })

                full_reply_sentences = []
                interrupt_event.clear()
                
                async for sentence in _stream_llm_sentences(messages):
                    if interrupt_event.is_set():
                        logger.info("Bot speech interrupted during LLM generation (text path)!")
                        break
                    full_reply_sentences.append(sentence)
                    
                    try:
                        audio = await _tts(sentence, current_lang, voice_gender)
                        if interrupt_event.is_set():
                            break
                        if audio:
                            import base64
                            audio_b64 = base64.b64encode(audio).decode("utf-8")
                            await ws.send_json({
                                "type": "bot_text_audio",
                                "text": sentence,
                                "audio": audio_b64,
                                "lang": current_lang
                            })
                        else:
                            await ws.send_json({"type": "bot_text", "text": sentence, "lang": current_lang})
                    except Exception as exc:
                        logger.error("TTS stream error on text suggestion: %s", exc)

                if full_reply_sentences:
                    reply = " ".join(full_reply_sentences)
                    messages.append({"role": "assistant", "content": reply})
                    if len(messages) > 21:
                        messages[1:] = messages[-20:]

                    cm.add_turn("assistant", reply, language=current_lang)
                    logger.info("Bot Text complete [%s]: %s", current_lang, reply)
                    
                    try:
                        await ws.send_json({
                            "type": "analytics_update",
                            "sentiment": cm.sentiment,
                            "detected_lang": current_lang,
                            "turn_count": cm.turn_count,
                            "scope_violations": len(cm.scope_violations),
                            "screening_goals": cm.get_screening_goals()
                        })
                    except Exception:
                        pass
    except Exception as e:
        logger.error("Text input worker error: %s", e)

