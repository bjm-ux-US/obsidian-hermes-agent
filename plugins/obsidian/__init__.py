"""
Obsidian vault tools.
Requires: Obsidian running with the obsidian CLI available.
CLI syntax: obsidian vault="<name>" <command> key=value
Configuration: set VAULT_NAME and VAULT_PATH env vars (or fall back to defaults).
"""

import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

VAULT = os.environ.get("VAULT_NAME", "MyVault")
VAULT_PATH = os.environ.get("VAULT_PATH") or os.path.expanduser("~/Desktop/MyVault")
HERMES_NAMESPACE = "hermes"


def _run_obsidian(*args) -> tuple[int, str, str]:
    """Run an obsidian CLI command. Returns (returncode, stdout, stderr)."""
    cmd = ["obsidian", f'vault="{VAULT}"'] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# vault_search
# ---------------------------------------------------------------------------

VAULT_SEARCH_SCHEMA = {
    "name": "vault_search",
    "description": "Search the Obsidian vault for notes matching a query.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (default 10)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}


def vault_search(args: dict, **kwargs) -> str:
    try:
        query = args["query"]
        limit = args.get("limit", 10)
        rc, stdout, stderr = _run_obsidian("search", f'query="{query}"', f"limit={limit}")
        if rc != 0:
            return json.dumps({"error": stderr.strip() or "obsidian CLI error", "results": []})
        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        if not lines:
            return json.dumps({"results": [], "query": query})
        return json.dumps({"results": lines, "query": query, "count": len(lines)})
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})


# ---------------------------------------------------------------------------
# vault_read
# ---------------------------------------------------------------------------

VAULT_READ_SCHEMA = {
    "name": "vault_read",
    "description": "Read the full content of a note in the vault by path.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the note relative to vault root (e.g. 'daily/2026-05-11')",
            },
        },
        "required": ["path"],
    },
}


def vault_read(args: dict, **kwargs) -> str:
    try:
        path = args["path"]
        rc, stdout, stderr = _run_obsidian("read", f'path="{path}"')
        if rc != 0:
            return json.dumps({"error": stderr.strip() or "note not found", "path": path, "content": None})
        return json.dumps({"path": path, "content": stdout})
    except Exception as e:
        return json.dumps({"error": str(e), "path": args.get("path"), "content": None})


# ---------------------------------------------------------------------------
# vault_backlinks
# ---------------------------------------------------------------------------

VAULT_BACKLINKS_SCHEMA = {
    "name": "vault_backlinks",
    "description": "Find all notes in the vault that link to the given note.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the target note relative to vault root",
            },
        },
        "required": ["path"],
    },
}


def vault_backlinks(args: dict, **kwargs) -> str:
    try:
        path = args["path"]
        rc, stdout, stderr = _run_obsidian("backlinks", f'path="{path}"')
        if rc != 0:
            return json.dumps({"error": stderr.strip() or "obsidian CLI error", "path": path, "backlinks": []})
        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        return json.dumps({"path": path, "backlinks": lines, "count": len(lines)})
    except Exception as e:
        return json.dumps({"error": str(e), "path": args.get("path"), "backlinks": []})


# ---------------------------------------------------------------------------
# vault_tags
# ---------------------------------------------------------------------------

VAULT_TAGS_SCHEMA = {
    "name": "vault_tags",
    "description": "List all tags in the vault, optionally filtered by a search term.",
    "parameters": {
        "type": "object",
        "properties": {
            "filter": {
                "type": "string",
                "description": "Optional substring to filter tags by",
            },
            "sort": {
                "type": "string",
                "enum": ["count", "name"],
                "description": "Sort order: 'count' (most used first) or 'name' (alphabetical)",
                "default": "count",
            },
        },
        "required": [],
    },
}


def vault_tags(args: dict, **kwargs) -> str:
    try:
        sort = args.get("sort", "count")
        cmd_args = ["tags"]
        if sort == "count":
            cmd_args.append("sort=count")
            cmd_args.append("counts")
        rc, stdout, stderr = _run_obsidian(*cmd_args)
        if rc != 0:
            return json.dumps({"error": stderr.strip() or "obsidian CLI error", "tags": []})
        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        tag_filter = args.get("filter")
        if tag_filter:
            lines = [l for l in lines if tag_filter.lower() in l.lower()]
        return json.dumps({"tags": lines, "count": len(lines)})
    except Exception as e:
        return json.dumps({"error": str(e), "tags": []})


# ---------------------------------------------------------------------------
# vault_graph
# ---------------------------------------------------------------------------

VAULT_GRAPH_SCHEMA = {
    "name": "vault_graph",
    "description": "Build a connection map for a note: its backlinks and outgoing [[wikilinks]].",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the note relative to vault root",
            },
        },
        "required": ["path"],
    },
}


def vault_graph(args: dict, **kwargs) -> str:
    try:
        path = args["path"]

        # Get backlinks via CLI
        rc_bl, stdout_bl, stderr_bl = _run_obsidian("backlinks", f'path="{path}"')
        backlinks = []
        if rc_bl == 0:
            backlinks = [l.strip() for l in stdout_bl.splitlines() if l.strip()]

        # Get note content to extract outgoing [[links]]
        rc_read, stdout_read, _ = _run_obsidian("read", f'path="{path}"')
        forward_links = []
        if rc_read == 0:
            forward_links = re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]", stdout_read)
            forward_links = list(dict.fromkeys(forward_links))  # dedupe, preserve order

        return json.dumps({
            "path": path,
            "backlinks": backlinks,
            "backlinks_count": len(backlinks),
            "forward_links": forward_links,
            "forward_links_count": len(forward_links),
        })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "path": args.get("path"),
            "backlinks": [],
            "forward_links": [],
        })


# ---------------------------------------------------------------------------
# vault_recent
# ---------------------------------------------------------------------------

VAULT_RECENT_SCHEMA = {
    "name": "vault_recent",
    "description": "List .md files in the vault modified within the last N hours.",
    "parameters": {
        "type": "object",
        "properties": {
            "hours": {
                "type": "number",
                "description": "How many hours back to look (default 24)",
                "default": 24,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum files to return (default 20)",
                "default": 20,
            },
        },
        "required": [],
    },
}


def vault_recent(args: dict, **kwargs) -> str:
    try:
        hours = float(args.get("hours", 24))
        limit = int(args.get("limit", 20))
        cutoff = datetime.now() - timedelta(hours=hours)

        vault = Path(VAULT_PATH)
        if not vault.exists():
            return json.dumps({"error": f"Vault path not found: {VAULT_PATH}", "files": []})

        results = []
        for md_file in vault.rglob("*.md"):
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            if mtime >= cutoff:
                rel = str(md_file.relative_to(vault))
                results.append({"path": rel, "modified": mtime.isoformat()})

        results.sort(key=lambda x: x["modified"], reverse=True)
        results = results[:limit]

        return json.dumps({"files": results, "count": len(results), "hours": hours})
    except Exception as e:
        return json.dumps({"error": str(e), "files": []})


# ---------------------------------------------------------------------------
# vault_write
# ---------------------------------------------------------------------------

VAULT_WRITE_SCHEMA = {
    "name": "vault_write",
    "description": (
        "Write or append content to a note in the vault. "
        "RESTRICTED: path must be under the 'hermes/' namespace."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path relative to vault root; MUST start with 'hermes/'",
            },
            "content": {
                "type": "string",
                "description": "Content to write",
            },
            "mode": {
                "type": "string",
                "enum": ["write", "append"],
                "description": "'write' overwrites, 'append' adds to end (default: write)",
                "default": "write",
            },
        },
        "required": ["path", "content"],
    },
}


def _validate_hermes_path(path: str) -> str:
    """Resolve and validate path is inside hermes/ namespace. Returns absolute path."""
    # Normalize: strip leading slash
    clean = path.lstrip("/")
    if not clean.startswith(HERMES_NAMESPACE + "/"):
        raise ValueError(f"vault_write is restricted to the 'hermes/' namespace. Got: {path!r}")
    abs_path = os.path.join(VAULT_PATH, clean)
    # Safety: ensure it stays within vault
    abs_vault = os.path.realpath(VAULT_PATH)
    abs_target = os.path.realpath(abs_path)
    if not abs_target.startswith(abs_vault + os.sep) and abs_target != abs_vault:
        raise ValueError(f"Path escapes vault root: {path!r}")
    return abs_path


def vault_write(args: dict, **kwargs) -> str:
    try:
        path = args["path"]
        content = args["content"]
        mode = args.get("mode", "write")

        abs_path = _validate_hermes_path(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        write_mode = "a" if mode == "append" else "w"
        with open(abs_path, write_mode, encoding="utf-8") as f:
            f.write(content)

        return json.dumps({"status": "ok", "path": path, "mode": mode})
    except ValueError as e:
        return json.dumps({"error": str(e), "status": "refused"})
    except Exception as e:
        return json.dumps({"error": str(e), "status": "error"})


# ---------------------------------------------------------------------------
# vault_properties
# ---------------------------------------------------------------------------

VAULT_PROPERTIES_SCHEMA = {
    "name": "vault_properties",
    "description": "Get or set YAML frontmatter properties on a vault note.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the note relative to vault root",
            },
            "action": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "'get' reads all properties, 'set' writes a property value",
                "default": "get",
            },
            "name": {
                "type": "string",
                "description": "Property name (required for 'set')",
            },
            "value": {
                "type": "string",
                "description": "Property value (required for 'set')",
            },
        },
        "required": ["path"],
    },
}


def vault_properties(args: dict, **kwargs) -> str:
    try:
        path = args["path"]
        action = args.get("action", "get")

        if action == "get":
            rc, stdout, stderr = _run_obsidian("property:get", f'path="{path}"')
            if rc != 0:
                return json.dumps({"error": stderr.strip() or "obsidian CLI error", "path": path, "properties": None})
            return json.dumps({"path": path, "properties": stdout.strip()})

        elif action == "set":
            prop_name = args.get("name")
            prop_value = args.get("value")
            if not prop_name or prop_value is None:
                return json.dumps({"error": "'name' and 'value' are required for action='set'", "status": "error"})
            rc, stdout, stderr = _run_obsidian(
                "property:set",
                f'name="{prop_name}"',
                f'value="{prop_value}"',
                f'file="{path}"',
            )
            if rc != 0:
                return json.dumps({"error": stderr.strip() or "obsidian CLI error", "status": "error"})
            return json.dumps({"status": "ok", "path": path, "name": prop_name, "value": prop_value})

        else:
            return json.dumps({"error": f"Unknown action: {action!r}", "status": "error"})

    except Exception as e:
        return json.dumps({"error": str(e), "path": args.get("path")})


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

_TOOLS = [
    ("vault_search", "obsidian", VAULT_SEARCH_SCHEMA, vault_search),
    ("vault_read", "obsidian", VAULT_READ_SCHEMA, vault_read),
    ("vault_backlinks", "obsidian", VAULT_BACKLINKS_SCHEMA, vault_backlinks),
    ("vault_tags", "obsidian", VAULT_TAGS_SCHEMA, vault_tags),
    ("vault_graph", "obsidian", VAULT_GRAPH_SCHEMA, vault_graph),
    ("vault_recent", "obsidian", VAULT_RECENT_SCHEMA, vault_recent),
    ("vault_write", "obsidian", VAULT_WRITE_SCHEMA, vault_write),
    ("vault_properties", "obsidian", VAULT_PROPERTIES_SCHEMA, vault_properties),
]


def register(ctx):
    for name, toolset, schema, handler in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=lambda: True,
        )
