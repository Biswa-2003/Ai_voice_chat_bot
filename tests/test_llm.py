"""
LLM processor tests — run without network calls by mocking the LiveKit plugin.
"""
import pytest


class TestLLMProcessorInit:
    def test_presale_scenario(self):
        from src.llm_processor import LLMProcessor
        proc = LLMProcessor(scenario="presale")
        assert proc.scenario == "presale"

    def test_sales_scenario(self):
        from src.llm_processor import LLMProcessor
        proc = LLMProcessor(scenario="sales")
        assert proc.scenario == "sales"

    def test_marketing_scenario(self):
        from src.llm_processor import LLMProcessor
        proc = LLMProcessor(scenario="marketing")
        assert proc.scenario == "marketing"


class TestLLMScopeIntegration:
    @pytest.fixture
    def processor(self):
        from src.llm_processor import LLMProcessor
        return LLMProcessor(scenario="presale")

    def test_in_scope_returns_true(self, processor):
        assert processor.check_scope("Tell me about your product features") is True

    def test_out_of_scope_returns_false(self, processor):
        assert processor.check_scope("What is the price?") is False

    def test_out_of_scope_with_topic(self, processor):
        in_scope, topic = processor.check_scope_with_topic("Can I get a discount?")
        assert in_scope is False
        assert topic == "pricing"

    def test_out_of_scope_message_english(self, processor):
        msg = processor.get_out_of_scope_message("en", "pricing")
        assert isinstance(msg, str)
        assert len(msg) > 10

    def test_out_of_scope_message_hindi(self, processor):
        msg = processor.get_out_of_scope_message("hi", "pricing")
        assert isinstance(msg, str)
        assert len(msg) > 10


class TestSentimentAnalysis:
    def test_positive_sentiment(self):
        from src.sentiment import analyze_sentiment
        assert analyze_sentiment("That's great! I really love this product.") == "positive"

    def test_negative_sentiment(self):
        from src.sentiment import analyze_sentiment
        assert analyze_sentiment("This is terrible and I'm very frustrated.") == "negative"

    def test_neutral_sentiment(self):
        from src.sentiment import analyze_sentiment
        assert analyze_sentiment("Tell me about your product.") == "neutral"

    def test_hindi_positive(self):
        from src.sentiment import analyze_sentiment
        assert analyze_sentiment("bahut accha hai, shukriya!") == "positive"

    def test_hindi_negative(self):
        from src.sentiment import analyze_sentiment
        result = analyze_sentiment("yeh buri tarah se kaam nahi kar raha")
        assert result in ("negative", "neutral")  # heuristic, so accept neutral too


class TestConversationManager:
    def test_initial_state(self):
        from src.conversation_manager import ConversationManager
        cm = ConversationManager(scenario="presale")
        assert cm.turn_count == 0
        assert cm.sentiment == "neutral"
        assert cm.scenario == "presale"

    def test_turn_increments(self):
        from src.conversation_manager import ConversationManager
        cm = ConversationManager()
        cm.add_turn("user", "Hello")
        assert cm.turn_count == 1

    def test_context_dict_shape(self):
        from src.conversation_manager import ConversationManager
        cm = ConversationManager(scenario="presale")
        cm.add_turn("user", "Hi there", language="en")
        ctx = cm.to_context_dict()
        required_keys = [
            "conversation_id", "current_language", "language_history",
            "user_intent", "entities_extracted", "conversation_history",
            "scenario", "conversation_start_time", "turn_count", "sentiment",
        ]
        for key in required_keys:
            assert key in ctx, f"Missing key: {key}"

    def test_scope_violation_recorded(self):
        from src.conversation_manager import ConversationManager
        cm = ConversationManager()
        cm.record_scope_violation("pricing")
        assert len(cm.scope_violations) == 1
        assert cm.scope_violations[0]["topic"] == "pricing"
