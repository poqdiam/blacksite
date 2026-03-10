#!/usr/bin/env python3
"""
Steps 3 & 4: Update POA&M items and system_controls to reflect policy documentation.
"""
import asyncio, sys, os
sys.path.insert(0, '/home/graycat/projects/blacksite')
if 'BLACKSITE_DB_KEY' not in os.environ:
    raise RuntimeError("BLACKSITE_DB_KEY not set. Export it before running this script.")
import yaml
with open('/home/graycat/projects/blacksite/config.yaml') as f:
    config = yaml.safe_load(f)
from app.models import make_engine, make_session_factory
from sqlalchemy import text

SYSTEM_ID = 'bsv-main-00000000-0000-0000-0000-000000000001'

# Controls to CLOSE with corresponding evidence
CLOSE_ITEMS = [
    # -1 policy controls — covered by ISMP
    ("ac-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("at-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("au-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("ca-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("cm-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("cp-1",   "Policy document created and approved — see ISMP v1.0 and CP v1.0 in ATO document library (2026-03-09)"),
    ("ia-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("ir-1",   "Policy document created and approved — see ISMP v1.0 and IRP v1.0 in ATO document library (2026-03-09)"),
    ("ma-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("mp-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("pe-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("pl-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("PL-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("ps-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("ra-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("sa-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("sc-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("si-1",   "Policy document created and approved — see ISMP v1.0 in ATO document library (2026-03-09)"),
    ("sr-1",   "Policy document created and approved — see ISMP v1.0 SA section and SCRM v1.0 in ATO document library (2026-03-09)"),
    # pl-4 — ROB
    ("pl-4",   "Rules of Behavior (ROB) v1.0 created and approved in ATO document library (2026-03-09)"),
    # sc-12 — KMP
    ("sc-12",  "Key Management Plan (KMP) v1.0 created and approved in ATO document library (2026-03-09)"),
    # sr-2, sr-2.1, sr-3 — SCRM
    ("sr-2",   "Supply Chain Risk Management Plan (SCRM) v1.0 created and approved in ATO document library (2026-03-09)"),
    ("sr-2.1", "Supply Chain Risk Management Plan (SCRM) v1.0 created and approved — SCRM manager role defined (2026-03-09)"),
    ("sr-3",   "SCRM v1.0 defines supply chain controls including version pinning, pip audit, and vendor review procedures (2026-03-09)"),
    # ca-7, ca-7.4 — CONMON
    ("ca-7",   "Continuous Monitoring Plan (CONMON) v1.0 created and approved in ATO document library (2026-03-09)"),
    ("ca-7.4", "CONMON v1.0 risk monitoring section covers risk assessment review schedule and POA&M tracking (2026-03-09)"),
    # ca-3, sa-9 — EXT-SA
    ("ca-3",   "External Service Agreements (EXT-SA) v1.0 created and approved — three external services documented with risk assessments (2026-03-09)"),
    ("sa-9",   "EXT-SA v1.0 documents all external services (ip-api.com, NIST GitHub, Let's Encrypt) with SA-9 required elements (2026-03-09)"),
    # sa-3 — CMP SDLC section
    ("sa-3",   "CMP v1.0 Section 5 defines the BLACKSITE SDLC with git-based version control, testing phases, and security integration points (2026-03-09)"),
    # sa-5 — SSP
    ("sa-5",   "SSP v1.0 provides comprehensive system documentation including architecture, data flows, user roles, and security controls (2026-03-09)"),
    # sa-8 — SSP engineering principles
    ("sa-8",   "SSP v1.0 Section 7 documents 8 security engineering principles applied in BLACKSITE design (2026-03-09)"),
    # cm-2 — CMP
    ("cm-2",   "CMP v1.0 Section 2 establishes configuration baseline with all configuration items identified and tracked in git (2026-03-09)"),
    # ra-7 — VMP and POA&M
    ("ra-7",   "VMP v1.0 defines risk response procedures; POA&M system tracks and manages all identified risks with milestones (2026-03-09)"),
    # si-5 — VMP advisory tracking
    ("si-5",   "VMP v1.0 Section 6 defines security advisory monitoring via NIST publications table, pip audit, and Ubuntu USN subscriptions (2026-03-09)"),
    # cm-10 — ISMP SA section
    ("cm-10",  "ISMP v1.0 SA section documents software usage restrictions; CMP prohibits unauthorized software installation (2026-03-09)"),
    # cm-11 — CMP
    ("cm-11",  "CMP v1.0 Section 4.3 explicitly prohibits unauthorized software installation and requires ISSO approval for any new software (2026-03-09)"),
    # pl-2 — SSP
    ("pl-2",   "SSP v1.0 created and approved — comprehensive system security plan with all required elements (2026-03-09)"),
    # pl-11 — documented in SSP/system_controls
    ("pl-11",  "N/A determinations documented in system_controls narratives and SSP; tailoring rationale recorded per control (2026-03-09)"),
    # ps-6 — ROB
    ("ps-6",   "ROB v1.0 serves as the access agreement for BLACKSITE; users acknowledge rules as condition of access (2026-03-09)"),
    # ca-9 — EXT-SA
    ("ca-9",   "EXT-SA v1.0 documents all external system connections with data exchanged and risk assessments (2026-03-09)"),
]

# Controls to move to in_remediation
REMEDIATION_ITEMS = [
    # IRP created, training/drills still needed
    ("ir-8",   "IRP v1.0 created and approved (2026-03-09). Tabletop exercise required to validate procedures.", "2026-04-08"),
    ("ir-4",   "IRP v1.0 covers incident handling procedures including containment. Tabletop exercise to validate.", "2026-04-08"),
    ("ir-2",   "IRP v1.0 created with response procedures. Formal training curriculum still needed.", "2026-04-08"),
    ("ir-6",   "IRP v1.0 defines reporting requirements. Formal escalation testing still needed.", "2026-04-08"),
    ("ir-7",   "IRP v1.0 covers IR assistance procedures. External support contacts to be formalized.", "2026-04-08"),
    # CP created, tabletop still needed
    ("cp-2",   "CP v1.0 created and approved with RTO/RPO, backup strategy, and recovery procedures (2026-03-09). Tabletop exercise required.", "2026-04-08"),
    ("cp-3",   "CP v1.0 defines contingency training requirements. Tabletop exercise to serve as training event.", "2026-04-08"),
    ("cp-4",   "CP v1.0 defines annual testing schedule. First tabletop exercise required by 2026-04-08.", "2026-04-08"),
    # Python upgrade in progress
    ("si-2",   "Python 3.8 EOL identified as High risk. Upgrade to Python 3.11+ in progress. Testing underway.", "2026-04-08"),
    ("sa-22",  "Python 3.8 is end-of-life. Upgrade path defined: Python 3.11+. Dependency testing in progress.", "2026-04-08"),
    # ADD created, formal AO signature pending
    ("ca-6",   "ADD v1.0 created and ATO granted (2026-03-09). AO signature process formalization pending.", "2026-03-31"),
    # au-11 — policy written, enforcement mechanism pending
    ("au-11",  "Log retention policy written in ISMP AU section (1 year total, 90 days online). Automated enforcement mechanism pending.", "2026-05-09"),
    # at-2, at-2.2, at-3 — training content in app, formal curriculum pending
    ("at-2",   "BLACKSITE built-in training modules cover security awareness. Formal annual training curriculum not yet documented.", "2026-05-09"),
    ("at-2.2", "BLACKSITE training modules include security topics. Insider threat content not yet formally structured.", "2026-05-09"),
    ("at-3",   "Role-aware training content exists in BLACKSITE. Formal role-based curriculum document needed.", "2026-05-09"),
]

# Controls to update in system_controls to 'implemented'
IMPLEMENT_CONTROLS = [
    # All -1 controls
    ("ac-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers AC family policy requirements"),
    ("at-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers AT family policy requirements"),
    ("au-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers AU family policy requirements"),
    ("ca-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers CA family policy requirements"),
    ("cm-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers CM family policy requirements"),
    ("cp-1",   "Satisfied by ISMP v1.0 and CP v1.0 dated 2026-03-09 — both policy and plan documents approved"),
    ("ia-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers IA family policy requirements"),
    ("ir-1",   "Satisfied by ISMP v1.0 and IRP v1.0 dated 2026-03-09 — both policy and plan documents approved"),
    ("ma-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers MA family policy requirements"),
    ("mp-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers MP family policy requirements"),
    ("pe-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers PE family policy requirements"),
    ("pl-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers PL family policy requirements"),
    ("ps-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers PS family policy requirements"),
    ("ra-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers RA family policy requirements"),
    ("sa-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers SA family policy requirements"),
    ("sc-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers SC family policy requirements"),
    ("si-1",   "Satisfied by ISMP v1.0 dated 2026-03-09 — Information Security Management Policy covers SI family policy requirements"),
    ("sr-1",   "Satisfied by ISMP v1.0 SA section and SCRM v1.0 dated 2026-03-09 — supply chain risk management policy established"),
    # pl-4 — ROB
    ("pl-4",   "Satisfied by ROB v1.0 dated 2026-03-09 — Rules of Behavior document created, acknowledged by all users as condition of access"),
    # sc-12 — KMP
    ("sc-12",  "Satisfied by KMP v1.0 dated 2026-03-09 — Key Management Plan documents generation, storage, rotation, and destruction of all cryptographic keys"),
    # ca-7 — CONMON
    ("ca-7",   "Satisfied by CONMON v1.0 dated 2026-03-09 — Continuous Monitoring Plan defines monitoring activities at continuous, monthly, quarterly, and annual frequencies"),
    # ca-3 — EXT-SA
    ("ca-3",   "Satisfied by EXT-SA v1.0 dated 2026-03-09 — all three external service connections documented with data exchanged, risk assessment, and approval"),
    # pl-2 — SSP
    ("pl-2",   "Satisfied by SSP v1.0 dated 2026-03-09 — comprehensive System Security Plan created, reviewed, and approved"),
]

async def main():
    engine = make_engine(config)
    SessionFactory = make_session_factory(engine)

    closed_count = 0
    remediation_count = 0
    implemented_count = 0

    async with SessionFactory() as s:
        print("=== CLOSING POA&M ITEMS ===")
        for control_id, evidence in CLOSE_ITEMS:
            result = await s.execute(text("""
                UPDATE poam_items
                SET status='closed_verified',
                    closure_evidence=:evidence,
                    completion_date=date('now'),
                    updated_at=datetime('now')
                WHERE system_id=:sid
                  AND control_id=:cid
                  AND status NOT IN ('closed_verified','accepted_risk')
            """), {"sid": SYSTEM_ID, "cid": control_id, "evidence": evidence})
            n = result.rowcount
            if n > 0:
                print(f"  CLOSED {control_id}: {n} row(s)")
                closed_count += n
            else:
                # Check if already closed
                chk = await s.execute(text(
                    "SELECT status FROM poam_items WHERE system_id=:sid AND control_id=:cid"
                ), {"sid": SYSTEM_ID, "cid": control_id})
                row = chk.fetchone()
                if row:
                    print(f"  SKIP {control_id}: already {row[0]}")
                else:
                    print(f"  NOT FOUND {control_id}")

        await s.commit()

        print("\n=== MOVING POA&M ITEMS TO IN_REMEDIATION ===")
        for control_id, plan, target_date in REMEDIATION_ITEMS:
            result = await s.execute(text("""
                UPDATE poam_items
                SET status='in_remediation',
                    remediation_plan=:plan,
                    scheduled_completion=:target,
                    updated_at=datetime('now')
                WHERE system_id=:sid
                  AND control_id=:cid
                  AND status='open'
            """), {"sid": SYSTEM_ID, "cid": control_id, "plan": plan, "target": target_date})
            n = result.rowcount
            if n > 0:
                print(f"  IN_REMEDIATION {control_id}: {n} row(s), target {target_date}")
                remediation_count += n
            else:
                chk = await s.execute(text(
                    "SELECT status FROM poam_items WHERE system_id=:sid AND control_id=:cid"
                ), {"sid": SYSTEM_ID, "cid": control_id})
                row = chk.fetchone()
                if row:
                    print(f"  SKIP {control_id}: already {row[0]}")
                else:
                    print(f"  NOT FOUND {control_id}")

        await s.commit()

        print("\n=== UPDATING SYSTEM_CONTROLS TO IMPLEMENTED ===")
        for control_id, notes in IMPLEMENT_CONTROLS:
            result = await s.execute(text("""
                UPDATE system_controls
                SET status='implemented',
                    assessment_result='pass',
                    assessment_notes=:notes,
                    assessed_by='dborisov',
                    assessed_at=datetime('now'),
                    last_updated_by='dborisov',
                    last_updated_at=datetime('now')
                WHERE system_id=:sid
                  AND control_id=:cid
            """), {"sid": SYSTEM_ID, "cid": control_id, "notes": notes})
            n = result.rowcount
            if n > 0:
                print(f"  IMPLEMENTED {control_id}")
                implemented_count += n
            else:
                print(f"  NOT FOUND {control_id} in system_controls")

        await s.commit()

        # Final counts
        print("\n=== FINAL POA&M STATUS COUNTS ===")
        result = await s.execute(text("""
            SELECT status, COUNT(*) as cnt
            FROM poam_items
            WHERE system_id=:sid
            GROUP BY status ORDER BY cnt DESC
        """), {"sid": SYSTEM_ID})
        total = 0
        open_count = 0
        for row in result.fetchall():
            print(f"  {str(row[0]):25} | {row[1]}")
            total += row[1]
            if row[0] == 'open':
                open_count = row[1]
        print(f"  {'TOTAL':25} | {total}")

        print("\n=== SUMMARY ===")
        print(f"  POA&M items closed:            {closed_count}")
        print(f"  POA&M items moved to in_remedi: {remediation_count}")
        print(f"  system_controls → implemented:  {implemented_count}")
        print(f"  Remaining open POA&M items:     {open_count}")

asyncio.run(main())
