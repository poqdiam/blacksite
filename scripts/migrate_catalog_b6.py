"""
Phase B-6 — Fill empty baseline_controls
=========================================
Run after migrate_catalog.py.

Populates:
  - nist_all        → all 1196 NIST 800-53r5 controls
  - iso27001_annex_a → all 93 ISO 27001 Annex A controls (from iso27001 catalog)
  - iso27001_core    → ISO 27001 Annex A core subset (~48 controls)
  - cmmc_l1          → 17 CMMC L1 practices (parsed from AC.L1- control_id prefix)
  - cmmc_l2          → 110 CMMC L2 practices (L1 + L2 practices)
  - cmmc_l3          → full CMMC practice set (L1 + L2 + L3)

CIS IG1/IG2/IG3: NOT seeded here — official CIS v8 IG assignments must be
imported from the CIS Controls v8 Excel spreadsheet to avoid inaccurate data.
A TODO marker is printed with import instructions.

Safe to re-run — all inserts use INSERT OR IGNORE.
"""

from __future__ import annotations
import re
import sys
import sqlite3
import logging
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "blacksite.db"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("migrate_b6")

# ── ISO 27001 "core" subset ────────────────────────────────────────────────────
# The ~48 Annex A controls most broadly applicable regardless of org size or type.
# Source: commonly cited SoA starting point across ISO 27001 practitioners.
ISO27001_CORE = {
    "A.5.1","A.5.2","A.5.3","A.5.4","A.5.9","A.5.10","A.5.12","A.5.15",
    "A.5.16","A.5.17","A.5.18","A.5.19","A.5.20","A.5.24","A.5.25","A.5.26",
    "A.5.29","A.5.31","A.5.33","A.5.35","A.5.36","A.5.37",
    "A.6.1","A.6.2","A.6.3","A.6.5","A.6.8",
    "A.7.1","A.7.2","A.7.4",
    "A.8.1","A.8.2","A.8.3","A.8.5","A.8.7","A.8.8","A.8.9","A.8.13",
    "A.8.15","A.8.16","A.8.20","A.8.21","A.8.22","A.8.24","A.8.25",
    "A.8.29","A.8.32","A.8.34",
}


def fw_id(con: sqlite3.Connection, short_name: str) -> str | None:
    row = con.execute(
        "SELECT id FROM compliance_frameworks WHERE short_name=?", (short_name,)
    ).fetchone()
    return row[0] if row else None


def catalog_controls_for(con: sqlite3.Connection, fw_sn: str) -> list[tuple[str, str]]:
    """Return [(catalog_control_id, control_id)] for a framework."""
    return con.execute("""
        SELECT cc.id, cc.control_id
        FROM catalog_controls cc
        JOIN compliance_frameworks cf ON cf.id=cc.framework_id
        WHERE cf.short_name=?
    """, (fw_sn,)).fetchall()


def seed_baseline(
    con: sqlite3.Connection,
    baseline_sn: str,
    controls: list[tuple[str, str]],   # [(cc_id, ctrl_label)]
    label: str,
):
    bl_id = fw_id(con, baseline_sn)
    if not bl_id:
        log.warning("No framework row for %s — skipping.", baseline_sn)
        return
    inserted = 0
    for cc_id, _ in controls:
        con.execute(
            "INSERT OR IGNORE INTO baseline_controls "
            "(baseline_id, catalog_control_id, is_required, created_at) "
            "VALUES (?,?,1,CURRENT_TIMESTAMP)",
            (bl_id, cc_id)
        )
        inserted += 1
    log.info("  %-22s  %d rows → baseline_controls", label, inserted)


def main():
    if not DB_PATH.exists():
        log.error("DB not found: %s", DB_PATH)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=OFF")

    try:
        # ── nist_all ─────────────────────────────────────────────────────────
        log.info("Seeding nist_all...")
        nist_ctrls = catalog_controls_for(con, "nist80053r5")
        seed_baseline(con, "nist_all", nist_ctrls, "nist_all")

        # ── ISO 27001 annex_a (all 93 Annex A from catalog) ──────────────────
        log.info("Seeding iso27001_annex_a...")
        iso_ctrls = catalog_controls_for(con, "iso27001")
        # Keep only proper Annex A entries (A.5.x – A.8.x)
        iso_annex = [(cc_id, cid) for cc_id, cid in iso_ctrls if cid.startswith("A.")]
        seed_baseline(con, "iso27001_annex_a", iso_annex, "iso27001_annex_a")

        # ── ISO 27001 core (~48 controls) ─────────────────────────────────────
        log.info("Seeding iso27001_core...")
        iso_core = [(cc_id, cid) for cc_id, cid in iso_annex if cid in ISO27001_CORE]
        seed_baseline(con, "iso27001_core", iso_core, "iso27001_core")
        log.info("    iso27001_core matched %d of %d defined core controls.", len(iso_core), len(ISO27001_CORE))

        # ── CMMC levels (parse from control_id prefix: AC.L1-, AC.L2-, AC.L3-) ──
        log.info("Seeding CMMC level baselines...")
        cmmc_all = catalog_controls_for(con, "cmmc2")

        def cmmc_level(ctrl_id: str) -> int:
            m = re.search(r"\.L(\d)-", ctrl_id)
            return int(m.group(1)) if m else 0

        # Update level column in catalog_controls while we're here
        level_updated = 0
        for cc_id, ctrl_id in cmmc_all:
            lv = cmmc_level(ctrl_id)
            if lv:
                con.execute(
                    "UPDATE catalog_controls SET level=? WHERE id=?",
                    (f"L{lv}", cc_id)
                )
                level_updated += 1
        log.info("  Updated level on %d CMMC catalog_controls rows.", level_updated)

        # L1: only L1 practices (17)
        cmmc_l1 = [(cc_id, cid) for cc_id, cid in cmmc_all if cmmc_level(cid) == 1]
        seed_baseline(con, "cmmc_l1", cmmc_l1, "cmmc_l1")

        # L2: L1 + L2 practices (110 total = NIST SP 800-171)
        cmmc_l2 = [(cc_id, cid) for cc_id, cid in cmmc_all if cmmc_level(cid) in (1, 2)]
        seed_baseline(con, "cmmc_l2", cmmc_l2, "cmmc_l2")

        # L3: L1 + L2 + L3 practices (all)
        cmmc_l3 = [(cc_id, cid) for cc_id, cid in cmmc_all if cmmc_level(cid) in (1, 2, 3)]
        seed_baseline(con, "cmmc_l3", cmmc_l3, "cmmc_l3")

        log.info("  CMMC L1: %d  L2: %d  L3: %d", len(cmmc_l1), len(cmmc_l2), len(cmmc_l3))

        con.commit()

        # ── Summary ───────────────────────────────────────────────────────────
        log.info("\n=== baseline_controls summary ===")
        for row in con.execute("""
            SELECT cf.short_name, COUNT(bc.id)
            FROM compliance_frameworks cf
            LEFT JOIN baseline_controls bc ON bc.baseline_id=cf.id
            WHERE cf.kind='baseline'
            GROUP BY cf.id ORDER BY cf.short_name
        """):
            log.info("  %-30s %d", row[0], row[1])

        log.info("\nTODO — CIS IG1/IG2/IG3 baselines are empty.")
        log.info("  Import from: https://www.cisecurity.org/controls/v8")
        log.info("  Download the CIS Controls v8 Excel spreadsheet.")
        log.info("  Each safeguard row has an 'IG' column (1, 2, or 3).")
        log.info("  Run: scripts/import_cis_ig.py <path-to-cis-v8.xlsx>")

    except Exception as e:
        con.rollback()
        log.error("Failed — rolled back: %s", e)
        raise
    finally:
        con.execute("PRAGMA foreign_keys=ON")
        con.close()


if __name__ == "__main__":
    main()
