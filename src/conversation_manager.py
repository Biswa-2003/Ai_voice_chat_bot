import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.sentiment import analyze_sentiment


class ConversationManager:
    """Manages full conversation state as defined in the project spec (section 3.5)."""

    def __init__(self, scenario: str = "presale"):
        self.scenario = scenario
        self.conversation_id: str = str(uuid.uuid4())
        self.current_language: str = "en"
        self.language_history: List[str] = ["en"]
        self.user_intent: str = ""
        self.entities_extracted: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.conversation_start_time: datetime = datetime.now()
        self.turn_count: int = 0
        self.sentiment: str = "neutral"
        self.topic_categories: List[str] = []
        self.scope_violations: List[str] = []

    # ------------------------------------------------------------------
    # Prompt loading
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "config",
            "prompts",
            f"{self.scenario}_system_prompt.txt",
        )
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()

        # Minimal built-in fallback
        return (
            "You are a professional AI assistant. "
            "Be polite, respectful, and helpful. "
            "Respond in the same language the user speaks (English or Hindi). "
            "Use natural Indian English phrasing."
        )

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    def add_turn(
        self,
        role: str,
        content: str,
        language: Optional[str] = None,
        intent: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> None:
        """Record a single conversation turn and update all state fields."""
        self.turn_count += 1

        # Language tracking
        if language and language != self.current_language:
            self.current_language = language
            self.language_history.append(language)
        elif language and not self.language_history:
            self.language_history.append(language)

        # Sentiment (user turns only)
        if role == "user":
            self.sentiment = analyze_sentiment(content)
            if intent:
                self.user_intent = intent
            if topic and topic not in self.topic_categories:
                self.topic_categories.append(topic)

        self.conversation_history.append(
            {
                "role": role,
                "content": content,
                "language": self.current_language,
                "timestamp": datetime.now().isoformat(),
                "sentiment": self.sentiment if role == "user" else None,
                "intent": intent,
            }
        )

    def record_scope_violation(self, topic: str) -> None:
        self.scope_violations.append(
            {"topic": topic, "timestamp": datetime.now().isoformat()}
        )

    # ------------------------------------------------------------------
    # Context export (spec section 3.5 shape)
    # ------------------------------------------------------------------

    def to_context_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "current_language": self.current_language,
            "language_history": self.language_history,
            "user_intent": self.user_intent,
            "entities_extracted": self.entities_extracted,
            "conversation_history": self.conversation_history,
            "scenario": self.scenario,
            "conversation_start_time": self.conversation_start_time,
            "turn_count": self.turn_count,
            "sentiment": self.sentiment,
            "topic_categories": self.topic_categories,
            "scope_violations": self.scope_violations,
        }
