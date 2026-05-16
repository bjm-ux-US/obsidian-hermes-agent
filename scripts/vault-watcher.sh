#!/bin/bash
# Watches for git ref changes in the configured vault and triggers reactive scan.
# Run by launchd with KeepAlive=true.
#
# Required env vars (set by the launchd plist or .env):
#   HERMES_HOME  - path to the hermes-agent install (with venv/ + hermes_runner.py)
#   VAULT_PATH   - path to the Obsidian vault (a git repo); watches .git/refs/heads/main

set -u

: "${HERMES_HOME:?HERMES_HOME not set}"
: "${VAULT_PATH:?VAULT_PATH not set}"

RUNNER="${HERMES_HOME}/venv/bin/python ${HERMES_HOME}/hermes_runner.py"
WATCH_PATH="${VAULT_PATH}/.git/refs/heads/main"
LOG="${HERMES_HOME}/logs/reactive.log"

mkdir -p "$(dirname "$LOG")"
echo "$(date): vault-watcher started (watching ${WATCH_PATH})" >> "$LOG"

while true; do
    fswatch -1 "$WATCH_PATH" 2>/dev/null
    echo "$(date): change detected, running reactive scan" >> "$LOG"
    $RUNNER --task reactive >> "$LOG" 2>&1
done
