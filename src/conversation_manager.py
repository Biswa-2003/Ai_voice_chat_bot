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

    def get_screening_goals(self) -> Dict[str, bool]:
        """Runs a fast, rule-based semantic parser on history to verify business qualification milestones."""
        history_text = " ".join([turn["content"].lower() for turn in self.conversation_history])
        
        if self.scenario == "presale":
            return {
                "Greeting & Welcome": any(w in history_text for w in ["welcome", "swaagat", "hello", "hi", "namaste", "priya", "aryan"]),
                "Identify Target Industry": any(w in history_text for w in ["industry", "sector", "business", "field", "kaam", "domain", "it", "tech", "retail", "finance"]),
                "Determine Team Size": any(w in history_text for w in ["size", "employee", "team", "people", "badi", "chhoti", "log", "member", "staff", "hundred", "thousand", "fifty", "ten"]),
                "Discover Key Pain Points": any(w in history_text for w in ["challenge", "pain", "problem", "difficult", "struggle", "ddikkat", "pareshani", "muskil", "slow", "error", "manual"]),
                "Offer Product Demo": any(w in history_text for w in ["schedule", "demo", "meeting", "consultation", "appointment", "connect", "baat", "call", "webinar"])
            }
        elif self.scenario == "sales":
            return {
                "Greeting & Introduction": any(w in history_text for w in ["welcome", "swaagat", "hello", "hi", "namaste", "arjun", "aryan"]),
                "Assess Current Solution": any(w in history_text for w in ["current", "solution", "system", "tool", "software", "already", "using", "use", "excel", "sheets"]),
                "Detail Product Features": any(w in history_text for w in ["feature", "capability", "benefit", "details", "integration", "api", "dashboard", "reporting", "speed"]),
                "Handle Core Objections": any(w in history_text for w in ["expensive", "cost", "think", "price", "daam", "budget", "competitor", "discount"]),
                "Schedule Closing Call": any(w in history_text for w in ["schedule", "demo", "meeting", "consultation", "appointment", "connect", "baat", "call", "close", "onboard"])
            }
        else:  # marketing
            return {
                "Greeting & Re-engage": any(w in history_text for w in ["welcome", "swaagat", "hello", "hi", "namaste", "meera", "priya"]),
                "Discover Business Goals": any(w in history_text for w in ["goal", "target", "focus", "plan", "aim", "achieve", "grow", "sales", "leads"]),
                "Share Case Study/Resource": any(w in history_text for w in ["resource", "webinar", "whitepaper", "guide", "blog", "details", "case study", "ebook", "pdf", "link"]),
                "Gauge Sales Readiness": any(w in history_text for w in ["ready", "evaluate", "buy", "interested", "sales", "introduce", "talk", "salesperson"]),
                "Collect Contact Details": any(w in history_text for w in ["contact", "email", "phone", "number", "follow up", "send"])
            }

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
            "screening_goals": self.get_screening_goals()
        }
