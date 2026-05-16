#!/bin/bash
# Render plist templates with your HERMES_HOME + VAULT_PATH + VAULT_NAME,
# then load them into launchd.
#
# Usage:
#   HERMES_HOME=/abs/path/to/hermes-agent \
#   VAULT_PATH=/abs/path/to/vault \
#   VAULT_NAME=MyVault \
#     ./scripts/install-launchd.sh

set -euo pipefail

: "${HERMES_HOME:?HERMES_HOME not set (e.g. /Users/you/hermes-agent)}"
: "${VAULT_PATH:?VAULT_PATH not set (e.g. /Users/you/Documents/MyVault)}"
: "${VAULT_NAME:?VAULT_NAME not set (e.g. MyVault)}"

if [[ ! -d "$HERMES_HOME" ]]; then
    echo "HERMES_HOME does not exist: $HERMES_HOME" >&2
    exit 1
fi
if [[ ! -d "$VAULT_PATH" ]]; then
    echo "VAULT_PATH does not exist: $VAULT_PATH" >&2
    exit 1
fi

LAUNCHAGENTS="${HOME}/Library/LaunchAgents"
mkdir -p "$LAUNCHAGENTS"
mkdir -p "${HERMES_HOME}/logs"

PLIST_DIR="${HERMES_HOME}/plists"
for tmpl in "${PLIST_DIR}"/*.plist.template; do
    name="$(basename "$tmpl" .template)"
    out="${LAUNCHAGENTS}/${name}"
    sed \
        -e "s|__HERMES_HOME__|${HERMES_HOME}|g" \
        -e "s|__VAULT_PATH__|${VAULT_PATH}|g" \
        -e "s|__VAULT_NAME__|${VAULT_NAME}|g" \
        "$tmpl" > "$out"
    launchctl unload "$out" 2>/dev/null || true
    launchctl load "$out"
    echo "Loaded: $out"
done

echo "Done. Check status with: launchctl list | grep com.hermes"
