"""
Phase 34 — Agnostic Control Catalog Migration
=============================================
Populates catalog_controls, control_relationships, and baseline_controls
from existing data sources, then backfills catalog_control_id FKs on all
tables that reference controls by raw string.

Run once from the project root:
    python scripts/migrate_catalog.py

Safe to re-run — all inserts use INSERT OR IGNORE.
"""

from __future__ import annotations
import json
import sys
import uuid
import logging
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sqlite3

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("migrate_catalog")

DB_PATH       = ROOT / "blacksite.db"
CONTROLS_DIR  = ROOT / "controls"
CATALOG_JSON  = CONTROLS_DIR / "nist_800_53r5.json"

# ── helpers ───────────────────────────────────────────────────────────────────

def _uid() -> str:
    return str(uuid.uuid4())


def get_framework_id(con: sqlite3.Connection, short_name: str) -> str | None:
    row = con.execute(
        "SELECT id FROM compliance_frameworks WHERE short_name=?", (short_name,)
    ).fetchone()
    return row[0] if row else None


# ── NIST 800-53r5 OSCAL parsing (mirrors updater.py logic) ───────────────────

def _get_label(part: dict) -> str:
    for prop in part.get("props", []):
        if prop.get("name") == "label":
            return prop.get("value", "")
    return ""


def _extract_prose(part: dict, depth: int = 0) -> str:
    lines = []
    label = _get_label(part)
    prose = (part.get("prose") or "").strip()
    indent = "   " * depth
    if prose:
        lines.append(f"{indent}{label} {prose}".strip())
    for sub in part.get("parts", []):
        t = _extract_prose(sub, depth + 1)
        if t:
            lines.append(t)
    return "\n".join(l for l in lines if l)


def _collect_nist_controls(group: dict, family_id: str, family_title: str, out: dict):
    for ctrl in group.get("controls", []):
        cid   = ctrl.get("id", "").lower()
        parts = ctrl.get("parts", [])
        statement = next((_extract_prose(p) for p in parts if p.get("name") == "statement"), "")
        params = []
        for p in ctrl.get("params", []):
            pid = p.get("id", "")
            if not pid:
                continue
            label = p.get("label", "")
            if not label:
                choices = p.get("select", {}).get("choice", [])
                label = " | ".join(choices) if choices else pid
            params.append({"id": pid, "label": label})
        enhancements = []
        for enh in ctrl.get("controls", []):
            eid = enh.get("id", "").lower()
            eparts = enh.get("parts", [])
            estmt = next((_extract_prose(p) for p in eparts if p.get("name") == "statement"), "")
            enhancements.append({"id": eid, "title": enh.get("title", ""), "statement": estmt})
        out[cid] = {
            "title":            ctrl.get("title", ""),
            "family_id":        family_id.upper(),
            "family_title":     family_title,
            "statement":        statement,
            "parameters":       params,
            "enhancements":     enhancements,
        }
        # recurse into enhancements (they also appear as sub-controls)
        _collect_nist_controls(ctrl, family_id, family_title, out)


def load_nist_controls() -> dict:
    if not CATALOG_JSON.exists():
        log.error("NIST catalog not found at %s", CATALOG_JSON)
        return {}
    raw     = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    catalog = raw.get("catalog", raw)
    out: dict = {}
    for group in catalog.get("groups", []):
        fid   = group.get("id", "??")
        ftit  = group.get("title", "Unknown")
        _collect_nist_controls(group, fid, ftit, out)
    log.info("Parsed %d NIST controls from OSCAL JSON.", len(out))
    return out


def load_baseline_ids(name: str) -> list[str]:
    path = CONTROLS_DIR / f"{name}_profile.json"
    if not path.exists():
        log.warning("Baseline profile not found: %s", path)
        return []
    raw     = json.loads(path.read_text(encoding="utf-8"))
    profile = raw.get("profile", raw)
    ids: list[str] = []
    for imp in profile.get("imports", []):
        for ic in imp.get("include-controls", []):
            for cid in ic.get("with-ids", []):
                ids.append(cid.lower())
    log.info("  %s baseline: %d controls", name, len(ids))
    return ids


# ── Phase B-1: populate catalog_controls from NIST OSCAL ─────────────────────

def seed_nist_catalog(con: sqlite3.Connection) -> dict[str, str]:
    """Insert NIST 800-53r5 controls.  Returns {control_id: row_uuid}."""
    fw_id = get_framework_id(con, "nist80053r5")
    if not fw_id:
        log.error("compliance_frameworks row for 'nist80053r5' not found — run the app first.")
        sys.exit(1)

    controls = load_nist_controls()
    if not controls:
        log.error("No NIST controls parsed — check controls/nist_800_53r5.json.")
        sys.exit(1)

    # Build id map: control_id → existing UUID (if already seeded)
    existing = {
        row[0]: row[1]
        for row in con.execute(
            "SELECT control_id, id FROM catalog_controls WHERE framework_id=?", (fw_id,)
        ).fetchall()
    }

    inserted = 0
    for cid, c in controls.items():
        if cid in existing:
            continue
        row_id = _uid()
        con.execute(
            """INSERT OR IGNORE INTO catalog_controls
               (id, framework_id, control_id, title, description, domain,
                parameters_json, enhancements_json, created_at)
               VALUES (?,?,?,?,?,?,?,?, CURRENT_TIMESTAMP)""",
            (
                row_id, fw_id, cid,
                c["title"],
                c["statement"] or None,
                c["family_id"],                           # domain = family (AC, SI, …)
                json.dumps(c["parameters"]) if c["parameters"] else None,
                json.dumps(c["enhancements"]) if c["enhancements"] else None,
            )
        )
        existing[cid] = row_id
        inserted += 1

    log.info("NIST catalog_controls: %d inserted, %d already present.", inserted, len(existing) - inserted)
    return existing   # {control_id: uuid}


# ── Phase B-2: migrate FrameworkControl → catalog_controls ───────────────────

def migrate_framework_controls(con: sqlite3.Connection) -> dict[int, str]:
    """
    Copy existing framework_controls rows into catalog_controls.
    Returns {old_framework_control.id: new_catalog_controls.id}.
    """
    rows = con.execute(
        """SELECT fc.id, fc.framework_id, fc.control_id, fc.title, fc.description, fc.domain
           FROM framework_controls fc"""
    ).fetchall()

    mapping: dict[int, str] = {}
    inserted = skipped = 0

    for old_id, fw_id, ctrl_id, title, desc, domain in rows:
        # Check if already in catalog_controls
        existing = con.execute(
            "SELECT id FROM catalog_controls WHERE framework_id=? AND control_id=?",
            (fw_id, ctrl_id)
        ).fetchone()
        if existing:
            mapping[old_id] = existing[0]
            skipped += 1
            continue
        new_id = _uid()
        con.execute(
            """INSERT OR IGNORE INTO catalog_controls
               (id, framework_id, control_id, title, description, domain, created_at)
               VALUES (?,?,?,?,?,?, CURRENT_TIMESTAMP)""",
            (new_id, fw_id, ctrl_id, title, desc, domain)
        )
        mapping[old_id] = new_id
        inserted += 1

    log.info("framework_controls migration: %d inserted, %d already present.", inserted, skipped)
    return mapping


# ── Phase B-3: migrate ControlCrosswalk → control_relationships ──────────────

def migrate_crosswalks(
    con: sqlite3.Connection,
    fc_map: dict[int, str],
    nist_map: dict[str, str],
):
    """Convert ControlCrosswalk rows to bidirectional ControlRelationship rows."""
    rows = con.execute(
        "SELECT framework_control_id, nist_control_id, mapping_type, confidence, source, notes "
        "FROM control_crosswalks"
    ).fetchall()

    inserted = skipped = errors = 0
    for fc_id, nist_cid, mapping_type, confidence, source, notes in rows:
        a_id = fc_map.get(fc_id)
        b_id = nist_map.get(nist_cid.lower() if nist_cid else "")
        if not a_id or not b_id:
            errors += 1
            continue

        # mapping_type direct → equivalent, partial → partial, inferred → addresses
        rel = {"direct": "equivalent", "partial": "partial", "inferred": "addresses"}.get(
            mapping_type or "direct", "equivalent"
        )
        direction = "bidirectional" if rel == "equivalent" else "a_satisfies_b"

        try:
            con.execute(
                """INSERT OR IGNORE INTO control_relationships
                   (control_a_id, control_b_id, relationship, direction,
                    confidence, source, notes, created_at)
                   VALUES (?,?,?,?,?,?,?, CURRENT_TIMESTAMP)""",
                (a_id, b_id, rel, direction,
                 confidence or "high", source or "nist_official", notes)
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    log.info("control_relationships: %d inserted, %d duplicates, %d unresolved.", inserted, skipped, errors)


# ── Phase B-4: populate baseline_controls ────────────────────────────────────

def seed_baseline_controls(con: sqlite3.Connection, nist_map: dict[str, str]):
    """Populate baseline_controls for NIST Low/Mod/High/Privacy baselines."""
    baselines = ["nist_low", "nist_mod", "nist_high", "nist_privacy"]
    total_inserted = 0

    for bname in baselines:
        fw_id = get_framework_id(con, bname)
        if not fw_id:
            log.warning("  No framework row for %s — skipping.", bname)
            continue
        ctrl_ids = load_baseline_ids(bname)
        if not ctrl_ids:
            continue
        inserted = 0
        for cid in ctrl_ids:
            cc_id = nist_map.get(cid)
            if not cc_id:
                continue
            con.execute(
                """INSERT OR IGNORE INTO baseline_controls
                   (baseline_id, catalog_control_id, is_required, created_at)
                   VALUES (?,?,1, CURRENT_TIMESTAMP)""",
                (fw_id, cc_id)
            )
            inserted += 1
        log.info("  baseline_controls %s: %d rows.", bname, inserted)
        total_inserted += inserted

    log.info("baseline_controls total: %d rows.", total_inserted)


# ── Phase B-5: backfill catalog_control_id FKs on existing records ───────────

def backfill_fks(con: sqlite3.Connection, nist_map: dict[str, str]):
    """
    For tables that store control_id as a NIST string, set catalog_control_id
    where it is currently NULL and a matching catalog_controls row exists.

    Tables with comma/JSON-encoded control_ids (observations, evidence_files)
    are left as-is — they keep their string columns as display cache.
    """
    tables = [
        ("system_controls",    "control_id",   "source_catalog"),
        ("control_results",    "control_id",   None),
        ("poam_items",         "control_id",   None),
        ("control_parameters", "control_id",   None),
        ("auto_fail_events",   "control_id",   None),
        ("artifacts",          "control_id",   None),
    ]

    for table, col, catalog_col in tables:
        # Fetch rows needing backfill
        rows = con.execute(
            f"SELECT rowid, {col} FROM {table} "
            f"WHERE catalog_control_id IS NULL AND {col} IS NOT NULL"
        ).fetchall()

        updated = skipped = 0
        for rowid, ctrl_id in rows:
            if not ctrl_id:
                continue
            # Normalise — could be "ac-2" or "ac-2,si-3" (poam) or uppercase
            cid = ctrl_id.strip().lower().split(",")[0].strip()
            cc_id = nist_map.get(cid)
            if not cc_id:
                # Try framework_controls for non-NIST (e.g. "A.5.18")
                existing = con.execute(
                    "SELECT id FROM catalog_controls WHERE LOWER(control_id)=?", (cid,)
                ).fetchone()
                cc_id = existing[0] if existing else None
            if cc_id:
                con.execute(
                    f"UPDATE {table} SET catalog_control_id=? WHERE rowid=?",
                    (cc_id, rowid)
                )
                updated += 1
            else:
                skipped += 1

        log.info("  backfill %s: %d updated, %d unresolved.", table, updated, skipped)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if not DB_PATH.exists():
        log.error("Database not found at %s", DB_PATH)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=OFF")   # allow inserts before FK targets exist in edge cases

    try:
        log.info("=== Phase B-1: Seed NIST 800-53r5 into catalog_controls ===")
        nist_map = seed_nist_catalog(con)

        log.info("=== Phase B-2: Migrate framework_controls → catalog_controls ===")
        fc_map = migrate_framework_controls(con)

        log.info("=== Phase B-3: Migrate control_crosswalks → control_relationships ===")
        migrate_crosswalks(con, fc_map, nist_map)

        log.info("=== Phase B-4: Seed baseline_controls for NIST baselines ===")
        seed_baseline_controls(con, nist_map)

        log.info("=== Phase B-5: Backfill catalog_control_id FKs ===")
        backfill_fks(con, nist_map)

        con.commit()
        log.info("=== Migration complete. ===")

        # Summary
        for tbl in ("catalog_controls", "control_relationships", "baseline_controls"):
            n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            log.info("  %-28s %d rows", tbl, n)

    except Exception as e:
        con.rollback()
        log.error("Migration failed — rolled back: %s", e)
        raise
    finally:
        con.execute("PRAGMA foreign_keys=ON")
        con.close()


if __name__ == "__main__":
    main()
