from enum import Enum
from datetime import date
import requests


class TaskType(Enum):
    SCAN = "scan"
    MAINTENANCE = "maintenance"
    REACTIVE_TRIAGE = "reactive_triage"
    CONTRADICTION_ANALYSIS = "contradiction_analysis"
    SKILL_CREATION = "skill_creation"
    INSIGHT_SYNTHESIS = "insight_synthesis"


_LOCAL_TASKS = {TaskType.SCAN, TaskType.MAINTENANCE, TaskType.REACTIVE_TRIAGE}
_DEEP_TASKS = {TaskType.INSIGHT_SYNTHESIS}


class ModelRouter:
    def __init__(
        self,
        local_endpoint: str,
        local_model: str,
        claude_cheap: str,
        claude_fast: str,
        claude_deep: str,
        anthropic_api_key: str,
        daily_budget: float = 0.50,
    ):
        self._local_endpoint = local_endpoint
        self._local_model = local_model
        self._claude_cheap = claude_cheap
        self._claude_fast = claude_fast
        self._claude_deep = claude_deep
        self._api_key = anthropic_api_key
        self._daily_budget = daily_budget
        self._daily_spend = 0.0
        self._spend_date = str(date.today())

    def is_local_available(self) -> bool:
        try:
            resp = requests.get(self._local_endpoint, timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def _local_config(self) -> dict:
        base = self._local_endpoint.rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        return {
            "provider": "openai",
            "base_url": base,
            "model": self._local_model,
            "api_key": "ollama",
        }

    def _cheap_config(self) -> dict:
        # Use openai provider with Anthropic endpoint - Hermes's anthropic
        # provider has broken credential resolution (sends Bearer None)
        return {
            "provider": "openai",
            "base_url": "https://api.anthropic.com/v1/",
            "model": self._claude_cheap,
            "api_key": self._api_key,
        }

    def _fast_config(self) -> dict:
        return {
            "provider": "openai",
            "base_url": "https://api.anthropic.com/v1/",
            "model": self._claude_fast,
            "api_key": self._api_key,
        }

    def _deep_config(self) -> dict:
        return {
            "provider": "openai",
            "base_url": "https://api.anthropic.com/v1/",
            "model": self._claude_deep,
            "api_key": self._api_key,
        }

    def record_spend(self, amount: float) -> None:
        today = str(date.today())
        if self._spend_date != today:
            self._daily_spend = 0.0
            self._spend_date = today
        self._daily_spend += amount

    def is_budget_exceeded(self) -> bool:
        today = str(date.today())
        if self._spend_date != today:
            return False
        return self._daily_spend >= self._daily_budget

    def resolve(self, task_type: TaskType) -> dict | None:
        # Budget exceeded: try local fallback regardless of task type
        if self.is_budget_exceeded():
            if self.is_local_available():
                return self._local_config()
            return None

        # Haiku for mechanical tasks (scan, maintenance, triage)
        # Sonnet for reasoning tasks (contradictions, skill creation)
        # Opus for synthesis
        # Local model reserved as budget-exceeded fallback only
        if task_type in _DEEP_TASKS:
            return self._deep_config()

        if task_type in _LOCAL_TASKS:
            return self._cheap_config()

        return self._fast_config()
