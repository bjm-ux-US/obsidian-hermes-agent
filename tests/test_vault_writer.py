import os
import tempfile
import pytest
from vault_writer import VaultWriter


class TestVaultWriter:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.writer = VaultWriter(vault_path=self.tmpdir)

    def test_write_insight_creates_file(self):
        self.writer.write_insight(
            date="2026-05-11",
            slug="morning",
            finding_type="contradiction",
            finding="TMR hypothesis X says Y but source Z says W",
            source_notes=[
                ("knowledge/trading/hypotheses", "hypothesis X: Y"),
                ("tmr-harness/sources/source-42", "finding: W"),
            ],
            why_matters="Direct conflict in trading logic",
            suggested_action="Review hypothesis X against latest backtest",
        )
        path = os.path.join(self.tmpdir, "hermes", "insights", "2026-05-11-morning.md")
        assert os.path.exists(path)
        content = open(path).read()
        assert "contradiction" in content
        assert "[[knowledge/trading/hypotheses]]" in content
        assert "[[tmr-harness/sources/source-42]]" in content
        assert "- [ ]" in content

    def test_write_insight_appends_to_existing(self):
        self.writer.write_insight(
            date="2026-05-11",
            slug="morning",
            finding_type="pattern",
            finding="First finding",
            source_notes=[("note-a", "excerpt")],
            why_matters="Reason 1",
            suggested_action="Action 1",
        )
        self.writer.write_insight(
            date="2026-05-11",
            slug="morning",
            finding_type="connection",
            finding="Second finding",
            source_notes=[("note-b", "excerpt")],
            why_matters="Reason 2",
            suggested_action="Action 2",
        )
        path = os.path.join(self.tmpdir, "hermes", "insights", "2026-05-11-morning.md")
        content = open(path).read()
        assert "First finding" in content
        assert "Second finding" in content
        assert content.count("## Finding") == 2

    def test_write_maintenance_log(self):
        self.writer.write_maintenance_log(
            date="2026-05-11",
            sections={
                "Orphan Notes": ["projects/old-thing.md - zero backlinks"],
                "Tag Hygiene": ["#trading and #trades appear to be duplicates"],
                "Link Rot": [],
                "Stale Hypotheses": ["knowledge/trading/hypotheses.md - last updated 2026-03-01"],
                "Memory Compaction": [],
            },
        )
        path = os.path.join(self.tmpdir, "hermes", "logs", "2026-05-11-maintenance.md")
        assert os.path.exists(path)
        content = open(path).read()
        assert "Orphan Notes" in content
        assert "#trading" in content
        assert "Link Rot" not in content  # empty sections omitted

    def test_insight_frontmatter_format(self):
        self.writer.write_insight(
            date="2026-05-11",
            slug="morning",
            finding_type="stale",
            finding="Test",
            source_notes=[("note-a", "x")],
            why_matters="Y",
            suggested_action="Z",
        )
        path = os.path.join(self.tmpdir, "hermes", "insights", "2026-05-11-morning.md")
        content = open(path).read()
        assert content.startswith("---\n")
        assert "source: hermes-insights" in content
        assert "created: 2026-05-11" in content

    def test_refuses_write_outside_hermes_namespace(self):
        with pytest.raises(ValueError, match="hermes"):
            self.writer._validate_output_path(
                os.path.join(self.tmpdir, "daily", "2026-05-11.md")
            )

    def test_creates_directories_on_first_write(self):
        path = os.path.join(self.tmpdir, "hermes", "insights")
        assert not os.path.exists(path)
        self.writer.write_insight(
            date="2026-05-11",
            slug="test",
            finding_type="pattern",
            finding="Test",
            source_notes=[("n", "x")],
            why_matters="Y",
            suggested_action="Z",
        )
        assert os.path.exists(path)
