"""
BLACKSITE RBAC Runner — Fixture bootstrap module.

Creates test fixtures directly in the SQLite database using SQLAlchemy:
  - Test users (bsv_test_principal, bsv_test_executive, bsv_test_manager, bsv_test_analyst)
  - 3 test systems: BSV-TEST-ALPHA, BSV-TEST-BRAVO, BSV-TEST-CHARLIE
  - A test Risk on ALPHA
  - A test POAM item on ALPHA
  - A test BCDR event on ALPHA
  - ProgramRoleAssignments for each system role on each system
  - DutyAssignments for pen_tester and auditor (time-boxed)

Writes fixture IDs to tests/rbac/config/fixtures.yaml

Usage:
  python -m tests.rbac.fixtures --db-path blacksite.db
  python -m tests.rbac.fixtures --db-path blacksite.db --clean
"""
from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

log = logging.getLogger("bsv.rbac.fixtures")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s")

PROJECT_ROOT = Path(__file__).parent.parent.parent
FIXTURES_YAML = Path(__file__).parent / "config" / "fixtures.yaml"

TEST_SYSTEMS = [
    {
        "name":         "BSV-TEST-ALPHA",
        "abbreviation": "ALPH",
        "auth_status":  "authorized",
        "description":  "RBAC test system A — authorized",
        "auth_date":    "2025-01-15",
        "auth_expiry":  "2028-01-15",
        "overall_impact": "High",
        "confidentiality_impact": "High",
        "integrity_impact": "High",
        "availability_impact": "High",
        "system_type":  "major_application",
        "environment":  "on_prem",
    },
    {
        "name":         "BSV-TEST-BRAVO",
        "abbreviation": "BRAV",
        "auth_status":  "in_progress",
        "description":  "RBAC test system B — in progress",
        "overall_impact": "Moderate",
        "confidentiality_impact": "Moderate",
        "integrity_impact": "Moderate",
        "availability_impact": "Low",
        "system_type":  "general_support_system",
        "environment":  "cloud",
    },
    {
        "name":         "BSV-TEST-CHARLIE",
        "abbreviation": "CHAR",
        "auth_status":  "not_authorized",
        "description":  "RBAC test system C — not authorized",
        "overall_impact": "Low",
        "confidentiality_impact": "Low",
        "integrity_impact": "Low",
        "availability_impact": "Low",
        "system_type":  "minor_application",
        "environment":  "hybrid",
    },
]

TEST_USERS = {
    "principal": {
        "remote_user":  "bsv_test_principal",
        "display_name": "BSV Test Principal",
        "email":        "bsv_test_principal@blacksite.test",
        "role":         "admin",
        "company_tier": "principal",
        "status":       "active",
    },
    "executive": {
        "remote_user":  "bsv_test_executive",
        "display_name": "BSV Test Executive",
        "email":        "bsv_test_executive@blacksite.test",
        "role":         "ao",
        "company_tier": "executive",
        "status":       "active",
    },
    "manager": {
        "remote_user":  "bsv_test_manager",
        "display_name": "BSV Test Manager",
        "email":        "bsv_test_manager@blacksite.test",
        "role":         "issm",
        "company_tier": "manager",
        "status":       "active",
    },
    "analyst": {
        "remote_user":  "bsv_test_analyst",
        "display_name": "BSV Test Analyst",
        "email":        "bsv_test_analyst@blacksite.test",
        # Native role must be "issm" (not "isso") so _get_user_role can shell into
        # both "isso" and "sca" via ROLE_CAN_VIEW_DOWN.get("issm") = [isso, sca, ...]
        "role":         "issm",
        "company_tier": "analyst",
        "status":       "active",
    },
}

# All system roles to assign to each test user on each system
SYSTEM_ROLES = [
    "ao", "aodr", "ciso", "issm", "isso", "sca", "system_owner", "pmo",
    "incident_responder", "bcdr_coordinator", "data_owner", "pen_tester", "auditor",
]

# Time-boxed duties (pen_tester + auditor expire in 90 days)
TIMEBOX_DUTIES = ["pen_tester", "auditor"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


def bootstrap(db_path: str, clean: bool = False) -> dict:
    """
    Create all test fixtures in the database.
    Returns the fixture IDs dict.
    """
    # Ensure we run from the project root so SQLAlchemy can find the DB
    import os
    os.chdir(PROJECT_ROOT)

    # Import app models (must be done from project root)
    sys.path.insert(0, str(PROJECT_ROOT))
    from app.models import (
        Base, System, UserProfile, ProgramRoleAssignment, DutyAssignment,
        SystemAssignment, Risk, PoamItem, BcdrEvent,
        make_engine, make_session_factory, init_db
    )
    import asyncio
    from sqlalchemy import select, text

    db_url = f"sqlite+aiosqlite:///{db_path}"
    config = {"db": {"path": db_path}}
    engine = make_engine(config)
    SessionLocal = make_session_factory(engine)

    async def _run():
        await init_db(engine)
        fixture_ids: dict = {
            "systems": {},
            "users": {},
            "risks": {},
            "poam": {},
            "bcdr": {},
        }

        async with SessionLocal() as session:
            # ── Clean existing test fixtures ──────────────────────────────────
            if clean:
                log.info("Cleaning existing test fixtures...")
                # Clean system_assignments for bsv_test_* users
                try:
                    await session.execute(text(
                        "DELETE FROM system_assignments WHERE remote_user LIKE 'bsv_test_%'"
                    ))
                except Exception as e:
                    log.debug("Clean system_assignments: %s", e)
                for tbl in ["bcdr_events", "bcdr_signoffs", "duty_assignments",
                             "program_role_assignments", "poam_items", "risks", "systems",
                             "user_profiles"]:
                    try:
                        if tbl == "systems":
                            await session.execute(text(
                                "DELETE FROM systems WHERE name LIKE 'BSV-TEST-%'"
                            ))
                        elif tbl == "user_profiles":
                            await session.execute(text(
                                "DELETE FROM user_profiles WHERE remote_user LIKE 'bsv_test_%'"
                            ))
                        elif tbl in ("poam_items",):
                            # Delete test poams linked to test systems
                            await session.execute(text(
                                "DELETE FROM poam_items WHERE weakness_name LIKE 'RBAC Test%'"
                            ))
                        elif tbl in ("risks",):
                            await session.execute(text(
                                "DELETE FROM risks WHERE risk_name LIKE 'RBAC Test%'"
                            ))
                    except Exception as e:
                        log.debug("Clean %s: %s", tbl, e)
                await session.commit()
                log.info("Cleanup complete")

            # ── Create test users ─────────────────────────────────────────────
            for tier, user_data in TEST_USERS.items():
                remote_user = user_data["remote_user"]
                existing = (await session.execute(
                    select(UserProfile).where(UserProfile.remote_user == remote_user)
                )).scalar_one_or_none()

                if existing is None:
                    profile = UserProfile(
                        remote_user=remote_user,
                        display_name=user_data["display_name"],
                        email=user_data["email"],
                        role=user_data["role"],
                        company_tier=user_data["company_tier"],
                        status="active",
                        created_at=_now(),
                    )
                    session.add(profile)
                    log.info("Created user: %s (%s)", remote_user, tier)
                else:
                    # Update tier in case it changed
                    existing.company_tier = user_data["company_tier"]
                    existing.role = user_data["role"]
                    log.info("User %s already exists — updated tier", remote_user)

                fixture_ids["users"][f"{tier}_user"] = remote_user

            await session.flush()

            # ── Create test systems ───────────────────────────────────────────
            system_ids: list[str] = []
            system_keys = ["alpha_id", "bravo_id", "charlie_id"]
            for i, sys_data in enumerate(TEST_SYSTEMS):
                existing = (await session.execute(
                    select(System).where(System.name == sys_data["name"])
                )).scalar_one_or_none()

                if existing is None:
                    sys_id = _uuid()
                    abbr = sys_data["abbreviation"]
                    inv_num = f"{abbr}-{9800 + i:04d}"
                    system = System(
                        id=sys_id,
                        name=sys_data["name"],
                        abbreviation=abbr,
                        system_type=sys_data.get("system_type", "major_application"),
                        environment=sys_data.get("environment", "on_prem"),
                        description=sys_data.get("description", ""),
                        auth_status=sys_data["auth_status"],
                        auth_date=sys_data.get("auth_date"),
                        auth_expiry=sys_data.get("auth_expiry"),
                        overall_impact=sys_data.get("overall_impact", "Moderate"),
                        confidentiality_impact=sys_data.get("confidentiality_impact", "Moderate"),
                        integrity_impact=sys_data.get("integrity_impact", "Moderate"),
                        availability_impact=sys_data.get("availability_impact", "Moderate"),
                        inventory_number=inv_num,
                        created_by="bsv_test_principal",
                        created_at=_now(),
                    )
                    session.add(system)
                    system_ids.append(sys_id)
                    fixture_ids["systems"][system_keys[i]] = sys_id
                    log.info("Created system: %s (%s)", sys_data["name"], sys_id)
                else:
                    system_ids.append(existing.id)
                    fixture_ids["systems"][system_keys[i]] = existing.id
                    log.info("System %s already exists (%s)", sys_data["name"], existing.id)

            await session.flush()
            alpha_id = fixture_ids["systems"]["alpha_id"]

            # ── Create ProgramRoleAssignments ─────────────────────────────────
            # Principal gets all roles on all test systems (broadest coverage).
            # Each other fixture user gets their native program role on BSV-TEST-ALPHA
            # so system-scoped routes (controls, artifacts, RMF, etc.) are accessible.
            principal_user = TEST_USERS["principal"]["remote_user"]
            for sys_id in system_ids:
                for role in SYSTEM_ROLES:
                    existing = (await session.execute(
                        select(ProgramRoleAssignment).where(
                            ProgramRoleAssignment.remote_user == principal_user,
                            ProgramRoleAssignment.system_id == sys_id,
                            ProgramRoleAssignment.program_role == role,
                        )
                    )).scalar_one_or_none()

                    if existing is None:
                        assignment = ProgramRoleAssignment(
                            remote_user=principal_user,
                            system_id=sys_id,
                            program_role=role,
                            status="active",
                            requested_by="bsv_test_principal",
                            requested_at=_now(),
                            approved_by="bsv_test_principal",
                            approved_at=_now(),
                        )
                        session.add(assignment)

            # Assign each fixture user their native role on BSV-TEST-ALPHA
            TIER_NATIVE_ROLE = {
                "executive": "ao",
                "manager":   "issm",
                "analyst":   "isso",
            }
            for tier, native_role in TIER_NATIVE_ROLE.items():
                ru = TEST_USERS[tier]["remote_user"]
                for sys_id in system_ids:
                    existing = (await session.execute(
                        select(ProgramRoleAssignment).where(
                            ProgramRoleAssignment.remote_user == ru,
                            ProgramRoleAssignment.system_id == sys_id,
                            ProgramRoleAssignment.program_role == native_role,
                        )
                    )).scalar_one_or_none()
                    if existing is None:
                        session.add(ProgramRoleAssignment(
                            remote_user=ru,
                            system_id=sys_id,
                            program_role=native_role,
                            status="active",
                            requested_by=principal_user,
                            requested_at=_now(),
                            approved_by=principal_user,
                            approved_at=_now(),
                        ))

            # ── Create SystemAssignments (required by _can_access_system) ────
            # _can_access_system checks system_assignments, not program_role_assignments.
            # Principal (admin) gets SystemAssignment on all test systems.
            # Non-admin fixture users get SystemAssignment on ALPHA only — this is
            # intentional so IDOR tests on SYSTEM_B (bravo) correctly return 403.
            principal_sa_user = TEST_USERS["principal"]["remote_user"]
            for sys_id in system_ids:
                existing_sa = (await session.execute(
                    select(SystemAssignment).where(
                        SystemAssignment.remote_user == principal_sa_user,
                        SystemAssignment.system_id == sys_id,
                    )
                )).scalar_one_or_none()
                if existing_sa is None:
                    session.add(SystemAssignment(
                        system_id=sys_id,
                        remote_user=principal_sa_user,
                        assigned_by="bsv_test_principal",
                        assigned_at=_now(),
                        note="RBAC test runner assignment",
                    ))
                    log.debug("Created SystemAssignment: %s → %s", principal_sa_user, sys_id)

            # Non-admin tiers: only assign to alpha (SYSTEM_ID). SYSTEM_B intentionally
            # has no assignment so IDOR flows can verify 403 is returned.
            non_admin_users = [
                v["remote_user"] for k, v in TEST_USERS.items() if k != "principal"
            ]
            for ru in non_admin_users:
                existing_sa = (await session.execute(
                    select(SystemAssignment).where(
                        SystemAssignment.remote_user == ru,
                        SystemAssignment.system_id == alpha_id,
                    )
                )).scalar_one_or_none()
                if existing_sa is None:
                    session.add(SystemAssignment(
                        system_id=alpha_id,
                        remote_user=ru,
                        assigned_by="bsv_test_principal",
                        assigned_at=_now(),
                        note="RBAC test runner assignment",
                    ))
                    log.debug("Created SystemAssignment: %s → %s (alpha only)", ru, alpha_id)

            # ── Create DutyAssignments (time-boxed) ──────────────────────────
            expires_at = _now() + timedelta(days=90)
            for sys_id in system_ids:
                for duty in TIMEBOX_DUTIES:
                    existing = (await session.execute(
                        select(DutyAssignment).where(
                            DutyAssignment.remote_user == principal_user,
                            DutyAssignment.system_id == sys_id,
                            DutyAssignment.duty == duty,
                        )
                    )).scalar_one_or_none()

                    if existing is None:
                        da = DutyAssignment(
                            remote_user=principal_user,
                            system_id=sys_id,
                            duty=duty,
                            assigned_by="bsv_test_principal",
                            assigned_at=_now(),
                            active=True,
                            expires_at=expires_at,
                            note="RBAC test runner assignment",
                        )
                        session.add(da)

            await session.flush()

            # ── Create test Risk on ALPHA ─────────────────────────────────────
            existing_risk = (await session.execute(
                select(Risk).where(Risk.risk_name == "RBAC Test Risk — Runner Fixture")
            )).scalar_one_or_none()

            if existing_risk is None:
                risk = Risk(
                    id=_uuid(),
                    system_id=alpha_id,
                    risk_name="RBAC Test Risk — Runner Fixture",
                    risk_description="Test risk created by RBAC runner bootstrap",
                    likelihood=2,
                    impact=2,
                    risk_score=4,
                    risk_level="Low",
                    treatment="Mitigate",
                    treatment_plan="Test risk — no real treatment required",
                    status="open",
                    created_by="bsv_test_principal",
                    created_at=_now(),
                )
                session.add(risk)
                await session.flush()
                fixture_ids["risks"]["test_risk_id"] = risk.id
                log.info("Created test Risk: %s", risk.id)
            else:
                fixture_ids["risks"]["test_risk_id"] = existing_risk.id
                log.info("Test Risk already exists: %s", existing_risk.id)

            # ── Create test POAM item on ALPHA ────────────────────────────────
            existing_poam = (await session.execute(
                select(PoamItem).where(
                    PoamItem.weakness_name == "RBAC Test POAM — Runner Fixture"
                )
            )).scalar_one_or_none()

            if existing_poam is None:
                poam = PoamItem(
                    id=_uuid(),
                    system_id=alpha_id,
                    weakness_name="RBAC Test POAM — Runner Fixture",
                    weakness_description="Test POA&M item created by RBAC runner bootstrap",
                    severity="Low",
                    status="open",
                    control_id="ac-1",
                    detection_source="self_report",
                    responsible_party="RBAC Test Runner",
                    scheduled_completion="2026-12-31",
                    created_by="bsv_test_principal",
                    created_at=_now(),
                )
                session.add(poam)
                await session.flush()
                fixture_ids["poam"]["test_poam_id"] = poam.id
                log.info("Created test POAM: %s", poam.id)
            else:
                fixture_ids["poam"]["test_poam_id"] = existing_poam.id
                log.info("Test POAM already exists: %s", existing_poam.id)

            # ── Create closed POAM for terminal-state lock tests ──────────────
            existing_closed_poam = (await session.execute(
                select(PoamItem).where(
                    PoamItem.weakness_name == "RBAC Test POAM — Closed Fixture"
                )
            )).scalar_one_or_none()

            if existing_closed_poam is None:
                closed_poam = PoamItem(
                    id=_uuid(),
                    system_id=alpha_id,
                    weakness_name="RBAC Test POAM — Closed Fixture",
                    weakness_description="Pre-closed POA&M for terminal state lock RBAC tests",
                    severity="Low",
                    status="closed_verified",
                    control_id="ac-1",
                    detection_source="self_report",
                    responsible_party="RBAC Test Runner",
                    scheduled_completion="2026-12-31",
                    created_by="bsv_test_principal",
                    created_at=_now(),
                )
                session.add(closed_poam)
                await session.flush()
                fixture_ids["poam"]["closed_poam_id"] = closed_poam.id
                log.info("Created closed POAM: %s", closed_poam.id)
            else:
                fixture_ids["poam"]["closed_poam_id"] = existing_closed_poam.id
                log.info("Closed POAM already exists: %s", existing_closed_poam.id)

            # ── Create test BCDR event on ALPHA ───────────────────────────────
            try:
                existing_bcdr = (await session.execute(
                    select(BcdrEvent).where(
                        BcdrEvent.system_id == alpha_id,
                        BcdrEvent.title == "RBAC Test BCDR Event — Runner Fixture",
                    )
                )).scalar_one_or_none()

                if existing_bcdr is None:
                    bcdr_event = BcdrEvent(
                        system_id=alpha_id,
                        event_type="test",
                        title="RBAC Test BCDR Event — Runner Fixture",
                        triggered_by="bsv_test_principal",
                        triggered_at=_now(),
                        status="open",
                    )
                    session.add(bcdr_event)
                    await session.flush()
                    fixture_ids["bcdr"]["test_event_id"] = str(bcdr_event.id)
                    log.info("Created test BCDR event: %s", bcdr_event.id)
                else:
                    fixture_ids["bcdr"]["test_event_id"] = str(existing_bcdr.id)
                    log.info("Test BCDR event already exists: %s", existing_bcdr.id)
            except Exception as exc:
                log.warning("Could not create BCDR event (table may vary): %s", exc)
                fixture_ids["bcdr"]["test_event_id"] = "1"

            await session.commit()
            log.info("All fixtures committed")

        return fixture_ids

    fixture_ids = asyncio.run(_run())
    return fixture_ids


def write_fixtures_yaml(fixture_ids: dict) -> None:
    """Write fixture IDs to tests/rbac/config/fixtures.yaml."""
    data = {
        "bootstrapped": True,
        "bootstrapped_at": datetime.now(timezone.utc).isoformat(),
        "systems": fixture_ids.get("systems", {}),
        "users":   fixture_ids.get("users", {}),
        "risks":   fixture_ids.get("risks", {}),
        "poam":    fixture_ids.get("poam", {}),
        "bcdr":    fixture_ids.get("bcdr", {}),
    }
    FIXTURES_YAML.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    log.info("Fixture IDs written to %s", FIXTURES_YAML)


def load_fixtures() -> dict:
    """Load fixture IDs from fixtures.yaml. Returns empty dict if not bootstrapped."""
    if not FIXTURES_YAML.exists():
        return {}
    try:
        return yaml.safe_load(FIXTURES_YAML.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        log.error("Failed to load fixtures.yaml: %s", exc)
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap RBAC test fixtures for BLACKSITE"
    )
    parser.add_argument("--db-path", default="blacksite.db",
                        help="Path to SQLite database (default: blacksite.db)")
    parser.add_argument("--clean", action="store_true",
                        help="Remove existing test fixtures before creating new ones")
    args = parser.parse_args()

    log.info("Bootstrapping fixtures (db=%s, clean=%s)", args.db_path, args.clean)
    fixture_ids = bootstrap(db_path=args.db_path, clean=args.clean)
    write_fixtures_yaml(fixture_ids)

    print("\nFixture IDs:")
    for section, ids in fixture_ids.items():
        if isinstance(ids, dict):
            for k, v in ids.items():
                print(f"  {section}.{k}: {v}")

    print(f"\nFixtures written to: {FIXTURES_YAML}")


if __name__ == "__main__":
    main()
