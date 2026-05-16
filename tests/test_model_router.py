import pytest
import time
from unittest.mock import patch, MagicMock
from model_router import ModelRouter, TaskType


class TestModelRouter:
    def setup_method(self):
        self.router = ModelRouter(
            local_endpoint="http://localhost:11434",
            local_model="gemma4:e4b",
            claude_cheap="claude-haiku-4-5-20251001",
            claude_fast="claude-sonnet-4-20250514",
            claude_deep="claude-opus-4-0-20250115",
            anthropic_api_key="test-key",
        )

    def test_scan_routes_to_haiku(self):
        config = self.router.resolve(TaskType.SCAN)
        assert config["provider"] == "openai"
        assert config["model"] == "claude-haiku-4-5-20251001"

    def test_contradiction_routes_to_sonnet(self):
        config = self.router.resolve(TaskType.CONTRADICTION_ANALYSIS)
        assert config["provider"] == "openai"
        assert config["model"] == "claude-sonnet-4-20250514"

    def test_insight_synthesis_routes_to_opus(self):
        config = self.router.resolve(TaskType.INSIGHT_SYNTHESIS)
        assert config["provider"] == "openai"
        assert config["model"] == "claude-opus-4-0-20250115"

    def test_maintenance_routes_to_haiku(self):
        config = self.router.resolve(TaskType.MAINTENANCE)
        assert config["provider"] == "openai"
        assert config["model"] == "claude-haiku-4-5-20251001"

    def test_reactive_routes_to_haiku(self):
        config = self.router.resolve(TaskType.REACTIVE_TRIAGE)
        assert config["provider"] == "openai"
        assert config["model"] == "claude-haiku-4-5-20251001"

    def test_skill_creation_routes_to_sonnet(self):
        config = self.router.resolve(TaskType.SKILL_CREATION)
        assert config["provider"] == "openai"
        assert config["model"] == "claude-sonnet-4-20250514"

    @patch("model_router.requests.get")
    def test_ollama_health_check_succeeds(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        assert self.router.is_local_available() is True

    @patch("model_router.requests.get")
    def test_ollama_health_check_fails(self, mock_get):
        mock_get.side_effect = ConnectionError()
        assert self.router.is_local_available() is False


class TestBudgetCap:
    def setup_method(self):
        self.router = ModelRouter(
            local_endpoint="http://localhost:11434",
            local_model="gemma4:e4b",
            claude_cheap="claude-haiku-4-5-20251001",
            claude_fast="claude-sonnet-4-20250514",
            claude_deep="claude-opus-4-0-20250115",
            anthropic_api_key="test-key",
            daily_budget=0.50,
        )

    @patch("model_router.requests.get")
    def test_budget_exceeded_falls_back_to_local(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        self.router.record_spend(0.51)
        config = self.router.resolve(TaskType.CONTRADICTION_ANALYSIS)
        assert config["provider"] == "openai"

    @patch("model_router.requests.get")
    def test_budget_exceeded_local_down_returns_none(self, mock_get):
        mock_get.side_effect = ConnectionError()
        self.router.record_spend(0.51)
        config = self.router.resolve(TaskType.CONTRADICTION_ANALYSIS)
        assert config is None

    def test_budget_resets_daily(self):
        self.router.record_spend(0.51)
        self.router._spend_date = "2026-01-01"
        assert self.router.is_budget_exceeded() is False

    def test_budget_not_exceeded(self):
        self.router.record_spend(0.10)
        assert self.router.is_budget_exceeded() is False

    def test_record_spend_accumulates(self):
        self.router.record_spend(0.20)
        self.router.record_spend(0.20)
        self.router.record_spend(0.15)
        assert self.router.is_budget_exceeded() is True
