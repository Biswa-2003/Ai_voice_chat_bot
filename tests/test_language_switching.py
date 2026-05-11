import pytest
from src.language_detector import LanguageDetector
from src.conversation_manager import ConversationManager


class TestLanguageDetection:
    def setup_method(self):
        self.d = LanguageDetector()

    def test_english_text(self):
        assert self.d.detect("Hello, how are you?") == "en"

    def test_hindi_devanagari(self):
        assert self.d.detect("नमस्ते, कैसे हैं आप?") == "hi"

    def test_hindi_transliterated(self):
        assert self.d.detect("Namaste, aap kaise hain? Main theek hoon.") == "hi"

    def test_empty_text(self):
        assert self.d.detect("") == "en"

    def test_english_with_namaste(self):
        # Single Hindi word surrounded by English should still be checked
        result = self.d.detect("Namaste! I am interested in your product.")
        # 'namaste' is one Hindi hint word, may not cross threshold — result is en or hi
        assert result in ("en", "hi")

    def test_devanagari_mixed(self):
        assert self.d.detect("Main aapka product देखना chahta hoon") == "hi"

    def test_hindi_sentence_threshold(self):
        # Multiple Hindi hint words should cross threshold
        assert self.d.detect("Main jaanna chahta hoon, kya aap batayenge?") == "hi"


class TestExplicitSwitchDetection:
    def setup_method(self):
        self.d = LanguageDetector()

    def test_switch_to_hindi(self):
        assert self.d.is_switch_request("Hindi mein baat kariye please") == "hi"

    def test_switch_to_hindi_variant(self):
        assert self.d.is_switch_request("Speak hindi please") == "hi"

    def test_switch_to_english(self):
        assert self.d.is_switch_request("Please speak English") == "en"

    def test_switch_to_english_variant(self):
        assert self.d.is_switch_request("English please") == "en"

    def test_no_switch_request(self):
        assert self.d.is_switch_request("Tell me about your product") is None

    def test_no_switch_in_hindi(self):
        assert self.d.is_switch_request("नमस्ते") is None


class TestConversationLanguageTracking:
    def test_initial_language_is_english(self):
        cm = ConversationManager()
        assert cm.current_language == "en"
        assert cm.language_history == ["en"]

    def test_language_switch_recorded(self):
        cm = ConversationManager()
        cm.add_turn("user", "Namaste", language="hi")
        assert cm.current_language == "hi"
        assert "hi" in cm.language_history

    def test_multiple_switches(self):
        cm = ConversationManager()
        cm.add_turn("user", "Hello", language="en")
        cm.add_turn("user", "Namaste", language="hi")
        cm.add_turn("user", "Hello again", language="en")
        assert len(cm.language_history) >= 3

    def test_same_language_no_duplicate(self):
        cm = ConversationManager()
        initial_len = len(cm.language_history)
        cm.add_turn("user", "Hello", language="en")
        # Same language — should not append again
        assert len(cm.language_history) == initial_len

    def test_context_preserved_after_switch(self):
        cm = ConversationManager()
        cm.add_turn("user", "What is your product?", language="en")
        cm.add_turn("assistant", "We offer an AI voicebot.", language="en")
        cm.add_turn("user", "Kya aap Hindi mein bata sakte hain?", language="hi")
        # History should have all 3 turns
        assert cm.turn_count == 3
        assert any(t["language"] == "en" for t in cm.conversation_history)
        assert any(t["language"] == "hi" for t in cm.conversation_history)
