"""
STT engine tests — verifies configuration without live API calls.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestSTTEngineConfig:
    def test_get_stt_engine_returns_object(self):
        mock_stt = MagicMock()
        with patch("livekit.plugins.deepgram.STT", return_value=mock_stt) as mock_cls:
            from src.stt_engine import get_stt_engine
            engine = get_stt_engine()
            assert engine is not None
            mock_cls.assert_called_once()

    def test_stt_uses_nova3_model(self):
        with patch("livekit.plugins.deepgram.STT", return_value=MagicMock()) as mock_cls:
            from src.stt_engine import get_stt_engine
            get_stt_engine()
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs.get("model") == "nova-3"

    def test_stt_detect_language_enabled(self):
        with patch("livekit.plugins.deepgram.STT", return_value=MagicMock()) as mock_cls:
            from src.stt_engine import get_stt_engine
            get_stt_engine()
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs.get("detect_language") is True

    def test_stt_interim_results_enabled(self):
        with patch("livekit.plugins.deepgram.STT", return_value=MagicMock()) as mock_cls:
            from src.stt_engine import get_stt_engine
            get_stt_engine()
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs.get("interim_results") is True

    def test_stt_smart_format_enabled(self):
        with patch("livekit.plugins.deepgram.STT", return_value=MagicMock()) as mock_cls:
            from src.stt_engine import get_stt_engine
            get_stt_engine()
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs.get("smart_format") is True


class TestTTSEngineConfig:
    def test_get_tts_engine_returns_object(self):
        mock_tts = MagicMock()
        with patch("livekit.plugins.elevenlabs.TTS", return_value=mock_tts):
            with patch("livekit.plugins.elevenlabs.VoiceSettings", return_value=MagicMock()):
                from src.tts_engine import get_tts_engine
                engine = get_tts_engine()
                assert engine is not None

    def test_tts_uses_multilingual_model(self):
        with patch("livekit.plugins.elevenlabs.TTS", return_value=MagicMock()) as mock_cls:
            with patch("livekit.plugins.elevenlabs.VoiceSettings", return_value=MagicMock()):
                from src.tts_engine import get_tts_engine
                get_tts_engine()
                call_kwargs = mock_cls.call_args.kwargs
                assert "multilingual" in (call_kwargs.get("model") or "")

    def test_tts_english_voice_env_override(self, monkeypatch):
        monkeypatch.setenv("TTS_EN_IN_VOICE_ID", "custom_voice_id_123")
        with patch("livekit.plugins.elevenlabs.TTS", return_value=MagicMock()) as mock_cls:
            with patch("livekit.plugins.elevenlabs.VoiceSettings", return_value=MagicMock()):
                from src.tts_engine import get_tts_engine
                import importlib
                import src.tts_engine
                importlib.reload(src.tts_engine)
                src.tts_engine.get_tts_engine(language="en")
                call_kwargs = mock_cls.call_args.kwargs
                assert call_kwargs.get("voice_id") == "custom_voice_id_123"
