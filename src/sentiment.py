import re
from typing import Literal

SentimentType = Literal["positive", "neutral", "negative"]

_POSITIVE_EN = re.compile(
    r"\b(great|good|excellent|awesome|perfect|thank|thanks|helpful|love|amazing|"
    r"wonderful|fantastic|nice|happy|pleased|satisfied|appreciate|brilliant|superb)\b",
    re.IGNORECASE,
)
_NEGATIVE_EN = re.compile(
    r"\b(bad|terrible|awful|horrible|disappointed|frustrated|angry|upset|"
    r"useless|worst|hate|problem|issue|wrong|not\s+working|broken|fail|annoyed)\b",
    re.IGNORECASE,
)

# Hindi positive/negative keywords (transliterated + Devanagari)
_POSITIVE_HI = re.compile(
    r"(धन्यवाद|अच्छा|बढ़िया|शानदार|bahut\s+accha|shukriya|dhanyavaad|badhiya|shandar|"
    r"khoob|zabardast|mast|wah)",
    re.IGNORECASE,
)
_NEGATIVE_HI = re.compile(
    r"(बुरा|समस्या|परेशान|गुस्सा|nahi\s+chal\s+raha|buri|pareshaan|gussa|dikkat|"
    r"problem\s+hai|kharab|galat)",
    re.IGNORECASE,
)


def analyze_sentiment(text: str) -> SentimentType:
    """Return positive/neutral/negative sentiment for the given text."""
    pos = bool(_POSITIVE_EN.search(text)) or bool(_POSITIVE_HI.search(text))
    neg = bool(_NEGATIVE_EN.search(text)) or bool(_NEGATIVE_HI.search(text))
    if pos and not neg:
        return "positive"
    if neg and not pos:
        return "negative"
    return "neutral"
