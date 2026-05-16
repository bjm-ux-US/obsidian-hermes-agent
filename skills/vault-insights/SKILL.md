---
name: vault-insights
description: Scan vault for contradictions, emerging patterns, unlinked references, and stale connections across Obsidian notes
version: 1.0.0
platforms: [macos]
requires_toolsets: [obsidian]
tags: [vault, knowledge, insights]
category: knowledge-management
---

## When to Use

Activated by the morning insights scan (default 6:45 AM local) or reactive scan on git push. Use when you need to find non-obvious connections or contradictions in the vault.

## Procedure

1. **Gather changed notes**
   - Use `vault_recent` with hours=24 (morning) or hours=1 (reactive)
   - If no changes, stop - no output needed

2. **Build context for each changed note**
   - Use `vault_read` to get full content
   - Use `vault_backlinks` to find what links to it
   - For each backlink, use `vault_read` to get that note's content
   - For important backlinks, go one more level (2-deep traversal)

3. **Detect findings**
   - **Contradictions:** Compare claims in /knowledge/hypotheses.md files against evidence in daily notes or project docs. A contradiction is when two notes make incompatible factual claims.
   - **Emerging patterns:** Same concept, keyword, or theme appearing in 3+ notes that don't link to each other. Use `vault_search` to find related terms.
   - **Stale connections:** A [[backlink]] exists but the linked note's meaning has shifted since the link was created. The link is now misleading.
   - **Unlinked references:** Two notes discuss the same topic but neither links to the other. Use `vault_search` to find these.

4. **Filter for quality**
   - Only report findings that are actionable
   - Skip trivial connections (e.g., two daily notes both mention "morning")
   - A good finding changes how the user thinks about something or reveals a risk

5. **Write output**
   - Use `vault_write` to write/append to `hermes/insights/{date}-morning.md` (or `-reactive.md`)
   - Follow the insight note format with frontmatter, [[backlinks]], and action checkbox

## Pitfalls

- Don't treat every shared tag as a "pattern" - look for substantive conceptual overlap
- Don't flag contradictions between notes at different abstraction levels (a hypothesis vs a raw data point isn't necessarily a contradiction)
- Hypotheses in /knowledge/ are the highest-value targets for contradiction detection
- Daily notes are context, not conclusions - don't over-index on casual observations

## Quality Bar

Ask yourself: would the user look at this finding and say "that's useful" or "that's obvious"? Only write the first kind.
