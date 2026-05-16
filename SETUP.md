---
title: Claude + Hermes + Obsidian Setup Guide
audience: macOS, comfortable with terminal + git
date: 2026-05-15
---

# Claude + Hermes + Obsidian on macOS

End state: Obsidian vault with Claude Code wired in as a coding/thinking partner, plus a Hermes background agent that scans the vault twice a day for connections, contradictions, and link rot.

Time: ~60-90 min. Assumes Homebrew, Python 3.11+, git, an Anthropic API key.

---

## Part 1 - Obsidian + vault skeleton (15 min)

1. **Install Obsidian**
   ```
   brew install --cask obsidian
   ```

2. **Create the vault folder** (anywhere, but pick a stable path - it gets hardcoded later):
   ```
   mkdir -p ~/Desktop/MyVault
   cd ~/Desktop/MyVault
   git init
   ```

3. **Open Obsidian -> Open folder as vault -> pick `~/Desktop/MyVault`.**
   Turn on these core plugins (Settings -> Core plugins):
   - Daily notes
   - Templates
   - Backlinks
   - Graph view
   - Properties view

4. **Folder skeleton** (mirror this structure so commands and Hermes prompts work without edits):
   ```
   mkdir -p daily/briefings people projects templates commands knowledge decisions hermes/{insights,logs,skills/vault-insights,skills/vault-maintenance} scripts docs
   ```

5. **Daily-note template** at `templates/daily.md`:
   ```markdown
   ---
   date: {{date}}
   tags: [daily]
   ---

   # {{date}}

   ## What I'm thinking about

   ## What I'm working on

   ## Today's Tasks
   - [ ]

   ## Notes

   ---

   ## EOD Update

   ### What actually got done

   ### Don't forget
   ```
   In Obsidian: Settings -> Daily notes -> set template to `templates/daily.md`, format `YYYY-MM-DD`, location `daily`.

6. **First commit**:
   ```
   git add .
   git commit -m "vault skeleton"
   ```
   (Optional: push to a private GitHub repo. Some hooks benefit from it; not required for local-only.)

---

## Part 2 - Claude Code (15 min)

1. **Install**:
   ```
   brew install anthropic/cli/claude-code
   ```
   Or follow https://docs.claude.com/en/docs/claude-code/quickstart for the latest install method.

2. **Auth**: run `claude` once in any directory. It'll prompt for login (web flow) or `ANTHROPIC_API_KEY`.

3. **Global instructions** at `~/.claude/CLAUDE.md` - this is your personality file for every project. Minimum useful starter:
   ```markdown
   # CLAUDE.md

   ## Output
   - Answer first, reasoning after.
   - No preamble ("Sure!", "Of course!").
   - Structured: bullets, tables, code blocks. Prose only when asked.

   ## No Speculation
   If you don't have direct evidence, say "I don't know" and go get it. Never guess with "likely" / "probably".

   ## Code
   - Read the file before editing it.
   - Simplest working solution. No speculative features.
   - Inline comments only where logic is non-obvious.
   ```
   A fuller version can add assumption-audit, decision journal, knowledge architecture sections. Start small; add as friction shows up.

4. **Project instructions** at `~/Desktop/MyVault/CLAUDE.md`:
   ```markdown
   # CLAUDE.md

   ## Environment
   This is an Obsidian vault. All files are markdown.

   ## Vault Structure
   - /daily - daily journal (YYYY-MM-DD)
   - /daily/briefings - automated briefings
   - /people, /projects, /knowledge, /decisions, /commands, /templates
   - /hermes - background agent outputs

   ## Rules
   - Never write directly into vault notes unless explicitly asked. Suggest content; user decides.
   - Use Obsidian [[backlinks]] when creating or editing notes.
   - When suggesting connections, explain WHY.
   - Challenge assumptions before agreeing.
   ```

5. **Optional: Obsidian CLI** for grep/backlink/tag operations from Claude:
   ```
   brew install obsidian-cli   # or follow project's install for the variant you want
   ```

6. **Smoke test**: in the vault dir, run `claude`, then ask: `read CLAUDE.md and tell me back the rules in one sentence each`. Should hit your project file.

---

## Part 3 - Hermes vault agent (30-45 min)

Hermes is a background agent that runs morning + evening scans of the vault and writes findings (contradictions, orphan notes, link rot, emerging patterns) to `hermes/insights/` and `hermes/logs/`.

The agent is on GitHub: https://github.com/bjm-ux-US/obsidian-hermes-agent. Repo README covers everything below in shorter form; this guide expands on the gotchas.

### 3a. Clone + venv

```
git clone https://github.com/bjm-ux-US/obsidian-hermes-agent.git ~/hermes-agent
cd ~/hermes-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 3b. .env file

```
cp ~/hermes-agent/.env.example ~/hermes-agent/.env
```
Edit `~/hermes-agent/.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
VAULT_PATH=/Users/<you>/Desktop/MyVault
VAULT_NAME=MyVault
```
Replace `<you>` with your macOS username. `VAULT_NAME` must match the vault name Obsidian shows in its window title.

### 3c. fswatch (for the reactive watcher)

```
brew install fswatch
```
Only needed if you want the reactive scan that fires on each git commit. Morning + evening scans work without it.

### 3d. Install launchd plists

The repo ships three `.plist.template` files plus an installer that renders them with your paths and loads them:

```
HERMES_HOME=$HOME/hermes-agent \
VAULT_PATH=$HOME/Desktop/MyVault \
VAULT_NAME=MyVault \
  ~/hermes-agent/scripts/install-launchd.sh
```

This writes three rendered plists into `~/Library/LaunchAgents/` and loads them. Defaults:

| Agent | When | Task |
|-------|------|------|
| `com.hermes.morning-scan` | 06:45 local daily | `insights` |
| `com.hermes.evening-maintenance` | 20:00 local daily | `maintenance` |
| `com.hermes.vault-watcher` | always-on (KeepAlive) | `reactive` on every commit to `main` |

To change schedule, edit the `.plist.template` files in `~/hermes-agent/plists/` and re-run the installer.

### 3e. Verify

```
launchctl list | grep hermes
```

Manual smoke test - don't wait for 6:45 AM:
```
source ~/hermes-agent/venv/bin/activate
python ~/hermes-agent/hermes_runner.py --task maintenance
```
Should write `~/Desktop/MyVault/hermes/logs/YYYY-MM-DD-maintenance.md`. Open in Obsidian to confirm.

### 3f. Full Disk Access (critical gotcha)

launchd jobs do NOT inherit Full Disk Access from your terminal. If logs show `Operation not permitted`:

System Settings -> Privacy & Security -> Full Disk Access -> add:
- `/bin/bash`
- `/usr/bin/python3`
- Your venv python: `/Users/<you>/hermes-agent/venv/bin/python`

Reload the plists after granting:
```
launchctl unload ~/Library/LaunchAgents/com.hermes.*.plist
launchctl load ~/Library/LaunchAgents/com.hermes.*.plist
```

---

## Part 4 - Daily flow (5 min to try)

1. **Morning**: open Obsidian, check `hermes/insights/YYYY-MM-DD-morning.md` (Hermes wrote it at 6:45). Skim, mark actionable items.
2. **During work**: in the vault dir, `claude` -> ask anything. Try:
   ```
   /context
   ```
   if you have a `commands/context.md` defined. Otherwise: `read recent daily notes and tell me what I'm working on`.
3. **Evening**: Hermes runs at 8 PM, writes `hermes/logs/YYYY-MM-DD-maintenance.md` with orphans, link rot, stale knowledge files.

---

## Part 5 - Gotchas + tips

- **`launchctl stop` vs `unload`**: never `stop` a `KeepAlive=true` plist - it'll respawn immediately. Use `launchctl unload` to actually stop the watcher.
- **Cost**: Hermes runs against the Anthropic API. Default cap is $0.50/day in `model_router.py`. Adjust if needed.
- **Vault in git**: keeps Hermes's reactive watcher meaningful (it triggers on git ref changes) and gives you a recovery path. Worth doing even if you never push.
- **Obsidian sync**: if you use iCloud or Obsidian Sync, point the vault path away from the synced folder OR add `.obsidian/workspace*.json` to `.gitignore` to avoid sync-vs-git conflicts.
- **First week**: don't try to use every command/skill at once. Get the daily note + Hermes morning scan loop working. Add commands and knowledge files as the friction shows you what's missing.

---

## What's NOT in this guide

- A full `commands/` library (close-day, weekly-synthesis, daily-brief). Build these as the friction shows you what you need.
- Custom hooks (`~/.claude/hooks/*.sh`) - caveman mode, goal-loop detector, memory curator. These are personal preference, not required.
- Anything domain-specific (trading, finance, research, journalism) - that's on top of the platform, not part of it.

If something breaks: check `~/hermes-agent/logs/*.log` first. 90% of issues are FDA, paths, or the venv python.
