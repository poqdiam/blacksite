#!/usr/bin/env python3
"""
seed_borisov.py — Populate Borisov Infrastructure Server (BRV) in BLACKSITE/AEGIS
                  Full RMF treatment: system record → RMF steps → controls → POA&Ms → ATO docs

Run from project root:
    .venv/bin/python3 scripts/seed_borisov.py
"""

import sqlite3, uuid, datetime, sys, json

DB_PATH = "blacksite.db"
NOW     = datetime.datetime.utcnow().isoformat(timespec="seconds")
TODAY   = datetime.date.today().isoformat()   # 2026-03-02
CREATOR = "dan"

SYS_ID  = "brv-host-00000000-0000-0000-0000-000000000001"
SYS_ABB = "BRV"

# ─────────────────────────────────────────────────────────────────────────────
def u(): return str(uuid.uuid4())

def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ── guard: skip if already seeded ────────────────────────────────────────
    c.execute("SELECT id FROM systems WHERE id=?", (SYS_ID,))
    if c.fetchone():
        print(f"[skip] BRV system {SYS_ID} already exists. Delete it to re-seed.")
        return

    print("Seeding Borisov Infrastructure Server (BRV) …")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. SYSTEM RECORD
    # ─────────────────────────────────────────────────────────────────────────
    c.execute("""INSERT INTO systems (
        id, name, abbreviation, system_type, environment,
        owner_name, owner_email, description, purpose, boundary,
        confidentiality_impact, integrity_impact, availability_impact, overall_impact,
        auth_status, auth_date, auth_expiry,
        has_pii, has_phi, has_ephi, has_financial_data,
        is_public_facing, has_cui, connects_to_federal,
        categorization_status, categorization_approved_by, categorization_note,
        ato_decision, ato_notes,
        created_at, updated_at, created_by
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        SYS_ID,
        "Borisov Infrastructure Server",
        SYS_ABB,
        "general_support_system",
        "on_prem",
        "Dan Kessler",
        "dan@borisov.network",
        (
            "Borisov is a Dell PowerEdge R720 running Ubuntu 22.04 (FIPS 140-2 kernel) that serves as the "
            "primary self-hosted infrastructure platform for the borisov.network homelab environment. "
            "It hosts 31+ Docker containers providing media, home automation, GRC, security monitoring, "
            "DNS, authentication, and development services. All production services on the borisov.network "
            "domain are delivered from or proxied through this system."
        ),
        (
            "Provide a consolidated general-purpose support platform for self-hosted applications including "
            "the BLACKSITE GRC platform (AEGIS), Home Assistant, Plex Media Server, AdGuard Home, "
            "Authelia SSO, Wazuh SIEM, Portainer, and supporting arr/media management services. "
            "The system enables secure remote access, continuous security monitoring, and home automation "
            "for the borisov.network environment."
        ),
        (
            "Physical boundary: single Dell PowerEdge R720 server (192.168.86.102) located in home datacenter. "
            "Logical boundary: all Docker containers and host OS services on borisov. "
            "Network boundary: LAN segment 192.168.86.0/24 (main LAN), with reverse proxy exposure of "
            "*.borisov.network subdomains via Caddy on ports 80/443. IoT VLAN (192.168.2.0/24) "
            "communicates over controlled inter-VLAN paths via polaris (UDM Pro). "
            "External exposure: HTTPS only via Cloudflare DNS-01 TLS certificates; no inbound port forwards "
            "except via CGNAT/Cloudflare tunnel. Excludes: Oumuamua test server (192.168.86.103), "
            "Iapetus NAS (192.168.86.213), UniFi network gear, IoT devices."
        ),
        "Moderate", "Moderate", "Low", "Moderate",
        "in_progress", None, None,
        1,   # has_pii — user credentials, home automation data, health integrations
        0,   # has_phi
        0,   # has_ephi
        0,   # has_financial_data
        1,   # is_public_facing — *.borisov.network exposed via Authelia
        0,   # has_cui
        0,   # connects_to_federal
        "approved",
        "dan",
        (
            "FIPS 199 assessment complete. Confidentiality=Moderate (aggregated personal data, credentials, "
            "home automation telemetry). Integrity=Moderate (compromise of infrastructure services would "
            "affect all hosted applications). Availability=Low (homelab context; planned outages acceptable; "
            "no SLA obligations). High water mark: Moderate overall. Review cycle: annual."
        ),
        None,
        "System is in active use and undergoing continuous improvement. ATO package in preparation.",
        NOW, NOW, CREATOR
    ))
    print("  [1/7] systems ✓")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. SYSTEM ASSIGNMENT — assign dan
    # ─────────────────────────────────────────────────────────────────────────
    c.execute("SELECT id FROM system_assignments WHERE system_id=? AND remote_user=?", (SYS_ID, CREATOR))
    if not c.fetchone():
        c.execute("""INSERT INTO system_assignments (system_id, remote_user, assigned_by, assigned_at, note)
                     VALUES (?,?,?,?,?)""",
                  (SYS_ID, CREATOR, CREATOR, NOW,
                   "System owner and ISSO — sole operator of borisov.network homelab environment"))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. PROGRAM ROLE ASSIGNMENT — dan as isso
    # ─────────────────────────────────────────────────────────────────────────
    c.execute("SELECT id FROM program_role_assignments WHERE remote_user=? AND system_id=? AND program_role='isso'",
              (CREATOR, SYS_ID))
    if not c.fetchone():
        c.execute("""INSERT INTO program_role_assignments
                     (remote_user, system_id, program_role, status, requested_by, requested_at,
                      approved_by, approved_at, note)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (CREATOR, SYS_ID, "isso", "active", CREATOR, NOW, CREATOR, NOW,
                   "Self-designated ISSO for homelab system — sole security responsible party"))
    print("  [2/7] assignments ✓")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. RMF RECORDS (7 steps)
    # ─────────────────────────────────────────────────────────────────────────
    rmf_steps = [
        ("prepare", "complete", "2026-01-01",
         "2026-01-15",
         "System purpose, boundary, and roles defined. ISSO assigned. Organization-level risk "
         "management roles and risk tolerance documented. System registration completed. "
         "Software/hardware inventory catalogued (Docker containers, host OS, network services).",
         json.dumps(["System boundary document", "Hardware inventory", "Software inventory",
                     "ISSO designation letter"])),

        ("categorize", "complete", "2026-01-15",
         "2026-01-20",
         "FIPS 199 impact analysis completed. Data types identified: user credentials, "
         "home automation telemetry, PII (household data), application secrets. "
         "C=Moderate, I=Moderate, A=Low → Overall=Moderate. Categorization approved by system owner.",
         json.dumps(["FIPS 199 worksheet", "Data type inventory", "FIPS 200 baseline selection memo"])),

        ("select", "complete", "2026-01-20",
         "2026-01-25",
         "NIST SP 800-53r5 Moderate baseline selected. Tailoring applied: SR and PS families marked "
         "not-applicable (homelab, single-operator). PM family reduced (no formal program). "
         "Control parameters documented. Continuous monitoring strategy established.",
         json.dumps(["SSP control list", "Tailoring rationale memo",
                     "Continuous monitoring strategy"])),

        ("implement", "in_progress", "2026-03-31",
         None,
         "Controls being implemented per SSP. Core security controls active: Authelia SSO (AC), "
         "Wazuh SIEM (AU/SI), Docker secrets management (IA), Caddy TLS (SC), "
         "nightly backups to Iapetus NAS (CP). Open POA&M items tracking residual gaps.",
         json.dumps(["Docker Compose configs", "Wazuh dashboards", "Caddy access logs",
                     "Backup verification reports"])),

        ("assess", "in_progress", "2026-04-15",
         None,
         "Self-assessment in progress. ISSO conducting control testing using NIST SP 800-53A Rev 5 "
         "assessment procedures. 15 findings identified and logged as POA&M items. "
         "Critical: Oumuamua Bay 0 drive failure (CP-9). High: SSH CA exposure (IA-2), "
         "HA credential expiry (IA-5), iDRAC unauthenticated access (AC-17). "
         "Penetration testing deferred — homelab scope.",
         json.dumps(["Self-assessment worksheet", "POA&M register (15 items)",
                     "Wazuh security event logs", "Port scan results"])),

        ("authorize", "not_started", "2026-05-01",
         None,
         "ATO package in preparation. Pending: completion of high/critical POA&Ms, "
         "final SSP review, Risk Executive acceptance memo. "
         "Expected authorization: Q2 2026 (homelab context — self-authorization by system owner as AO).",
         json.dumps([])),

        ("monitor", "in_progress", "2026-12-31",
         None,
         "Continuous monitoring active. Wazuh SIEM collecting host and container events. "
         "Netdata providing real-time resource monitoring. AdGuard Home DNS logging active. "
         "Weekly security review cadence established. Backup verification daily. "
         "SIEM alert rules tuned for authentication failures, privilege escalation, unusual network traffic.",
         json.dumps(["Wazuh dashboard", "Netdata dashboards", "AdGuard query logs",
                     "Weekly review notes"])),
    ]

    for step, status, target, actual, evidence, artifacts in rmf_steps:
        c.execute("SELECT id FROM rmf_records WHERE system_id=? AND step=?", (SYS_ID, step))
        if not c.fetchone():
            c.execute("""INSERT INTO rmf_records
                         (id, system_id, step, status, owner, target_date, actual_date,
                          evidence, artifacts, created_at, updated_at, created_by)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (u(), SYS_ID, step, status, CREATOR, target, actual,
                       evidence, artifacts, NOW, NOW, CREATOR))
    print("  [3/7] rmf_records (7 steps) ✓")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. SYSTEM CONTROLS — NIST 800-53r5 Moderate baseline
    # ─────────────────────────────────────────────────────────────────────────
    # (control_id, family, title, status, impl_type, responsible_role, narrative)
    controls = [
        # ── AC — Access Control ───────────────────────────────────────────────
        ("ac-1", "AC", "Access Control Policy and Procedures", "implemented", "policy",
         "ISSO",
         "Access control policy documented in CLAUDE.md and operating procedures. Authelia SSO enforces "
         "role-based access for all web-facing services. Docker containers run with least-privilege "
         "non-root users where possible."),

        ("ac-2", "AC", "Account Management", "in_progress", "hybrid",
         "ISSO",
         "Local user accounts limited to graycat (interactive) and assistant (HA service account). "
         "Docker service accounts are container-isolated. FINDING: Teleport VPN peer accounts (Molty) "
         "not reviewed since original provisioning — see POA&M BRV-0008. SSH key inventory partially "
         "complete; iDRAC accounts not yet audited — see POA&M BRV-0016."),

        ("ac-3", "AC", "Access Enforcement", "implemented", "technical",
         "ISSO",
         "Authelia forward-auth enforces authentication before all *.borisov.network services. "
         "Caddy reverse proxy rejects requests from non-RFC1918 addresses via lan_only snippet. "
         "SSH daemon restricted to key-based authentication (PasswordAuthentication no)."),

        ("ac-6", "AC", "Least Privilege", "in_progress", "technical",
         "ISSO",
         "Principle of least privilege applied to Docker containers via UID mapping and read-only "
         "volume mounts where feasible. graycat user is in sudo group — escalation required for "
         "administrative operations. Root login disabled via SSH. FINDING: some containers still "
         "run as root (Wazuh, Home Assistant host-network) — tracked for future hardening."),

        ("ac-11", "AC", "Device Lock", "in_progress", "technical",
         "ISSO",
         "SSH sessions terminate on inactivity via ClientAliveInterval/ClientAliveCountMax in sshd_config. "
         "FINDING: iDRAC6 web UI session timeout not configured — see POA&M BRV-0017."),

        ("ac-12", "AC", "Session Termination", "implemented", "technical",
         "ISSO",
         "Authelia session tokens expire per configured TTL. SSH sessions terminate via kernel keepalive. "
         "Web service sessions use server-side tokens with expiry."),

        ("ac-17", "AC", "Remote Access", "in_progress", "hybrid",
         "ISSO",
         "Remote access via SSH (key-only, port 22) and Authelia-protected HTTPS services. "
         "Teleport VPN configured for privileged remote access. "
         "FINDING: Teleport VPN peers not audited (Molty instance) — see POA&M BRV-0008. "
         "FINDING: iDRAC remote management uses password auth — see POA&M BRV-0016."),

        ("ac-20", "AC", "Use of External Systems", "implemented", "operational",
         "ISSO",
         "External system connections limited to: Iapetus NAS (backup/sync via SMB/rsync over LAN), "
         "Cloudflare DNS API (certificate provisioning), upstream DNS providers (DoH via AdGuard). "
         "No direct cloud data storage of sensitive system data."),

        # ── AT — Awareness and Training ───────────────────────────────────────
        ("at-1", "AT", "Awareness and Training Policy", "not_applicable", "policy",
         "ISSO",
         "Single-operator homelab environment. Formal training policy not applicable. ISSO maintains "
         "self-directed security awareness via security community resources and threat intelligence feeds."),

        ("at-2", "AT", "Awareness Training", "not_applicable", "operational",
         "ISSO",
         "Not applicable — sole operator. Security awareness maintained through direct system operation."),

        # ── AU — Audit and Accountability ─────────────────────────────────────
        ("au-1", "AU", "Audit and Accountability Policy", "implemented", "policy",
         "ISSO",
         "Audit policy defined: all authentication events, privilege escalations, container lifecycle "
         "events, and network anomalies are logged. Retention policy: 30 days in Wazuh (ElasticSearch), "
         "7 days in journald. Logs shipped off-host to Wazuh indexer."),

        ("au-2", "AU", "Event Logging", "in_progress", "technical",
         "ISSO",
         "Wazuh agent collects syslog, auth.log, Docker daemon events, and custom integrations. "
         "Caddy access logs capture all HTTP requests. Authelia audit log active. "
         "FINDING: daily_health_report timer not yet installed — summary emails not sending — "
         "see POA&M BRV-0007."),

        ("au-3", "AU", "Content of Audit Records", "implemented", "technical",
         "ISSO",
         "Wazuh alerts include: timestamp, source IP, user, event type, affected resource, outcome. "
         "Caddy logs include: timestamp, client IP, request URI, response code, TLS version. "
         "Authelia logs include: username, auth result, MFA method."),

        ("au-6", "AU", "Audit Record Review, Analysis, and Reporting", "in_progress", "operational",
         "ISSO",
         "Wazuh dashboard used for ad-hoc review. FINDING: no automated daily summary report yet "
         "— see POA&M BRV-0007. Weekly manual review of Wazuh alerts and Caddy access logs performed."),

        ("au-9", "AU", "Audit Record Protection", "implemented", "technical",
         "ISSO",
         "Wazuh indexer runs in dedicated container with separate volume. Audit logs on host are "
         "root-owned with 640 permissions. Log shipping to Wazuh provides separation between log "
         "generation and storage."),

        ("au-11", "AU", "Audit Record Retention", "in_progress", "operational",
         "ISSO",
         "Wazuh configured for 30-day retention. Systemd journal retention needs maintenance vacuum. "
         "FINDING: journald disk usage elevated — see POA&M BRV-0018."),

        ("au-12", "AU", "Audit Record Generation", "implemented", "technical",
         "ISSO",
         "Wazuh agent configured on host and in applicable containers. Linux audit daemon (auditd) "
         "active via Wazuh integration. Container stdout/stderr logs captured by Docker daemon and "
         "forwarded to Wazuh."),

        # ── CA — Security Assessment ──────────────────────────────────────────
        ("ca-1", "CA", "Security Assessment Policies and Procedures", "implemented", "policy",
         "ISSO",
         "Self-assessment policy: annual full assessment plus continuous monitoring. "
         "Assessment methodology: NIST SP 800-53A Rev 5 assessment procedures (examine/interview/test). "
         "Current assessment cycle: 2026-01 through 2026-04."),

        ("ca-2", "CA", "Control Assessments", "in_progress", "operational",
         "ISSO",
         "Annual self-assessment in progress. ISSO conducting examination and testing of each "
         "Moderate baseline control. 15 findings identified to date. Assessment expected completion: "
         "2026-04-15."),

        ("ca-5", "CA", "Plan of Action and Milestones", "in_progress", "operational",
         "ISSO",
         "POA&M register maintained in BLACKSITE/AEGIS. 15 open items spanning Critical to Low "
         "severity. Weekly review and status update. Completion targets set per severity: "
         "Critical=30 days, High=60 days, Moderate=90 days, Low=180 days."),

        ("ca-6", "CA", "Authorization", "not_started", "operational",
         "ISSO",
         "ATO package in preparation. Self-authorization by system owner (serving as AO for "
         "homelab context). Expected authorization: Q2 2026. Prerequisites: closure of "
         "Critical/High POA&Ms, SSP finalization, Risk Executive memo."),

        ("ca-7", "CA", "Continuous Monitoring", "in_progress", "hybrid",
         "ISSO",
         "Continuous monitoring implemented via: Wazuh SIEM (real-time alerting), Netdata "
         "(resource/availability), AdGuard Home (DNS-layer threat detection), "
         "automated backup verification, Telegram alert notifications for critical events. "
         "Monitoring strategy documented. FINDING: monitoring coverage gaps for IoT VLAN "
         "traffic analysis."),

        # ── CM — Configuration Management ─────────────────────────────────────
        ("cm-1", "CM", "Configuration Management Policy and Procedures", "implemented", "policy",
         "ISSO",
         "Configuration management policy: all service configurations in Git (pre-commit hooks), "
         "Docker image versions pinned in compose files, SOPS for secrets management, "
         "change documentation in session notes."),

        ("cm-2", "CM", "Baseline Configuration", "implemented", "technical",
         "ISSO",
         "Baseline configuration documented in Docker Compose files and CLAUDE.md. "
         "Git repository tracks all compose file changes. Image versions pinned to specific "
         "tags (no :latest in production). Host OS: Ubuntu 22.04 FIPS, packages tracked via dpkg."),

        ("cm-3", "CM", "Configuration Change Control", "in_progress", "operational",
         "ISSO",
         "Changes tracked via Git commits with gitleaks pre-commit hooks for secrets scanning. "
         "Docker Compose changes tested on Oumuamua test environment before production deployment. "
         "FINDING: blacksite code changes not yet pushed to remote backup — see POA&M BRV-0020."),

        ("cm-6", "CM", "Configuration Settings", "in_progress", "technical",
         "ISSO",
         "Security configuration baselines applied: SSH hardened (key-only, strong ciphers), "
         "Caddy TLS 1.2+ enforced, Docker security options applied where supported. "
         "FINDING: IoT VLAN iptables rules are ephemeral (lost on reboot) — see POA&M BRV-0011. "
         "FINDING: sync-projects and greensite not yet running as systemd services — "
         "see POA&Ms BRV-0014, BRV-0015."),

        ("cm-7", "CM", "Least Functionality", "in_progress", "technical",
         "ISSO",
         "Unnecessary services disabled. Host OS does not run a desktop environment. "
         "FINDING: Apache2 residual config-files present on host — see POA&M BRV-0013. "
         "FINDING: build-essential installed on host — see POA&M BRV-0013. "
         "FINDING: Plex UPnP port mapping enabled — see POA&M BRV-0012."),

        ("cm-8", "CM", "System Component Inventory", "in_progress", "operational",
         "ISSO",
         "Container inventory maintained via Portainer CE and Docker Compose files. "
         "Host hardware inventory: Dell PowerEdge R720, Oumuamua Bay 0 drive critical. "
         "Software inventory: Ubuntu 22.04 + FIPS kernel, 31+ Docker containers. "
         "FINDING: Oumuamua Bay 0 drive SMART failure — see POA&M BRV-0005."),

        ("cm-11", "CM", "User-Installed Software", "in_progress", "technical",
         "ISSO",
         "Software installation restricted to package manager and Docker. FINDING: old unsigned "
         "kernel packages present — see POA&M BRV-0019. FINDING: openclaw:latest tag in Oumuamua "
         "compose (MoltyB) — see POA&M BRV-0022."),

        # ── CP — Contingency Planning ─────────────────────────────────────────
        ("cp-1", "CP", "Contingency Planning Policy and Procedures", "in_progress", "policy",
         "ISSO",
         "Backup policy implemented (daily automated backups to Iapetus NAS). "
         "Formal BCDR plan not yet documented. Contingency planning procedures to be "
         "formalized as part of ATO package."),

        ("cp-2", "CP", "Contingency Plan", "not_started", "operational",
         "ISSO",
         "Formal contingency plan not yet documented. Informal recovery procedures known to ISSO. "
         "Full BCDR documentation planned for Q2 2026 ATO package preparation."),

        ("cp-7", "CP", "Alternate Processing Site", "not_applicable", "operational",
         "ISSO",
         "Not applicable in homelab context. Single physical server. Acceptable for non-critical "
         "homelab use case. Cloud failover not in scope."),

        ("cp-9", "CP", "System Backup", "in_progress", "hybrid",
         "ISSO",
         "Daily automated backups to Iapetus NAS (192.168.86.213) via backup-all.sh timer. "
         "Backup contents: Docker volumes, configs, databases, media metadata. "
         "CRITICAL FINDING: Oumuamua Bay 0 drive (WD 1TB, serial WOL240039921) has SMART FAILURE — "
         "imminent disk failure affects backup integrity and media library — see POA&M BRV-0005. "
         "Backup verification: automated daily. Last verified success: 2026-03-01."),

        ("cp-10", "CP", "System Recovery and Reconstitution", "not_started", "operational",
         "ISSO",
         "Recovery procedures not formally documented. ISSO has knowledge of reconstitution steps. "
         "FINDING: Oumuamua Bay 0 failure represents active data loss risk — see POA&M BRV-0005. "
         "Formal recovery runbook planned for ATO package."),

        # ── IA — Identification and Authentication ────────────────────────────
        ("ia-1", "IA", "Identification and Authentication Policy and Procedures", "implemented", "policy",
         "ISSO",
         "Authentication policy: all web services require Authelia SSO with MFA. SSH requires "
         "Ed25519 key authentication. Service accounts use API keys stored in SOPS-managed secrets. "
         "Passwords must meet complexity requirements enforced by Authelia."),

        ("ia-2", "IA", "User Identification and Authentication", "in_progress", "technical",
         "ISSO",
         "Interactive user authentication via Authelia OIDC (one_factor + TOTP MFA). "
         "SSH authentication via Ed25519 keys (password disabled). "
         "CRITICAL FINDING: SSH CA TrustedUserCAKeys enabled in sshd_config — allows any "
         "CA-signed cert to authenticate — see POA&M BRV-0009. "
         "Service-to-service auth via API keys in SOPS-managed env vars."),

        ("ia-4", "IA", "Identifier Management", "implemented", "operational",
         "ISSO",
         "User identifiers: graycat (primary), assistant (HA service), dan (BLACKSITE admin). "
         "Service identifiers: Docker container names, domain names. "
         "No shared or default credentials in active use."),

        ("ia-5", "IA", "Authenticator Management", "in_progress", "technical",
         "ISSO",
         "SSH private keys: Ed25519, passphrase-protected, backed up. "
         "Service API keys rotated via credential-manager.py. "
         "SOPS age key at /home/graycat/.docker/secrets/age.key — secured, backup to Iapetus. "
         "FINDING: Home Assistant integration credentials expired (Portainer API, Nest, Google Mail, "
         "AccuWeather, Samsung TV) — see POA&M BRV-0006. "
         "FINDING: iDRAC password auth on management interface — see POA&M BRV-0016."),

        ("ia-8", "IA", "Non-Organizational User Identification and Authentication", "implemented",
         "technical", "ISSO",
         "External-facing services protected by Authelia forward-auth before any content is served. "
         "Cloudflare handles external TLS termination and DDoS protection. No anonymous access "
         "to sensitive services."),

        # ── IR — Incident Response ────────────────────────────────────────────
        ("ir-1", "IR", "Incident Response Policy and Procedures", "not_started", "policy",
         "ISSO",
         "Formal incident response policy not yet documented. Wazuh alerting via Telegram provides "
         "real-time notification. Incident response runbook to be created as part of ATO package."),

        ("ir-4", "IR", "Incident Handling", "in_progress", "operational",
         "ISSO",
         "Wazuh SIEM provides detection and alerting. Ring camera watchdog provides physical security "
         "monitoring. Telegram notifications for critical events. "
         "Formal incident handling procedures to be documented."),

        ("ir-5", "IR", "Incident Monitoring", "implemented", "technical",
         "ISSO",
         "Wazuh SIEM active with custom rules for authentication failures, privilege escalation, "
         "and unusual network activity. Netdata provides infrastructure anomaly detection. "
         "AdGuard Home provides DNS-layer threat detection."),

        # ── MA — Maintenance ──────────────────────────────────────────────────
        ("ma-1", "MA", "System Maintenance Policy and Procedures", "implemented", "policy",
         "ISSO",
         "Maintenance policy: OS patching via unattended-upgrades (security patches auto-apply). "
         "Docker image updates tested on Oumuamua before production promotion. "
         "Kernel updates: tested before reboot. Maintenance windows performed during low-usage periods."),

        ("ma-2", "MA", "Controlled Maintenance", "in_progress", "operational",
         "ISSO",
         "Maintenance activities logged in session notes. Docker container updates tracked in Git. "
         "FINDING: unsigned old kernel packages from prior FIPS update still installed — "
         "see POA&M BRV-0019."),

        ("ma-4", "MA", "Nonlocal Maintenance", "in_progress", "technical",
         "ISSO",
         "All system maintenance performed via SSH from LAN. iDRAC6 provides out-of-band access. "
         "FINDING: iDRAC management interface uses password authentication only — "
         "see POA&M BRV-0016."),

        # ── MP — Media Protection ─────────────────────────────────────────────
        ("mp-1", "MP", "Media Protection Policy", "implemented", "policy",
         "ISSO",
         "Physical storage: server located in home environment with physical access controls. "
         "Digital media: LUKS encryption not currently applied to data drives (homelab context, "
         "physical security acceptable). Backup media encrypted via rsync+SSH to Iapetus NAS."),

        ("mp-6", "MP", "Media Sanitization", "implemented", "operational",
         "ISSO",
         "Decommissioned drives: zeroed using shred or hdparm secure-erase before disposal. "
         "Docker volume removal: docker volume rm followed by filesystem cleanup. "
         "FINDING: Bay 0 drive (SMART FAILED) must be physically destroyed after replacement "
         "— see POA&M BRV-0005."),

        # ── PE — Physical and Environmental Protection ────────────────────────
        ("pe-1", "PE", "Physical and Environmental Protection Policy", "implemented", "policy",
         "ISSO",
         "Physical security policy: server in locked home office environment. Physical access "
         "limited to authorized household members. Environmental controls: UPS battery backup, "
         "temperature monitoring via iDRAC sensors, fan redundancy (Dell R720 dual-fan)."),

        ("pe-3", "PE", "Physical Access Control", "implemented", "operational",
         "ISSO",
         "Server room (home office) accessible only to household authorized parties. "
         "Server rack with physical lock. iDRAC provides remote access for hardware management."),

        ("pe-6", "PE", "Monitoring Physical Access", "implemented", "operational",
         "ISSO",
         "Ring cameras provide visual monitoring of entry points. Home Assistant automation "
         "alerts on unusual access patterns."),

        # ── PL — Planning ─────────────────────────────────────────────────────
        ("pl-1", "PL", "System Security Plan Policy", "implemented", "policy",
         "ISSO",
         "SSP policy: system security plan maintained in BLACKSITE/AEGIS. Updated after significant "
         "changes. Annual review cycle. Current SSP version in draft — being finalized for ATO."),

        ("pl-2", "PL", "System Security and Privacy Plan", "in_progress", "operational",
         "ISSO",
         "SSP in active development in BLACKSITE/AEGIS. All 20 control families addressed. "
         "System description, boundary, and categorization complete. Control narratives: ~60% complete. "
         "Expected completion: 2026-04-30."),

        ("pl-8", "PL", "Security and Privacy Architectures", "in_progress", "operational",
         "ISSO",
         "Security architecture documented in CLAUDE.md: defense-in-depth layering "
         "(Authelia→Caddy→container), network segmentation (main LAN/IoT VLAN), SOPS secrets mgmt. "
         "FINDING: blacksite-co service does not yet have a production brand name — "
         "see POA&M BRV-0021."),

        # ── PM — Program Management ───────────────────────────────────────────
        ("pm-1", "PM", "Information Security Program Plan", "in_progress", "policy",
         "ISSO",
         "Single-operator information security program. Program plan documented in CLAUDE.md and "
         "session notes. Risk management strategy defined. Continuous improvement cycle active."),

        ("pm-10", "PM", "Security Authorization Process", "in_progress", "operational",
         "ISSO",
         "ATO process in progress. Following NIST SP 800-37 Rev 2 RMF. Self-authorization model "
         "(system owner serves as AO in homelab context). Target ATO: Q2 2026."),

        # ── PS — Personnel Security ───────────────────────────────────────────
        ("ps-1", "PS", "Personnel Security Policy", "not_applicable", "policy",
         "ISSO",
         "Not applicable — single-operator homelab. No personnel screening or formal HR processes "
         "applicable. ISSO is sole authorized operator."),

        # ── RA — Risk Assessment ──────────────────────────────────────────────
        ("ra-1", "RA", "Risk Assessment Policy and Procedures", "implemented", "policy",
         "ISSO",
         "Risk assessment policy: annual formal risk assessment plus continuous risk identification "
         "via Wazuh SIEM and ISSO review. Risks documented in BLACKSITE/AEGIS risk register. "
         "Risk acceptance threshold: Low risks may be accepted; Moderate+ require remediation plan."),

        ("ra-3", "RA", "Risk Assessment", "in_progress", "operational",
         "ISSO",
         "Annual risk assessment in progress. 15 findings identified. Risk register being populated "
         "in BLACKSITE. Key risks: disk failure (Critical), SSH CA exposure (High), "
         "expired credentials (High), ephemeral firewall rules (Moderate). "
         "Risk assessment scheduled for completion: 2026-04-15."),

        ("ra-5", "RA", "Vulnerability Monitoring and Scanning", "in_progress", "technical",
         "ISSO",
         "Wazuh provides CVE monitoring via integration with OpenVAS/NVD feeds. "
         "Docker image vulnerability scanning via Trivy (ad-hoc). "
         "OS patches via unattended-upgrades. FINDING: Docker images on Oumuamua test stack "
         "were on :latest — now pinned (2026-03-02). Production images verified pinned."),

        # ── SA — System and Services Acquisition ─────────────────────────────
        ("sa-1", "SA", "System and Services Acquisition Policy", "implemented", "policy",
         "ISSO",
         "Acquisition policy: only open-source or self-hosted software. No third-party SaaS for "
         "sensitive data. Software vetted for known CVEs before deployment. "
         "Docker images from official registries (Docker Hub official, GitHub Container Registry)."),

        ("sa-9", "SA", "External System Services", "implemented", "operational",
         "ISSO",
         "External services used: Cloudflare (DNS/TLS), Ring (camera API), Nest (thermostat API), "
         "Google (OAuth/mail relay), AccuWeather (weather data). "
         "All external integrations reviewed for data sharing scope. SOPS-managed API keys."),

        ("sa-10", "SA", "Developer Configuration Management", "in_progress", "operational",
         "ISSO",
         "Source code in Git with gitleaks pre-commit hooks for secrets scanning. "
         "FINDING: BLACKSITE source code not yet backed up to remote Git repository — "
         "see POA&M BRV-0020."),

        # ── SC — System and Communications Protection ─────────────────────────
        ("sc-1", "SC", "System and Communications Protection Policy", "implemented", "policy",
         "ISSO",
         "Communications protection policy: TLS 1.2+ enforced on all external-facing services. "
         "Internal container communication via Docker networks (isolated bridge networks). "
         "DNS encryption via DoH to AdGuard. Inter-VLAN traffic controlled by UDM Pro policies."),

        ("sc-5", "SC", "Denial-of-Service Protection", "implemented", "technical",
         "ISSO",
         "Cloudflare DNS/proxy provides external DDoS mitigation. Caddy rate limiting on "
         "authentication endpoints. Authelia brute-force protection. UFW default-deny inbound."),

        ("sc-7", "SC", "Boundary Protection", "in_progress", "technical",
         "ISSO",
         "Network boundary enforced via: UDM Pro firewall policies, UFW on host, Caddy reverse proxy "
         "with lan_only snippet. IoT VLAN (br2) isolated with controlled egress rules. "
         "FINDING: IoT VLAN iptables rules (STUN 3478/3479, WeMo TCP 8990) are ephemeral — "
         "lost on UDM Pro reboot — see POA&M BRV-0011. "
         "FINDING: Plex UPnP auto-creates port mappings bypassing firewall intent — "
         "see POA&M BRV-0012."),

        ("sc-8", "SC", "Transmission Confidentiality and Integrity", "implemented", "technical",
         "ISSO",
         "All external traffic encrypted via TLS 1.2+. Caddy enforces HTTPS redirect. "
         "DNS queries encrypted via DoH (AdGuard → Cloudflare/Google). "
         "SSH communications encrypted. Internal container communications on isolated Docker networks."),

        ("sc-12", "SC", "Cryptographic Key Establishment and Management", "in_progress", "technical",
         "ISSO",
         "TLS certificates via Cloudflare DNS-01 challenge (auto-renewal in Caddy). "
         "SOPS age key for secrets encryption. SSH Ed25519 keys for authentication. "
         "FINDING: SOPS .secrets.env currently plain text (SOPS key resolution issue) — "
         "tracked as operational risk."),

        ("sc-13", "SC", "Cryptographic Protection", "implemented", "technical",
         "ISSO",
         "Cryptographic standards: Ed25519 (SSH), ECDSA-P256 (TLS), AES-256-GCM (SOPS age), "
         "argon2id (Authelia password hashing), bcrypt (Wazuh passwords). "
         "FIPS 140-2 validated kernel modules active via fips=1 boot parameter."),

        ("sc-28", "SC", "Protection of Information at Rest", "in_progress", "technical",
         "ISSO",
         "Docker volumes with sensitive data on host filesystem. LUKS encryption not applied "
         "to data drives (homelab context risk acceptance). SOPS encrypts secrets at rest. "
         "Backup data transmitted encrypted (rsync over SSH to Iapetus NAS). "
         "FINDING: SSH CA key infrastructure could allow credential persistence — "
         "see POA&M BRV-0009."),

        # ── SI — System and Information Integrity ─────────────────────────────
        ("si-1", "SI", "System and Information Integrity Policy", "implemented", "policy",
         "ISSO",
         "Integrity policy: OS and container security updates applied promptly. "
         "Wazuh file integrity monitoring (FIM) enabled for critical paths. "
         "gitleaks pre-commit hooks prevent secrets from entering source control."),

        ("si-2", "SI", "Flaw Remediation", "in_progress", "technical",
         "ISSO",
         "OS: unattended-upgrades applies security patches automatically. "
         "Docker images: updated on test stack, promoted to production after verification. "
         "FINDING: old unsigned FIPS kernel packages still installed — see POA&M BRV-0019. "
         "FINDING: sync-projects and greensite still running as nohup processes instead of "
         "systemd services — see POA&Ms BRV-0014, BRV-0015."),

        ("si-3", "SI", "Malware Protection", "implemented", "technical",
         "ISSO",
         "Wazuh HIDS provides malware detection via YARA rules and rootkit checks. "
         "ClamAV integration via Wazuh for file scanning. "
         "Docker image integrity verified via digest pinning (planned)."),

        ("si-4", "SI", "System Monitoring", "implemented", "technical",
         "ISSO",
         "Wazuh SIEM: real-time host and container monitoring, custom alert rules, "
         "Telegram notifications for critical events. Netdata: resource utilization, "
         "disk health monitoring (SMART via netdata plugin). AdGuard: DNS query monitoring "
         "with blocklists for known malicious domains."),

        ("si-5", "SI", "Security Alerts, Advisories, and Directives", "in_progress", "operational",
         "ISSO",
         "Security advisories monitored via: Wazuh NVD integration, Docker Hub security advisories, "
         "Ubuntu USN mailing list subscription. FINDING: formal advisory tracking process not "
         "yet documented."),

        ("si-12", "SI", "Information Management and Retention", "implemented", "operational",
         "ISSO",
         "Log retention: Wazuh 30 days, journald 7 days (pending vacuum), Caddy access logs 90 days. "
         "Backup retention: 30 days on Iapetus NAS. Media data: indefinite (user-managed)."),

        # ── SR — Supply Chain ─────────────────────────────────────────────────
        ("sr-1", "SR", "Supply Chain Risk Management Policy", "not_applicable", "policy",
         "ISSO",
         "Not applicable — homelab context with no formal supply chain processes. "
         "Risk mitigated by using established open-source projects with active security communities."),

        # ── PT — PII Processing ───────────────────────────────────────────────
        ("pt-1", "PT", "Privacy Policy for PII Processing", "in_progress", "policy",
         "ISSO",
         "PII processed: user credentials, home automation telemetry (occupancy, device usage), "
         "Ring camera footage (household members). Privacy policy for household data applies. "
         "Data minimization: only necessary data collected and retained."),
    ]

    for ctrl_id, family, title, status, impl_type, role, narrative in controls:
        c.execute("SELECT id FROM system_controls WHERE system_id=? AND control_id=?",
                  (SYS_ID, ctrl_id))
        if not c.fetchone():
            c.execute("""INSERT INTO system_controls
                         (system_id, control_id, control_family, control_title, status,
                          implementation_type, narrative, responsible_role,
                          last_updated_by, last_updated_at, created_at, created_by)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (SYS_ID, ctrl_id, family, title, status,
                       impl_type, narrative, role, CREATOR, NOW, NOW, CREATOR))
    print(f"  [4/7] system_controls ({len(controls)} controls) ✓")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. POA&M ITEMS — 15 findings from current security posture
    # ─────────────────────────────────────────────────────────────────────────
    # (poam_id, control_id, weakness_name, weakness_description, severity,
    #  detection_source, remediation_plan, scheduled_completion, status,
    #  responsible_party, resources_required, root_cause, comments)
    poams = [
        ("BRV-0005", "cp-9",
         "Critical Storage Failure — Oumuamua Bay 0 Drive SMART FAILED",
         ("Bay 0 of the Oumuamua NAS (192.168.86.103) contains a WD 1TB hard drive "
          "(serial WOL240039921) that has exceeded SMART failure threshold. The drive is reporting "
          "pre-failure condition indicating imminent data loss risk. This drive is part of the "
          "media library array and backup infrastructure chain that supports CP-9 System Backup "
          "and CP-10 Recovery objectives."),
         "critical", "hardware_health_monitoring",
         ("1. Procure replacement WD 1TB SATA drive (compatible model verified). "
          "2. Initiate Unraid parity-protect rebuild while drive still partially readable. "
          "3. Replace failed drive with new unit. "
          "4. Verify Unraid array health post-rebuild. "
          "5. Run backup-all.sh and verify successful backup to Iapetus NAS. "
          "6. Schedule SMART monitoring alerts in Netdata for early warning on remaining drives."),
         "2026-03-16",  # 14 days — critical
         "open", "Dan Kessler (System Owner)",
         "~$50 replacement drive; 4 hours rebuild time",
         "Hardware wear — drive exceeded rated TBWI. No indicator of malicious activity.",
         "IMMEDIATE ACTION REQUIRED. Risk of data loss increases daily until drive is replaced."),

        ("BRV-0006", "ia-5",
         "Expired Integration Credentials — Home Assistant API Keys",
         ("Multiple Home Assistant integrations have expired or invalid credentials: "
          "(1) Portainer — API key revoked during CE migration; "
          "(2) Nest — OAuth token expired; "
          "(3) Google Mail — OAuth token expired; "
          "(4) AccuWeather — API key not configured; "
          "(5) Samsung TV — session expired. "
          "Affected integrations are in error state in HA UI. Some automations dependent on "
          "these integrations are non-functional."),
         "high", "application_monitoring",
         ("1. Log in to Home Assistant UI at ha.borisov.network. "
          "2. Portainer: generate new API key in Portainer → Settings → API Keys; update HA config entry. "
          "3. Nest: re-authenticate via Google OAuth flow in HA integration settings. "
          "4. Google Mail: re-authenticate via Google OAuth flow. "
          "5. AccuWeather: obtain new API key from developer.accuweather.com; enter in HA. "
          "6. Samsung TV: trigger re-authentication flow in HA integration settings. "
          "7. Verify all integrations show 'Loaded' status."),
         "2026-03-09",  # 7 days — high
         "open", "Dan Kessler (System Owner)",
         "Google developer API access; AccuWeather free API key (~30 min total)",
         "API keys rotated during infrastructure migration without updating HA configuration.",
         "Requires manual HA UI interaction — cannot be scripted via API (LLAT token revoked)."),

        ("BRV-0007", "au-2",
         "Daily Health Report Timer Not Installed",
         ("The daily_health_report systemd timer has not been installed, causing automated daily "
          "system health summary emails to not be sent. The unit files exist at "
          "/home/graycat/scripts/ (daily_health_report.service and daily_health_report.timer) "
          "but have not been enabled in systemd. Without this timer, ISSO lacks daily "
          "automated visibility into system health status (AU-2, AU-6 continuous monitoring)."),
         "low", "isso_review",
         ("Run the maintenance script: sudo bash /home/graycat/scripts/maint-run.sh "
          "(ITEM 7 section will install and activate the timer). "
          "Verify: systemctl status daily_health_report.timer"),
         "2026-03-09",
         "open", "Dan Kessler (ISSO)",
         "5 minutes; requires sudo",
         "Administrative backlog — unit files prepared but install step deferred.",
         "Handled in maint-run.sh ITEM 7. Can be closed once maint-run.sh is executed."),

        ("BRV-0008", "ac-17",
         "Teleport VPN Peer Accounts Not Reviewed (Molty Instance)",
         ("Teleport VPN peer account for 'Molty' workstation has not been reviewed since initial "
          "provisioning. It is unknown whether this peer account is still needed, whether the "
          "associated device is still authorized, or whether the trust certificate is current. "
          "Unreviewed VPN peers represent unauthorized remote access risk."),
         "moderate", "isso_review",
         ("1. Log in to polaris (UDM Pro) UniFi UI → Teleport → Devices. "
          "2. Identify all peer entries. "
          "3. For each peer: verify device owner, confirm still needed, check last-seen date. "
          "4. Remove any peers not currently needed or not seen in > 30 days. "
          "5. Document approved peers in system inventory."),
         "2026-04-01",
         "open", "Dan Kessler (System Owner)",
         "30 minutes; UniFi UI access",
         "Initial provisioning without scheduled review cycle.",
         "Requires UniFi UI access — cannot be automated."),

        ("BRV-0009", "ia-2",
         "SEC-2: SSH CA TrustedUserCAKeys Enabled in sshd_config",
         ("The sshd_config directive TrustedUserCAKeys is active, configuring sshd to accept "
          "certificates signed by the specified CA. This allows any holder of the CA private key "
          "to authenticate as any local user without an individual authorized_keys entry. "
          "The CA key is not needed for current operations (all access via individual Ed25519 keys). "
          "This represents a privilege escalation vector if the CA key is compromised."),
         "high", "configuration_review",
         ("Comment out the TrustedUserCAKeys directive in /etc/ssh/sshd_config and reload sshd. "
          "Handled in maint-run.sh ITEM 9: sed -i 's/^TrustedUserCAKeys/#TrustedUserCAKeys/' "
          "/etc/ssh/sshd_config && systemctl reload ssh. "
          "Verify: grep TrustedUserCAKeys /etc/ssh/sshd_config"),
         "2026-03-09",
         "open", "Dan Kessler (ISSO)",
         "5 minutes; requires sudo",
         "SSH CA configured during initial setup but CA feature not actively used. "
         "Disable preserves all existing authorized_keys-based access.",
         "Handled in maint-run.sh ITEM 9. Disabling does not affect normal SSH access."),

        ("BRV-0010", "sc-7",
         "WeMo Subscription Failures — IoT Device Callback Errors",
         ("WeMo Kitchen (192.168.2.63) and WeMo Bedroom (192.168.2.64) smart plugs are generating "
          "subscription callback errors to Home Assistant. Errors indicate the devices' internal "
          "subscription tables are full, preventing HA from receiving state-change notifications. "
          "Control commands still function. Root cause: devices need power cycle to flush "
          "subscription table."),
         "low", "application_monitoring",
         ("1. Physically power cycle WeMo Kitchen plug (unplug for 30 seconds, replug). "
          "2. Physically power cycle WeMo Bedroom plug. "
          "3. Verify HA WeMo integration shows no errors: Settings → Integrations → WeMo. "
          "4. Test subscription: toggle plug in HA and verify state reflects in 2s."),
         "2026-03-09",
         "open", "Dan Kessler (System Owner)",
         "5 minutes; physical access to plugs",
         "WeMo device firmware limitation — subscription table fills over time without power cycle.",
         "Pre-existing device quirk. Power cycle resolves without firmware update."),

        ("BRV-0011", "sc-7",
         "IoT VLAN Firewall Rules Ephemeral — Lost on UDM Pro Reboot",
         ("Iptables rules permitting Ring STUN (UDP 3478/3479 IoT→WAN) and WeMo callbacks "
          "(TCP 8990 IoT→borisov) are set as ephemeral iptables commands only. These rules are "
          "not persisted in the UDM Pro configuration and will be lost on any reboot of polaris. "
          "After a reboot, Ring live-view streams and WeMo control callbacks would fail."),
         "moderate", "isso_review",
         ("Write rules to /mnt/data/on_boot.d/98-iot-vlan-extras.sh on polaris. "
          "Handled in maint-run.sh ITEM 11: SSH to polaris, write script, execute immediately. "
          "The on_boot.d script survives polaris reboots. "
          "Verify after maint-run: ssh polaris 'ls -la /mnt/data/on_boot.d/98-iot-vlan-extras.sh'"),
         "2026-03-09",
         "open", "Dan Kessler (ISSO)",
         "10 minutes; requires SSH to polaris",
         "Rules added manually for immediate need; persistence step deferred.",
         "Handled in maint-run.sh ITEM 11. Critical for Ring camera live view after any polaris reboot."),

        ("BRV-0012", "cm-7",
         "Plex UPnP Port Mapping Enabled — Bypasses Firewall Policy",
         ("Plex Media Server has UPnP auto-discovery enabled, which causes it to automatically "
          "request port forwarding rules from the UDM Pro gateway. This bypasses the intended "
          "firewall policy by automatically creating inbound port mappings without administrator "
          "review. UPnP port mappings can expose services that should not be externally accessible."),
         "moderate", "port_scan_review",
         ("1. In Plex Web UI: Settings → Remote Access → disable 'Enable Automatic Port Mapping'. "
          "2. In UniFi UI: check UPnP active mappings and remove any Plex entries. "
          "3. Configure static port forwarding if external Plex access is desired (explicit rule). "
          "4. Document decision in system configuration notes."),
         "2026-04-01",
         "open", "Dan Kessler (System Owner)",
         "15 minutes; Plex Web UI + UniFi UI access",
         "Default Plex setting. UPnP enabled by default in Plex and on UDM Pro.",
         "Requires manual Plex UI action. Alternative: disable UPnP globally on UDM Pro."),

        ("BRV-0013", "cm-7",
         "Apache2 Residual Config and Build-Essential on Host",
         ("apache2 package has status 'deinstall ok config-files' — residual configuration files "
          "remain on the system despite the package being removed. Additionally, build-essential "
          "(gcc, g++, cpp, make) is installed on the production server. Build tools on a production "
          "server increase attack surface and violate least functionality principle."),
         "low", "configuration_review",
         ("apt-get purge apache2 apache2-utils apache2-bin; "
          "apt-get remove build-essential gcc g++ cpp make; "
          "apt-get autoremove. "
          "Handled in maint-run.sh ITEM 13."),
         "2026-03-09",
         "open", "Dan Kessler (ISSO)",
         "10 minutes; requires sudo",
         "Apache2 removed but not purged. Build-essential installed for one-time use, never removed.",
         "Handled in maint-run.sh ITEM 13. Low risk — apache2 is deinstalled, config files only."),

        ("BRV-0014", "si-2",
         "sync-projects Running as nohup Process — No Systemd Service",
         ("The sync-projects.sh script (syncs projects/ to Iapetus NAS) is running as a nohup "
          "background loop process rather than a managed systemd service. A nohup process will not "
          "automatically restart after system reboot, does not provide crash recovery, and is not "
          "visible in standard service management tools."),
         "low", "isso_review",
         ("Install sync-projects.service systemd unit. "
          "Handled in maint-run.sh ITEM 14: kill nohup loop, install unit, enable and start. "
          "Verify: systemctl status sync-projects.service"),
         "2026-03-09",
         "open", "Dan Kessler (ISSO)",
         "5 minutes; requires sudo",
         "Initially run as nohup loop; systemd unit prepared but not installed.",
         "Handled in maint-run.sh ITEM 14."),

        ("BRV-0015", "si-2",
         "greensite Running as nohup Process — No Systemd Service",
         ("The greensite FastAPI application (port 8102) is running as a nohup uvicorn process "
          "rather than a managed systemd service. Same risks as BRV-0014: no auto-restart, "
          "no crash recovery, not visible in service management."),
         "low", "isso_review",
         ("Install greensite.service systemd unit. "
          "Handled in maint-run.sh ITEM 15: kill nohup instance on port 8102, install unit. "
          "Verify: systemctl status greensite.service"),
         "2026-03-09",
         "open", "Dan Kessler (ISSO)",
         "5 minutes; requires sudo",
         "Initially run as nohup; systemd unit prepared but not installed.",
         "Handled in maint-run.sh ITEM 15."),

        ("BRV-0016", "ia-5",
         "iDRAC6 Management Interface — Password Authentication Only",
         ("The iDRAC6 out-of-band management interfaces on both Borisov (192.168.86.100) and "
          "Oumuamua (192.168.86.101) use only password-based SSH authentication. SSH key-based "
          "authentication has not been configured. iDRAC management interface is accessible on "
          "the management LAN. Password: 4Pf4F?0B9Lp (same on both — reuse risk)."),
         "high", "configuration_review",
         ("1. Generate dedicated SSH key pair for iDRAC access: "
          "ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_idrac "
          "(iDRAC6 firmware 2.92 only supports RSA, not Ed25519). "
          "2. In iDRAC web UI: Users → graycat → Add SSH Public Key. "
          "3. Test key-based login: ssh -p 20234 -i ~/.ssh/id_rsa_idrac graycat@192.168.86.100. "
          "4. Optionally set PasswordAuthentication no in iDRAC SSH settings (if supported). "
          "5. Repeat for Oumuamua (192.168.86.101). "
          "6. Update credential-manager with unique passwords per iDRAC."),
         "2026-04-01",
         "open", "Dan Kessler (ISSO)",
         "1 hour; iDRAC web UI access required",
         "iDRAC6 configured with defaults during initial server setup; hardening deferred.",
         "iDRAC6 FW 2.92 (final). Note: paramiko requires disabled_algorithms for rsa-sha2-256/512."),

        ("BRV-0017", "ac-11",
         "iDRAC6 Web UI Session Timeout Not Configured",
         ("The iDRAC6 web interface on both Borisov and Oumuamua does not have a session "
          "inactivity timeout configured. An authenticated iDRAC session left open provides "
          "a window for unauthorized access to hardware management functions including power "
          "control, console access, and system logs."),
         "moderate", "configuration_review",
         ("1. Log in to iDRAC web UI: https://192.168.86.100 (Borisov) and https://192.168.86.101 "
          "(Oumuamua). "
          "2. Navigate to iDRAC Settings → Network/Services → Web Server. "
          "3. Set Session Timeout to 15 minutes (or minimum supported value). "
          "4. Save and verify by leaving session idle to confirm timeout."),
         "2026-04-01",
         "open", "Dan Kessler (ISSO)",
         "20 minutes; iDRAC web UI access",
         "Default iDRAC6 configuration. Session timeout not set during initial hardening.",
         "iDRAC6 FW 2.92. NTP not supported on this firmware version."),

        ("BRV-0018", "au-11",
         "Systemd Journal Disk Usage Elevated — Vacuum Required",
         ("The systemd journal has accumulated log entries beyond the 7-day retention policy. "
          "Excessive journal size consumes disk space and can slow log queries. "
          "A vacuum operation is required to enforce the 7-day retention policy."),
         "low", "isso_review",
         ("sudo journalctl --vacuum-time=7d. "
          "Handled in maint-run.sh ITEM 18. "
          "Consider setting SystemMaxUse and MaxRetentionSec in /etc/systemd/journald.conf "
          "for permanent enforcement."),
         "2026-03-09",
         "open", "Dan Kessler (ISSO)",
         "2 minutes; requires sudo",
         "Journal accumulates continuously. Vacuum not yet run since system setup.",
         "Handled in maint-run.sh ITEM 18."),

        ("BRV-0019", "si-2",
         "Old Unsigned FIPS Kernel Packages Installed",
         ("Unsigned FIPS kernel packages from a previous kernel version remain installed: "
          "linux-image-unsigned-5.4.0-1125-fips and linux-image-unsigned-hmac-5.4.0-1125-fips. "
          "The current running kernel is 5.4.0-1128-fips. Retaining old kernel packages "
          "increases disk usage and maintains a larger attack surface."),
         "low", "configuration_review",
         ("sudo apt-get purge linux-image-unsigned-5.4.0-1125-fips "
          "linux-image-unsigned-hmac-5.4.0-1125-fips; sudo update-grub. "
          "Handled in maint-run.sh ITEM 19."),
         "2026-03-09",
         "open", "Dan Kessler (ISSO)",
         "5 minutes; requires sudo",
         "Previous FIPS kernel update left old packages installed. Not auto-removed.",
         "Handled in maint-run.sh ITEM 19. Verify grub menu has correct default entry after removal."),

        ("BRV-0020", "sa-10",
         "BLACKSITE Source Code Not Backed Up to Remote Repository",
         ("The BLACKSITE GRC platform source code (Git repository at /home/graycat/projects/blacksite) "
          "has not been pushed to the remote backup repository since recent Phase 26/27 changes. "
          "Loss of the local Git repository would result in loss of all code changes since last push."),
         "low", "isso_review",
         ("1. cd /home/graycat/projects/blacksite "
          "2. gh auth login (if not already authenticated) "
          "3. git push origin main "
          "4. Verify push: gh repo view"),
         "2026-03-16",
         "open", "Dan Kessler (ISSO)",
         "15 minutes; GitHub authentication required",
         "Code changes made faster than push cadence. sync-projects.sh syncs to Iapetus (partial backup).",
         "sync-projects.sh provides local network backup to Iapetus. GitHub push provides offsite backup."),

        ("BRV-0022", "cm-11",
         "MoltyB Test Stack Uses :latest Tag for openclaw Image",
         ("The Oumuamua test compose file (oumuamua-test.yml) contains an :latest tag for the "
          "openclaw container image. Using :latest tags means the exact image version is undefined "
          "and can change unexpectedly on pull, violating the version-pinning policy established "
          "for all production and test containers."),
         "moderate", "configuration_review",
         ("1. Identify the running openclaw container version on Oumuamua: "
          "ssh oumuamua 'docker inspect openclaw --format={{.Config.Image}}' "
          "2. Pin the tag in oumuamua-test.yml to the specific version digest or tag. "
          "3. Update test.yml reference as well. "
          "4. Decision point: confirm with operator whether openclaw is still needed."),
         "2026-04-01",
         "open", "Dan Kessler (ISSO)",
         "30 minutes including testing",
         "Image added without pinning. Version pinning policy applied to all other images 2026-03-02.",
         "All other test stack images pinned 2026-03-02. openclaw:latest is the last remaining."),
    ]

    for (poam_id, ctrl, name, desc, sev, src, plan, sched, status_v,
         responsible, resources, root_cause, comments) in poams:
        c.execute("SELECT id FROM poam_items WHERE poam_id=?", (poam_id,))
        if not c.fetchone():
            c.execute("""INSERT INTO poam_items (
                id, system_id, assessment_id, control_id, weakness_name, weakness_description,
                detection_source, severity, responsible_party, resources_required,
                scheduled_completion, status, remediation_plan,
                root_cause, comments,
                created_at, updated_at, created_by, poam_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (u(), SYS_ID, None, ctrl, name, desc, src, sev, responsible, resources,
             sched, status_v, plan, root_cause, comments, NOW, NOW, CREATOR, poam_id))
    print(f"  [5/7] poam_items ({len(poams)} findings) ✓")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. ATO DOCUMENTS
    # ─────────────────────────────────────────────────────────────────────────
    ato_docs = [
        (u(), "fips199",
         "BRV FIPS 199 Security Categorization Worksheet",
         "1.0", "approved",
         ("FIPS 199 SECURITY CATEGORIZATION — BRV\n\n"
          "System: Borisov Infrastructure Server (BRV)\n"
          "Date: 2026-01-20\n\n"
          "DATA TYPES AND IMPACT LEVELS:\n\n"
          "1. User Credentials / Authentication Data\n"
          "   Confidentiality: Moderate (exposure enables unauthorized system access)\n"
          "   Integrity: Moderate (modification enables privilege escalation)\n"
          "   Availability: Low (recoverable from backup)\n\n"
          "2. Home Automation Telemetry (HA states, sensor data, presence)\n"
          "   Confidentiality: Moderate (presence/occupancy data is personal)\n"
          "   Integrity: Low (incorrect automation is inconvenient, not harmful)\n"
          "   Availability: Low (HA restart restores state)\n\n"
          "3. Media Library Metadata and Files\n"
          "   Confidentiality: Low (personal media catalog)\n"
          "   Integrity: Low (metadata corruption recoverable)\n"
          "   Availability: Low (entertainment, not critical)\n\n"
          "4. Application Secrets (API keys, SOPS-managed)\n"
          "   Confidentiality: High (exposure compromises integrated services)\n"
          "   Integrity: Moderate (modification disrupts services)\n"
          "   Availability: Low (secrets can be regenerated)\n\n"
          "SYSTEM SECURITY CATEGORIZATION:\n"
          "   Confidentiality: Moderate\n"
          "   Integrity: Moderate\n"
          "   Availability: Low\n"
          "   OVERALL (high water mark): MODERATE\n\n"
          "Approved by: Dan Kessler (System Owner / AO) — 2026-01-20")),

        (u(), "ssp",
         "BRV System Security Plan (SSP)",
         "0.8", "in_review",
         ("SYSTEM SECURITY PLAN — BORISOV INFRASTRUCTURE SERVER (BRV)\n"
          "Version: 0.8 (Draft for Review)\n"
          "Date: 2026-03-02\n\n"
          "1. SYSTEM IDENTIFICATION\n"
          "   Name: Borisov Infrastructure Server\n"
          "   Abbreviation: BRV\n"
          "   Type: General Support System\n"
          "   Environment: On-Premise (homelab)\n"
          "   Owner: Dan Kessler (dan@borisov.network)\n"
          "   ISSO: Dan Kessler\n\n"
          "2. SYSTEM DESCRIPTION\n"
          "   Dell PowerEdge R720 running Ubuntu 22.04 FIPS. Hosts 31+ Docker containers "
          "   providing home automation, media, GRC, security monitoring, DNS, authentication, "
          "   and development services.\n\n"
          "3. SYSTEM CATEGORIZATION\n"
          "   C=Moderate / I=Moderate / A=Low → Overall: Moderate\n\n"
          "4. CONTROL BASELINE\n"
          "   NIST SP 800-53 Rev 5 Moderate baseline with tailoring.\n"
          "   Tailoring: SR family (N/A - homelab), PS family (N/A - single operator),\n"
          "   PM family reduced.\n\n"
          "5. INTERCONNECTIONS\n"
          "   - Iapetus NAS (192.168.86.213): SMB/rsync for backup and project sync\n"
          "   - Polaris UDM Pro (192.168.86.1): network gateway and firewall\n"
          "   - Oumuamua test server (192.168.86.103): test/staging environment\n"
          "   - Cloudflare: DNS-01 certificate authority\n"
          "   - Ring, Nest, Google APIs: external integrations via HA\n\n"
          "6. LAWS AND REGULATIONS\n"
          "   No regulatory compliance obligations (homelab, personal use).\n"
          "   Voluntary alignment with NIST SP 800-53r5 Moderate baseline.\n\n"
          "7. STATUS: Draft. Pending final control narrative completion and ATO authorization.\n"
          "   Expected completion: 2026-04-30")),

        (u(), "sap",
         "BRV Security Assessment Plan (SAP)",
         "1.0", "approved",
         ("SECURITY ASSESSMENT PLAN — BRV\n"
          "Version: 1.0\n"
          "Date: 2026-01-25\n\n"
          "1. SCOPE\n"
          "   Annual self-assessment of all Moderate baseline controls implemented on BRV.\n"
          "   Assessment period: 2026-01-25 through 2026-04-15.\n\n"
          "2. ASSESSMENT METHODOLOGY\n"
          "   NIST SP 800-53A Rev 5 assessment procedures.\n"
          "   Methods: Examine (document review), Interview (ISSO), Test (technical verification).\n"
          "   Assessor: Dan Kessler (ISSO — self-assessment, homelab context).\n\n"
          "3. ASSESSMENT ACTIVITIES\n"
          "   Phase 1 (Jan): Control selection and baseline scoping\n"
          "   Phase 2 (Feb): Documentation review and examination\n"
          "   Phase 3 (Mar): Technical testing and configuration review\n"
          "   Phase 4 (Apr): Findings compilation, SAR draft, POA&M population\n\n"
          "4. DELIVERABLES\n"
          "   - Security Assessment Report (SAR) — due 2026-04-15\n"
          "   - Updated POA&M register\n"
          "   - Updated SSP\n"
          "   - ATO recommendation memo")),

        (u(), "sar",
         "BRV Security Assessment Report (SAR) — DRAFT",
         "0.5", "draft",
         ("SECURITY ASSESSMENT REPORT — BRV (DRAFT)\n"
          "Version: 0.5\n"
          "Date: 2026-03-02 (Assessment in progress)\n\n"
          "1. EXECUTIVE SUMMARY\n"
          "   Assessment of Borisov Infrastructure Server (BRV) against NIST SP 800-53r5 "
          "   Moderate baseline. 15 findings identified. No Critical controls entirely failed.\n"
          "   Critical: 1 (CP-9 — disk failure imminent)\n"
          "   High: 3 (IA-5 expired creds, IA-2 SSH CA, IA-5/AC-17 iDRAC)\n"
          "   Moderate: 4 (AC-17 VPN peers, SC-7 ephemeral rules, SC-7 UPnP, AC-11/CM-11)\n"
          "   Low: 7 (AU-2 timer, SC-7 WeMo, CM-7 apache2, SI-2 systemd units x2, "
          "AU-11 journal, SI-2 old kernels)\n\n"
          "2. FINDINGS\n"
          "   See POA&M register (15 items: BRV-0005 through BRV-0022).\n\n"
          "3. OVERALL RISK POSTURE\n"
          "   Moderate risk. Core security controls (Authelia SSO, Wazuh SIEM, TLS, "
          "   FIPS kernel, backups) are functioning. Primary risks are operational gaps: "
          "   disk hardware failure, expired credentials, and configuration hygiene items "
          "   that are actively being remediated via maint-run.sh.\n\n"
          "4. ATO RECOMMENDATION\n"
          "   Pending. Authorize to Operate recommended after resolution of Critical/High POA&Ms. "
          "   Expected authorization date: 2026-05-01.\n\n"
          "   [Draft — Final version due 2026-04-15]")),
    ]

    for (doc_id, doc_type, title, version, status_v, content) in ato_docs:
        c.execute("SELECT id FROM ato_documents WHERE system_id=? AND doc_type=?",
                  (SYS_ID, doc_type))
        if not c.fetchone():
            c.execute("""INSERT INTO ato_documents
                         (id, system_id, doc_type, title, version, status, content,
                          assigned_to, due_date, created_by, created_at, updated_at)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (doc_id, SYS_ID, doc_type, title, version, status_v, content,
                       CREATOR, "2026-04-30", CREATOR, NOW, NOW))
    print(f"  [6/7] ato_documents ({len(ato_docs)} docs) ✓")

    # ─────────────────────────────────────────────────────────────────────────
    # 8. RISKS (summary risk entries for portfolio view)
    # ─────────────────────────────────────────────────────────────────────────
    # Check risk table schema
    c.execute("PRAGMA table_info(risks)")
    risk_cols = {row[1] for row in c.fetchall()}

    if "system_id" in risk_cols:
        # risks columns: id, system_id, poam_id, risk_name, risk_description,
        # threat_source, threat_event, vulnerability, likelihood, impact,
        # risk_score, risk_level, treatment, treatment_plan, residual_likelihood,
        # residual_impact, residual_score, residual_level, owner, status, review_date,
        # created_at, updated_at, created_by
        risks_data = [
            ("Imminent Storage Failure — Media Library Data Loss",
             "hardware",
             "Drive SMART failure detected on Oumuamua Bay 0 — data loss imminent",
             "drive failure, media library data loss",
             "SMART pre-failure condition on WD 1TB drive (serial WOL240039921)",
             3, 3, 9, "high",
             "replace", "Replace drive immediately; verify backup integrity on Iapetus NAS",
             1, 2, 2, "low",
             "2026-03-16"),

            ("Unauthorized Remote Access via SSH Certificate Authority",
             "technical",
             "TrustedUserCAKeys active in sshd_config allows CA-signed cert holders to authenticate",
             "privilege escalation via compromised or shared CA key",
             "sshd_config misconfiguration — TrustedUserCAKeys not disabled",
             2, 3, 6, "moderate",
             "remediate", "Comment out TrustedUserCAKeys in sshd_config (maint-run.sh ITEM 9)",
             1, 1, 1, "low",
             "2026-03-09"),

            ("Firewall Rules Lost on Gateway Reboot",
             "operational",
             "IoT VLAN iptables rules are ephemeral — lost after UDM Pro reboot",
             "Ring live-view failure, WeMo control degradation after gateway reboot",
             "Rules added manually without persistence to on_boot.d",
             2, 2, 4, "moderate",
             "remediate", "Write rules to /mnt/data/on_boot.d/98-iot-vlan-extras.sh (maint-run.sh ITEM 11)",
             1, 1, 1, "low",
             "2026-03-09"),
        ]

        try:
            for (name, src, desc, threat_evt, vuln, lik, imp, score, level,
                 treatment, plan, r_lik, r_imp, r_score, r_level, review) in risks_data:
                c.execute("SELECT id FROM risks WHERE system_id=? AND risk_name=?", (SYS_ID, name))
                if not c.fetchone():
                    c.execute("""INSERT INTO risks
                                 (id, system_id, risk_name, risk_description, threat_source,
                                  threat_event, vulnerability, likelihood, impact,
                                  risk_score, risk_level, treatment, treatment_plan,
                                  residual_likelihood, residual_impact, residual_score, residual_level,
                                  owner, status, review_date, created_at, updated_at, created_by)
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (u(), SYS_ID, name, desc, src, threat_evt, vuln, lik, imp,
                               score, level, treatment, plan, r_lik, r_imp, r_score, r_level,
                               CREATOR, "open", review, NOW, NOW, CREATOR))
            print(f"  [7/7] risks (3 entries) ✓")
        except Exception as e:
            print(f"  [7/7] risks: skipped ({e})")
    else:
        print(f"  [7/7] risks: skipped (system_id column not in risks table)")

    # ─────────────────────────────────────────────────────────────────────────
    conn.commit()
    conn.close()
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✔  Borisov (BRV) seeded successfully in BLACKSITE/AEGIS")
    print()
    print("  System ID  :", SYS_ID)
    print("  Abbrev     :", SYS_ABB)
    print("  RMF Steps  : 7  (prepare=complete, categorize=complete, select=complete,")
    print("                    implement=in_progress, assess=in_progress,")
    print("                    authorize=not_started, monitor=in_progress)")
    print(f"  Controls   : {len(controls)}  (Moderate baseline, 20 families)")
    print(f"  POA&Ms     : {len(poams)}  (1 critical, 3 high, 4 moderate, 7 low)")
    print(f"  ATO Docs   : {len(ato_docs)}  (FIPS199=approved, SSP=in_review, SAP=approved, SAR=draft)")
    print()
    print("  View in BLACKSITE → http://localhost:8100/systems/" + SYS_ID)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    run()
