#!/usr/bin/env python3
# hermes_runner.py - Hermes Agent vault intelligence runner
import argparse
import json
import logging
import os
import shutil
import sys
import time

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from model_router import ModelRouter, TaskType

logger = logging.getLogger("hermes-runner")

VAULT_PATH = os.environ.get("VAULT_PATH") or os.path.expanduser("~/Desktop/MyVault")
HERMES_HOME = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_RUN_FILE = os.path.join(PROJECT_DIR, "logs", "last_run.json")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")

TASK_CHOICES = ["insights", "maintenance", "reactive", "all"]

_INSIGHTS_PROMPT = """You are running the morning vault insights scan on the Obsidian vault.

Today's date: {date}

Your task:
1. Use vault_recent to find notes modified in the last 24 hours
2. For each modified note, use vault_backlinks to traverse connections 2 levels deep
3. Look for:
   - Contradictions: a hypothesis in /knowledge/ that conflicts with evidence in a daily note or source
   - Emerging patterns: the same concept appearing in 3+ unconnected notes
   - Stale connections: backlinked notes where the linked content's meaning has shifted
   - Unlinked references: notes that mention the same concept but don't link to each other
4. For each real finding, use vault_write to write to hermes/insights/{date}-morning.md
5. Use the insight note format with frontmatter, finding, source notes with [[backlinks]], why it matters, and a suggested action checkbox

Only report findings that are actionable. Skip trivial or obvious connections.
If nothing interesting was found, write nothing - no output is better than noise."""

_MAINTENANCE_PROMPT = """You are running the evening vault maintenance scan on the Obsidian vault.

Today's date: {date}

Your task:
1. Orphan detection: find notes with zero backlinks (exclude daily/, briefings/, templates/, hermes/)
2. Tag hygiene: find similar or duplicate tags (e.g., #trading vs #trades)
3. Link rot: find [[backlinks]] that point to notes that don't exist
4. Knowledge staleness: check /knowledge/ files - flag any not updated in 30+ days
5. Memory compaction: check if any memory files are excessively long

Write a maintenance report to hermes/logs/{date}-maintenance.md.
Only include sections that have findings. Skip empty sections.
Suggest fixes but do NOT auto-fix anything. The user reviews first."""

_REACTIVE_PROMPT = """You are running a reactive scan triggered by a vault change.

Today's date: {date}

Your task:
1. Use vault_recent with hours=1 to find what just changed
2. For each changed note, do a lightweight check:
   - Does it contradict anything in /knowledge/?
   - Does it connect to something unexpected?
3. Only report genuinely interesting findings
4. If interesting, append to hermes/insights/{date}-reactive.md
5. If nothing interesting, produce no output at all

This is a lightweight scan. Be fast and selective."""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Hermes vault intelligence runner")
    parser.add_argument(
        "--task",
        choices=TASK_CHOICES,
        required=True,
        help="Which task to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the prompt but don't run the agent",
    )
    return parser.parse_args(argv)


def build_prompt(task: str) -> str:
    today = time.strftime("%Y-%m-%d")
    prompts = {
        "insights": _INSIGHTS_PROMPT,
        "maintenance": _MAINTENANCE_PROMPT,
        "reactive": _REACTIVE_PROMPT,
    }
    prompt = prompts[task]
    return prompt.replace("{date}", today)


def should_skip_run(task: str, min_interval: int = 300) -> bool:
    try:
        with open(LAST_RUN_FILE) as f:
            data = json.load(f)
        last = data.get(task, 0)
        return (time.time() - last) < min_interval
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return False


def record_run(task: str):
    os.makedirs(os.path.dirname(LAST_RUN_FILE), exist_ok=True)
    try:
        with open(LAST_RUN_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data[task] = time.time()
    with open(LAST_RUN_FILE, "w") as f:
        json.dump(data, f)


def install_starter_skills():
    """Copy starter skills to vault and Hermes skills directory on first run."""
    src_dir = os.path.join(PROJECT_DIR, "skills")
    destinations = [
        os.path.join(VAULT_PATH, "hermes", "skills"),
        os.path.join(HERMES_HOME, "skills"),
    ]
    if not os.path.exists(src_dir):
        return
    for dst_dir in destinations:
        for skill_name in os.listdir(src_dir):
            src = os.path.join(src_dir, skill_name)
            dst = os.path.join(dst_dir, skill_name)
            if os.path.isdir(src) and not os.path.exists(dst):
                shutil.copytree(src, dst)
                logger.info(f"Installed starter skill: {skill_name} -> {dst_dir}")


def run_task(task: str, dry_run: bool = False):
    if task == "reactive" and should_skip_run("reactive", min_interval=300):
        logger.info("Skipping reactive - last run <5 min ago")
        return

    prompt = build_prompt(task)

    if dry_run:
        print(f"=== DRY RUN: {task} ===")
        print(prompt)
        return

    router = ModelRouter(
        local_endpoint="http://localhost:11434",
        local_model="gemma4:e4b",
        claude_cheap=os.getenv("CLAUDE_CHEAP_MODEL", "claude-haiku-4-5-20251001"),
        claude_fast=os.getenv("CLAUDE_FAST_MODEL", "claude-sonnet-4-20250514"),
        claude_deep=os.getenv("CLAUDE_DEEP_MODEL", "claude-opus-4-0-20250115"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    )

    task_type_map = {
        "insights": TaskType.SCAN,
        "maintenance": TaskType.MAINTENANCE,
        "reactive": TaskType.REACTIVE_TRIAGE,
    }
    config = router.resolve(task_type_map[task])

    if config is None:
        logger.error(f"No model available for {task} (budget exceeded + Ollama down)")
        return

    logger.info(f"Running {task} with {config['provider']}/{config['model']}")

    os.environ["HERMES_HOME"] = HERMES_HOME
    # Force Anthropic key into env - Hermes credential pool ignores constructor api_key
    if config["provider"] == "anthropic" and config["api_key"]:
        os.environ["ANTHROPIC_API_KEY"] = config["api_key"]
    from run_agent import AIAgent

    agent = AIAgent(
        provider=config["provider"],
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
        quiet_mode=True,
        max_iterations=25,
        disabled_toolsets=["browser", "audio", "vision", "gateway", "automation"],
        skip_context_files=True,
    )

    result = agent.run_conversation(
        user_message=prompt,
        task_id=f"hermes-{task}-{time.strftime('%Y%m%d-%H%M')}",
    )

    response = result.get("final_response") or ""
    logger.info(f"Task {task} complete. Response length: {len(response)}")
    record_run(task)


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(LOG_DIR, "hermes-runner.log")),
            logging.StreamHandler(),
        ],
    )

    install_starter_skills()
    args = parse_args()

    if args.task == "all":
        for task in ["insights", "maintenance"]:
            run_task(task, dry_run=args.dry_run)
    else:
        run_task(args.task, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
