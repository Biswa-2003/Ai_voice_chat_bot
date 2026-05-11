import logging
import os

from livekit.plugins import deepgram

logger = logging.getLogger("stt_engine")


def get_stt_engine():
    """
    Return a Deepgram STT configured for bilingual Indian speech.

    Deepgram nova-3 with language='multi' handles English/Hindi code-switching
    in streaming mode.  detect_language is incompatible with streaming — the
    language is determined per-turn by our LanguageDetector instead.
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        logger.warning("DEEPGRAM_API_KEY not set — STT may fail at runtime")

    return deepgram.STT(
        model="nova-3",
        language="multi",
        interim_results=True,
        smart_format=True,
        punctuate=True,
    )
