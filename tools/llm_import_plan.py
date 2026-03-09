#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

RE_FASTAPI_DECORATOR = re.compile(r"^@(app|router)\.(get|post|put|delete|patch|websocket)\b")
RE_AREA_TAGS = [
    ("app/main.py", ["entrypoint", "routes", "ui", "api"]),
    ("app/models.py", ["db", "schema"]),
    ("app/parser.py", ["ssp", "parser"]),
    ("app/assessor.py", ["assessment", "scoring"]),
    ("app/remediation.py", ["remediation"]),
    ("app/mailer.py", ["email", "notifications"]),
    ("app/updater.py", ["jobs", "feeds", "nist"]),
    ("templates/", ["ui", "templates"]),
    ("static/", ["ui", "static"]),
    ("scripts/", ["ops", "scripts"]),
    ("docs/", ["docs"]),
    ("tests/", ["tests"]),
    ("config.yaml", ["config"]),
]

SENSITIVITY_RULES = [
    ("config.yaml", "admin"),
    ("app/main.py", "admin"),
    ("app/models.py", "admin"),
    ("app/mailer.py", "secret"),
    ("/etc/blacksite/", "secret"),
    ("data/.app_secret", "secret"),
]

DEFAULT_SENSITIVITY = "employee"

RUNTIME_SNAPSHOTS = [
    {
        "name": "version_stamp",
        "purpose": "branch, sha, build_time_utc for deployed instance",
        "fields": ["env", "branch", "sha_short", "sha_full", "build_time_utc"],
    },
    {
        "name": "route_map",
        "purpose": "effective routes plus methods plus tags plus auth guard names",
        "fields": ["path", "method", "endpoint", "tags", "auth_guard"],
    },
    {
        "name": "effective_config_redacted",
        "purpose": "effective config values with secrets removed",
        "fields": ["key", "value"],
        "redact_keys": ["app.secret_key", "ai.api_key", "email", "smtp", "password", "token"],
    },
    {
        "name": "job_status",
        "purpose": "scheduled jobs plus last-run plus last-status plus last-error",
        "fields": ["job_name", "schedule", "last_run", "last_status", "last_error"],
    },
    {
        "name": "db_schema",
        "purpose": "tables, columns, indexes, foreign keys",
        "fields": ["table", "column", "type", "nullable", "default", "indexes", "fks"],
    },
    {
        "name": "audit_vocab",
        "purpose": "event types, resource types, action codes, UI mapping rules",
        "fields": ["event_type", "resource_type", "action_code", "human_label", "details_template"],
    },
]

INTENT_ALLOWLIST = [
    "how do i do X in this app",
    "what happens when i click X",
    "which role is allowed to do X",
    "where is X implemented in code",
    "which config key controls X",
    "which job runs X",
    "what data is written when X runs",
    "why did request_id X fail",
]

@dataclass
class SourceItem:
    path: str
    purpose: str
    area_tags: List[str]
    sensitivity: str

def run(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()

def git_sha(repo_root: Path) -> str:
    try:
        return run(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    except Exception:
        return "unknown"

def git_ls_files(repo_root: Path) -> List[str]:
    out = run(["git", "-C", str(repo_root), "ls-files"])
    return [line.strip() for line in out.splitlines() if line.strip()]

def pick_tags(path: str) -> List[str]:
    tags: Set[str] = set()
    for prefix, t in RE_AREA_TAGS:
        if prefix.endswith("/") and path.startswith(prefix):
            tags.update(t)
        elif path == prefix:
            tags.update(t)
    if path.endswith(".md"):
        tags.add("docs")
    if path.endswith(".html"):
        tags.add("ui")
    if path.endswith(".css") or path.endswith(".js"):
        tags.add("ui")
    if path.endswith(".py"):
        tags.add("python")
    return sorted(tags)

def pick_sensitivity(path: str) -> str:
    for prefix, level in SENSITIVITY_RULES:
        if prefix.endswith("/") and path.startswith(prefix):
            return level
        if path == prefix:
            return level
    if "secrets" in path.lower():
        return "secret"
    return DEFAULT_SENSITIVITY

def one_line_purpose(path: str) -> str:
    if path == "app/main.py":
        return "FastAPI entrypoint, routes, session rules, settings cache, build stamp, UI shell"
    if path == "config.yaml":
        return "App configuration defaults, ports, base_url, cron schedule, feed URLs, email settings"
    if path.startswith("app/") and path.endswith(".py"):
        return "Application logic module"
    if path.startswith("templates/"):
        return "Server-rendered UI templates"
    if path.startswith("static/"):
        return "Static UI assets"
    if path.startswith("scripts/"):
        return "Operational scripts"
    if path.startswith("docs/"):
        return "Runbooks and documentation"
    if path.startswith("tests/"):
        return "Tests and regression coverage"
    return "Repo source"

def parse_main_for_routes_and_imports(repo_root: Path) -> Tuple[List[Dict[str, str]], Set[str]]:
    main_path = repo_root / "app" / "main.py"
    routes: List[Dict[str, str]] = []
    imports: Set[str] = set()
    if not main_path.exists():
        return routes, imports

    text = main_path.read_text(encoding="utf-8", errors="replace").splitlines()

    for line in text:
        m = RE_FASTAPI_DECORATOR.match(line.strip())
        if m:
            routes.append({"decorator": line.strip()})

    try:
        tree = ast.parse(main_path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("app."):
                    imports.add(node.module.replace(".", "/") + ".py")
    except Exception:
        pass

    return routes, imports

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Path to local blacksite repo root")
    ap.add_argument("--out", default="llm_import_manifest.json", help="Output manifest path")
    args = ap.parse_args()

    repo_root = Path(args.repo).resolve()
    files = git_ls_files(repo_root)
    sha = git_sha(repo_root)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    routes, imported_modules = parse_main_for_routes_and_imports(repo_root)

    sources: List[SourceItem] = []
    include_set: Set[str] = set(files)

    for mod in imported_modules:
        if mod in files:
            include_set.add(mod)

    for path in sorted(include_set):
        sources.append(
            SourceItem(
                path=path,
                purpose=one_line_purpose(path),
                area_tags=pick_tags(path),
                sensitivity=pick_sensitivity(path),
            )
        )

    manifest = {
        "repo": str(repo_root),
        "git_sha": sha,
        "generated_at_utc": generated_at,
        "intent_allowlist": INTENT_ALLOWLIST,
        "runtime_snapshots": RUNTIME_SNAPSHOTS,
        "routes_seen_in_main_py": routes,
        "sources": [asdict(s) for s in sources],
        "redaction_notes": [
            "Do not index /etc/blacksite/email.conf contents",
            "Do not index data/.app_secret contents",
            "Redact secret_key and ai api keys from config snapshots",
        ],
    }

    Path(args.out).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    txt_out = Path(args.out).with_suffix(".txt")
    lines: List[str] = []
    lines.append(f"Repo: {repo_root}")
    lines.append(f"SHA: {sha}")
    lines.append(f"Generated: {generated_at}")
    lines.append("")
    lines.append("Top priority sources")
    for p in ["app/main.py", "config.yaml", "app/models.py", "app/updater.py", "app/mailer.py"]:
        if p in include_set:
            lines.append(f"- {p}")
    lines.append("")
    lines.append("Runtime snapshots to capture")
    for s in RUNTIME_SNAPSHOTS:
        lines.append(f"- {s['name']}: {s['purpose']}")
    lines.append("")
    lines.append("Sources list")
    for s in sources:
        lines.append(f"- {s.path} | {','.join(s.area_tags)} | {s.sensitivity}")
    txt_out.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote: {args.out}")
    print(f"Wrote: {txt_out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
