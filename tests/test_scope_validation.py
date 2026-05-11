import pytest
from src.scope_validator import ScopeValidator


class TestPresaleScope:
    def setup_method(self):
        self.v = ScopeValidator(scenario="presale")

    # In-scope
    def test_product_inquiry_in_scope(self):
        assert self.v.is_in_scope("I want to know about your product") is True

    def test_schedule_meeting_in_scope(self):
        assert self.v.is_in_scope("Can you schedule a meeting with your team?") is True

    def test_use_case_in_scope(self):
        assert self.v.is_in_scope("What are the main use cases for your platform?") is True

    def test_company_size_in_scope(self):
        assert self.v.is_in_scope("We have a team of 50 people") is True

    # Out-of-scope
    def test_price_out_of_scope(self):
        in_scope, topic = self.v.check("What is the price?")
        assert in_scope is False
        assert topic == "pricing"

    def test_discount_out_of_scope(self):
        in_scope, topic = self.v.check("Can I get a discount?")
        assert in_scope is False
        assert topic == "pricing"

    def test_hindi_price_out_of_scope(self):
        in_scope, topic = self.v.check("Kitna cost karega?")
        assert in_scope is False
        assert topic == "pricing"

    def test_contract_out_of_scope(self):
        in_scope, topic = self.v.check("Let's negotiate the contract terms")
        assert in_scope is False
        assert topic == "contract_negotiation"

    def test_competitor_out_of_scope(self):
        in_scope, topic = self.v.check("How do you compare versus your competitor?")
        assert in_scope is False
        assert topic == "competitor_analysis"

    def test_order_out_of_scope(self):
        in_scope, topic = self.v.check("I want to place an order now")
        assert in_scope is False
        assert topic == "order_processing"


class TestSalesScope:
    def setup_method(self):
        self.v = ScopeValidator(scenario="sales")

    def test_feature_in_scope(self):
        assert self.v.is_in_scope("Tell me about the dashboard features") is True

    def test_case_study_in_scope(self):
        assert self.v.is_in_scope("Do you have any case studies to share?") is True

    def test_pricing_out_of_scope(self):
        in_scope, topic = self.v.check("What are the pricing plans?")
        assert in_scope is False
        assert topic == "pricing"

    def test_invoice_out_of_scope(self):
        in_scope, topic = self.v.check("Please send me an invoice")
        assert in_scope is False
        assert topic == "order_processing"


class TestMarketingScope:
    def setup_method(self):
        self.v = ScopeValidator(scenario="marketing")

    def test_success_story_in_scope(self):
        assert self.v.is_in_scope("Do you have any customer success stories?") is True

    def test_webinar_in_scope(self):
        assert self.v.is_in_scope("Are there any upcoming webinars?") is True

    def test_pricing_out_of_scope(self):
        in_scope, topic = self.v.check("What does it cost per month?")
        assert in_scope is False
        assert topic == "pricing"


class TestOutOfScopeMessages:
    def test_english_pricing_message(self):
        v = ScopeValidator(scenario="presale")
        msg = v.get_out_of_scope_reply("en", "pricing")
        assert "sales team" in msg.lower() or "pricing" in msg.lower()

    def test_hindi_pricing_message(self):
        v = ScopeValidator(scenario="presale")
        msg = v.get_out_of_scope_reply("hi", "pricing")
        # Should contain Hindi or transliterated text
        assert len(msg) > 20

    def test_fallback_message(self):
        v = ScopeValidator(scenario="presale")
        msg = v.get_out_of_scope_reply("en")
        assert len(msg) > 0
