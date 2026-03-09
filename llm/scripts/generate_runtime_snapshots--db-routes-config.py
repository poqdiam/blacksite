#!/usr/bin/env python3
"""
generate_runtime_snapshots.py
Generates runtime context snapshots for the BLACKSITE LLM knowledge base.

Snapshots capture the live state of the system:
  - version_stamp: git sha, build time
  - route_map: all FastAPI routes with methods and tags
  - effective_config_redacted: config.yaml with secrets removed
  - job_status: scheduled job states
  - db_schema: live database schema (tables, columns, indexes)
  - audit_vocab: action codes, resource types, human labels

Run: python3 llm/scripts/generate_runtime_snapshots.py --out llm/runtime/
Schedule: After each deploy + daily via blacksite-update-controls.timer
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml  # pip install pyyaml

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
DB_PATH = REPO_ROOT / "blacksite.db"
CONFIG_PATH = REPO_ROOT / "config.yaml"
MAIN_PY = REPO_ROOT / "app" / "main.py"

REDACT_KEYS = {
    "secret_key", "api_key", "password", "token", "smtp_password",
    "smtp_user", "smtp_host", "from_addr", "email", "relay",
}

REDACT_PATTERN = re.compile(
    r"(secret|key|password|token|smtp|email|relay|api_key)", re.IGNORECASE
)


def redact_value(key: str, value: object) -> object:
    key_lower = str(key).lower()
    if any(k in key_lower for k in REDACT_KEYS):
        return "[REDACTED]"
    if isinstance(value, str) and REDACT_PATTERN.search(key):
        return "[REDACTED]"
    return value


def flatten_dict(d: dict, prefix: str = "") -> dict:
    """Flatten nested YAML dict to dotted key paths."""
    result = {}
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(flatten_dict(v, full_key))
        else:
            result[full_key] = redact_value(full_key, v)
    return result


def get_version_stamp() -> dict:
    """Capture git SHA, branch, and build time."""
    def run(cmd):
        try:
            return subprocess.check_output(
                cmd, cwd=str(REPO_ROOT), stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            return "unknown"

    sha_full = run(["git", "rev-parse", "HEAD"])
    sha_short = sha_full[:8] if sha_full != "unknown" else "unknown"
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    return {
        "snapshot": "version_stamp",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "env": "production",
        "branch": branch,
        "sha_short": sha_short,
        "sha_full": sha_full,
        "build_time_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
    }


def get_effective_config_redacted() -> dict:
    """Load config.yaml and redact sensitive values."""
    if not CONFIG_PATH.exists():
        return {"snapshot": "effective_config_redacted", "error": "config.yaml not found"}

    with CONFIG_PATH.open() as f:
        raw = yaml.safe_load(f)

    flat = flatten_dict(raw or {})
    return {
        "snapshot": "effective_config_redacted",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": flat,
    }


def get_db_schema() -> dict:
    """Read live SQLite schema: tables, columns, indexes, foreign keys."""
    if not DB_PATH.exists():
        return {"snapshot": "db_schema", "error": f"DB not found at {DB_PATH}"}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = {}

    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for (table_name,) in cur.fetchall():
        if table_name.startswith("sqlite_"):
            continue

        # Columns
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for row in cur.fetchall():
            columns.append({
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "default": row["dflt_value"],
                "pk": bool(row["pk"]),
            })

        # Indexes
        cur.execute(f"PRAGMA index_list({table_name})")
        indexes = []
        for irow in cur.fetchall():
            cur.execute(f"PRAGMA index_info({irow['name']})")
            idx_cols = [r["name"] for r in cur.fetchall()]
            indexes.append({
                "name": irow["name"],
                "unique": bool(irow["unique"]),
                "columns": idx_cols,
            })

        # Foreign keys
        cur.execute(f"PRAGMA foreign_key_list({table_name})")
        fks = []
        for frow in cur.fetchall():
            fks.append({
                "from": frow["from"],
                "table": frow["table"],
                "to": frow["to"],
            })

        # Row count
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cur.fetchone()[0]
        except Exception:
            row_count = -1

        tables[table_name] = {
            "columns": columns,
            "indexes": indexes,
            "foreign_keys": fks,
            "row_count": row_count,
        }

    conn.close()
    return {
        "snapshot": "db_schema",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "db_path": str(DB_PATH),
        "tables": tables,
        "table_count": len(tables),
    }


def get_route_map() -> dict:
    """Extract routes from main.py via regex (no import needed)."""
    if not MAIN_PY.exists():
        return {"snapshot": "route_map", "error": "main.py not found"}

    text = MAIN_PY.read_text(encoding="utf-8", errors="replace")
    routes = []

    # Match FastAPI decorators followed by function definitions
    # Pattern: @app.METHOD("PATH") + optional response_model, etc.
    # then async def FUNCNAME(
    decorator_re = re.compile(
        r'@(?:app|router)\.(get|post|put|delete|patch|websocket)\(\s*["\']([^"\']+)["\']',
        re.MULTILINE,
    )
    func_re = re.compile(r'async def (\w+)\s*\(')

    lines = text.splitlines()
    for i, line in enumerate(lines):
        dm = decorator_re.search(line)
        if dm:
            method = dm.group(1).upper()
            path = dm.group(2)
            # Look ahead for function name
            func_name = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                fm = func_re.search(lines[j])
                if fm:
                    func_name = fm.group(1)
                    break
            routes.append({
                "method": method,
                "path": path,
                "endpoint": func_name,
                "auth_guard": "Remote-User header required",
            })

    return {
        "snapshot": "route_map",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "routes": routes,
        "route_count": len(routes),
    }


def get_audit_vocab() -> dict:
    """Extract audit action/resource type vocabulary from main.py."""
    if not MAIN_PY.exists():
        return {"snapshot": "audit_vocab", "error": "main.py not found"}

    text = MAIN_PY.read_text(encoding="utf-8", errors="replace")

    # Extract _RTYPE_LABELS and _ACTION_LABELS dicts
    rtype_labels = {}
    action_labels = {}

    rtype_m = re.search(r"_RTYPE_LABELS\s*=\s*\{([^}]+)\}", text, re.DOTALL)
    if rtype_m:
        for pair in re.finditer(r'"(\w+)"\s*:\s*"([^"]+)"', rtype_m.group(1)):
            rtype_labels[pair.group(1)] = pair.group(2)

    action_m = re.search(r"_ACTION_LABELS\s*=\s*\{([^}]+)\}", text, re.DOTALL)
    if action_m:
        for pair in re.finditer(r'"(\w+)"\s*:\s*"([^"]+)"', action_m.group(1)):
            action_labels[pair.group(1)] = pair.group(2)

    return {
        "snapshot": "audit_vocab",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "resource_type_labels": rtype_labels,
        "action_labels": action_labels,
        "outcome_codes": {
            "ok": "Action completed successfully",
            "denied": "Access denied or authorization failed",
            "error": "Server-side error during action",
        },
    }


def get_job_status() -> dict:
    """Read job/scheduler status from DB if available."""
    status = {
        "snapshot": "job_status",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "jobs": [],
    }

    if not DB_PATH.exists():
        return status

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Check if control_update_jobs table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='control_update_jobs'")
        if cur.fetchone():
            cur.execute("SELECT * FROM control_update_jobs ORDER BY started_at DESC LIMIT 10")
            for row in cur.fetchall():
                status["jobs"].append(dict(row))
        conn.close()
    except Exception as e:
        status["error"] = str(e)

    return status


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="llm/runtime", help="Output directory for snapshots")
    ap.add_argument("--snapshot", default="all",
                    help="Which snapshot to generate: all|version|config|schema|routes|audit|jobs")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    snapshots = {
        "version": ("version_stamp.json", get_version_stamp),
        "config": ("effective_config_redacted.json", get_effective_config_redacted),
        "schema": ("db_schema.json", get_db_schema),
        "routes": ("route_map.json", get_route_map),
        "audit": ("audit_vocab.json", get_audit_vocab),
        "jobs": ("job_status.json", get_job_status),
    }

    to_run = snapshots.keys() if args.snapshot == "all" else [args.snapshot]

    for key in to_run:
        if key not in snapshots:
            print(f"Unknown snapshot: {key}", file=sys.stderr)
            continue
        filename, fn = snapshots[key]
        data = fn()
        out_path = out_dir / filename
        out_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
