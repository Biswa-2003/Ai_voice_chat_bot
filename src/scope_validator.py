import re
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Per-scenario out-of-scope keyword patterns (English + Hindi transliteration
# + Devanagari).  Returns (in_scope: bool, topic: str).
# ---------------------------------------------------------------------------

_PRICING_PATTERN = re.compile(
    r"\b(price|pricing|cost|costs|quote|discount|cheap|expensive|afford|budget|"
    r"how\s+much|kitna|कितना|cost\s+kar|daam|rate\b|paisa|paise|rupee|rupees)\b",
    re.IGNORECASE,
)
_CONTRACT_PATTERN = re.compile(
    r"\b(contract|negotiate|negotiation|legal|compliance|terms\s+and\s+conditions|"
    r"liability|warranty|sla|agreement|sign|signing|contract\s+terms|"
    r"anubandh|kanoon|kanooni|shart)\b",
    re.IGNORECASE,
)
_ORDER_PATTERN = re.compile(
    r"\b(order|purchase|buy|checkout|invoice|payment|billing|subscription\s+now|"
    r"process\s+order|khareedna|khareed|bill\b|kharidar)\b",
    re.IGNORECASE,
)
_COMPETITOR_PATTERN = re.compile(
    r"\b(competitor|competing|vs\b|versus|better\s+than|worse\s+than|comparison|"
    r"compare\s+with|muqabala|pratiyogi)\b",
    re.IGNORECASE,
)
_TIMELINE_PATTERN = re.compile(
    r"\b(guarantee\s+delivery|guaranteed\s+by|commit\s+to\s+deadline|"
    r"by\s+exactly\s+when|specific\s+timeline|samay\s+pakka|pakka\s+date)\b",
    re.IGNORECASE,
)
_CONFIDENTIAL_PATTERN = re.compile(
    r"\b(confidential\s+client|client\s+data\s+of|nda\s+info|secret\s+deal|"
    r"internal\s+data|gairein\s+jaankari)\b",
    re.IGNORECASE,
)

# Scenario-specific blocked patterns: list of (compiled_regex, topic_label)
_SCENARIO_PATTERNS = {
    "presale": [
        (_PRICING_PATTERN, "pricing"),
        (_CONTRACT_PATTERN, "contract_negotiation"),
        (_ORDER_PATTERN, "order_processing"),
        (_COMPETITOR_PATTERN, "competitor_analysis"),
        (_TIMELINE_PATTERN, "implementation_timeline"),
    ],
    "sales": [
        (_ORDER_PATTERN, "order_processing"),
        (_PRICING_PATTERN, "pricing"),
        (_CONTRACT_PATTERN, "contract_negotiation"),
        (_CONFIDENTIAL_PATTERN, "confidential_info"),
    ],
    "marketing": [
        (_PRICING_PATTERN, "pricing"),
        (_CONTRACT_PATTERN, "contract_negotiation"),
        (_ORDER_PATTERN, "order_processing"),
        (_CONFIDENTIAL_PATTERN, "confidential_info"),
    ],
}

_OUT_OF_SCOPE_MESSAGES = {
    "pricing": {
        "en": (
            "That's a great question about pricing! Pricing details are best discussed "
            "with our sales team who can give you a customised proposal. "
            "Shall I arrange a quick call for you?"
        ),
        "hi": (
            "Pricing ke baare mein hamare sales team se baat karna sabse behtar rahega — "
            "woh aapke liye ek customised proposal taiyaar kar sakte hain. "
            "Kya main unse aapki meeting fix kar doon?"
        ),
    },
    "contract_negotiation": {
        "en": (
            "Contract and legal terms are handled by our dedicated team. "
            "I'd be happy to connect you with the right person. "
            "May I schedule a call?"
        ),
        "hi": (
            "Contract aur legal matters ke liye hamare specialist team se baat karna zaroori hai. "
            "Kya main aapke liye unse meeting arrange kar sakta hoon?"
        ),
    },
    "order_processing": {
        "en": (
            "Order processing and transactions are managed directly by our sales team. "
            "I can set up a conversation with them — would that work for you?"
        ),
        "hi": (
            "Orders aur transactions ke liye hamare sales team se seedha baat karni hogi. "
            "Kya main unse aapki meeting set kar doon?"
        ),
    },
    "competitor_analysis": {
        "en": (
            "I'm not in a position to comment on other products, "
            "but I'd love to walk you through what makes our solution stand out. "
            "Would that be helpful?"
        ),
        "hi": (
            "Mujhe doosre products ke baare mein tippani karna theek nahi lagta, "
            "lekin main aapko hamare solution ki khaasiyat zaroor bata sakta hoon. "
            "Kya aap yeh jaanna chahenge?"
        ),
    },
    "implementation_timeline": {
        "en": (
            "Specific delivery commitments need to come from our project team. "
            "I can connect you with them to discuss realistic timelines. "
            "Shall I arrange that?"
        ),
        "hi": (
            "Specific delivery timelines ke liye hamare project team se baat karna padega. "
            "Kya main aapki unse meeting set kar sakta hoon?"
        ),
    },
    "confidential_info": {
        "en": (
            "I'm not able to share confidential client information, "
            "but I can provide general case studies and success metrics. "
            "Would you like to hear about those?"
        ),
        "hi": (
            "Confidential client information share karna mere liye possible nahi hai, "
            "lekin main aapko general success stories zaroor bata sakta hoon. "
            "Kya aap sunna chahenge?"
        ),
    },
}

_DEFAULT_OUT_OF_SCOPE = {
    "en": (
        "That's slightly outside what I can help with directly. "
        "Let me connect you with the right team who can assist you further. "
        "Shall I arrange that?"
    ),
    "hi": (
        "Yeh topic mere scope se thoda bahar hai. "
        "Main aapko sahi team se connect kar sakta hoon — kya woh theek rahega?"
    ),
}


class ScopeValidator:
    """Validates user input against scenario-specific scope boundaries."""

    def __init__(self, scenario: str = "presale"):
        self.scenario = scenario if scenario in _SCENARIO_PATTERNS else "presale"
        self._patterns = _SCENARIO_PATTERNS[self.scenario]

    def check(self, text: str) -> Tuple[bool, Optional[str]]:
        """Return (in_scope, topic_label). topic_label is None if in scope."""
        for pattern, topic in self._patterns:
            if pattern.search(text):
                return False, topic
        return True, None

    def is_in_scope(self, text: str) -> bool:
        in_scope, _ = self.check(text)
        return in_scope

    def get_out_of_scope_reply(self, language: str, topic: Optional[str] = None) -> str:
        lang = language if language in ("en", "hi") else "en"
        messages = _OUT_OF_SCOPE_MESSAGES.get(topic or "", _DEFAULT_OUT_OF_SCOPE)
        return messages.get(lang, messages.get("en", _DEFAULT_OUT_OF_SCOPE["en"]))
