import os


class VaultWriter:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path

    def _validate_output_path(self, path: str):
        rel = os.path.relpath(path, self.vault_path)
        if not rel.startswith(os.path.join("hermes", "")):
            raise ValueError(
                f"Refusing to write outside hermes namespace: {rel}"
            )

    def _ensure_dir(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def write_insight(
        self,
        date: str,
        slug: str,
        finding_type: str,
        finding: str,
        source_notes: list[tuple[str, str]],
        why_matters: str,
        suggested_action: str,
    ):
        path = os.path.join(
            self.vault_path, "hermes", "insights", f"{date}-{slug}.md"
        )
        self._validate_output_path(path)
        self._ensure_dir(path)

        sources_md = "\n".join(
            f"- [[{name}]] - {excerpt}" for name, excerpt in source_notes
        )

        entry = f"""## Finding

{finding}

## Source Notes

{sources_md}

## Why This Matters

{why_matters}

## Suggested Action

- [ ] {suggested_action}

---

"""

        if os.path.exists(path):
            with open(path, "a") as f:
                f.write(entry)
        else:
            frontmatter = f"""---
created: {date}
source: hermes-insights
type: {finding_type}
---

"""
            with open(path, "w") as f:
                f.write(frontmatter + entry)

    def write_maintenance_log(self, date: str, sections: dict[str, list[str]]):
        path = os.path.join(
            self.vault_path, "hermes", "logs", f"{date}-maintenance.md"
        )
        self._validate_output_path(path)
        self._ensure_dir(path)

        parts = [
            f"---\ncreated: {date}\nsource: hermes-maintenance\n---\n"
        ]

        for title, items in sections.items():
            if not items:
                continue
            parts.append(f"\n## {title}\n")
            for item in items:
                parts.append(f"- {item}")
            parts.append("")

        with open(path, "w") as f:
            f.write("\n".join(parts))
