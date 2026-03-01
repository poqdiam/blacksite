#!/usr/bin/env python3
"""
BLACKSITE — Phase 17: Advanced Asset Management Framework (AAMF) Notional Data Generator
=========================================================================================

Generates a fully-populated, NIST 800-53r5-compliant demonstration system for
the Advanced Asset Management Framework (AAMF).

Usage:
  python scripts/generate_aamf_data.py           # create / refresh AAMF data
  python scripts/generate_aamf_data.py --clean   # remove AAMF data

The script is idempotent: re-running it will update existing records in place.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone, date, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH      = os.path.join(PROJECT_ROOT, "blacksite.db")
CATALOG_PATH = os.path.join(PROJECT_ROOT, "controls", "nist_800_53r5.json")

# ---------------------------------------------------------------------------
# AAMF system constants
# ---------------------------------------------------------------------------
AAMF_NAME   = "Advanced Asset Management Framework"
AAMF_ABBR   = "AAMF"
AAMF_INV    = "AAMF-0001"
AAMF_OWNER  = "Dan Kessler"
AAMF_EMAIL  = "d.kessler@thekramerica.com"
AAMF_PURPOSE = (
    "The Advanced Asset Management Framework (AAMF) provides enterprise-wide tracking, "
    "lifecycle management, and compliance reporting for all IT and physical assets across "
    "the organization. It serves as the authoritative system of record for asset inventory, "
    "software licensing, configuration baselines, and hardware disposition, supporting "
    "both NIST 800-53 CM controls and OMB A-130 asset accountability requirements."
)
AAMF_BOUNDARY = (
    "The AAMF security boundary encompasses: the web application server (NGINX + FastAPI), "
    "PostgreSQL asset database, Redis cache tier, S3-compatible object store for asset "
    "documentation, REST API gateway, and all agency staff with asset steward roles. "
    "Excludes: underlying cloud IaaS infrastructure managed by the CSP, and end-user "
    "workstations used solely for browser-based access."
)
AAMF_DESC = (
    "AAMF integrates with Active Directory for identity federation, SIEM for audit log "
    "forwarding, the Help Desk ticketing system for asset request workflows, and the "
    "Financial Management System for depreciation and cost tracking. Deployed on FedRAMP-"
    "authorized IaaS (IL2). ATO scope: 847 NIST 800-53r5 controls across 20 families."
)

# ---------------------------------------------------------------------------
# Per-family narrative templates
# ---------------------------------------------------------------------------
FAMILY_NARRATIVES = {
    "AC": (
        "The AAMF enforces access control through role-based access controls (RBAC) aligned "
        "to asset ownership hierarchies. Asset Stewards may only view and modify assets within "
        "their assigned organizational units. Privileged access (bulk import, system config) "
        "is restricted to Asset Administrators and System Owners. All access decisions are "
        "mediated by the application's authorization middleware, which validates JWT claims "
        "against the RBAC policy engine on every request. Inactive sessions are terminated "
        "after 30 minutes per AC-12. Remote access requires MFA through the agency IdP."
    ),
    "AT": (
        "AAMF-specific security awareness training is delivered to all asset steward roles "
        "annually. Training modules cover proper asset handling, data sensitivity classification, "
        "and incident reporting procedures specific to asset management operations. Training "
        "completion is tracked within the AAMF itself as a training record asset type. "
        "Role-based training for Asset Administrators covers privileged account hygiene, "
        "bulk import validation, and audit log review responsibilities. Training records are "
        "retained for 3 years per agency policy."
    ),
    "AU": (
        "The AAMF logs all asset lifecycle events (create, update, transfer, disposal) to an "
        "immutable audit trail backed by PostgreSQL with write-once semantics. Audit records "
        "capture: timestamp (UTC), actor identity, action type, affected asset ID and prior "
        "state (JSON diff), source IP, and session identifier. Logs are forwarded in real-time "
        "to the agency SIEM via syslog-TLS. Audit logs are retained for 3 years on-system "
        "and 7 years in cold archive per AU-11. The audit subsystem is protected from "
        "modification by a separate privileged audit role unavailable to standard administrators."
    ),
    "CA": (
        "The AAMF system security plan is maintained current and reviewed annually. Security "
        "assessments are conducted annually by an independent SCA team using NIST SP 800-53A "
        "procedures. Penetration testing is performed biennially. Assessment findings are "
        "tracked in BLACKSITE as POA&M items with assigned remediation owners and milestone "
        "dates. The AAMF Authorizing Official conducts annual authorization reviews. "
        "Interconnection Security Agreements cover all external data feeds (AD, SIEM, FMS)."
    ),
    "CM": (
        "The AAMF maintains a current baseline inventory of all managed assets as its core "
        "function — the system itself is the authoritative CM database. Software component "
        "inventory (SBOM) is maintained and reviewed quarterly. Configuration settings are "
        "documented in baseline configuration documents versioned in git. Changes to AAMF "
        "configuration require a Change Advisory Board review and are tracked as change records "
        "within the system. Unapproved software installation is prevented by application-layer "
        "controls. Configuration drift detection runs daily via automated scanning."
    ),
    "CP": (
        "The AAMF has a documented Contingency Plan tested annually via tabletop exercise. "
        "RTO is 4 hours; RPO is 1 hour. Database backups run every 15 minutes to a geographically "
        "separated replica. Full system snapshots are taken daily and retained for 30 days. "
        "Backup restoration is tested quarterly. The contingency plan covers: system failure, "
        "data corruption, ransomware, and cloud provider outage scenarios. Alternate processing "
        "capabilities are pre-provisioned in a secondary availability zone."
    ),
    "IA": (
        "All AAMF users authenticate via the agency SSO system (SAML 2.0 federation). "
        "Multi-factor authentication is enforced for all accounts with no exceptions. "
        "Service accounts use certificate-based authentication; passwords are not used for "
        "API access. User identities are provisioned and deprovisioned automatically via SCIM "
        "from the HR system within 24 hours of hire/separation. Account review occurs quarterly "
        "per IA-4. Device certificates are required for API access from automated systems."
    ),
    "IR": (
        "The AAMF Incident Response Plan is integrated with the agency-wide IR program. "
        "Asset-related incidents (unauthorized disposal, data exfiltration, bulk access anomalies) "
        "are detected by SIEM correlation rules and trigger automated alerts to the SOC. "
        "IR procedures specific to AAMF (preserving audit evidence, isolating the asset DB) "
        "are documented in Annex B of the agency IR plan. The AAMF team participates in "
        "quarterly IR exercises. Incident records are retained for 3 years."
    ),
    "MA": (
        "AAMF maintenance activities are documented as change records within the system itself. "
        "Maintenance windows are scheduled during off-peak hours with advance notice to users. "
        "All maintenance personnel are background-checked and access-controlled. Remote "
        "maintenance sessions require MFA, are logged, and are reviewed by the system owner "
        "within 24 hours. Diagnostic media (USB, optical) is prohibited without explicit "
        "authorization documented as a maintenance record."
    ),
    "MP": (
        "AAMF media handling policies restrict physical media use to authorized asset disposal "
        "workflows. Digital media containing asset records is encrypted at rest using AES-256. "
        "Media sanitization records are tracked as disposal events in the AAMF with chain-of-"
        "custody documentation. Portable media is prohibited from connecting to AAMF servers "
        "without documented authorization. Media transport outside the facility requires "
        "encryption and tamper-evident packaging."
    ),
    "PE": (
        "AAMF servers are hosted in a FedRAMP-authorized data center with physical access "
        "controls including badge readers, biometric verification, and video surveillance. "
        "Physical access to server racks requires dual-person integrity. Environmental controls "
        "include UPS, HVAC monitoring, and fire suppression with automated alerts. Physical "
        "access logs are reviewed monthly. All physical access events for the AAMF server "
        "rack are correlated with logical access logs quarterly."
    ),
    "PL": (
        "The AAMF System Security Plan (SSP) is maintained in BLACKSITE, reviewed annually, "
        "and updated within 30 days of significant system changes. The Privacy Impact Assessment "
        "covers PII fields in asset records (employee-to-asset assignments). The Rules of "
        "Behavior are acknowledged by all users at account activation and annually thereafter. "
        "The AAMF privacy plan addresses asset data containing workforce PII and is reviewed "
        "by the agency Privacy Officer annually."
    ),
    "PM": (
        "AAMF is designated as a mission-essential system in the agency's Information Security "
        "Program Plan. The system is included in the agency-wide risk assessment conducted "
        "annually. Threat intelligence relevant to asset management systems (supply chain "
        "attacks, insider threats) is monitored via CISA advisories and applied to the AAMF "
        "risk register within 14 days of new intelligence. Program management controls are "
        "executed at the enterprise level and inherited by AAMF."
    ),
    "PS": (
        "All AAMF privileged users undergo position risk designation and appropriate background "
        "investigations (Tier 2 minimum). Personnel security requirements are documented in "
        "the AAMF SSP. Termination procedures include same-day account deactivation via SCIM "
        "from the HR system and revocation of all AAMF access tokens. Transfer procedures "
        "include role review within 5 business days of transfer notification. User activity "
        "is monitored for anomalous access patterns using UEBA rules in the SIEM."
    ),
    "PT": (
        "The AAMF processes workforce PII in the form of employee-to-asset assignment records. "
        "A Privacy Impact Assessment was completed and approved by the agency Privacy Officer. "
        "Data minimization principles are applied — only the minimum PII necessary for asset "
        "accountability (employee ID, name, department) is collected. PII is encrypted in the "
        "database and masked in non-production environments. Subject access requests are "
        "fulfilled within 20 business days per agency privacy policy."
    ),
    "RA": (
        "A comprehensive risk assessment was completed for AAMF prior to initial authorization "
        "and is updated annually or upon significant change. Risk assessments follow NIST SP "
        "800-30 methodology. Supply chain risk management procedures are applied to all AAMF "
        "software components and hardware. The AAMF risk register is maintained in BLACKSITE "
        "with quarterly reviews. Vulnerability scanning occurs weekly; critical findings are "
        "remediated within 15 days per RA-5."
    ),
    "SA": (
        "AAMF development follows a secure software development lifecycle (S-SDLC) aligned to "
        "NIST SP 800-218. All third-party components are evaluated for supply chain risk before "
        "inclusion. Software composition analysis (SCA) scans run in CI/CD pipelines. "
        "Developer security training is completed annually. System and services acquisition "
        "contracts include security requirements and the right to audit. External service "
        "providers are assessed annually against FedRAMP baselines."
    ),
    "SC": (
        "Network communications for the AAMF are encrypted using TLS 1.3 for all data in "
        "transit. The application enforces HSTS with a 1-year max-age. Database connections "
        "use mTLS with certificate pinning. The AAMF is isolated in a dedicated network segment "
        "with microsegmentation enforced by network policy. API endpoints implement rate "
        "limiting and request validation to prevent injection attacks. The AAMF boundary "
        "includes a WAF with OWASP Core Rule Set deployed in blocking mode."
    ),
    "SI": (
        "The AAMF runs weekly vulnerability scans using an authenticated scanner. Critical and "
        "High findings are remediated within 15 and 30 days respectively per SI-2. Anti-malware "
        "is deployed on all AAMF hosts with real-time scanning enabled. Security-relevant "
        "software updates are applied within 30 days of release. Input validation is enforced "
        "at all API ingestion points. Anomalous activity (bulk exports, unusual query patterns) "
        "triggers automated SIEM alerts. Memory-safe language practices are enforced in the "
        "application codebase via static analysis gates in CI/CD."
    ),
    "SR": (
        "Supply chain risk management is implemented for all AAMF hardware and software "
        "components. Approved vendor lists are maintained and reviewed annually. Software "
        "bills of materials (SBOMs) are maintained for all AAMF application components. "
        "Critical software components are verified against known-good checksums before "
        "deployment. Third-party code review is conducted for all significant library updates. "
        "The AAMF procurement process includes supply chain security requirements in all "
        "vendor contracts."
    ),
}

# Roles by family
FAMILY_ROLES = {
    "AC": "Identity & Access Manager",
    "AT": "Security Awareness Coordinator",
    "AU": "Security Operations Analyst",
    "CA": "Information System Security Officer",
    "CM": "Configuration Manager",
    "CP": "Continuity Planner",
    "IA": "Identity & Access Manager",
    "IR": "Incident Response Coordinator",
    "MA": "System Maintenance Lead",
    "MP": "Media Control Officer",
    "PE": "Facilities Manager",
    "PL": "Information System Security Officer",
    "PM": "Program Manager",
    "PS": "Human Resources Security Officer",
    "PT": "Privacy Officer",
    "RA": "Risk Analyst",
    "SA": "System Acquisition Officer",
    "SC": "Network Security Engineer",
    "SI": "System Integrity Analyst",
    "SR": "Supply Chain Risk Manager",
}

# Inherited families (common controls)
INHERITED_FAMILIES = {"PE", "PM", "AT", "PS"}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _id() -> str:
    return str(uuid.uuid4())

def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con

# ---------------------------------------------------------------------------
# Load NIST catalog
# ---------------------------------------------------------------------------

def _extract_text(parts) -> str:
    """Recursively extract prose text from OSCAL parts list."""
    if not parts:
        return ""
    texts = []
    for part in parts:
        if isinstance(part, dict):
            prose = part.get("prose", "")
            if prose:
                texts.append(prose)
            sub = part.get("parts", [])
            if sub:
                texts.append(_extract_text(sub))
    return "\n".join(t for t in texts if t)


def load_catalog():
    """Parse NIST 800-53r5 OSCAL catalog JSON into flat list of {id, family, title, text}."""
    if not os.path.exists(CATALOG_PATH):
        print(f"[ERROR] Catalog not found: {CATALOG_PATH}")
        sys.exit(1)
    with open(CATALOG_PATH) as f:
        data = json.load(f)

    controls = []
    groups = data.get("catalog", {}).get("groups", [])
    for group in groups:
        group_id    = group.get("id", "").upper()
        group_title = group.get("title", "")
        for ctrl in group.get("controls", []):
            ctrl_id = ctrl.get("id", "").lower()
            if not ctrl_id:
                continue
            family  = ctrl_id.split("-")[0].upper() if "-" in ctrl_id else group_id
            title   = ctrl.get("title", "")
            text    = _extract_text(ctrl.get("parts", []))
            controls.append({"id": ctrl_id, "family": family, "title": title, "text": text})
            # Include control enhancements
            for enh in ctrl.get("controls", []):
                enh_id = enh.get("id", "").lower()
                if not enh_id:
                    continue
                enh_family = enh_id.split("-")[0].upper() if "-" in enh_id else family
                enh_title  = enh.get("title", "")
                enh_text   = _extract_text(enh.get("parts", []))
                controls.append({"id": enh_id, "family": enh_family, "title": enh_title, "text": enh_text})
    return controls

# ---------------------------------------------------------------------------
# CLEAN
# ---------------------------------------------------------------------------

def clean(con: sqlite3.Connection):
    cur = con.cursor()
    # Disable FK constraints temporarily for clean
    cur.execute("PRAGMA foreign_keys=OFF")
    # Find ALL AAMF systems (including duplicates from failed runs)
    cur.execute("SELECT id FROM systems WHERE name = ? OR abbreviation = ?", (AAMF_NAME, AAMF_ABBR))
    rows = cur.fetchall()
    if not rows:
        print("[CLEAN] No AAMF system found — nothing to remove.")
        cur.execute("PRAGMA foreign_keys=ON")
        return
    for (sys_id,) in rows:
        print(f"[CLEAN] Removing AAMF data for system_id={sys_id}")
        for table in ("system_controls", "assessments", "poam_items", "risks",
                      "rmf_records", "system_assignments", "ato_documents",
                      "ato_document_versions", "ato_workflow_events",
                      "observations", "inventory_items", "system_connections",
                      "artifacts", "system_teams"):
            try:
                cur.execute(f"DELETE FROM {table} WHERE system_id = ?", (sys_id,))
                if cur.rowcount:
                    print(f"  Deleted {cur.rowcount} rows from {table}")
            except Exception as e:
                print(f"  Skip {table}: {e}")
        cur.execute("DELETE FROM systems WHERE id = ?", (sys_id,))
        print(f"  Deleted system record.")
    cur.execute("PRAGMA foreign_keys=ON")
    con.commit()

# ---------------------------------------------------------------------------
# GENERATE
# ---------------------------------------------------------------------------

def run(con: sqlite3.Connection):
    cur = con.cursor()
    t0  = time.time()

    # ── 1. Create or find system ────────────────────────────────────────────
    print("\n[1/8] Creating AAMF system record…")
    cur.execute("SELECT id FROM systems WHERE abbreviation = ? AND deleted_at IS NULL", (AAMF_ABBR,))
    row = cur.fetchone()
    if row:
        sys_id = row[0]
        print(f"  Found existing system: {sys_id}")
    else:
        sys_id = _id()
        print(f"  Creating new system: {sys_id}")

    cur.execute("""
        INSERT OR REPLACE INTO systems
          (id, name, abbreviation, inventory_number, system_type, environment,
           owner_name, owner_email, description, purpose, boundary,
           confidentiality_impact, integrity_impact, availability_impact, overall_impact,
           auth_status, auth_date, auth_expiry,
           has_pii, has_financial_data, connects_to_federal,
           categorization_status,
           created_by, created_at, updated_at)
        VALUES
          (?, ?, ?, ?, 'major_application', 'on_prem',
           ?, ?, ?, ?, ?,
           'high', 'high', 'high', 'high',
           'authorized', '2025-01-15', '2028-01-15',
           1, 1, 1,
           'approved',
           'dan', ?, ?)
    """, (
        sys_id, AAMF_NAME, AAMF_ABBR, AAMF_INV,
        AAMF_OWNER, AAMF_EMAIL, AAMF_DESC, AAMF_PURPOSE, AAMF_BOUNDARY,
        now_iso(), now_iso()
    ))
    print(f"  System '{AAMF_NAME}' ({AAMF_ABBR}) → {sys_id}")
    print(f"  Elapsed: {time.time()-t0:.1f}s")

    # ── 2. Build SystemControl records for all ~900 controls ────────────────
    print("\n[2/8] Generating system control implementation records…")
    t1 = time.time()
    catalog = load_catalog()
    print(f"  Catalog loaded: {len(catalog)} controls")

    # Delete existing AAMF control records to start fresh
    cur.execute("DELETE FROM system_controls WHERE system_id = ?", (sys_id,))

    batch = []
    for ctrl in catalog:
        ctrl_id  = (ctrl.get("id") or ctrl.get("control_id") or "").lower().strip()
        family   = (ctrl.get("family") or ctrl_id.split("-")[0] if ctrl_id else "").upper()
        title    = ctrl.get("title") or ctrl.get("name") or ""
        if not ctrl_id:
            continue

        is_inherited = family in INHERITED_FAMILIES
        status       = "inherited" if is_inherited else "implemented"
        itype        = "inherited" if is_inherited else "system"
        narrative    = FAMILY_NARRATIVES.get(family, FAMILY_NARRATIVES.get("SI", ""))
        role         = FAMILY_ROLES.get(family, "Information System Security Officer")

        batch.append((
            sys_id, ctrl_id, family, title,
            status, itype, narrative, role,
            None,  # inherited_from
            "dan", now_iso(), now_iso()
        ))

    cur.executemany("""
        INSERT INTO system_controls
          (system_id, control_id, control_family, control_title,
           status, implementation_type, narrative, responsible_role,
           inherited_from, last_updated_by, last_updated_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    print(f"  Inserted {len(batch)} system_control records in {time.time()-t1:.1f}s")

    # ── 3. Create Assessment + ControlResults ───────────────────────────────
    print("\n[3/8] Creating security assessment with control results…")
    t2 = time.time()

    # Candidate
    cand_id = _id()
    cur.execute("""
        INSERT OR IGNORE INTO candidates (id, name, email, created_at)
        VALUES (?, 'AAMF Security Assessment Team', 'sca@thekramerica.com', ?)
    """, (cand_id, now_iso()))

    asmt_id = _id()
    cur.execute("""
        INSERT OR REPLACE INTO assessments
          (id, candidate_id, system_id, filename, file_path, uploaded_at, submitted_by,
           status, total_controls_found, controls_complete, controls_partial,
           controls_insufficient, controls_not_found,
           ssp_score, quiz_score, combined_score, is_allstar)
        VALUES
          (?, ?, ?, 'System_Security_Plan_AAMF.pdf', 'uploads/System_Security_Plan_AAMF.pdf',
           '2025-01-10 09:00:00', 'dan',
           'complete', ?, ?, 0, 0, 0,
           93.5, 0.0, 93.5, 1)
    """, (asmt_id, cand_id, sys_id, len(batch), len(batch)))

    # Create control results — score 90+ for all controls
    cr_batch = []
    for ctrl in catalog:
        ctrl_id = (ctrl.get("id") or ctrl.get("control_id") or "").lower().strip()
        family  = (ctrl.get("family") or ctrl_id.split("-")[0] if ctrl_id else "").upper()
        title   = ctrl.get("title") or ctrl.get("name") or ""
        if not ctrl_id:
            continue
        cr_batch.append((
            asmt_id, ctrl_id, family, title,
            True,    # found_in_ssp
            False,   # is_na
            "implemented",
            FAMILY_ROLES.get(family, "ISSO"),
            FAMILY_NARRATIVES.get(family, "")[:500],
            5, "COMPLETE",
        ))

    cur.executemany("""
        INSERT INTO control_results
          (assessment_id, control_id, control_family, control_title,
           found_in_ssp, is_na, implementation_status, responsible_role,
           narrative_excerpt, ai_score, ai_grade)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cr_batch)
    print(f"  Created assessment {asmt_id[:8]}… + {len(cr_batch)} control results in {time.time()-t2:.1f}s")

    # ── 4. Create RMF Records (all 7 steps complete) ────────────────────────
    print("\n[4/8] Creating RMF lifecycle records…")
    cur.execute("DELETE FROM rmf_records WHERE system_id = ?", (sys_id,))
    rmf_steps = [
        ("prepare",    "2024-06-01", "2024-07-15", "dan"),
        ("categorize", "2024-07-16", "2024-08-01", "dan"),
        ("select",     "2024-08-02", "2024-09-15", "dan"),
        ("implement",  "2024-09-16", "2024-11-30", "alice.chen"),
        ("assess",     "2024-12-01", "2024-12-31", "marcus.okafor"),
        ("authorize",  "2025-01-10", "2025-01-15", "dan"),
        ("monitor",    "2025-01-16", None,          "dan"),
    ]
    for step, target, actual, owner in rmf_steps:
        cur.execute("""
            INSERT INTO rmf_records
              (id, system_id, step, status, owner, target_date, actual_date, created_at, created_by)
            VALUES (?, ?, ?, 'complete', ?, ?, ?, ?, 'dan')
        """, (_id(), sys_id, step, owner, target, actual, now_iso()))
    print(f"  Created 7 RMF records (all complete)")

    # ── 5. Create POA&M items (3 closed) ────────────────────────────────────
    print("\n[5/8] Creating closed POA&M items…")
    cur.execute("DELETE FROM poam_items WHERE system_id = ?", (sys_id,))
    poams = [
        ("Insufficient rate-limiting on bulk asset export API", "High",
         "API endpoint /api/assets/export lacked request rate limiting, "
         "allowing high-volume scraping of asset inventory.",
         "2024-11-15", "Implemented API rate limiting (100 req/min) and added "
         "SIEM alert for bulk export events exceeding threshold."),
        ("Missing MFA enforcement for service accounts", "Moderate",
         "Three service account tokens did not require certificate-based "
         "authentication, relying solely on long-lived API keys.",
         "2024-12-01", "Migrated all service accounts to mTLS certificate "
         "authentication; legacy API keys revoked."),
        ("Audit log retention below 3-year requirement", "Low",
         "Log rotation policy deleted audit records after 365 days, "
         "failing to meet the 3-year retention requirement.",
         "2024-10-01", "Updated log retention to 1095 days; historical gap "
         "documented and risk-accepted by ISSO."),
    ]
    for name, sev, desc, due, closure in poams:
        cur.execute("""
            INSERT INTO poam_items
              (id, system_id, weakness_name, weakness_description, severity,
               scheduled_completion, status, closure_evidence,
               detection_source, responsible_party, root_cause,
               created_at, created_by)
            VALUES (?, ?, ?, ?, ?,
                    ?, 'closed_verified', ?,
                    'assessment', 'dan', 'Configuration gap identified during SCA review.',
                    ?, 'dan')
        """, (_id(), sys_id, name, desc, sev, due, closure, now_iso()))
    print(f"  Created 3 closed POA&M items")

    # ── 6. Create Risk entry (1 accepted Low) ───────────────────────────────
    print("\n[6/8] Creating risk register entry…")
    cur.execute("DELETE FROM risks WHERE system_id = ?", (sys_id,))
    risk_name = "Supply Chain Software Component Vulnerability"
    risk_desc = (
        "A vulnerability in a third-party open-source library used by AAMF could be "
        "exploited to gain unauthorized access to asset records or disrupt service."
    )
    treatment_plan = (
        "SCA scanning in CI/CD pipeline detects vulnerable components within 24h of "
        "CVE publication. Automated PRs opened for patch application. Critical patches "
        "applied within 15 days per SI-2 policy."
    )
    cur.execute(
        """INSERT INTO risks
           (id, system_id, risk_name, risk_description, threat_source, threat_event,
            likelihood, impact, risk_score, risk_level, treatment, treatment_plan,
            residual_likelihood, residual_impact, residual_score, residual_level,
            owner, status, review_date, created_at, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_id(), sys_id, risk_name, risk_desc,
         "technical", "Exploitation of vulnerable library component",
         2, 2, 4, "Low", "Mitigate", treatment_plan,
         1, 1, 1, "Low",
         "dan", "accepted", "2026-01-15", now_iso(), "dan")
    )
    print(f"  Created 1 accepted-risk (Low) record")

    # ── 7. Create SystemAssignment for dan ──────────────────────────────────
    print("\n[7/8] Creating system assignment for dan…")
    cur.execute("DELETE FROM system_assignments WHERE system_id = ?", (sys_id,))
    cur.execute("""
        INSERT INTO system_assignments (system_id, remote_user, assigned_by, assigned_at, note)
        VALUES (?, 'dan', 'dan', ?, 'AAMF primary ISSO')
    """, (sys_id, now_iso()))
    print(f"  Assigned 'dan' as ISSO for AAMF")

    # ── 8. Create ATO document placeholders ─────────────────────────────────
    print("\n[8/8] Creating ATO document records…")
    try:
        cur.execute("DELETE FROM ato_documents WHERE system_id = ?", (sys_id,))
        ato_docs = [
            ("SSP",     "System Security Plan — AAMF",           "2.1", "finalized"),
            ("SAR",     "Security Assessment Report — AAMF",      "1.0", "finalized"),
            ("POAM",    "Plan of Action & Milestones — AAMF",    "3.2", "finalized"),
            ("ATO",     "ATO Decision Letter — AAMF",            "1.0", "approved"),
            ("CP",      "Contingency Plan — AAMF",               "1.4", "finalized"),
            ("FIPS199", "FIPS 199 Categorization — AAMF",        "1.1", "approved"),
            ("PIA",     "Privacy Impact Assessment — AAMF",      "1.0", "approved"),
        ]
        for doc_type, title, ver, status in ato_docs:
            cur.execute("""
                INSERT INTO ato_documents
                  (id, system_id, doc_type, title, version, status, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'dan', ?)
            """, (_id(), sys_id, doc_type, title, ver, status, now_iso()))
        print(f"  Created {len(ato_docs)} ATO document records")
    except Exception as e:
        print(f"  ATO documents: {e} (skipping)")

    # ── Commit + summary ─────────────────────────────────────────────────────
    con.commit()
    total = time.time() - t0
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  AAMF Data Generation — Complete                            ║
╠══════════════════════════════════════════════════════════════╣
║  System ID:      {sys_id[:36]}  ║
║  Controls:       {len(batch):<5} (all implemented)                     ║
║  Assessment:     {len(cr_batch):<5} control results (score: 93.5)       ║
║  RMF Steps:      7/7 complete                               ║
║  POA&M Items:    3 (all closed_verified)                    ║
║  Risks:          1 (accepted, Low)                          ║
║  ATO Status:     Authorized (2025-01-15 → 2028-01-15)       ║
║  Total time:     {total:.1f}s                                         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    return sys_id

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate AAMF notional data for BLACKSITE")
    parser.add_argument("--clean", action="store_true", help="Remove AAMF data")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    con = _conn()
    try:
        if args.clean:
            clean(con)
        else:
            sys_id = run(con)
            print(f"\n  → View at: http://localhost:8100/systems/{sys_id}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
