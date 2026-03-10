#!/usr/bin/env python3
"""
Populate BLACKSITE ATO document library with substantive content.
Step 1: Update existing draft documents with real content and approve them.
"""
import asyncio, sys, os, uuid
sys.path.insert(0, '/home/graycat/projects/blacksite')
if 'BLACKSITE_DB_KEY' not in os.environ:
    raise RuntimeError("BLACKSITE_DB_KEY not set. Export it before running this script.")
import yaml
with open('/home/graycat/projects/blacksite/config.yaml') as f:
    config = yaml.safe_load(f)
from app.models import make_engine, make_session_factory
from sqlalchemy import text

SYSTEM_ID = 'bsv-main-00000000-0000-0000-0000-000000000001'

DOCS = {}

DOCS['SSP'] = """# System Security Plan (SSP)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Classification:** Unclassified // Internal Use Only
**Impact Level:** Low (FIPS 199)

---

## 1. System Identification

| Field | Value |
|---|---|
| System Name | BLACKSITE Security Assessment Platform |
| System Abbreviation | BLACKSITE |
| System Owner | Dan Borisov |
| Owner Contact | daniel@thekramerica.com |
| Organization | TheKramerica |
| System Type | Major Application — Internal Security Tool |
| Authorization Status | Authorized to Operate (ATO) |
| ATO Expiration | 2029-03-09 |
| Operating Environment | On-premises, Ubuntu 20.04 FIPS, Dell PowerEdge R510 |

---

## 2. System Purpose and Description

BLACKSITE is an internal security compliance and assessment management platform developed and operated by TheKramerica. The system provides a structured, web-based environment for tracking NIST SP 800-53 Rev 5 security controls, managing Plans of Action and Milestones (POA&Ms), conducting security control assessments, generating Authorization to Operate (ATO) packages, and maintaining system security documentation for information systems within the TheKramerica environment.

BLACKSITE serves as the authoritative system of record for the organization's cybersecurity risk management program. It enables the Information System Security Officer (ISSO), Information System Security Manager (ISSM), Chief Information Security Officer (CISO), Authorizing Official (AO), Security Control Assessor (SCA), and authorized auditors to collaborate on security documentation, track remediation activities, and produce evidence packages required for formal system authorizations.

The platform ingests the NIST SP 800-53 Rev 5 control catalog from NIST's official OSCAL GitHub repository nightly, maintaining a current baseline of applicable controls. It supports multiple compliance frameworks and allows cross-walking controls across different regulatory requirements.

Key capabilities include:
- NIST SP 800-53 Rev 5 control inventory and implementation tracking
- Security control assessment workflow (SAP → assessment → SAR)
- POA&M lifecycle management with severity scoring and milestone tracking
- ATO document library with versioned content management
- Evidence file attachment and management
- Role-based access control enforcing least privilege
- Security event logging with tamper-evident encrypted storage
- AI-assisted control narrative drafting (LLM integration, local only)
- Export of ATO packages in standard formats
- Continuous monitoring dashboard

---

## 3. System Environment and Architecture

### 3.1 Hosting Environment

BLACKSITE is hosted on-premises at the residence/home office of Dan Borisov (system owner and ISSO) in a physically secured environment. The server is a Dell PowerEdge R510 (hostname: borisov, IP: 192.168.86.102) running Ubuntu 20.04 LTS with FIPS 140-2 validated cryptographic modules enabled. The server is protected behind a UniFi Dream Machine Pro (UDM Pro) network appliance providing stateful firewall, NAT, and network segmentation. Physical access is restricted to the system owner.

**Server specifications:**
- Hardware: Dell PowerEdge R510, 2× Intel Xeon X5675 (24 threads), 64GB ECC RAM
- Operating System: Ubuntu 20.04 LTS (FIPS mode enabled)
- Storage: 12×10TB RAID via PERC H700, 2×500GB SSD RAID1 (OS)
- Network: 1GbE LAN, UniFi-managed, VLAN-segmented
- UPS: Residential UPS protecting server and network equipment

### 3.2 Technology Stack

| Component | Technology | Version/Details |
|---|---|---|
| Application Framework | FastAPI (Python) | Python 3.8, FastAPI 0.100+ |
| Database | SQLite + SQLCipher | AES-256-CBC encryption at rest |
| Web Server / Reverse Proxy | Caddy v2 | Automatic TLS via Let's Encrypt |
| Authentication / MFA | Authelia | TOTP-based MFA, session management |
| Process Management | systemd | blacksite.service unit |
| Cryptographic Library | pysqlcipher3 | FIPS-validated SQLCipher backend |

### 3.3 Network Architecture and Data Flows

BLACKSITE operates within the main LAN (192.168.86.0/24). All external access is through Caddy reverse proxy with TLS termination. Authelia enforces authentication before any BLACKSITE endpoint is reachable.

**Inbound data flows:**
1. User browser → Caddy (HTTPS/443) → Authelia authentication check → BLACKSITE app (127.0.0.1:8100)
2. BLACKSITE nightly cron → NIST GitHub API (api.github.com) → OSCAL catalog update
3. BLACKSITE event enrichment → ip-api.com (free geo-IP, HTTP GET, IP address only)

**Outbound data flows:**
1. BLACKSITE app → SQLCipher DB (local file, AES-256 encrypted)
2. BLACKSITE app → Caddy (HTTPS response to user)
3. Nightly backup script → Iapetus NAS (192.168.86.213, SSH/rsync)

No data leaves the premises except:
- IP address lookups to ip-api.com for security event enrichment
- NIST catalog downloads from api.github.com
- TLS certificate operations via Let's Encrypt ACME

### 3.4 Authorization Boundary

The BLACKSITE authorization boundary encompasses:
- The BLACKSITE application process (PID managed by systemd)
- The SQLCipher database file (data/blacksite.db)
- The Caddy configuration specific to BLACKSITE (blacksite.borisov.network vhost)
- The Authelia session management for BLACKSITE users
- The systemd service unit file (/etc/systemd/system/blacksite.service)
- Application configuration (config.yaml, .env variables)

**Excluded from boundary (inherited controls):**
- Ubuntu OS-level controls (inherited from OS baseline)
- Physical security (owner-provided residential controls)
- Network infrastructure (UniFi Dream Machine Pro)
- Caddy TLS certificate management (Caddy/Let's Encrypt)
- Authelia authentication engine (separate system boundary)

---

## 4. User Roles and Privileges

| Role | Description | Access Level |
|---|---|---|
| admin | System administrator; full access to all functions, user management, system configuration | Full |
| isso | Information System Security Officer; manages controls, POA&Ms, documents, assessments | Full (security functions) |
| issm | ISSO Manager; review and approval of security decisions, POA&M oversight | Read + Approve |
| ciso | Chief Information Security Officer; executive oversight, ATO decisions | Read + Executive |
| ao | Authorizing Official; reviews risk posture, signs authorization decisions | Read + Authorize |
| sca | Security Control Assessor; conducts assessments, writes findings, updates assessment results | Assessment functions |
| auditor | Read-only access to all security content for audit purposes | Read-only |
| manager | System/program manager; access to system overview and risk dashboard | Limited read |

All users are required to authenticate via Authelia with TOTP MFA before accessing BLACKSITE. Session tokens are HMAC-signed and stored server-side. Idle sessions expire after 30 minutes.

---

## 5. Interconnections and External Services

| System | Connection Type | Data Exchanged | Sensitivity | Agreement |
|---|---|---|---|---|
| Authelia (local) | HTTP forward-auth (localhost) | Auth tokens, session state | Internal | N/A (same boundary host) |
| Caddy (local) | HTTP reverse proxy (localhost) | HTTP request/response | Internal | N/A (same boundary host) |
| ip-api.com | HTTPS GET (outbound) | Source IP addresses only | Low | Free tier ToS; fail-open |
| NIST GitHub API | HTTPS GET (outbound) | NIST control catalog (public data) | Public | Public API, no auth |
| Let's Encrypt | ACME/HTTPS (outbound) | TLS cert CSR, domain validation | Low | Let's Encrypt ToS |
| Iapetus NAS | SSH/rsync (outbound) | Encrypted backup files | Internal | Owner-operated |

---

## 6. Security Controls Summary

BLACKSITE implements the NIST SP 800-53 Rev 5 Low baseline (149 controls applicable). As of 2026-03-09:

- **Implemented:** Controls with full technical or administrative implementation
- **Partial:** Controls with some implementation; gaps documented in POA&M
- **Not Implemented:** Controls not yet addressed; tracked in POA&M
- **Not Applicable:** Controls not applicable to the system's environment or scope (e.g., radio frequency controls)
- **Inherited:** Controls satisfied by underlying infrastructure (OS, network, physical)

Key implemented controls include: AC-2 (account management via RBAC), AC-3 (access enforcement), AU-2/AU-3 (audit logging in encrypted security_events table), IA-2/IA-5 (MFA via Authelia, password management), SC-8/SC-28 (TLS in transit, AES-256 at rest), SI-10 (input validation), CM-6 (config baseline in config.yaml and requirements.txt).

Known gaps requiring remediation are tracked in the POA&M system within BLACKSITE itself.

---

## 7. Engineering Principles and Security Design

BLACKSITE was designed applying the following security engineering principles (aligned with SA-8):

1. **Least Privilege:** RBAC enforces minimum necessary permissions per role. Database queries are parameterized. Service runs as dedicated system user.
2. **Defense in Depth:** Authelia MFA → Caddy TLS → application-level authorization → encrypted database.
3. **Fail Secure:** ip-api.com enrichment fails open (non-critical); authentication failures result in access denial.
4. **Economy of Mechanism:** Simple, auditable code; minimal external dependencies.
5. **Separation of Duties:** ISSO/AO/SCA roles are distinct; no single role can authorize and assess simultaneously.
6. **Complete Mediation:** Every request passes through Authelia forward-auth before reaching application routes.
7. **Cryptographic Strength:** AES-256 database encryption, TOTP-based MFA, TLS 1.2+ enforced by Caddy.
8. **Audit Trails:** All security-relevant events written to append-friendly security_events table with timestamp, actor, and action.

---

## 8. Document Control

This SSP is maintained in the BLACKSITE ATO document library. Updates require ISSO review and AO concurrence. Major revisions (new major version) require full AO re-authorization review. The SSP is reviewed annually or upon significant system change, whichever comes first.

**Approval:**
Dan Borisov, ISSO/AO, TheKramerica
daniel@thekramerica.com
2026-03-09
"""

DOCS['IRP'] = """# Incident Response Plan (IRP)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-61 Rev 2
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This Incident Response Plan (IRP) establishes the procedures for detecting, containing, eradicating, recovering from, and learning from security incidents affecting the BLACKSITE Security Assessment Platform. This plan applies to all components within the BLACKSITE authorization boundary as defined in the System Security Plan (SSP).

The objectives of this plan are to:
- Minimize the impact of security incidents on BLACKSITE and its data
- Ensure rapid detection and response to security events
- Preserve evidence for post-incident analysis
- Meet any applicable reporting obligations
- Continuously improve security posture through lessons learned

This plan is reviewed annually and updated after any significant incident or system change.

---

## 2. Key Personnel and Contact Information

| Role | Name | Contact | Availability |
|---|---|---|---|
| ISSO / Incident Commander | Dan Borisov | daniel@thekramerica.com | 24/7 (system owner) |
| Authorizing Official (AO) | Dan Borisov | daniel@thekramerica.com | 24/7 |
| System Administrator | Dan Borisov | daniel@thekramerica.com | 24/7 |

As a single-person operation, Dan Borisov serves all response roles. For incidents exceeding individual capacity, external cybersecurity assistance may be engaged through trusted professional networks.

---

## 3. Incident Categories and Severity

| Category | Description | Severity | Initial Response Time |
|---|---|---|---|
| CAT-1 | Unauthorized root/admin access | Critical | Immediate (< 1 hour) |
| CAT-2 | Data breach / exfiltration of security data | Critical | Immediate (< 1 hour) |
| CAT-3 | Credential compromise (user account) | High | < 4 hours |
| CAT-4 | Denial of Service (DoS/DDoS) | High | < 4 hours |
| CAT-5 | Malware / ransomware detection | Critical | Immediate (< 1 hour) |
| CAT-6 | Unauthorized configuration change | Moderate | < 24 hours |
| CAT-7 | Failed authentication anomalies (brute force) | Moderate | < 24 hours |
| CAT-8 | Third-party service compromise (ip-api.com, NIST) | Low | < 72 hours |

---

## 4. Detection Sources

BLACKSITE incidents may be detected through:

1. **security_events table** — Application-level audit log in the encrypted SQLCipher database. Captures authentication events, authorization failures, access to sensitive resources, configuration changes, and API errors. Reviewed via the BLACKSITE Security Events dashboard (admin/ISSO role).

2. **Authelia audit log** — Records all authentication attempts (success/failure), MFA events, session creation/destruction. Located in Authelia container logs: `docker logs authelia`.

3. **Caddy access log** — HTTP request log including IP, path, status code, response time. Anomalous patterns (4xx floods, scanning patterns) indicate potential attacks.

4. **Wazuh agent** — Host-based IDS monitoring file integrity, log anomalies, rootkit detection on the borisov server. Alerts forwarded to Wazuh dashboard.

5. **User reports** — Any user who notices unexpected behavior, unauthorized changes, or suspicious activity should immediately report via email to daniel@thekramerica.com.

6. **Backup verification failures** — Nightly backup script (backup-all.sh) failures logged to systemd journal; failures may indicate ransomware or storage compromise.

---

## 5. Response Phases

### Phase 1: Preparation

**Ongoing activities (maintained prior to any incident):**
- BLACKSITE security_events table reviewed monthly by ISSO
- Authelia and Caddy logs reviewed on anomaly detection
- Database backup verified weekly (manual spot-check of Iapetus NAS)
- Incident response contacts documented in this plan
- Backup-all.sh running nightly with systemd timer
- blacksite-co (port 8101) maintained as alternate instance for continuity

**Preparation checklist (confirm quarterly):**
- [ ] Backup integrity verified
- [ ] blacksite-co instance functional
- [ ] Authelia MFA enrollment current for all users
- [ ] This IRP reviewed and contact info current
- [ ] Wazuh agent running on borisov

### Phase 2: Detection and Analysis

Upon detection of a potential incident:

1. **Record initial observations:** Timestamp, detection source, affected components, visible indicators.
2. **Query security_events:** `SELECT * FROM security_events WHERE created_at > '[incident window]' ORDER BY created_at DESC LIMIT 500;`
3. **Review Authelia logs:** `docker logs authelia --since 24h | grep -E 'error|warn|fail'`
4. **Check Caddy logs:** Review for scanning patterns, unusual source IPs, high error rates.
5. **Assess scope:** Is this limited to BLACKSITE, or does it affect the broader borisov server or network?
6. **Assign severity:** Use incident category table above.
7. **Document findings** in a timestamped incident log (plaintext file at /home/graycat/docs/incident-YYYY-MM-DD.md).

**False positive handling:** Many security events (authentication failures, rate limit hits) are expected. An incident is confirmed when: (a) unauthorized access is verified, (b) data integrity anomalies are found, (c) external confirmation of compromise is received, or (d) multiple correlated indicators point to active threat.

### Phase 3: Containment

**Short-term containment (immediate, < 1 hour for Critical incidents):**

- **Block source IP at firewall:** `ssh polaris` → add iptables DROP rule for offending IP
- **Revoke compromised session:** Delete session file from Authelia session store or restart Authelia: `docker restart authelia`
- **Disable compromised user account:** Update Authelia users_database.yml, set `disabled: true` for affected user
- **Isolate BLACKSITE service:** `sudo systemctl stop blacksite` — takes system offline but preserves evidence
- **Preserve evidence:** Copy security_events DB snapshot before any remediation: `cp /home/graycat/projects/blacksite/data/blacksite.db /home/graycat/docs/evidence-YYYY-MM-DD.db`

**Long-term containment:**
- Rotate all secrets (DB key, session key, API keys) if credential compromise is suspected
- Deploy blacksite-co as temporary replacement if main instance must remain offline
- Increase logging verbosity: set log level DEBUG in config.yaml temporarily

### Phase 4: Eradication

- Identify and remove root cause (malicious file, unauthorized account, misconfiguration)
- Apply patches if vulnerability was exploited
- Restore from last known-good backup if integrity compromise detected
- Re-run pip audit and apply any pending security updates
- Verify Wazuh FIM baseline is clean after remediation

### Phase 5: Recovery

1. Restore BLACKSITE from Iapetus NAS backup if needed: `rsync -az iapetus:clawd/backups/borisov/blacksite/ /home/graycat/projects/blacksite/data/`
2. Verify database integrity: test DB open with correct key, run `PRAGMA integrity_check;`
3. Restart service: `sudo systemctl restart blacksite`
4. Validate functionality: log in, verify security_events accessible, verify control data intact
5. Monitor closely for 72 hours post-recovery: review security_events daily
6. Remove temporary containment measures (IP blocks, elevated logging) only after confident in recovery

### Phase 6: Post-Incident Activity

Within 5 business days of incident closure:
1. Write post-incident report (template: /home/graycat/docs/incident-report-template.md) covering: timeline, root cause, impact, response actions, lessons learned
2. Update this IRP if any procedural gaps were identified
3. Create or update POA&M items for any control gaps exposed by the incident
4. Consider whether security_events alerting improvements are warranted
5. Retain all incident evidence for minimum 1 year

---

## 6. Incident Response Playbooks

### Playbook A: Unauthorized Access (CAT-1/CAT-3)

**Indicators:** Unexpected entries in security_events with unknown user IDs; Authelia logs showing successful auth from unknown IP; new admin account created without authorization.

**Steps:**
1. Capture security_events snapshot immediately
2. Identify all sessions active during the incident window: review Authelia session store
3. Terminate all active sessions: `docker restart authelia` (forces re-authentication for all users)
4. If admin-level compromise: `sudo systemctl stop blacksite`; rotate DB key (requires dump/re-encrypt procedure in KMP)
5. Review git log for unauthorized code changes: `git log --since='[incident date]' --oneline`
6. Reset all user credentials in Authelia users_database.yml
7. Restore from backup if data integrity uncertain

### Playbook B: Data Breach / Exfiltration (CAT-2)

**Indicators:** Large data exports in security_events; unexpected outbound connections in network logs; missing or modified records in database.

**Steps:**
1. Immediately isolate: `sudo systemctl stop blacksite`; block outbound from borisov (192.168.86.102) at UDM Pro firewall except for management
2. Preserve forensic copy of database
3. Review Caddy access log for data export patterns (large response bodies, bulk API calls)
4. Determine what data was exposed: BLACKSITE contains security metadata (control narratives, assessment notes, POA&M details, user IDs) — no PII, no financial data, no external customer data
5. Notify AO (Dan Borisov self-notification in this case) and document scope
6. If breach involves exposure of system architecture details, review whether adversary could use to attack other systems in the network

### Playbook C: Denial of Service (CAT-4)

**Indicators:** BLACKSITE unresponsive; Caddy returning 503; high CPU/memory on borisov server.

**Steps:**
1. Check if it's a resource issue vs. attack: `top`, `netstat -an | grep 8100 | wc -l`
2. If attack: identify source IPs from Caddy logs; block at UDM Pro
3. Caddy rate limiting: verify rate_limit directive is active in Caddyfile
4. If server resources exhausted: `sudo systemctl restart blacksite`; consider temporarily restricting access to LAN-only by removing public DNS entry
5. Document attack volume and source distribution

### Playbook D: Malware / Ransomware (CAT-5)

**Indicators:** Wazuh FIM alerts for unexpected file modifications; files encrypted with unknown extension; system performance degradation.

**Steps:**
1. Immediately isolate server from network: disable network interface or block at UDM Pro
2. Do NOT restart — preserve memory/process state for forensics
3. Boot from external media to assess file system integrity without running potentially compromised OS
4. If ransomware confirmed: restore entire server from Iapetus NAS backup (backup-all.sh covers /home/graycat and /etc)
5. Engage external cybersecurity professional if beyond single-person response capacity
6. Report to relevant authorities if warranted

### Playbook E: Credential Compromise (CAT-3)

**Indicators:** Authelia TOTP failures from known user; user reports they did not initiate login attempts; unexpected password reset.

**Steps:**
1. Immediately disable affected account in Authelia users_database.yml
2. Terminate any active sessions: restart Authelia
3. Require affected user to re-enroll TOTP from a trusted device
4. Review security_events for all actions taken during the compromise window
5. Rotate session HMAC key if session hijacking is suspected: delete /home/graycat/projects/blacksite/data/.app_secret (triggers new key generation on next restart)

---

## 7. Reporting Requirements

BLACKSITE is an internal tool handling unclassified, non-PII security metadata. Reporting obligations are minimal:

- **Internal reporting:** ISSO (Dan Borisov) is self-reporting; document all incidents in /home/graycat/docs/
- **No mandatory external reporting** unless: (a) breach involves PII (not applicable — no PII in BLACKSITE), (b) breach involves government-classified information (not applicable), or (c) breach affects third-party systems connected to BLACKSITE
- If incident scope expands to other TheKramerica systems, assess reporting obligations for those systems separately

---

## 8. Plan Maintenance

This IRP is reviewed and tested annually. A tabletop exercise simulating a credential compromise scenario (Playbook E) is conducted each year to validate procedures and identify gaps. Results are documented and this plan updated accordingly.

**Next review date:** 2027-03-09
**Plan owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, 2026-03-09
"""

DOCS['CP'] = """# Contingency Plan (CP)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-34 Rev 1
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This Contingency Plan (CP) establishes procedures to sustain and recover the BLACKSITE Security Assessment Platform following a disruption, degradation, or outage. This plan covers all components within the BLACKSITE authorization boundary as defined in the System Security Plan.

BLACKSITE is classified as a **Low criticality** system. Its primary function — security compliance management — is important but not time-critical at hourly resolution. Brief outages do not constitute a safety or mission-critical emergency.

---

## 2. System Criticality and Recovery Objectives

| Metric | Value | Rationale |
|---|---|---|
| Maximum Tolerable Downtime (MTD) | 72 hours | Security program work can pause briefly without organizational risk |
| Recovery Time Objective (RTO) | 4 hours | System should be restored within 4 hours of decision to recover |
| Recovery Point Objective (RPO) | 24 hours | Daily backup cycle; up to 24 hours of data entry may need to be re-entered |
| System Availability Target | 95% (measured monthly) | Internal tool; scheduled maintenance windows acceptable |

---

## 3. Key Personnel

| Role | Name | Contact |
|---|---|---|
| ISSO / Recovery Lead | Dan Borisov | daniel@thekramerica.com |
| System Administrator | Dan Borisov | daniel@thekramerica.com |
| Authorizing Official | Dan Borisov | daniel@thekramerica.com |

---

## 4. Backup Strategy

### 4.1 Primary Backup — Nightly to Iapetus NAS

**Script:** `/home/graycat/scripts/backup-all.sh`
**Schedule:** Daily at 03:00 via systemd timer (backup-all.timer)
**Destination:** Iapetus NAS (192.168.86.213) at `clawd/backups/borisov/`
**Method:** SSH/rsync, key authentication, graycat@iapetus
**Scope:** /home/graycat/projects/blacksite/ (includes data/, config.yaml, all application files)
**Retention:** Controlled by Iapetus NAS capacity; minimum 30 days retained

**Backup verification:**
- Backup script logs to systemd journal; check with: `journalctl -u backup-all --since today`
- Spot-check files weekly: `ssh iapetus ls -lh clawd/backups/borisov/`
- Full restore test: conducted annually per this plan's testing schedule

### 4.2 Secondary — Projects Sync to Iapetus

**Script:** `/home/graycat/scripts/sync-projects.sh`
**Schedule:** Every 10 minutes (continuous loop)
**Destination:** `iapetus:clawd/projects/blacksite/`
**Method:** SSH/rsync
**Note:** This is a sync (not versioned backup) — provides near-real-time copy but not point-in-time recovery

### 4.3 Local DB Snapshot (Manual, On-Demand)

For pre-change snapshots before major updates:
```bash
cp /home/graycat/projects/blacksite/data/blacksite.db \
   /home/graycat/docs/blacksite-$(date +%Y%m%d-%H%M%S).db
```

---

## 5. Alternate Processing Site

**Primary site:** borisov (192.168.86.102), port 8100
**Alternate site:** blacksite-co instance (port 8101 on same server) or any other Linux host with Python 3.8+ and the application code restored from backup.

For server-level failures, the alternate site procedure (Section 8.3) describes deploying to a different physical host using backup restoration.

---

## 6. Disruption Scenarios and Impact

| Scenario | Probability | Impact | Recovery Approach |
|---|---|---|---|
| Application crash (bug, OOM) | Medium | Low | systemd auto-restart; manual restart if needed |
| OS / kernel issue | Low | Medium | Reboot server; check logs |
| Database corruption | Very Low | High | Restore from nightly backup |
| Server hardware failure | Very Low | High | Restore to alternate host from backup |
| Network outage (LAN) | Low | Medium | Resolve network issue; app unaffected internally |
| Iapetus NAS unavailable | Low | Low | App continues; backups queue when NAS returns |
| Ransomware / malware | Very Low | Critical | Full restore from verified clean backup |
| Accidental deletion | Low | Medium | Restore specific files from Iapetus backup |

---

## 7. Recovery Procedures

### 7.1 Procedure CP-1: Application Restart (RTO: 5 minutes)

**Use when:** BLACKSITE is unresponsive but OS is healthy.

```bash
# Check service status
sudo systemctl status blacksite

# Restart the service
sudo systemctl restart blacksite

# Verify it's listening
curl -s http://127.0.0.1:8100/health | python3 -m json.tool

# Check logs for errors
journalctl -u blacksite -n 50
```

**Success criteria:** HTTP 200 from /health endpoint; able to log in via browser.

### 7.2 Procedure CP-2: Database Recovery from Backup (RTO: 1 hour)

**Use when:** Database corruption detected or data integrity failure.

```bash
# Stop the service
sudo systemctl stop blacksite

# Preserve the current (possibly corrupt) database
cp /home/graycat/projects/blacksite/data/blacksite.db \
   /home/graycat/docs/blacksite-corrupt-$(date +%Y%m%d).db

# Find most recent backup on Iapetus
ssh iapetus ls -lt clawd/backups/borisov/ | head -20

# Restore the database file
rsync -az iapetus:clawd/backups/borisov/YYYY-MM-DD/home/graycat/projects/blacksite/data/blacksite.db \
      /home/graycat/projects/blacksite/data/blacksite.db

# Verify database opens correctly
BLACKSITE_DB_KEY=<key> /home/graycat/projects/blacksite/.venv/bin/python3 -c "
import asyncio, sys, os
sys.path.insert(0, '/home/graycat/projects/blacksite')
os.environ['BLACKSITE_DB_KEY'] = '<key>'
import yaml
with open('/home/graycat/projects/blacksite/config.yaml') as f:
    config = yaml.safe_load(f)
from app.models import make_engine, make_session_factory
from sqlalchemy import text
async def test():
    engine = make_engine(config)
    sf = make_session_factory(engine)
    async with sf() as s:
        r = await s.execute(text('SELECT COUNT(*) FROM system_controls'))
        print('Controls:', r.scalar())
asyncio.run(test())
"

# Restart service
sudo systemctl start blacksite
```

**Data loss expectation:** Up to 24 hours of data entry (RPO) may need to be re-entered from notes or memory.

### 7.3 Procedure CP-3: Full Application Restore (RTO: 4 hours)

**Use when:** Application files corrupted, venv broken, or after server re-imaging.

```bash
# On the recovery host (or after OS reinstall):

# 1. Restore application files from Iapetus
mkdir -p /home/graycat/projects/
rsync -az iapetus:clawd/backups/borisov/LATEST/home/graycat/projects/blacksite/ \
      /home/graycat/projects/blacksite/

# 2. Recreate the Python virtual environment
cd /home/graycat/projects/blacksite
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Restore systemd service file
sudo cp /home/graycat/projects/blacksite/blacksite.service /etc/systemd/system/
sudo systemctl daemon-reload

# 4. Set environment variable in service file
# Edit /etc/systemd/system/blacksite.service to include:
# Environment=BLACKSITE_DB_KEY=<key-from-secure-storage>

# 5. Start and enable the service
sudo systemctl enable blacksite
sudo systemctl start blacksite

# 6. Verify
curl -s http://127.0.0.1:8100/health
```

### 7.4 Procedure CP-4: Alternate Processing (blacksite-co)

**Use when:** Primary instance (port 8100) must remain offline during investigation but continuity is needed.

```bash
# Ensure blacksite-co is running on port 8101
cd /home/graycat/projects/blacksite-co
nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8101 > /tmp/blacksite-co.log 2>&1 &

# Update Caddyfile to route blacksite.borisov.network to 8101 temporarily
# Edit /home/graycat/.docker/compose/caddy/Caddyfile
# Change: reverse_proxy localhost:8100 → reverse_proxy localhost:8101
# Reload: docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

**Note:** blacksite-co has its own separate database; data entered during failover may need to be migrated back to the primary instance after recovery.

---

## 8. Contingency Plan Testing

### 8.1 Testing Schedule

| Test Type | Frequency | Description |
|---|---|---|
| Tabletop exercise | Annual (March) | Walk through scenarios with key personnel; identify gaps |
| Backup restore test | Annual (September) | Actually restore from Iapetus backup to verify recoverability |
| Application restart test | Quarterly | Verify CP-1 procedure works; check RTO < 5 min |

### 8.2 Test Documentation

Test results are documented in /home/graycat/docs/ with filename format: `cp-test-YYYY-MM-DD.md`. Results include: test scenario, procedure followed, actual RTO/RPO achieved, issues identified, corrective actions taken.

### 8.3 Next Scheduled Tests

- **Tabletop exercise:** 2026-04-08 (within 30 days per POA&M requirement)
- **Backup restore test:** 2026-09-09
- **Quarterly restart test:** 2026-06-09

---

## 9. Plan Maintenance

This CP is reviewed annually or after any significant system change, infrastructure change, or actual contingency event. The ISSO (Dan Borisov) is responsible for maintaining and testing this plan.

**Next review date:** 2027-03-09
**Plan owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, 2026-03-09
"""

DOCS['SAP'] = """# Security Assessment Plan (SAP)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-53A Rev 5
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This Security Assessment Plan (SAP) documents the methodology, scope, schedule, and procedures for conducting a comprehensive security control assessment of the BLACKSITE Security Assessment Platform. The assessment evaluates implementation of NIST SP 800-53 Rev 5 Low baseline controls and produces findings that feed the Security Assessment Report (SAR) and inform ATO decision-making.

**Assessment scope:** All 149 NIST SP 800-53 Rev 5 Low baseline controls applicable to BLACKSITE, including inherited controls (documented as such), not-applicable determinations (with rationale), and all fully or partially implemented controls.

**Assessment basis:** NIST SP 800-53A Rev 5 assessment procedures
**Assessment type:** Initial authorization assessment
**Impact level assessed:** Low

---

## 2. System Overview

| Item | Details |
|---|---|
| System Name | BLACKSITE Security Assessment Platform |
| Owner / ISSO | Dan Borisov (daniel@thekramerica.com) |
| Organization | TheKramerica |
| Hosting | On-premises, borisov (192.168.86.102), Ubuntu 20.04 FIPS |
| Stack | FastAPI/Python 3.8, SQLCipher AES-256, Caddy/TLS, Authelia MFA |
| Impact Level | Low (FIPS 199) |

---

## 3. Assessment Team

| Role | Name | Qualifications |
|---|---|---|
| Lead Assessor (ISSO) | Dan Borisov | System owner; NIST 800-53 expertise; operational knowledge of all system components |

**Independence note:** Dan Borisov serves as both system owner and assessor for this assessment. This arrangement is acceptable for Low-impact systems in small organizations where dedicated independent assessment resources are not available. The use of BLACKSITE's built-in self-assessment tooling (control narratives, automated evidence collection) provides a structured, repeatable framework that partially compensates for the lack of assessor independence. Known gaps and weaknesses are reported candidly in the SAR without minimization.

---

## 4. Assessment Methods

Each control is assessed using one or more of the following methods per NIST SP 800-53A:

| Method | Description | Application |
|---|---|---|
| **Examine** | Review documents, configurations, logs, code | config.yaml, Caddyfile, Authelia config, requirements.txt, systemd unit, application source code, security_events table, this ATO document library |
| **Interview** | Discuss implementation with responsible personnel | Self-interview by ISSO; informal discussion of design intent and operational practice |
| **Test** | Exercise the control mechanism and observe behavior | Login flow testing (MFA verification), access control boundary testing, audit log generation, backup script execution verification, encryption verification |

---

## 5. Assessment Procedures by Control Family

### Access Control (AC)
- **Examine:** RBAC implementation in application code; role assignments in database; Authelia forward-auth configuration
- **Test:** Attempt access to restricted endpoints with insufficient role; verify session timeout behavior; verify MFA enforcement
- **Automated evidence:** BLACKSITE system_controls narratives for AC family

### Audit and Accountability (AU)
- **Examine:** security_events table schema and content; log retention configuration; Caddy access log configuration
- **Test:** Perform security-relevant action; verify event appears in security_events with correct fields; verify logs are encrypted (attempt to read without DB key)

### Configuration Management (CM)
- **Examine:** config.yaml, requirements.txt, git log, systemd service file
- **Test:** Verify pip requirements are pinned; verify config.yaml changes are tracked in git

### Contingency Planning (CP)
- **Examine:** This CP document; backup-all.sh script; systemd timer configuration; Iapetus backup contents
- **Test:** Verify backup-all.timer is active; verify backup files exist on Iapetus NAS (spot check)

### Identification and Authentication (IA)
- **Examine:** Authelia users_database.yml; TOTP configuration; session management code in application
- **Test:** Attempt login without TOTP code; verify lockout after failed attempts; verify session expiration

### Incident Response (IR)
- **Examine:** IRP document (this library); security_events review capability; Wazuh configuration
- **Interview:** ISSO familiarity with IR procedures; awareness of incident categories

### Planning (PL)
- **Examine:** SSP, Rules of Behavior (ROB), FIPS 199 categorization documents in ATO library
- **Interview:** ISSO understanding of system purpose, boundary, and authorization status

### Risk Assessment (RA)
- **Examine:** POA&M system in BLACKSITE; NIST publications table (vulnerability tracking); scan_findings table
- **Test:** Verify NIST catalog updates run nightly (check nist_publications last_updated timestamp)

### System and Communications Protection (SC)
- **Examine:** Caddyfile TLS configuration; SQLCipher encryption setup; network segmentation (UDM Pro firewall rules)
- **Test:** Verify HTTPS enforced (HTTP redirect); verify TLS version minimum; attempt DB read without key

### System and Information Integrity (SI)
- **Examine:** pip audit results; apt security update configuration; application input validation code
- **Test:** Run pip audit; verify no known CVEs in installed packages; test input validation on API endpoints

---

## 6. Assessment Schedule

| Activity | Target Date | Status |
|---|---|---|
| SSP and boundary review | 2026-02-01 | Complete |
| Control inventory and tailoring | 2026-02-15 | Complete |
| Technical assessment (examine/test) | 2026-02-20 — 2026-03-01 | Complete |
| Findings documentation | 2026-03-01 — 2026-03-07 | Complete |
| Draft SAR preparation | 2026-03-07 — 2026-03-09 | Complete |
| SAR review and approval | 2026-03-09 | Complete |
| ATO decision | 2026-03-09 | Complete |

---

## 7. Automated Assessment Tooling

BLACKSITE's self-assessment capability is used throughout the assessment:

1. **Control inventory:** BLACKSITE system_controls table maintains implementation status, narratives, and assessment results for all 149 Low baseline controls
2. **Evidence management:** ATO document library stores all policy documents, plans, and procedures as assessment evidence
3. **POA&M tracking:** BLACKSITE poam_items table captures all findings with severity, responsible party, and milestone dates
4. **NIST publications:** nist_publications table provides current CVE/advisory data for RA-5 assessment
5. **Security events:** security_events table provides live audit trail evidence for AU-family controls

---

## 8. Rules of Engagement

- Assessment activities are limited to the BLACKSITE system boundary
- No intrusive testing (port scanning, fuzzing) against shared infrastructure without explicit scheduling to avoid unintended impact on other homelab services
- All test actions are logged in the security_events audit trail
- Findings are documented candidly; no minimization of weaknesses

---

## 9. Deliverables

| Deliverable | Description | Target Completion |
|---|---|---|
| Security Assessment Report (SAR) | Findings, risk ratings, recommendations | 2026-03-09 |
| Updated POA&M | New/updated POA&M items for all findings | 2026-03-09 |
| Updated system_controls | Assessment results recorded per control | 2026-03-09 |
| ATO Package | SSP + SAP + SAR + POA&M + supporting docs | 2026-03-09 |

**Approval:** Dan Borisov, Lead Assessor and ISSO, 2026-03-09
"""

DOCS['SAR'] = """# Security Assessment Report (SAR)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-53A Rev 5
**Classification:** Unclassified // Internal Use Only

---

## 1. Executive Summary

A comprehensive security assessment of the BLACKSITE Security Assessment Platform was conducted from February through March 2026. The assessment evaluated all 149 applicable NIST SP 800-53 Rev 5 Low baseline controls using examine, interview, and test methods as documented in the Security Assessment Plan (SAP).

**Overall Risk Determination: MODERATE — Acceptable for Authorization**

BLACKSITE is approved for an Authority to Operate (ATO) at the Low impact level. The system implements strong technical controls for its core functions (authentication, encryption, access control, audit logging). Identified weaknesses are primarily administrative and documentation gaps — controls whose technical implementation exists but lacks formal written policy. These gaps are tracked in the POA&M system and are addressable without major remediation effort.

**Assessment Results Summary:**

| Category | Count | Percentage |
|---|---|---|
| Implemented (Pass) | 25 | 17% |
| Partial (Partial) | 78 | 52% |
| Not Implemented (Fail) | 27 | 18% |
| Not Applicable (N/A) | 18 | 12% |
| Inherited | 1 | 1% |
| **Total** | **149** | **100%** |

---

## 2. System Description

| Item | Details |
|---|---|
| System | BLACKSITE Security Assessment Platform |
| Owner / ISSO | Dan Borisov (daniel@thekramerica.com) |
| Organization | TheKramerica |
| Impact Level | Low (FIPS 199) |
| Hosting | borisov (192.168.86.102), Ubuntu 20.04 FIPS, Dell R510 |
| Stack | FastAPI/Python 3.8, SQLCipher AES-256, Caddy TLS, Authelia MFA |
| Assessment Period | 2026-02-01 through 2026-03-09 |
| Assessor | Dan Borisov (ISSO; dual-role assessment acceptable for Low systems) |

---

## 3. Scope and Methodology

All 149 Low baseline controls were assessed. Assessment methods per NIST SP 800-53A:
- **Examine:** SSP, configuration files, source code, audit logs, this document library
- **Interview:** Self-interview by ISSO; design intent and operational practices
- **Test:** Authentication flow, access control enforcement, encryption verification, audit log generation, backup verification

Detailed methodology is documented in the SAP.

---

## 4. Key Findings

### Finding 1 — CRITICAL: Incomplete IR/CP Documentation (HIGH severity)
**Controls affected:** IR-1, IR-2, IR-4, IR-6, IR-7, IR-8, CP-1, CP-2, CP-3, CP-4
**Description:** At the start of assessment, BLACKSITE lacked formal Incident Response and Contingency Planning documentation. While the application has technical capabilities supporting incident detection (security_events table, Authelia logging), no written IRP or CP existed. Without documented procedures, personnel cannot respond consistently to incidents or recover the system predictably.
**Risk:** High — an undocumented response to a real incident increases likelihood of missteps, evidence loss, or extended downtime.
**Remediation:** IRP v1.0 and CP v1.0 have been created and approved as part of this ATO package (2026-03-09). Training and tabletop exercise are planned for 2026-04-08.
**Residual status:** In remediation; documentation complete, procedural validation pending.

### Finding 2 — HIGH: Python 3.8 End-of-Life
**Controls affected:** SI-2 (Flaw Remediation), SA-22 (Unsupported System Components)
**Description:** BLACKSITE runs on Python 3.8, which reached end-of-life in October 2024. No security patches are available for Python 3.8 vulnerabilities discovered after that date. This creates a growing attack surface over the ATO period.
**Risk:** High — unpatched language runtime vulnerabilities could be exploited.
**Remediation plan:** Upgrade to Python 3.11 or 3.12 by 2026-04-08. Requires testing all application dependencies for compatibility.
**Compensating control:** Ubuntu FIPS OS patching continues; network segmentation limits exposure; application input validation reduces exploit surface.

### Finding 3 — HIGH: No Formal Patch Management Process
**Controls affected:** SI-2, CM-3 (Configuration Change Control)
**Description:** Software updates are applied ad hoc by the administrator. No documented patch cadence, no tracking of applied patches, no formal approval process for changes.
**Risk:** Moderate-High — delayed patching increases window of exposure for known vulnerabilities.
**Remediation:** The CMP establishes the patch management framework. A 30/7/48-hour patch SLA based on severity is defined in the VMP. Formal patch tracking via POA&M is in place.

### Finding 4 — MODERATE: No Antivirus / EDR
**Controls affected:** SI-3 (Malicious Code Protection)
**Description:** No antivirus or endpoint detection/response (EDR) solution is installed on the borisov server. Wazuh provides FIM and rootkit detection but is not a full AV solution.
**Risk:** Moderate — malware execution risk present, partially mitigated by Wazuh and network segmentation.
**Remediation plan:** Evaluate ClamAV or similar for server-side scanning. Accepted risk pending evaluation; Wazuh compensates partially.

### Finding 5 — MODERATE: No SIEM / Automated Log Analysis
**Controls affected:** SI-4 (System Monitoring), AU-6 (Audit Record Review)
**Description:** Security events are captured in the BLACKSITE database and Wazuh is deployed, but no automated correlation or alerting for security anomaly patterns is configured.
**Risk:** Moderate — anomalies may go undetected until manual review.
**Compensating control:** Monthly manual review of security_events; Wazuh FIM alerts on file changes.

### Finding 6 — MODERATE: Documentation Gaps for Policy Controls (-1 family)
**Controls affected:** AC-1, AT-1, AU-1, CA-1, CM-1, CP-1, IA-1, IR-1, MA-1, MP-1, PE-1, PL-1, PS-1, RA-1, SA-1, SC-1, SI-1
**Description:** Formal policy documents for each NIST control family were not established prior to assessment. Technical implementations exist for most controls, but the formal policy layer was missing.
**Risk:** Low — the underlying controls work; documentation gap creates audit and accountability risk.
**Remediation:** The Information Security Management Policy (ISMP) v1.0 has been created and approved (2026-03-09), covering all 17 control family policy requirements in a single unified document.

### Finding 7 — LOW: Physical Security Controls Informal
**Controls affected:** PE-1 through PE-16 (Physical and Environmental)
**Description:** BLACKSITE is hosted in a residential environment. Physical security relies on residential door locks and household environmental controls (smoke detectors, HVAC). No formal visitor log, no security guard, no data center-grade physical controls.
**Risk:** Low — system handles Unclassified/Internal data only; residential physical security is appropriate for the data sensitivity.
**Determination:** Accepted risk; physical controls are commensurate with Low impact classification and residential hosting model.

---

## 5. Not-Applicable Controls

The following control categories are not applicable to BLACKSITE and rationale is documented in system_controls:

- **MA-6** (Timely Maintenance): No hardware maintenance contracts needed for residential server
- **PE-4/PE-5** (Access/Output Control for Transmission Media): No physical media transmission
- **SC-15** (Collaborative Computing Devices): No webcams/microphones on server
- **MP-6/MP-7** (Media Sanitization/Use): No removable media used in normal operations
- **IA-8.1** (PKI-based authentication): No PIV/CAC infrastructure
- Additional PE, MA, and MP controls not applicable to single-server residential hosting model

---

## 6. Inherited Controls

- **PE-physical infrastructure** controls are partially inherited from the facility owner (Dan Borisov as property occupant).
- **SC-TLS** — Let's Encrypt certificate authority operations inherited (Caddy manages automatically).

---

## 7. Recommendations

1. **Complete Python upgrade (Priority 1):** Upgrade from Python 3.8 to Python 3.11+ within 30 days. Test all dependencies against new runtime. This closes the highest-risk technical finding.

2. **Conduct IR tabletop exercise (Priority 2):** Execute the Playbook E (credential compromise) scenario from the IRP within 30 days to validate procedures while they are fresh.

3. **Run backup restore test (Priority 3):** Actually restore from an Iapetus NAS backup to a test location to verify the CP procedures work end-to-end. Target by 2026-09-09.

4. **Evaluate ClamAV deployment (Priority 4):** Install and configure ClamAV on-access scanning for /home/graycat/projects/ directories. Low effort, meaningful risk reduction.

5. **Implement Caddy rate limiting formally:** Ensure Caddy rate_limit directive is explicitly configured in Caddyfile for the BLACKSITE vhost.

---

## 8. Overall Risk Determination

BLACKSITE operates with a **Moderate aggregate residual risk** based on findings. However, given that:
- The system impact level is Low (FIPS 199)
- No PII, CUI, or sensitive external data is processed
- The primary risk findings are administrative documentation gaps (now being addressed)
- Technical security controls are substantive and well-implemented (MFA, AES-256 encryption, RBAC, TLS, audit logging)
- All High-severity findings have defined remediation plans with concrete milestones

...the AO has determined that the residual risk is **acceptable** and an ATO with conditions is appropriate. The conditions are documented in the Authorization Decision Document (ADD).

**Assessor Signature:** Dan Borisov, ISSO/Lead Assessor
**Date:** 2026-03-09
"""

DOCS['AUP'] = """# Acceptable Use Policy (AUP)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose

This Acceptable Use Policy (AUP) establishes the rules and obligations governing access to and use of the BLACKSITE Security Assessment Platform. All users must read, understand, and comply with this policy as a condition of access. Violation of this policy may result in immediate account suspension, removal of access privileges, and other disciplinary action as appropriate.

---

## 2. Scope

This policy applies to all individuals who have been granted access to BLACKSITE, including administrators, ISSOs, ISSMs, CISOs, Authorizing Officials, Security Control Assessors, auditors, and managers operating under TheKramerica's cybersecurity program.

---

## 3. Authorized Use

BLACKSITE is an internal security compliance management tool. Authorized uses include:
- Reviewing, updating, and managing NIST SP 800-53 control implementation records
- Conducting and documenting security control assessments
- Managing Plans of Action and Milestones (POA&Ms)
- Creating, reviewing, and approving ATO documentation
- Accessing security event logs for audit and investigation purposes
- Generating reports and export packages for authorization decisions
- Using the AI assistant capability to draft control narratives (content must be reviewed and verified by the user)

All use of BLACKSITE must be in furtherance of legitimate, authorized security program activities for TheKramerica systems.

---

## 4. Prohibited Activities

Users are prohibited from:

1. **Unauthorized access:** Accessing BLACKSITE with credentials other than your own assigned account. Sharing passwords, session tokens, or MFA codes with any other person for any reason.

2. **Privilege abuse:** Attempting to access system functions, data, or endpoints beyond what is permitted by your assigned role. Attempting to escalate privileges by exploiting application bugs or misconfigurations.

3. **Data misuse:** Exporting, copying, or transmitting BLACKSITE data (control narratives, assessment findings, system architecture details, security event logs) outside of authorized channels or for unauthorized purposes.

4. **Unauthorized software or configuration changes:** Installing software, modifying configuration files, or altering the application environment without authorization from the system administrator (Dan Borisov).

5. **Testing attacks:** Performing penetration testing, fuzzing, SQL injection testing, or any other adversarial testing against BLACKSITE without explicit written approval from the system owner. Authorized assessment activities are defined in the SAP.

6. **Circumventing security controls:** Attempting to bypass MFA, disable audit logging, modify security_events records, or otherwise circumvent any security mechanism of the platform.

7. **Personal use:** Using BLACKSITE for personal projects, data storage, or any purpose unrelated to TheKramerica's security program.

8. **Introducing false data:** Entering false control implementation narratives, fabricated assessment results, or misleading POA&M information. BLACKSITE is an authoritative record; accuracy is essential.

9. **Unauthorized disclosure:** Sharing information from BLACKSITE (system vulnerabilities, unresolved POA&M details, security event data) with parties outside TheKramerica without explicit authorization.

---

## 5. User Obligations

All BLACKSITE users must:

1. **Protect credentials:** Maintain the confidentiality of your username, password, and TOTP secret. Use a strong, unique password (minimum 16 characters). Never write credentials in insecure locations.

2. **Enroll in MFA:** Maintain active TOTP enrollment. If your MFA device is lost, immediately report to the ISSO (Dan Borisov at daniel@thekramerica.com) to reset enrollment.

3. **Report security incidents:** Immediately report any suspected unauthorized access, data breach, unexpected system behavior, or loss/theft of authentication credentials to the ISSO (daniel@thekramerica.com). Do not wait to confirm before reporting; timely reporting is critical.

4. **Log out properly:** Log out of active sessions when done, especially on shared or portable devices. Do not leave authenticated BLACKSITE sessions unattended.

5. **Comply with data classification:** Treat all BLACKSITE content as Unclassified // Internal Use Only. Do not store or process information in BLACKSITE that requires a higher classification level.

6. **Keep access current:** Notify the administrator immediately if your role changes, you leave the organization, or you no longer require access. Access should be revoked promptly when no longer needed.

7. **Verify AI-generated content:** When using the BLACKSITE AI assistant for control narrative drafting, independently verify all generated content for accuracy before saving. AI output is a drafting aid, not an authoritative source.

---

## 6. Monitoring and Privacy Notice

BLACKSITE logs all security-relevant user actions in the security_events table, including login events, access to sensitive resources, data exports, and configuration changes. These logs are reviewed by the ISSO as part of the continuous monitoring program.

By using BLACKSITE, you acknowledge and consent to this monitoring. There is no expectation of privacy for actions taken within BLACKSITE. Audit logs may be reviewed in the course of security investigations, routine audits, or compliance activities.

---

## 7. Consequences of Violation

Violations of this AUP may result in:
- Immediate suspension of BLACKSITE account pending investigation
- Permanent revocation of access privileges
- Escalation to organizational management or legal counsel if warranted
- Reporting to law enforcement if criminal activity is suspected

The severity of consequences will be proportionate to the nature and intent of the violation.

---

## 8. Acknowledgment

All users are required to acknowledge this AUP upon initial account creation and annually thereafter. Acknowledgment is recorded in the BLACKSITE user account management system.

**Policy Owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, TheKramerica
**Date:** 2026-03-09
**Next Review:** 2027-03-09
"""

DOCS['CMP'] = """# Configuration Management Plan (CMP)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-53 Rev 5 CM family
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This Configuration Management Plan (CMP) establishes the policies, procedures, and responsibilities for managing the configuration of the BLACKSITE Security Assessment Platform throughout its lifecycle. Configuration management ensures that changes to BLACKSITE are controlled, documented, and authorized, maintaining the integrity and security of the system.

This plan applies to all configuration items (CIs) within the BLACKSITE authorization boundary.

---

## 2. Configuration Baseline

The BLACKSITE configuration baseline consists of the following items, all tracked in the git repository at /home/graycat/projects/blacksite/:

| Configuration Item | Location | Description |
|---|---|---|
| Application source code | app/ | FastAPI application, routes, models, utilities |
| Application configuration | config.yaml | Database path, session settings, feature flags, integration URLs |
| Python dependencies | requirements.txt | All dependencies with pinned versions |
| Systemd service unit | blacksite.service | Process management, environment variables, restart policy |
| Alembic migrations | alembic/ | Database schema version history |
| Caddyfile vhost | caddy/Caddyfile (in compose repo) | Reverse proxy and TLS configuration for BLACKSITE vhost |
| Authelia user database | authelia/users_database.yml | User accounts and TOTP enrollment |
| Environment secrets | /etc/systemd/system/blacksite.service (Environment= lines) | DB key, session key (not in git; managed separately per KMP) |

**Baseline establishment:** The initial baseline was established at the first production deployment. All subsequent changes must follow the change control process defined in Section 4.

---

## 3. Configuration Item Identification

Configuration items are identified by:
- **Source code:** git commit SHA (full 40-character hash), branch (main), tag for releases
- **Dependencies:** requirements.txt version pin (e.g., `fastapi==0.100.1`)
- **OS packages:** apt package name and version (tracked via `dpkg -l` snapshot)
- **Database schema:** Alembic revision ID

---

## 4. Change Control Process

### 4.1 Change Categories

| Category | Description | Examples | Approval Required |
|---|---|---|---|
| **Routine** | Minor updates, bug fixes, documentation, dependency security updates | Fix typo in template, update pip package for CVE patch | ISSO self-approval |
| **Standard** | Feature additions, configuration changes, new integrations | Add new API endpoint, change session timeout, add new control family | ISSO review and documented approval |
| **Emergency** | Security patches requiring immediate deployment | Critical CVE with active exploitation, active incident response | Deploy immediately, document within 24 hours |
| **Major** | Architectural changes, database schema changes, new external services | Database migration, new external API integration | AO notification required |

### 4.2 Change Control Procedure

**For Routine and Standard changes:**

1. **Identify change:** Document what is changing, why, and expected impact
2. **Development:** Make change in development/test environment first (blacksite-co instance or local branch)
3. **Testing:** Verify change works as expected; confirm no security regressions
4. **Impact analysis:** Brief assessment of whether the change affects security controls or the authorization boundary
5. **Documentation:** Commit to git with descriptive commit message including: what changed, why, ticket/issue reference if applicable
6. **Production deployment:** Apply change to production instance
7. **Verification:** Confirm system functions correctly post-change; check security_events for anomalies
8. **Record:** ISSO notes the change in the system security documentation if it affects control implementation status

**Git commit message format:**
```
[CM] Brief description of change

Longer description of what changed and why.
Impact: [None / Low / Medium] security impact
Controls affected: [list control IDs if applicable]
Approved by: Dan Borisov (ISSO)
```

**For Emergency changes:**
1. Deploy immediately to contain the security risk
2. Document the change in git within 24 hours of deployment
3. Review impact and update POA&M if new issues introduced
4. Notify AO if the change is significant

### 4.3 Prohibited Changes

The following changes require explicit AO approval and cannot be self-approved by the ISSO:
- Changes to the authorization boundary (adding new systems, services, or data types)
- Changes to the database encryption key
- Changes that would disable security audit logging
- Changes that would remove MFA requirement for any user role

---

## 5. SDLC Integration

BLACKSITE development follows an informal but structured SDLC (satisfying SA-3):

| Phase | Activities |
|---|---|
| **Planning** | Define feature or fix; assess security impact; identify affected controls |
| **Development** | Code on main branch or feature branch; inline security review |
| **Testing** | Manual functional testing; security_events log review; pip audit run |
| **Deployment** | systemctl restart blacksite; health check verification |
| **Post-deployment** | Monitor security_events for 24 hours; update system_controls if implementation status changed |

Code review: Given single-person development team, self-review is conducted with deliberate focus on: input validation, authorization checks, SQL parameterization, and audit log generation for new functionality.

---

## 6. Dependency Management

Python dependencies are managed as follows:

1. **Version pinning:** All packages in requirements.txt are pinned to specific versions
2. **Security updates:** pip audit is run monthly (per VMP) to identify vulnerable dependencies
3. **Upgrade process:** Before upgrading any dependency: (a) review changelog for breaking changes, (b) test in blacksite-co first, (c) apply standard change process, (d) commit updated requirements.txt
4. **New dependencies:** Any new package addition follows Standard change process; justification documented in commit message
5. **OS packages:** apt security updates applied per VMP patch cadence (Critical=48h, High=7d, etc.)

---

## 7. Configuration Verification

Monthly configuration verification (part of continuous monitoring):
- Run `git status` to confirm no uncommitted changes in production
- Run `git diff HEAD` to verify working directory matches committed baseline
- Verify systemd service environment variables match expected values (without exposing secrets)
- Confirm pip packages match requirements.txt: `.venv/bin/pip list --format=freeze`

---

## 8. Roles and Responsibilities

| Role | Responsibility |
|---|---|
| ISSO (Dan Borisov) | Approve all changes, conduct impact analysis, maintain CMP |
| Administrator (Dan Borisov) | Implement approved changes, perform testing, execute deployments |
| AO (Dan Borisov) | Approve major/boundary changes; receive notification of significant changes |

---

## 9. Plan Maintenance

This CMP is reviewed annually and updated when the SDLC process, technology stack, or change control procedures materially change.

**Plan Owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, 2026-03-09
**Next Review:** 2027-03-09
"""

DOCS['VMP'] = """# Vulnerability Management Procedures (VMP)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This document establishes procedures for identifying, evaluating, prioritizing, and remediating vulnerabilities in the BLACKSITE Security Assessment Platform. These procedures satisfy NIST SP 800-53 Rev 5 controls RA-5 (Vulnerability Monitoring and Scanning), SI-2 (Flaw Remediation), and SI-5 (Security Alerts, Advisories, and Directives).

Scope: All software components within the BLACKSITE authorization boundary — application code, Python dependencies, OS packages, and supporting infrastructure (Caddy, Authelia).

---

## 2. Vulnerability Sources

| Source | Frequency | Description | Integration |
|---|---|---|---|
| **NIST NVD / CVE** | Nightly | NIST publishes CVEs via OSCAL/GitHub API; BLACKSITE nightly cron updates nist_publications table | Automated via built-in catalog sync |
| **pip audit** | Monthly | Scans installed Python packages against PyPI advisory database for known CVEs | Manual execution; results reviewed by ISSO |
| **apt security notices** | Weekly | Ubuntu security team publishes USNs for OS package vulnerabilities | Manual apt-get update && apt list --upgradable review |
| **GitHub security advisories** | As published | BLACKSITE dependencies tracked; GitHub advisories may be checked manually | Manual review |
| **CISA KEV** | Monthly | CISA Known Exploited Vulnerabilities catalog reviewed for any overlapping components | Manual review |
| **Wazuh vulnerability detection** | Continuous | Wazuh agent on borisov performs vulnerability scanning of installed packages | Automated alerts |

---

## 3. Severity Classification and Response Times

Vulnerabilities are classified using CVSS v3.1 Base Score and must be remediated within the following timeframes from discovery:

| Severity | CVSS Score | Response Time | Action |
|---|---|---|---|
| **Critical** | 9.0 – 10.0 | 48 hours | Emergency patch; deploy immediately; notify AO |
| **High** | 7.0 – 8.9 | 7 days | Priority patch; follow Emergency change process if needed |
| **Moderate** | 4.0 – 6.9 | 30 days | Standard change process; update requirements.txt / apply apt patch |
| **Low** | 0.1 – 3.9 | 90 days | Routine change; patch in next scheduled maintenance window |
| **Informational** | N/A | Next review cycle | Document and monitor |

**Exceptions:** If a patch is unavailable (e.g., Python 3.8 EOL), create a POA&M item with: severity rating, compensating controls documented, target date for remediation (upgrade/replacement), and AO acknowledgment.

---

## 4. Vulnerability Scanning Procedures

### 4.1 Python Dependency Scan (Monthly)

```bash
cd /home/graycat/projects/blacksite
.venv/bin/pip audit

# Review output for any CVEs
# For each finding:
# 1. Look up CVE details on nvd.nist.gov
# 2. Assess severity and exploitability in BLACKSITE context
# 3. Create POA&M item if not patchable immediately
# 4. Update requirements.txt and test if patch available
```

Expected output format: package name, affected version, CVE ID, description.

### 4.2 OS Package Security Updates (Weekly)

```bash
sudo apt-get update
apt list --upgradable 2>/dev/null | grep -i security

# Review security-tagged packages
# Apply updates per severity SLA:
sudo apt-get upgrade -y  # for routine security updates
# Test application still functions after update
sudo systemctl restart blacksite
curl -s http://127.0.0.1:8100/health
```

### 4.3 NIST Publications Review (Monthly)

BLACKSITE's nist_publications table is updated nightly. Monthly review:
1. Navigate to BLACKSITE Security Events or NIST Publications section
2. Filter advisories from last 30 days
3. Cross-reference against installed components
4. Create POA&M items for applicable advisories requiring action

### 4.4 CISA KEV Review (Monthly)

Access CISA KEV catalog at cisa.gov/known-exploited-vulnerabilities-catalog.
Search for any of the following components: Python, FastAPI, SQLite, Caddy, Authelia, Ubuntu, Dell iDRAC (server firmware).
Document any matches and assess applicability.

---

## 5. Remediation Tracking

All identified vulnerabilities that cannot be patched within the defined SLA windows are tracked as POA&M items in BLACKSITE with:
- **weakness_name:** CVE ID and brief description
- **severity:** Based on CVSS score (Critical/High/Moderate/Low)
- **remediation_plan:** Specific patching steps or upgrade path
- **scheduled_completion:** Date within SLA window
- **responsible_party:** Dan Borisov (ISSO/admin)
- **resources_required:** Time estimate; any external dependencies

POA&M items are reviewed monthly and at every continuous monitoring cycle.

---

## 6. Security Advisory Monitoring (SI-5)

BLACKSITE satisfies SI-5 through:

1. **Automated NIST catalog sync:** nightly cron job fetches latest NIST OSCAL data including recent publications, which includes references to new CVEs and advisories
2. **nist_publications table:** Stores and displays advisories within the BLACKSITE UI for ISSO review
3. **Manual subscription:** ISSO subscribes to Ubuntu Security Notices (USN) mailing list; pip advisory RSS/Atom feed
4. **Python security list:** Monitor python.org security announcements for Python runtime vulnerabilities

When a critical advisory is received:
1. Assess applicability immediately
2. If applicable and Critical severity: initiate Emergency change process within 24 hours
3. Document the advisory review and action taken in the ISSO journal (/home/graycat/docs/)

---

## 7. Software License and Open Source Compliance (CM-10)

All BLACKSITE dependencies are open-source with permissive licenses (MIT, Apache 2.0, BSD). License compliance:
- requirements.txt lists all dependencies; licenses are documented per package
- No GPL-licensed packages are included that would impose copyleft obligations on internal/proprietary code
- License review is conducted when adding new dependencies

---

## 8. Current Known Vulnerabilities (as of 2026-03-09)

| Component | Issue | CVE/Ref | Severity | Status | POA&M |
|---|---|---|---|---|---|
| Python 3.8 | End-of-life; no security patches after 2024-10-07 | N/A (EOL) | High | In remediation; upgrade planned by 2026-04-08 | si-2, sa-22 |
| No AV/EDR | No malicious code protection beyond Wazuh FIM | SI-3 gap | Moderate | Open; ClamAV evaluation pending | si-3 |

---

## 9. Roles and Responsibilities

| Role | Responsibility |
|---|---|
| ISSO (Dan Borisov) | Own and execute VMP; review scan results; create POA&Ms; approve patches |
| Administrator (Dan Borisov) | Apply patches; run scans; update requirements.txt |
| AO (Dan Borisov) | Receive notification of Critical vulnerabilities; accept risk for items that cannot be patched within SLA |

---

## 10. Plan Maintenance

This VMP is reviewed annually and updated when the technology stack changes significantly.

**Plan Owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, 2026-03-09
**Next Review:** 2027-03-09
"""

DOCS['FIPS199'] = """# FIPS 199 Security Categorization
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Regulation:** FIPS Publication 199, Standards for Security Categorization of Federal Information and Information Systems
**Classification:** Unclassified // Internal Use Only

---

## 1. System Identification

| Item | Value |
|---|---|
| System Name | BLACKSITE Security Assessment Platform |
| System Abbreviation | BLACKSITE |
| System Owner | Dan Borisov, TheKramerica |
| ISSO | Dan Borisov (daniel@thekramerica.com) |
| System Type | Major Application — Internal Security Management Tool |
| Operating Environment | On-premises, residential data center (borisov server, 192.168.86.102) |
| Date of Categorization | 2026-03-09 |

---

## 2. Information Types Processed

BLACKSITE processes the following categories of information:

| Information Type | Description |
|---|---|
| Security control implementation data | Narratives describing how security controls are implemented in TheKramerica systems |
| Assessment findings | Results of security control assessments; findings and weaknesses identified |
| Plan of Action & Milestones (POA&M) data | Weakness descriptions, remediation plans, milestone dates, responsible parties |
| ATO documentation | System Security Plans, Contingency Plans, IRP, and other authorization documents |
| Security event logs | Audit trail of user actions within BLACKSITE; authentication events, access logs |
| User account data | Internal usernames, role assignments, authentication metadata (hashed passwords, TOTP) |
| System architecture data | Technology stack details, network topology, interconnection information for TheKramerica systems |

**Data NOT processed by BLACKSITE:**
- No Personally Identifiable Information (PII)
- No Protected Health Information (PHI)
- No financial records
- No Controlled Unclassified Information (CUI)
- No classified national security information
- No external customer data of any kind

---

## 3. Security Categorization

### 3.1 Confidentiality

**Potential Impact if confidentiality is compromised:** LOW

**Rationale:** BLACKSITE contains internal security program documentation and system architecture details for TheKramerica's homelab infrastructure. This information is not sensitive beyond the internal use level. Exposure of this data could give an adversary insight into TheKramerica's security posture and vulnerabilities, which is a concern, but the systems described are personal homelab systems with no external customer data, no financial systems, and no safety-critical systems. The harm from confidentiality breach would be limited to potential facilitation of attacks against the homelab infrastructure. This constitutes a limited adverse effect — meeting the Low threshold.

**FIPS 199 determination:** CONFIDENTIALITY = **LOW**

### 3.2 Integrity

**Potential Impact if integrity is compromised:** LOW

**Rationale:** If BLACKSITE data integrity is compromised (e.g., falsified control assessments, modified POA&M records), the harm would be incorrect security decision-making for TheKramerica systems. For a Low-impact homelab system, incorrect security assessments could delay remediation of real vulnerabilities. However, the systems managed are personal infrastructure with no safety-critical functions, no financial transactions, and no external dependencies. The adverse effect of integrity loss is limited — meeting the Low threshold.

**FIPS 199 determination:** INTEGRITY = **LOW**

### 3.3 Availability

**Potential Impact if availability is compromised:** LOW

**Rationale:** BLACKSITE is a security management tool used by a single-person security team on a flexible schedule. Extended outages (hours to days) would delay security program work but would not disrupt any operational services, safety functions, or external obligations. Security control data can be accessed from backups; work can continue manually during BLACKSITE downtime. The adverse effect of availability loss is limited — meeting the Low threshold.

**FIPS 199 determination:** AVAILABILITY = **LOW**

---

## 4. Overall Security Categorization

Following FIPS 199 Section 3 (high-water mark principle):

**SC BLACKSITE = {(confidentiality, LOW), (integrity, LOW), (availability, LOW)}**

**Overall Impact Level: LOW**

---

## 5. Applicable Baseline

Based on the Low impact categorization, BLACKSITE implements the **NIST SP 800-53 Rev 5 Low baseline** (149 controls, after tailoring for system-specific not-applicable determinations).

---

## 6. Privacy Impact Assessment Determination

BLACKSITE does not collect, process, store, or transmit any Personally Identifiable Information (PII) as defined by OMB Memorandum M-07-16 or the Privacy Act of 1974. The user account data consists of internal system usernames only — not tied to real-world identifiers, Social Security Numbers, addresses, financial information, or any other PII categories.

**Privacy Act Applicability:** NOT APPLICABLE
**PIA Required:** NO
**SORN Required:** NO

This determination is documented in the Privacy Threshold Analysis (PTA) in the ATO document library.

---

## 7. Categorization Approval

This security categorization has been reviewed and approved by the system owner and Authorizing Official.

**System Owner/ISSO:** Dan Borisov
**Authorizing Official:** Dan Borisov
**Organization:** TheKramerica
**Contact:** daniel@thekramerica.com
**Approval Date:** 2026-03-09
**Next Review:** 2027-03-09 (or upon significant change to system or data types processed)
"""

DOCS['ADD'] = """# Authorization Decision Document (ADD)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Classification:** Unclassified // Internal Use Only

---

## 1. Authorization Decision

**AUTHORITY TO OPERATE (ATO) GRANTED**

By authority of the Authorizing Official (AO) for TheKramerica, the BLACKSITE Security Assessment Platform is hereby granted an Authority to Operate (ATO) effective **2026-03-09**, valid for a period of **three (3) years**, expiring **2029-03-09**, subject to the conditions listed in Section 5.

---

## 2. System Identification

| Item | Value |
|---|---|
| System Name | BLACKSITE Security Assessment Platform |
| System ID | bsv-main-00000000-0000-0000-0000-000000000001 |
| System Owner | Dan Borisov |
| ISSO | Dan Borisov (daniel@thekramerica.com) |
| Organization | TheKramerica |
| Hosting | borisov (192.168.86.102), Ubuntu 20.04 FIPS, Dell PowerEdge R510 |
| Impact Level | Low (FIPS 199 categorization dated 2026-03-09) |
| Security Baseline | NIST SP 800-53 Rev 5, Low Baseline |

---

## 3. Authorization Package

The following documents comprised the authorization package reviewed by the AO:

| Document | Version | Date | Status |
|---|---|---|---|
| System Security Plan (SSP) | 1.0 | 2026-03-09 | Approved |
| FIPS 199 Security Categorization | 1.0 | 2026-03-09 | Approved |
| Privacy Threshold Analysis (PTA) | 1.0 | 2026-03-09 | Approved |
| Security Assessment Plan (SAP) | 1.0 | 2026-03-09 | Approved |
| Security Assessment Report (SAR) | 1.0 | 2026-03-09 | Approved |
| Plan of Action & Milestones (POA&M) | 1.0 | 2026-03-09 | Approved |
| Incident Response Plan (IRP) | 1.0 | 2026-03-09 | Approved |
| Contingency Plan (CP) | 1.0 | 2026-03-09 | Approved |
| Information Security Management Policy (ISMP) | 1.0 | 2026-03-09 | Approved |
| Acceptable Use Policy (AUP) | 1.0 | 2026-03-09 | Approved |
| Configuration Management Plan (CMP) | 1.0 | 2026-03-09 | Approved |
| Vulnerability Management Procedures (VMP) | 1.0 | 2026-03-09 | Approved |
| Key Management Plan (KMP) | 1.0 | 2026-03-09 | Approved |
| Rules of Behavior (ROB) | 1.0 | 2026-03-09 | Approved |
| Supply Chain Risk Management Plan (SCRM) | 1.0 | 2026-03-09 | Approved |
| Continuous Monitoring Plan (CONMON) | 1.0 | 2026-03-09 | Approved |
| External Service Agreements (EXT-SA) | 1.0 | 2026-03-09 | Approved |

---

## 4. Risk Determination

The AO reviewed the Security Assessment Report (SAR) findings and the complete POA&M. Key risk considerations:

**Strengths identified:**
- Strong authentication: Authelia MFA with TOTP enforced for all users
- Encryption at rest: SQLCipher AES-256 for all sensitive data
- Encryption in transit: TLS 1.2+ enforced by Caddy for all connections
- Role-based access control: Granular RBAC with seven distinct roles
- Audit logging: Comprehensive security_events table with tamper-evident encrypted storage
- Network protection: UniFi firewall/NAT, VLAN segmentation
- Operational backup: Nightly backup to Iapetus NAS with systemd timer

**Residual risks accepted:**
- Python 3.8 EOL (High): Upgrade planned by 2026-04-08; compensated by network segmentation and input validation
- Documentation gaps for policy controls (Moderate): Comprehensive policy library created 2026-03-09; training pending
- No AV/EDR (Moderate): Partially mitigated by Wazuh FIM; ClamAV evaluation planned
- No SIEM (Moderate): Partially mitigated by monthly manual security_events review; Wazuh continuous monitoring
- Informal physical security (Low): Commensurate with Low impact level and residential hosting model

**Overall residual risk: MODERATE — Acceptable for Low-impact system**

The AO determines that the residual risk is acceptable given the system's Low impact level, limited data sensitivity (no PII/PHI/CUI), small user base (single-person operation), and strong technical controls already in place. The identified administrative gaps are being remediated through this ATO package and the associated POA&M.

---

## 5. Conditions of Authorization

This ATO is granted subject to the following conditions:

**Condition 1 (30 days — by 2026-04-08):**
Complete Python 3.8 to Python 3.11+ upgrade. Validate all dependencies for compatibility. Update requirements.txt. Close POA&M items si-2 and sa-22 upon completion.

**Condition 2 (30 days — by 2026-04-08):**
Conduct IR tabletop exercise using IRP Playbook E (credential compromise scenario). Document results. Close POA&M items ir-4, ir-8 upon successful exercise completion.

**Condition 3 (30 days — by 2026-04-08):**
Conduct CP tabletop exercise and initiate backup restore test. Close POA&M items cp-3, cp-4 upon completion.

**Condition 4 (Ongoing):**
Maintain continuous monitoring activities per the CONMON plan. Submit annual status report to AO by 2027-03-09.

**Condition 5 (Ongoing):**
Any significant change to the system boundary, technology stack, or data types processed requires notification to the AO and may require re-authorization review.

**Condition 6 (90 days — by 2026-06-07):**
Close or formally accept risk for all 33 Moderate-severity open POA&M items.

---

## 6. Authorization Timeline

| Milestone | Date |
|---|---|
| ATO effective date | 2026-03-09 |
| 30-day condition deadline (Python, IR/CP exercises) | 2026-04-08 |
| 90-day condition deadline (Moderate POA&Ms) | 2026-06-07 |
| Annual review | 2027-03-09 |
| ATO expiration | 2029-03-09 |

---

## 7. Authorizing Official Signature

This Authorization Decision Document is approved and signed by:

**Dan Borisov**
Authorizing Official (AO)
Information System Security Officer (ISSO)
TheKramerica
daniel@thekramerica.com

**Date:** 2026-03-09
**ATO Valid Through:** 2029-03-09
"""

DOCS['PTA'] = """# Privacy Threshold Analysis (PTA)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose

This Privacy Threshold Analysis (PTA) determines whether BLACKSITE collects, processes, stores, or transmits Personally Identifiable Information (PII) and whether a Privacy Impact Assessment (PIA) or System of Records Notice (SORN) is required under the Privacy Act of 1974 or OMB guidance.

---

## 2. System Overview

BLACKSITE is an internal security compliance management platform operated by TheKramerica. It tracks NIST SP 800-53 security controls, manages POA&M items, stores ATO documentation, and logs security events for audit purposes. It is used exclusively by Dan Borisov as part of TheKramerica's information security program.

---

## 3. PII Assessment

### 3.1 What information does BLACKSITE collect?

BLACKSITE collects and stores:

| Data Type | Description | PII? |
|---|---|---|
| Internal usernames | System-assigned or user-chosen identifiers (e.g., "dborisov", "admin") for BLACKSITE login | No — usernames are internal system identifiers not linked to government records |
| Hashed passwords | bcrypt-hashed authentication credentials | No — hashed credentials are not PII |
| TOTP secrets | Encrypted TOTP enrollment secrets for MFA | No — authentication metadata, not biographical PII |
| Role assignments | Access control roles (admin, isso, auditor, etc.) | No — system authorization data |
| Security event logs | Actions taken within BLACKSITE: login timestamp, IP address, action type | Borderline — IP addresses may be considered PII in some frameworks |
| Control narratives | Text descriptions of security control implementations | No — system documentation |
| Assessment findings | Technical findings from security assessments | No — system security data |
| POA&M records | Weakness descriptions, remediation plans, milestones | No — security management data |
| ATO documents | SSP, IRP, CP, policy documents | No — governance documentation |

### 3.2 IP Address Assessment

BLACKSITE logs source IP addresses in security_events for audit trail purposes. In the context of this system:
- All users are within the TheKramerica LAN (192.168.86.0/24) or connecting via VPN
- IP addresses are internal RFC 1918 addresses (192.168.x.x)
- There are no external users whose IP addresses are logged
- No external customer or public user data is collected

Internal IP addresses associated with a single-person organization's administrator accounts do not rise to the level of PII requiring Privacy Act protections.

---

## 4. Privacy Act Applicability

**Question 1: Is BLACKSITE operated by a Federal agency?**
No. BLACKSITE is operated by TheKramerica, a private organization.

**Question 2: Does BLACKSITE maintain a system of records on individuals?**
No. The user accounts in BLACKSITE are internal system accounts for security personnel only. There is no collection of records on members of the public or external individuals.

**Question 3: Does BLACKSITE collect PII as defined by OMB M-07-16?**
No. BLACKSITE does not collect name, Social Security Number, date of birth, address, financial information, health information, biometric data, or any other PII category.

**Privacy Act Applicability: NOT APPLICABLE**

---

## 5. PIA and SORN Determination

| Requirement | Determination | Basis |
|---|---|---|
| Privacy Impact Assessment (PIA) | **NOT REQUIRED** | No PII collected; not a federal system |
| System of Records Notice (SORN) | **NOT REQUIRED** | Not a federal system; no Privacy Act records |
| Privacy Act compliance | **NOT APPLICABLE** | Private organization; no PII |

---

## 6. Future Considerations

If BLACKSITE is ever modified to:
- Collect PII (names, SSNs, addresses, etc.) for any purpose
- Process records about external individuals (customers, contractors, members of the public)
- Interface with government systems subject to the Privacy Act

...a new PTA must be conducted and a PIA may be required before such changes are implemented.

---

## 7. Approval

**Reviewed by:** Dan Borisov, ISSO
**Approved by:** Dan Borisov, AO
**Organization:** TheKramerica
**Date:** 2026-03-09
**Next Review:** 2027-03-09 or upon system change affecting data collection
"""

DOCS['POAM'] = """# Plan of Action & Milestones — Executive Summary
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose

This document provides the executive summary and management overview of the BLACKSITE Plan of Action and Milestones (POA&M) program. Detailed POA&M item data — individual weakness records, remediation plans, milestone dates, and evidence — are maintained in the BLACKSITE database (poam_items table) and managed through the BLACKSITE POA&M management interface. This document summarizes the overall posture and priority order for leadership review.

---

## 2. POA&M Program Overview

The BLACKSITE POA&M program tracks all identified security weaknesses from the Security Assessment Report (SAR), continuous monitoring activities, and self-identified findings. Each item includes: control ID, weakness description, severity, responsible party, remediation plan, scheduled completion date, and closure evidence.

**POA&M data is the authoritative source** for weakness tracking. This document is the executive summary only.

---

## 3. Current POA&M Status (as of 2026-03-09)

| Status | Count | Description |
|---|---|---|
| Open | ~95 | Active weaknesses requiring remediation |
| In Remediation | ~15 | Remediation plan in place; actively being worked |
| Closed (Verified) | ~20+ | Weakness resolved; closure evidence documented |
| Accepted Risk | 1 | Risk formally accepted by AO; no further remediation planned |
| **Total** | **~130+** | Includes all items from initial assessment |

---

## 4. Severity Distribution

| Severity | Open Count | In Remediation | Notes |
|---|---|---|---|
| High | 12 | 6 | IR/CP documentation (now complete), Python 3.8 EOL, patch management |
| Moderate | 33 | 5 | Policy gaps, SIEM, AV, supply chain |
| Low | 66 | 4 | Physical security, personnel policy, minor procedure gaps |

---

## 5. Priority Remediation Order

### Priority 1 — High Severity (Address within 30 days per ADD Condition)

1. **Python 3.8 EOL (si-2, sa-22):** Upgrade to Python 3.11+. Target: 2026-04-08.
2. **IR tabletop exercise (ir-4, ir-8):** IRP created; exercise required to validate. Target: 2026-04-08.
3. **CP tabletop exercise (cp-3, cp-4):** CP created; exercise required to validate. Target: 2026-04-08.
4. **Formal AO signature process (ca-6):** ADD signed; any remaining procedural formalization. Target: 2026-03-31.

### Priority 2 — Moderate Severity (Address within 90 days per ADD Condition)

5. **No AV/EDR (si-3):** Evaluate and deploy ClamAV. Target: 2026-05-09.
6. **Automated log alerting (au-6, si-4):** Configure Wazuh alerts for BLACKSITE-specific patterns. Target: 2026-05-09.
7. **Formal patch management documentation:** VMP created; implement tracking mechanism. Target: 2026-04-30.
8. **Change impact analysis process (cm-4):** CMP created; formalize impact analysis checklist. Target: 2026-04-30.
9. **Vulnerability scanning automation (ra-5, ra-5.2):** Script pip audit to run monthly with output logged. Target: 2026-05-09.

### Priority 3 — Low Severity (Address within 180 days or accept risk)

10. All -1 policy control POA&Ms: **CLOSED** — covered by ISMP v1.0.
11. Physical security controls (pe-*): Document current residential controls; accept residual risk for Low-impact system.
12. Personnel security policies (ps-*): Draft brief HR/personnel procedures appropriate for single-person operation.
13. Maintenance procedures (ma-*): Document informal maintenance practices.

---

## 6. Recently Closed POA&M Items (as of 2026-03-09)

The following items were closed as part of the ATO package preparation:

| Control | Weakness | Closure Method |
|---|---|---|
| ac-1 through si-1 (17 -1 controls) | Policy documents missing | ISMP v1.0 created and approved |
| pl-4 | No rules of behavior | ROB v1.0 created and approved |
| sc-12 | No key management plan | KMP v1.0 created and approved |
| sr-1, sr-2, sr-2.1, sr-3 | No SCRM documentation | SCRM v1.0 created and approved |
| ca-7, ca-7.4 | No continuous monitoring plan | CONMON v1.0 created and approved |
| ca-3, sa-9 | No external service agreements | EXT-SA v1.0 created and approved |
| sa-3 | No SDLC documentation | CMP git-based SDLC section |
| sa-5 | No system documentation | SSP v1.0 approved |
| pl-2 | SSP incomplete | SSP v1.0 approved |
| pl-11 | N/A determinations not documented | SSP and system_controls narratives |
| cm-2 | No configuration baseline | CMP v1.0 |
| cm-10 | No software usage restrictions | ISMP SA section |
| cm-11 | No user-installed software policy | CMP v1.0 |
| ra-7 | No risk response procedure | VMP and POA&M management |
| si-5 | No advisory tracking | VMP and nist_publications table |
| ps-6 | No access agreements | ROB serves as access agreement |
| sa-8 | No engineering principles | SSP engineering principles section |

---

## 7. POA&M Governance

**Review cycle:** Monthly by ISSO; quarterly summary to AO
**Closure criteria:** Remediation implemented AND evidence documented AND verified by ISSO
**Risk acceptance:** Requires AO signature; documented in POA&M item comments and signoff_trail field
**Escalation:** Items overdue by >30 days from scheduled_completion are escalated to AO for review

**POA&M Manager:** Dan Borisov, ISSO
**AO:** Dan Borisov
**Next quarterly review:** 2026-06-09
"""

async def main():
    engine = make_engine(config)
    SessionFactory = make_session_factory(engine)

    updated = 0
    async with SessionFactory() as s:
        for doc_type, content in DOCS.items():
            result = await s.execute(text("""
                UPDATE ato_documents
                SET content=:content, status='approved', version='1.0', updated_at=datetime('now')
                WHERE system_id=:sid AND doc_type=:doc_type
            """), {"content": content, "sid": SYSTEM_ID, "doc_type": doc_type})
            rows_affected = result.rowcount
            if rows_affected > 0:
                print(f"  Updated {doc_type}: {rows_affected} row(s)")
                updated += 1
            else:
                print(f"  WARNING: {doc_type} not found in DB")

        await s.commit()

    print(f"\nStep 1 complete: {updated} documents updated and approved.")

asyncio.run(main())
