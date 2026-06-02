"""
LLM processor — direct OpenAI / OpenRouter call (no LiveKit dependency).
Used by voice_server.py for scope validation helpers.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from src.scope_validator import ScopeValidator

logger = logging.getLogger("llm_processor")


class LLMProcessor:
    """Wraps OpenAI with scope validation (no LiveKit)."""

    def __init__(self, scenario: str = "presale"):
        self.scenario = scenario
        self.scope_validator = ScopeValidator(scenario=scenario)

    @property
    def model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o")

    @property
    def api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")

    @property
    def base_url(self) -> Optional[str]:
        url = os.getenv("OPENAI_BASE_URL")
        key = self.api_key or ""
        if key.startswith("sk-or-v1-") and not url:
            return "https://openrouter.ai/api/v1"
        return url

    def check_scope(self, user_text: str) -> bool:
        return self.scope_validator.is_in_scope(user_text)

    def check_scope_with_topic(self, user_text: str):
        return self.scope_validator.check(user_text)

    def get_out_of_scope_message(self, language: str, topic: str = None) -> str:
        return self.scope_validator.get_out_of_scope_reply(language, topic)
