#!/usr/bin/env python3
"""
Ingest PT (PII Processing and Transparency) control family from the NIST 800-53r5
OSCAL catalog into the BLACKSITE system_controls table.

For each system × each PT control, inserts a row with:
  - status: "not_implemented"
  - implementation_type: "system_specific"
  - created_by: "nist_ingest"
Uses INSERT OR IGNORE so re-runs are safe.
"""

import json
import asyncio
import aiosqlite
from datetime import datetime, timezone

CATALOG_PATH = "/home/graycat/projects/blacksite/controls/nist_800_53r5.json"
DB_PATH = "/home/graycat/projects/blacksite/blacksite.db"
CONTROL_FAMILY = "PT"


def extract_pt_controls(catalog_path: str):
    """Parse OSCAL catalog and return all PT-family controls (base + enhancements)."""
    with open(catalog_path) as f:
        catalog = json.load(f)

    groups = catalog.get("catalog", {}).get("groups", [])
    pt_controls = []

    for group in groups:
        if group.get("id", "").lower() != "pt":
            continue
        for ctrl in group.get("controls", []):
            pt_controls.append({
                "id": ctrl["id"],
                "title": ctrl.get("title", ""),
            })
            # Control enhancements are nested under 'controls' key
            for enh in ctrl.get("controls", []):
                pt_controls.append({
                    "id": enh["id"],
                    "title": enh.get("title", ""),
                })

    return pt_controls


async def get_all_system_ids(db: aiosqlite.Connection):
    async with db.execute("SELECT id FROM systems") as cur:
        rows = await cur.fetchall()
    return [row[0] for row in rows]


async def ingest(db_path: str, catalog_path: str) -> None:
    pt_controls = extract_pt_controls(catalog_path)
    print(f"PT controls found (base + enhancements): {len(pt_controls)}")
    for c in pt_controls:
        print(f"  {c['id']:12s}  {c['title']}")
    print()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    async with aiosqlite.connect(db_path) as db:
        # Batch writes are much faster with WAL pragma
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")

        system_ids = await get_all_system_ids(db)
        print(f"Systems to receive PT controls: {len(system_ids)}")
        print(f"Expected inserts (system × control): {len(system_ids)} × {len(pt_controls)} = {len(system_ids) * len(pt_controls)}")
        print()

        rows = []
        for sid in system_ids:
            for ctrl in pt_controls:
                rows.append((
                    sid,                    # system_id
                    ctrl["id"],             # control_id
                    CONTROL_FAMILY,         # control_family
                    ctrl["title"],          # control_title
                    "not_implemented",      # status
                    "system_specific",      # implementation_type
                    None,                   # narrative
                    None,                   # responsible_role
                    None,                   # inherited_from
                    None,                   # inherited_narrative
                    None,                   # last_updated_by
                    now,                    # last_updated_at
                    now,                    # created_at
                    "nist_ingest",          # created_by
                ))

        await db.executemany(
            """
            INSERT OR IGNORE INTO system_controls
                (system_id, control_id, control_family, control_title,
                 status, implementation_type, narrative, responsible_role,
                 inherited_from, inherited_narrative, last_updated_by,
                 last_updated_at, created_at, created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        await db.commit()

        # Report actual rows inserted (vs skipped duplicates)
        async with db.execute(
            "SELECT COUNT(*) FROM system_controls WHERE control_family = 'PT'"
        ) as cur:
            result = await cur.fetchone()
            inserted = result[0]

    print(f"Rows in system_controls with family=PT after ingest: {inserted}")
    print(f"Done.")


if __name__ == "__main__":
    asyncio.run(ingest(DB_PATH, CATALOG_PATH))
