"""
Tests for the Obsidian vault plugin tools.
Handlers are imported directly; subprocess.run is mocked for CLI-dependent tools.
"""

import json
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

# Plugin lives at plugins/obsidian/__init__.py; conftest inserts project root into sys.path.
# We import via the package path used in PYTHONPATH.
from plugins.obsidian import (
    vault_backlinks,
    vault_graph,
    vault_properties,
    vault_read,
    vault_recent,
    vault_search,
    vault_tags,
    vault_write,
    _validate_hermes_path,
    VAULT_PATH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_proc(stdout="", stderr="", returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


# ---------------------------------------------------------------------------
# vault_search
# ---------------------------------------------------------------------------

class TestVaultSearch:
    def test_returns_results_key(self):
        proc = _mock_proc(stdout="daily/2026-05-11.md\nprojects/tmr.md\n")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_search({"query": "tmr"}))
        assert "results" in out
        assert len(out["results"]) == 2

    def test_no_results_returns_empty_list(self):
        proc = _mock_proc(stdout="")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_search({"query": "xyznotfound"}))
        assert out["results"] == []

    def test_cli_error_returns_error_json(self):
        proc = _mock_proc(stderr="vault not found", returncode=1)
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_search({"query": "anything"}))
        assert "error" in out
        assert out["results"] == []

    def test_never_raises(self):
        with patch("plugins.obsidian.subprocess.run", side_effect=FileNotFoundError("obsidian not found")):
            result = vault_search({"query": "test"})
        assert isinstance(result, str)
        out = json.loads(result)
        assert "error" in out


# ---------------------------------------------------------------------------
# vault_read
# ---------------------------------------------------------------------------

class TestVaultRead:
    def test_returns_content(self):
        proc = _mock_proc(stdout="# My Note\nsome content")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_read({"path": "daily/2026-05-11"}))
        assert out["content"] == "# My Note\nsome content"
        assert out["path"] == "daily/2026-05-11"

    def test_missing_note_returns_error(self):
        proc = _mock_proc(stderr="note not found", returncode=1)
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_read({"path": "does/not/exist"}))
        assert "error" in out
        assert out["content"] is None

    def test_never_raises(self):
        with patch("plugins.obsidian.subprocess.run", side_effect=OSError("boom")):
            result = vault_read({"path": "anything"})
        assert isinstance(json.loads(result), dict)


# ---------------------------------------------------------------------------
# vault_backlinks
# ---------------------------------------------------------------------------

class TestVaultBacklinks:
    def test_returns_backlinks_list(self):
        proc = _mock_proc(stdout="projects/tmr.md\nknowledge/trading/rules.md\n")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_backlinks({"path": "daily/2026-05-11"}))
        assert out["backlinks"] == ["projects/tmr.md", "knowledge/trading/rules.md"]
        assert out["count"] == 2

    def test_no_backlinks_returns_empty(self):
        proc = _mock_proc(stdout="")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_backlinks({"path": "orphan-note"}))
        assert out["backlinks"] == []

    def test_never_raises(self):
        with patch("plugins.obsidian.subprocess.run", side_effect=Exception("fail")):
            result = vault_backlinks({"path": "x"})
        assert "error" in json.loads(result)


# ---------------------------------------------------------------------------
# vault_tags
# ---------------------------------------------------------------------------

class TestVaultTags:
    def test_returns_tags(self):
        proc = _mock_proc(stdout="#trading 12\n#project 8\n#hypothesis 3\n")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_tags({}))
        assert len(out["tags"]) == 3

    def test_filter_applied(self):
        proc = _mock_proc(stdout="#trading 12\n#project 8\n#hypothesis 3\n")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_tags({"filter": "trading"}))
        assert all("trading" in t for t in out["tags"])

    def test_cli_error_returns_error(self):
        proc = _mock_proc(returncode=1, stderr="err")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_tags({}))
        assert "error" in out

    def test_never_raises(self):
        with patch("plugins.obsidian.subprocess.run", side_effect=Exception("x")):
            result = vault_tags({})
        assert isinstance(json.loads(result), dict)


# ---------------------------------------------------------------------------
# vault_graph
# ---------------------------------------------------------------------------

class TestVaultGraph:
    def test_combines_backlinks_and_forward_links(self):
        bl_proc = _mock_proc(stdout="projects/example.md\n")
        read_proc = _mock_proc(stdout="# Note\n[[knowledge/topic]] and [[people/alice]]\n")
        with patch("plugins.obsidian.subprocess.run", side_effect=[bl_proc, read_proc]):
            out = json.loads(vault_graph({"path": "daily/2026-05-11"}))
        assert "projects/example.md" in out["backlinks"]
        assert "knowledge/topic" in out["forward_links"]
        assert "people/alice" in out["forward_links"]

    def test_deduplicates_forward_links(self):
        bl_proc = _mock_proc(stdout="")
        read_proc = _mock_proc(stdout="[[example]] see [[example]] again\n")
        with patch("plugins.obsidian.subprocess.run", side_effect=[bl_proc, read_proc]):
            out = json.loads(vault_graph({"path": "note"}))
        assert out["forward_links"].count("example") == 1

    def test_never_raises(self):
        with patch("plugins.obsidian.subprocess.run", side_effect=Exception("fail")):
            result = vault_graph({"path": "x"})
        assert "error" in json.loads(result)


# ---------------------------------------------------------------------------
# vault_recent
# ---------------------------------------------------------------------------

class TestVaultRecent:
    def test_finds_recently_modified_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch VAULT_PATH to tmpdir
            import plugins.obsidian as plugin_mod
            original = plugin_mod.VAULT_PATH
            plugin_mod.VAULT_PATH = tmpdir
            try:
                # Create a fresh .md file
                note = os.path.join(tmpdir, "recent.md")
                with open(note, "w") as f:
                    f.write("# Recent")
                out = json.loads(vault_recent({"hours": 1}))
                assert any("recent.md" in f["path"] for f in out["files"])
            finally:
                plugin_mod.VAULT_PATH = original

    def test_excludes_old_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import plugins.obsidian as plugin_mod
            original = plugin_mod.VAULT_PATH
            plugin_mod.VAULT_PATH = tmpdir
            try:
                old_note = os.path.join(tmpdir, "old.md")
                with open(old_note, "w") as f:
                    f.write("# Old")
                # Set mtime to 48 hours ago
                old_mtime = time.time() - 48 * 3600
                os.utime(old_note, (old_mtime, old_mtime))
                out = json.loads(vault_recent({"hours": 1}))
                assert not any("old.md" in f["path"] for f in out["files"])
            finally:
                plugin_mod.VAULT_PATH = original

    def test_vault_path_missing_returns_error(self):
        import plugins.obsidian as plugin_mod
        original = plugin_mod.VAULT_PATH
        plugin_mod.VAULT_PATH = "/does/not/exist/at/all"
        try:
            out = json.loads(vault_recent({}))
            assert "error" in out
        finally:
            plugin_mod.VAULT_PATH = original

    def test_never_raises(self):
        result = vault_recent({"hours": "not-a-number"})
        assert isinstance(result, str)
        # should be error JSON
        assert isinstance(json.loads(result), dict)


# ---------------------------------------------------------------------------
# vault_write
# ---------------------------------------------------------------------------

class TestVaultWrite:
    def test_refuses_write_outside_hermes_namespace(self):
        out = json.loads(vault_write({"path": "daily/2026-05-11.md", "content": "x"}))
        assert out["status"] == "refused"
        assert "error" in out

    def test_refuses_absolute_path_outside_hermes(self):
        out = json.loads(vault_write({"path": "/etc/passwd", "content": "x"}))
        assert out["status"] == "refused"

    def test_allows_write_in_hermes_namespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import plugins.obsidian as plugin_mod
            original = plugin_mod.VAULT_PATH
            plugin_mod.VAULT_PATH = tmpdir
            try:
                out = json.loads(vault_write({
                    "path": "hermes/test-note.md",
                    "content": "# Test",
                }))
                assert out["status"] == "ok"
                written = os.path.join(tmpdir, "hermes", "test-note.md")
                assert os.path.exists(written)
                assert open(written).read() == "# Test"
            finally:
                plugin_mod.VAULT_PATH = original

    def test_append_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import plugins.obsidian as plugin_mod
            original = plugin_mod.VAULT_PATH
            plugin_mod.VAULT_PATH = tmpdir
            try:
                vault_write({"path": "hermes/append-test.md", "content": "line1\n"})
                vault_write({"path": "hermes/append-test.md", "content": "line2\n", "mode": "append"})
                content = open(os.path.join(tmpdir, "hermes", "append-test.md")).read()
                assert "line1" in content and "line2" in content
            finally:
                plugin_mod.VAULT_PATH = original

    def test_never_raises(self):
        # Pass bad args - should still return JSON
        result = vault_write({})
        assert isinstance(json.loads(result), dict)


# ---------------------------------------------------------------------------
# vault_properties
# ---------------------------------------------------------------------------

class TestVaultProperties:
    def test_get_returns_properties(self):
        proc = _mock_proc(stdout="status: active\ntags: [trading]")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_properties({"path": "projects/tmr", "action": "get"}))
        assert "status: active" in out["properties"]

    def test_get_cli_error(self):
        proc = _mock_proc(returncode=1, stderr="not found")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_properties({"path": "missing", "action": "get"}))
        assert "error" in out

    def test_set_property(self):
        proc = _mock_proc(stdout="ok")
        with patch("plugins.obsidian.subprocess.run", return_value=proc):
            out = json.loads(vault_properties({
                "path": "projects/tmr",
                "action": "set",
                "name": "status",
                "value": "done",
            }))
        assert out["status"] == "ok"

    def test_set_missing_name_returns_error(self):
        out = json.loads(vault_properties({"path": "x", "action": "set", "value": "y"}))
        assert "error" in out

    def test_never_raises(self):
        with patch("plugins.obsidian.subprocess.run", side_effect=Exception("boom")):
            result = vault_properties({"path": "x"})
        assert isinstance(json.loads(result), dict)


# ---------------------------------------------------------------------------
# validate_hermes_path (unit)
# ---------------------------------------------------------------------------

class TestValidateHermesPath:
    def test_valid_path_accepted(self):
        p = _validate_hermes_path("hermes/insights/2026-05-11.md")
        assert p.endswith("hermes/insights/2026-05-11.md")

    def test_invalid_path_raises(self):
        with pytest.raises(ValueError, match="hermes"):
            _validate_hermes_path("daily/2026-05-11.md")

    def test_leading_slash_stripped(self):
        p = _validate_hermes_path("/hermes/logs/test.md")
        assert "hermes/logs/test.md" in p
