import re
import logging
from typing import Optional

logger = logging.getLogger("language_detector")

# Devanagari Unicode block U+0900–U+097F
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Explicit switch phrases the user might say
_SWITCH_TO_HINDI = re.compile(
    r"\b(hindi\s+mein|hindi\s+me|hindi\s+boliye|hindi\s+baat|"
    r"hindi\s+mein\s+baat|speak\s+hindi|switch\s+to\s+hindi|"
    r"hindi\s+please|hind[i]?\s+kar|devanagari|hindi\s+main)\b",
    re.IGNORECASE,
)
_SWITCH_TO_ENGLISH = re.compile(
    r"\b(english\s+mein|english\s+me|speak\s+english|switch\s+to\s+english|"
    r"english\s+please|english\s+boliye|english\s+baat|let'?s?\s+speak\s+english)\b",
    re.IGNORECASE,
)

# Hindi keyword hints (transliterated) — each match scores +1
_HINDI_HINTS = re.compile(
    r"\b(namaste|namaskar|kya|aap|main|hoon|hai|nahi|haan|kaise|kyun|kab|kahan|"
    r"achha|theek|shukriya|dhanyavaad|bhai|ji|matlab|samajh|jaanna|chahta|"
    r"batao|bataye|mujhe|hamare|aapka|kaisa|iska|uska|yahan|wahan|zaroor)\b",
    re.IGNORECASE,
)
_HINDI_HINT_THRESHOLD = 2


class LanguageDetector:
    """Detects language from text using script detection, keyword hints, and langdetect."""

    def __init__(self):
        self._langdetect_available = False
        try:
            import langdetect  # noqa: F401
            self._langdetect_available = True
        except ImportError:
            logger.warning("langdetect not installed; falling back to heuristics only")

    def detect(self, text: str) -> str:
        """Return 'hi' or 'en' for the given text."""
        if not text or not text.strip():
            return "en"

        # 1. Explicit switch request
        if _SWITCH_TO_HINDI.search(text):
            return "hi"
        if _SWITCH_TO_ENGLISH.search(text):
            return "en"

        # 2. Devanagari characters → definitely Hindi
        if _DEVANAGARI.search(text):
            return "hi"

        # 3. Hindi keyword heuristics
        matches = _HINDI_HINTS.findall(text)
        if len(matches) >= _HINDI_HINT_THRESHOLD:
            return "hi"

        # 4. Fallback: langdetect library
        if self._langdetect_available:
            try:
                import langdetect
                lang = langdetect.detect(text)
                if lang in ("hi", "mr", "ne", "gu", "pa"):
                    return "hi"
                return "en"
            except Exception:
                pass

        return "en"

    def is_switch_request(self, text: str) -> Optional[str]:
        """Return the target language if the text is an explicit switch request, else None."""
        if _SWITCH_TO_HINDI.search(text):
            return "hi"
        if _SWITCH_TO_ENGLISH.search(text):
            return "en"
        return None
