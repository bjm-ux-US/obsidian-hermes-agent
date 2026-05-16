---
name: vault-maintenance
description: Detect orphan notes, tag duplicates, link rot, stale hypotheses, and memory bloat in the Obsidian vault
version: 1.0.0
platforms: [macos]
requires_toolsets: [obsidian]
tags: [vault, maintenance, hygiene]
category: knowledge-management
---

## When to Use

Activated by the evening maintenance scan (default 8:00 PM local). Use for routine vault health checks.

## Procedure

1. **Orphan detection**
   - Use `vault_search` and `vault_backlinks` to find notes with zero incoming backlinks
   - Exclude: daily/*.md, daily/briefings/*.md, templates/*.md, hermes/*.md (these are OK without backlinks)
   - Report each orphan with its path and a brief note on what it contains

2. **Tag hygiene**
   - Use `vault_tags` (no argument) to list all tags
   - Look for near-duplicates: singular/plural (#trade/#trades), abbreviations (#ml/#machine-learning), typos
   - Report pairs with a suggestion for which to standardize on

3. **Link rot**
   - Scan for [[backlinks]] that point to notes that don't exist
   - Use `vault_search` for `[[` patterns and cross-reference with actual files
   - Report each broken link with the source note and the missing target

4. **Knowledge staleness**
   - Read files in /knowledge/ subdirectories
   - Use `vault_properties` or file modification dates to check last update
   - Flag any knowledge file not updated in 30+ days
   - Priority flag: hypotheses that have not been revisited since creation

5. **Memory compaction check**
   - If a memory index file is configured (e.g., ~/.claude/projects/<project>/memory/MEMORY.md), read it
   - Count entries. If >50 entries, flag for consolidation
   - Do NOT modify the file - just report

6. **Write report**
   - Use `vault_write` to write `hermes/logs/{date}-maintenance.md`
   - Only include sections that have findings
   - Each finding should include the path and a specific suggested action

## Pitfalls

- Don't suggest deleting orphans without checking if they're new notes in progress
- Tag standardization suggestions should prefer the more descriptive tag
- Stale knowledge is not bad knowledge - it just needs review. Flag, don't judge.

## Output Rules

- Suggest fixes, never auto-fix
- The user reviews everything before acting
- If vault is clean (no findings), write a one-line "all clear" log entry
