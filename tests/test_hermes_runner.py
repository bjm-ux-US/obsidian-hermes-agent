import os
import json
import tempfile
import time
import pytest
from unittest.mock import patch, MagicMock

from hermes_runner import (
    parse_args,
    build_prompt,
    should_skip_run,
)


class TestParseArgs:
    def test_insights_task(self):
        args = parse_args(["--task", "insights"])
        assert args.task == "insights"

    def test_maintenance_task(self):
        args = parse_args(["--task", "maintenance"])
        assert args.task == "maintenance"

    def test_reactive_task(self):
        args = parse_args(["--task", "reactive"])
        assert args.task == "reactive"

    def test_all_task(self):
        args = parse_args(["--task", "all"])
        assert args.task == "all"

    def test_invalid_task(self):
        with pytest.raises(SystemExit):
            parse_args(["--task", "bogus"])

    def test_dry_run_flag(self):
        args = parse_args(["--task", "insights", "--dry-run"])
        assert args.dry_run is True


class TestBuildPrompt:
    def test_insights_prompt_mentions_vault(self):
        prompt = build_prompt("insights")
        assert "vault" in prompt.lower()
        assert "contradiction" in prompt.lower()

    def test_maintenance_prompt_mentions_orphan(self):
        prompt = build_prompt("maintenance")
        assert "orphan" in prompt.lower()

    def test_reactive_prompt_mentions_git(self):
        prompt = build_prompt("reactive")
        assert "git" in prompt.lower() or "changed" in prompt.lower()

    def test_prompt_contains_todays_date(self):
        prompt = build_prompt("insights")
        today = time.strftime("%Y-%m-%d")
        assert today in prompt


class TestDebounce:
    def test_skip_when_recent(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"reactive": time.time()}, f)
            f.flush()
            with patch("hermes_runner.LAST_RUN_FILE", f.name):
                assert should_skip_run("reactive", min_interval=300) is True
        os.unlink(f.name)

    def test_no_skip_when_stale(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"reactive": time.time() - 600}, f)
            f.flush()
            with patch("hermes_runner.LAST_RUN_FILE", f.name):
                assert should_skip_run("reactive", min_interval=300) is False
        os.unlink(f.name)

    def test_no_skip_when_no_file(self):
        with patch("hermes_runner.LAST_RUN_FILE", "/tmp/nonexistent_hermes_test_xyz.json"):
            assert should_skip_run("reactive", min_interval=300) is False
