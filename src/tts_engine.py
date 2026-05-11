import logging
import os

from livekit.plugins import elevenlabs, openai as lk_openai

logger = logging.getLogger("tts_engine")


def get_tts_engine(language: str = "en"):
    """
    Return a TTS engine based on TTS_PROVIDER env var.

    Providers:
      sarvam     — Sarvam AI (Indian voices, works with SARVAM_API_KEY) [DEFAULT]
      elevenlabs — ElevenLabs (requires valid ELEVEN_API_KEY with TTS permissions)
      openai     — OpenAI TTS (requires direct OPENAI_API_KEY, not OpenRouter)
    """
    provider = os.getenv("TTS_PROVIDER", "sarvam").lower()

    if provider == "elevenlabs":
        return _elevenlabs_tts(language)
    if provider == "openai":
        return _openai_tts(language)
    return _sarvam_tts(language)


def _sarvam_tts(language: str):
    from src.sarvam_tts import SarvamTTS
    logger.info("Using Sarvam AI TTS, language=%s", language)
    return SarvamTTS(language=language)


def _elevenlabs_tts(language: str):
    api_key = os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY", "")
    default_voice = "l7kNoIfnJKPg7779LI2t"
    voice_id = (
        os.getenv("TTS_HI_VOICE_ID", default_voice)
        if language == "hi"
        else os.getenv("TTS_EN_IN_VOICE_ID", default_voice)
    )
    logger.info("Using ElevenLabs TTS, voice=%s", voice_id)
    return elevenlabs.TTS(
        voice_id=voice_id,
        model="eleven_multilingual_v2",
        api_key=api_key,
        voice_settings=elevenlabs.VoiceSettings(
            stability=0.55,
            similarity_boost=0.80,
            style=0.15,
            use_speaker_boost=True,
        ),
    )


def _openai_tts(language: str):
    logger.info("Using OpenAI TTS")
    instructions = (
        "Speak in a warm Indian English accent at natural pace (~150 wpm). "
        "Be polite and professional."
    )
    return lk_openai.TTS(
        model="gpt-4o-mini-tts",
        voice="shimmer",
        speed=0.95,
        instructions=instructions,
        api_key=os.getenv("OPENAI_API_KEY", ""),
    )
