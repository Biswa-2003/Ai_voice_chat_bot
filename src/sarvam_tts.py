"""
Sarvam AI TTS adapter for LiveKit Agents (v1.5+).
"""
from __future__ import annotations

import base64
import logging
import os

import aiohttp

from livekit.agents import tts, utils
from livekit.agents.types import APIConnectOptions

logger = logging.getLogger("sarvam_tts")

_API_URL = "https://api.sarvam.ai/text-to-speech"
_MODEL   = "bulbul:v2"
_SAMPLE_RATE = 22050

_SPEAKERS = {
    "en": os.getenv("SARVAM_EN_SPEAKER", "anushka"),
    "hi": os.getenv("SARVAM_HI_SPEAKER", "anushka"),
}


class SarvamTTS(tts.TTS):
    """LiveKit TTS adapter for Sarvam AI — Indian English and Hindi voices."""

    def __init__(self, language: str = "en"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=_SAMPLE_RATE,
            num_channels=1,
        )
        self._language = language
        self._api_key = os.getenv("SARVAM_API_KEY", "")
        if not self._api_key:
            logger.warning("SARVAM_API_KEY not set")

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = APIConnectOptions(),
    ) -> "SarvamChunkedStream":
        return SarvamChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            language=self._language,
            api_key=self._api_key,
        )


class SarvamChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: SarvamTTS,
        input_text: str,
        conn_options: APIConnectOptions,
        language: str,
        api_key: str,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._language = language
        self._api_key = api_key

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        lang_code = "hi-IN" if self._language == "hi" else "en-IN"
        speaker   = _SPEAKERS.get(self._language, "anushka")

        payload = {
            "inputs": [self._input_text],
            "target_language_code": lang_code,
            "speaker": speaker,
            "model": _MODEL,
        }
        headers = {"api-subscription-key": self._api_key}

        async with aiohttp.ClientSession() as session:
            async with session.post(_API_URL, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()

        wav_bytes: bytes = base64.b64decode(data["audios"][0])

        request_id = utils.shortuuid()
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=_SAMPLE_RATE,
            num_channels=1,
            mime_type="audio/wav",
        )
        output_emitter.push(wav_bytes)
