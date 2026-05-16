# obsidian-hermes-agent

A vault-intelligence agent for [Obsidian](https://obsidian.md/) knowledge bases.
It runs on a schedule (morning insights, evening maintenance) and reactively
on git pushes, scanning your vault for contradictions, emerging patterns,
unlinked references, and link rot. Findings are written into a sandboxed
`hermes/` namespace inside the vault. Nothing else gets modified.

Built on top of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
with custom Obsidian tools, scan prompts, and a model router that prefers a
local Ollama model for cheap tasks and falls back to Claude (Haiku / Sonnet /
Opus) for harder ones.

## What you need

- macOS (launchd is used for scheduling; the Python code itself is portable)
- An Obsidian vault that is also a git repo (for the reactive watcher)
- The [`obsidian` CLI](https://github.com/jaynus/obsidian-cli) on your `$PATH`
- Python 3.11+
- An Anthropic API key
- Optional: [Ollama](https://ollama.com/) running locally for cheap tasks

## Install

```bash
git clone <this-repo-url> ~/hermes-agent
cd ~/hermes-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY, VAULT_PATH, VAULT_NAME
```

## Try it (dry run)

```bash
source venv/bin/activate
python hermes_runner.py --task insights --dry-run
python hermes_runner.py --task maintenance --dry-run
```

That just prints the prompt without calling any models.

## Run a real scan

```bash
python hermes_runner.py --task insights
python hermes_runner.py --task maintenance
```

Output goes to `<VAULT_PATH>/hermes/insights/` and `<VAULT_PATH>/hermes/logs/`.

## Schedule with launchd (macOS)

```bash
HERMES_HOME=$HOME/hermes-agent \
VAULT_PATH=/abs/path/to/your/vault \
VAULT_NAME=YourVaultName \
  ./scripts/install-launchd.sh
```

This renders the templates in `plists/` and loads three agents:

| Agent | When | Task |
|-------|------|------|
| `com.hermes.morning-scan` | 06:45 local daily | `insights` |
| `com.hermes.evening-maintenance` | 20:00 local daily | `maintenance` |
| `com.hermes.vault-watcher` | always-on (KeepAlive) | runs `reactive` on every commit to `main` |

Check status: `launchctl list | grep com.hermes`
Logs: `<HERMES_HOME>/logs/`

The vault-watcher uses `fswatch`; install with `brew install fswatch` if you
want the reactive scan.

## Configuration

| Env var | Required | Default | Meaning |
|---------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | yes | - | Anthropic API key |
| `VAULT_PATH` | yes | `~/Desktop/MyVault` | Absolute path to the vault on disk |
| `VAULT_NAME` | yes | `MyVault` | Vault name as Obsidian sees it |
| `HERMES_HOME` | no | `~/.hermes` | Where Hermes stores skills/state |
| `CLAUDE_CHEAP_MODEL` | no | `claude-haiku-4-5-20251001` | Cheap-tier model |
| `CLAUDE_FAST_MODEL` | no | `claude-sonnet-4-20250514` | Mid-tier model |
| `CLAUDE_DEEP_MODEL` | no | `claude-opus-4-0-20250115` | Deep-reasoning model |

## What it writes

Only inside `<VAULT_PATH>/hermes/`:

- `hermes/insights/YYYY-MM-DD-morning.md` - morning findings
- `hermes/insights/YYYY-MM-DD-reactive.md` - reactive findings
- `hermes/logs/YYYY-MM-DD-maintenance.md` - evening maintenance report
- `hermes/skills/` - starter skills copied on first run

The `vault_write` tool refuses any path that does not start with `hermes/`,
so the agent cannot edit your other notes even if it tries.

## Tools the agent has

- `vault_search` - search notes by query
- `vault_read` - read a note by path
- `vault_backlinks` - find notes that link to a given note
- `vault_tags` - list all tags
- `vault_graph` - get backlinks + outgoing `[[wikilinks]]` for a note
- `vault_recent` - list notes modified in the last N hours
- `vault_write` - write into `hermes/` namespace only
- `vault_properties` - get/set YAML frontmatter

## License

See [LICENSE](LICENSE).
