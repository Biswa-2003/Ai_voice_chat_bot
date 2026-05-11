"""Central settings loaded from environment variables."""
import os

# LiveKit
LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_AGENT_NAME: str = os.getenv("LIVEKIT_AGENT_NAME", "voicebot")
LIVEKIT_AGENT_PORT: int = int(os.getenv("LIVEKIT_AGENT_PORT", "0"))

# LLM
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.65"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "512"))

# STT
DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
STT_MODEL: str = os.getenv("STT_MODEL", "nova-3")

# TTS
ELEVEN_API_KEY: str = os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY", "")
TTS_EN_IN_VOICE_ID: str = os.getenv("TTS_EN_IN_VOICE_ID", "9BWtsMINqrJLrRacOk9x")
TTS_HI_VOICE_ID: str = os.getenv("TTS_HI_VOICE_ID", "9BWtsMINqrJLrRacOk9x")
TTS_MODEL: str = os.getenv("TTS_MODEL", "eleven_multilingual_v2")

# Sarvam AI (optional — for native Hindi TTS/STT)
SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")

# App behaviour
SCENARIO: str = os.getenv("SCENARIO", "presale")
DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
LOG_DIR: str = os.getenv("LOG_DIR", "logs")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
