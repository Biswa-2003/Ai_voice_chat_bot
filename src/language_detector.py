"""
Bilingual language detector — English vs Hindi (including Hinglish/romanized Hindi).

Detection pipeline (ordered by confidence):
  1. Explicit switch request phrases
  2. Devanagari Unicode characters → definitely Hindi
  3. Strong Hindi-only words (1 match sufficient)
  4. Weak Hindi hint words (3+ matches)
  5. langdetect fallback (Bayesian classifier)
"""
from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger("language_detector")

# ── Devanagari block U+0900–U+097F ──────────────────────────────────────────
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# ── Explicit switch requests ──────────────────────────────────────────────────
_SWITCH_TO_HINDI = re.compile(
    r"\b(hindi\s*mein|hindi\s*me\b|hindi\s*boliye|hindi\s*baat|"
    r"hindi\s*main|speak\s*hindi|switch\s*to\s*hindi|hindi\s*please|"
    r"hindi\s*kar|hindi\s*mein\s*baat|ab\s*hindi|hindi\s*bol|"
    r"mujhe\s*hindi|hindi\s*chahiye)\b",
    re.IGNORECASE,
)
_SWITCH_TO_ENGLISH = re.compile(
    r"\b(english\s*mein|english\s*me\b|speak\s*english|switch\s*to\s*english|"
    r"english\s*please|english\s*boliye|english\s*baat|"
    r"let'?s?\s*speak\s*english|english\s*main|ab\s*english)\b",
    re.IGNORECASE,
)

# ── Strong Hindi-only words (1 match → Hindi) ─────────────────────────────────
# These words virtually never appear in natural English sentences.
_STRONG_HINDI = re.compile(
    r"\b("
    # Common spoken Hindi words
    r"haan|nahi|nahin|theek|achha|acha|accha|shukriya|dhanyavaad|dhanyawad|"
    r"namaste|namaskar|sahib|bhai\s*sahab|yaar|dost|"
    # Questions
    r"kya\s+hai|kaise\s+ho|kya\s+haal|kaisa\s+hai|kahan\s+hai|"
    r"kyun\s+nahi|kab\s+tak|kitna\s+time|"
    # Common phrases
    r"thoda\s+sa|bahut\s+accha|bilkul\s+sahi|koi\s+baat\s+nahi|"
    r"theek\s+hai|sab\s+theek|aap\s+kaise|main\s+samajh|"
    r"mujhe\s+batao|please\s+batao|kya\s+aap|aap\s+bata|"
    r"ek\s+minute|ek\s+second|zaroor|bilkul|jawab\s+do|"
    # Verbs (common in speech)
    r"chahiye|chahta|chahti|milega|milegi|karunga|karenge|"
    r"samjha|samjhi|suniye|dekho|dekhi|jaiye|"
    # Identity / pronouns in Hindi context
    r"main\s+hoon|aap\s+hain|woh\s+hai|hum\s+hain|"
    r"mera\s+naam|aapka\s+naam|unka\s+naam|"
    # Hindi connectors / particles
    r"lekin\s|magar\s|isliye\s|isiliye\s|kyonki\s|"
    r"phir\s+bhi|ab\s+tak|abhi\s+tak|fir\s+se|dobara"
    r")\b",
    re.IGNORECASE,
)

# ── Weak Hindi hint words (3+ matches → Hindi) ───────────────────────────────
_WEAK_HINDI = re.compile(
    r"\b("
    r"kya|aap|main|mein|hai|hain|hoon|nahi|haan|kaise|kyun|kab|kahan|"
    r"achha|theek|shukriya|bhai|ji\b|matlab|samajh|jaanna|chahta|"
    r"batao|bataye|mujhe|hamare|aapka|kaisa|iska|uska|yahan|wahan|zaroor|"
    r"bahut|bohot|thoda|zyada|kam|accha|bilkul|bas|toh|na\b|"
    r"hoga|hogi|karega|karegi|bolna|sunna|dekhna|jaana|aana|"
    r"unka|unki|unhe|humara|tumhara|tera|meri|teri|uski|uska|"
    r"phir|fir|lekin|magar|aur\b|ya\b|agar|jab|tab|woh|yeh|"
    r"abhi|kabhi|sab|kuch|kitna|kitni|kaafi|zyaada|"
    r"pehle|baad|saath|bina|liye|wala|wali|waale|"
    r"gaya|gayi|gaye|raha|rahi|rahe|tha|thi|the|"
    r"padh|likh|bol|sun|dekh|ja|aa|kar|le|de|"
    r"karo|karna|karta|karti|karein|kariye|"
    r"samjha|samjhe|bata|batao|suno|dekho|"
    r"dono|teeno|sab\s+log|har\s+koi|koi\s+bhi|"
    r"kal|aaj|parso|subah|shaam|raat|din|mahina|saal|"
    r"ghar|daftar|office\s+mein|kaam|paisa|rupaye|"
    r"acchi|buri|bada|chota|lamba|chhota|naya|purana"
    r")\b",
    re.IGNORECASE,
)
_WEAK_THRESHOLD = 3


class LanguageDetector:
    """Detects Hindi vs English from transcribed speech text."""

    def __init__(self):
        self._langdetect_ok = False
        try:
            import langdetect  # noqa: F401
            self._langdetect_ok = True
        except ImportError:
            logger.warning("langdetect not available; using heuristics only")

    def detect(self, text: str) -> str:
        """Return 'hi' or 'en'."""
        if not text or not text.strip():
            return "en"

        # 1. Explicit switch request
        if _SWITCH_TO_HINDI.search(text):
            return "hi"
        if _SWITCH_TO_ENGLISH.search(text):
            return "en"

        # 2. Devanagari → definitely Hindi
        if _DEVANAGARI.search(text):
            return "hi"

        # 3. Strong Hindi-only words (1 hit = Hindi)
        if _STRONG_HINDI.search(text):
            return "hi"

        # 4. Weak Hindi hints (3+ hits = Hindi)
        hits = len(_WEAK_HINDI.findall(text))
        if hits >= _WEAK_THRESHOLD:
            return "hi"

        # 5. langdetect fallback
        if self._langdetect_ok:
            try:
                import langdetect
                lang = langdetect.detect(text)
                if lang in ("hi", "mr", "ne", "gu", "pa", "ur"):
                    return "hi"
            except Exception:
                pass

        return "en"

    def is_switch_request(self, text: str) -> Optional[str]:
        """Return 'hi', 'en', or None."""
        if _SWITCH_TO_HINDI.search(text):
            return "hi"
        if _SWITCH_TO_ENGLISH.search(text):
            return "en"
        return None
