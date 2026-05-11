import logging
import os
from typing import Optional

from livekit.plugins import openai as lk_openai
from src.scope_validator import ScopeValidator

logger = logging.getLogger("llm_processor")


class LLMProcessor:
    """Wraps the LiveKit OpenAI LLM plugin with scope validation."""

    def __init__(self, scenario: str = "presale"):
        self.scenario = scenario
        self.scope_validator = ScopeValidator(scenario=scenario)
        self._engine = self._build_engine()

    def _build_engine(self):
        api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        base_url: Optional[str] = os.getenv("OPENAI_BASE_URL")
        model: str = os.getenv("OPENAI_MODEL", "gpt-4o")

        # Auto-detect OpenRouter keys
        if api_key and api_key.startswith("sk-or-v1-") and not base_url:
            base_url = "https://openrouter.ai/api/v1"
            model = model if model != "gpt-4o" else "openai/gpt-4o-mini"

        if not api_key:
            logger.warning("OPENAI_API_KEY not set — LLM calls will fail")

        return lk_openai.LLM(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.65,
            max_completion_tokens=512,
        )

    def get_engine(self):
        return self._engine

    def check_scope(self, user_text: str) -> bool:
        return self.scope_validator.is_in_scope(user_text)

    def check_scope_with_topic(self, user_text: str):
        """Return (in_scope: bool, topic: str | None)."""
        return self.scope_validator.check(user_text)

    def get_out_of_scope_message(self, language: str, topic: str = None) -> str:
        return self.scope_validator.get_out_of_scope_reply(language, topic)
