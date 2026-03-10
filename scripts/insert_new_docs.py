#!/usr/bin/env python3
"""
Step 2: Insert new policy documents into ato_documents.
ISMP, ROB, KMP, SCRM, CONMON, EXT-SA
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

NEW_DOCS = [
    {
        "doc_type": "ISMP",
        "title": "Information Security Management Policy — BLACKSITE",
        "content": """# Information Security Management Policy (ISMP)
## BLACKSITE Security Assessment Platform / TheKramerica
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Authority

This Information Security Management Policy (ISMP) establishes the overarching information security policy for the BLACKSITE Security Assessment Platform and the TheKramerica information security program. This document satisfies the policy requirement (-1 control) for all 17 NIST SP 800-53 Rev 5 control families. Family-specific procedures are documented in dedicated plans (IRP, CP, CMP, VMP, KMP, SAP, SCRM, CONMON) referenced within each section below.

This policy is issued under the authority of Dan Borisov, Authorizing Official and Information System Security Officer (ISSO) for TheKramerica. It is effective as of 2026-03-09 and applies to all information systems, personnel, and activities within the TheKramerica information security boundary.

---

## 2. Scope

This policy applies to:
- All TheKramerica information systems, including BLACKSITE
- All personnel with access to TheKramerica information systems
- All contractors and third parties operating on behalf of TheKramerica
- All information assets owned, operated, or managed by TheKramerica

---

## 3. Control Family Policy Statements

### 3.1 Access Control (AC)

**Policy Statement:** Access to TheKramerica information systems is granted based on the principle of least privilege. Users receive only the minimum access rights necessary to perform their assigned duties. Access rights are based on defined roles and are assigned by the system administrator with ISSO approval.

**Procedures:** Access is enforced through RBAC in BLACKSITE. Authelia provides authentication gateway for web services. Account creation requires ISSO approval. Accounts are reviewed quarterly and disabled immediately upon personnel departure or role change.

**Responsible Role:** ISSO (Dan Borisov)
**Review Schedule:** Annual; quarterly access review

### 3.2 Awareness and Training (AT)

**Policy Statement:** All personnel with access to TheKramerica information systems must receive security awareness training commensurate with their role before accessing the system and annually thereafter. Role-specific training is required for personnel in privileged roles.

**Procedures:** BLACKSITE provides built-in security awareness training modules and quizzes. Completion is tracked in the system. ISSO personnel receive additional training on NIST 800-53 and security assessment methodology through professional development resources.

**Responsible Role:** ISSO (Dan Borisov)
**Review Schedule:** Annual curriculum review; training completion verified annually per user

### 3.3 Audit and Accountability (AU)

**Policy Statement:** All security-relevant events in TheKramerica information systems must be logged with sufficient detail to reconstruct the event, identify the actor, and determine the outcome. Audit logs are protected from unauthorized modification and retained for a minimum of 90 days online and 1 year total.

**Procedures:** BLACKSITE security_events table provides application-level audit logging with tamper-evident SQLCipher encryption. Caddy provides HTTP access logging. Authelia logs authentication events. Logs are reviewed monthly by the ISSO. Automated alerting for critical events is planned (see POA&M au-5, au-6).

**Responsible Role:** ISSO (Dan Borisov)
**Review Schedule:** Monthly log review; annual policy review

### 3.4 Certification, Accreditation, and Security Assessments (CA)

**Policy Statement:** All TheKramerica information systems must obtain and maintain a formal Authorization to Operate (ATO) before processing organizational information. Security controls must be assessed periodically to verify continued effectiveness. Continuous monitoring is required for all authorized systems.

**Procedures:** BLACKSITE is the authoritative system for managing ATO documentation and security control assessments. The Security Assessment Plan (SAP) and Security Assessment Report (SAR) document the assessment methodology and results. Continuous monitoring procedures are defined in the CONMON plan. External service interconnections are documented in EXT-SA.

**Responsible Role:** AO and ISSO (Dan Borisov)
**Review Schedule:** Triennial full reassessment; annual review of POA&M and controls

### 3.5 Configuration Management (CM)

**Policy Statement:** All TheKramerica information systems must maintain a documented configuration baseline. Changes to system configuration must be controlled, authorized, and documented. Unauthorized software installation is prohibited on production systems.

**Procedures:** Defined in the Configuration Management Plan (CMP). Git version control tracks all application code and configuration changes. Requirements.txt pins all dependency versions. Change categories (routine/standard/emergency/major) determine approval requirements. Software installation requires ISSO approval.

**Responsible Role:** System Administrator / ISSO (Dan Borisov)
**Review Schedule:** Monthly configuration verification; annual CMP review

### 3.6 Contingency Planning (CP)

**Policy Statement:** TheKramerica must establish and maintain contingency plans for all information systems to ensure continuity of operations and timely recovery from disruptions. Plans must include recovery time and recovery point objectives, backup procedures, and alternate processing arrangements.

**Procedures:** Defined in the Contingency Plan (CP). BLACKSITE has RTO=4 hours, RPO=24 hours. Nightly backup to Iapetus NAS via backup-all.sh. Annual tabletop exercise required. Backup restore test required annually.

**Responsible Role:** ISSO (Dan Borisov)
**Review Schedule:** Annual CP review and test; tabletop exercise within 30 days of this policy

### 3.7 Identification and Authentication (IA)

**Policy Statement:** All users of TheKramerica information systems must be uniquely identified and authenticated before access is granted. Multi-factor authentication (MFA) is required for all privileged accounts and all remote access. Passwords must meet minimum complexity and length requirements.

**Procedures:** Authelia enforces MFA (TOTP) for all BLACKSITE users without exception. Passwords are hashed with bcrypt. Session tokens are HMAC-signed and expire after 30 minutes of inactivity. No shared accounts permitted. Service accounts use dedicated credentials.

**Responsible Role:** ISSO (Dan Borisov)
**Review Schedule:** Annual IA policy review; MFA enrollment verified at each account review

### 3.8 Incident Response (IR)

**Policy Statement:** TheKramerica must establish and maintain an incident response capability to detect, contain, eradicate, and recover from security incidents. All security incidents must be reported to the ISSO within 1 hour of discovery. Lessons learned from incidents must be incorporated into security improvements.

**Procedures:** Defined in the Incident Response Plan (IRP). Security events are captured in the security_events table. Incident categories, severity levels, response times, and playbooks are documented in the IRP. Post-incident reviews are required within 5 business days of closure.

**Responsible Role:** ISSO / Incident Commander (Dan Borisov)
**Review Schedule:** Annual IRP review and tabletop exercise; update after every significant incident

### 3.9 Maintenance (MA)

**Policy Statement:** System maintenance must be performed by authorized personnel using approved tools and procedures. Remote maintenance sessions must be authenticated and logged. Maintenance activities that affect system security posture must be documented.

**Procedures:** All maintenance of the borisov server and BLACKSITE application is performed by Dan Borisov (sole administrator) via SSH with key authentication. Remote maintenance sessions are logged by the OS SSH daemon. Maintenance activities affecting security controls are documented in git commit messages and the ISSO journal.

**Responsible Role:** System Administrator (Dan Borisov)
**Review Schedule:** Annual maintenance policy review

### 3.10 Media Protection (MP)

**Policy Statement:** Information system media containing organizational data must be protected from unauthorized access and disposed of securely. Removable media usage on production systems requires ISSO approval. Digital media must be sanitized before disposal or reuse.

**Procedures:** BLACKSITE stores all data in SQLCipher encrypted database. No removable media is used in normal BLACKSITE operations. Server hard drives use RAID and are not removed without ISSO authorization. Decommissioned drives are sanitized per NIST SP 800-88 (secure erase or physical destruction) before disposal.

**Responsible Role:** System Administrator / ISSO (Dan Borisov)
**Review Schedule:** Annual MP policy review; verify drive disposal records when applicable

### 3.11 Physical and Environmental Protection (PE)

**Policy Statement:** The physical environment housing TheKramerica information systems must be protected from unauthorized physical access, environmental hazards, and disruption to supporting utilities. Access to server hardware is restricted to authorized personnel.

**Procedures:** The borisov server is located in Dan Borisov's residence in a dedicated server area. Physical access is controlled by residential door locks. Environmental hazards (fire, flood, temperature) are mitigated by residential smoke detectors, HVAC, and UPS power protection. No unauthorized visitors are permitted in the server area without ISSO escort.

**Responsible Role:** Facility Owner / ISSO (Dan Borisov)
**Review Schedule:** Annual PE policy review; environmental controls verified annually

### 3.12 Planning (PL)

**Policy Statement:** TheKramerica must maintain a current System Security Plan (SSP) for each information system. Rules of Behavior must be established and acknowledged by all users before access is granted. Security planning must be integrated into the system development lifecycle.

**Procedures:** The SSP is maintained in the BLACKSITE ATO document library and updated at least annually. Rules of Behavior (ROB) are documented and acknowledged at account creation and annually. The SSP includes authorization boundary, data flows, control summary, and all interconnections.

**Responsible Role:** ISSO (Dan Borisov)
**Review Schedule:** Annual SSP review; ROB acknowledged annually per user

### 3.13 Personnel Security (PS)

**Policy Statement:** Personnel with access to TheKramerica information systems must be appropriately vetted for their level of access. Access must be terminated promptly upon separation. Personnel security violations are subject to disciplinary action.

**Procedures:** As a single-person organization, Dan Borisov self-administers personnel security. All system access is granted by the ISSO. Account access is reviewed at least quarterly. Upon personnel departure (if the organization expands), accounts are disabled within 24 hours and access credentials are revoked.

**Responsible Role:** ISSO (Dan Borisov)
**Review Schedule:** Annual PS policy review; access review quarterly

### 3.14 Risk Assessment (RA)

**Policy Statement:** TheKramerica must conduct and document risk assessments for all information systems at least every three years or upon significant system change. Identified risks must be tracked, assigned to responsible parties, and remediated within defined timeframes based on severity.

**Procedures:** Risk assessments are conducted as part of the ATO process using the Security Assessment Plan (SAP) methodology. Findings are documented in the SAR and tracked as POA&M items in BLACKSITE. The VMP defines scanning and patching procedures. The risks table in BLACKSITE tracks organizational risks. Risk register reviewed quarterly.

**Responsible Role:** ISSO / Risk Manager (Dan Borisov)
**Review Schedule:** Triennial full risk assessment; annual POA&M review; quarterly risk register review

### 3.15 System and Services Acquisition (SA)

**Policy Statement:** Security requirements must be integrated into the system development lifecycle and procurement process. External services must be assessed for risk before integration. Unsupported system components must be upgraded or removed.

**Procedures:** BLACKSITE development follows the SDLC defined in the CMP. External services are documented in EXT-SA with risk assessment. Unsupported components are tracked as POA&M items (e.g., Python 3.8 EOL — si-2). Security engineering principles are documented in the SSP Section 7.

**Responsible Role:** System Developer / ISSO (Dan Borisov)
**Review Schedule:** Annual SA policy review; external service review annually

### 3.16 System and Communications Protection (SC)

**Policy Statement:** Information transmitted across networks must be encrypted using FIPS-approved algorithms. Data at rest must be encrypted where it contains sensitive information. Network communications must be protected from unauthorized disclosure and modification.

**Procedures:** TLS 1.2+ enforced by Caddy for all external connections. SQLCipher AES-256 encrypts all database content at rest. Network segmentation via UniFi firewall/VLAN. Key management procedures defined in the Key Management Plan (KMP). DNS secured by AdGuard Home.

**Responsible Role:** System Administrator / ISSO (Dan Borisov)
**Review Schedule:** Annual SC policy review; TLS configuration verified at each certificate renewal

### 3.17 System and Information Integrity (SI)

**Policy Statement:** Information systems must be protected against malicious code, unauthorized changes, and known vulnerabilities. Security alerts and advisories must be monitored and acted upon within defined timeframes based on severity. Flaw remediation must occur within the timeframes defined in the Vulnerability Management Procedures.

**Procedures:** Defined in the Vulnerability Management Procedures (VMP). pip audit run monthly. apt security updates applied per VMP SLA. Wazuh provides continuous FIM and rootkit detection. nist_publications table tracks NIST advisories. Python 3.8 EOL tracked as High-severity POA&M item.

**Responsible Role:** System Administrator / ISSO (Dan Borisov)
**Review Schedule:** Annual SI policy review; monthly vulnerability scan; advisory monitoring continuous

---

## 4. Compliance and Enforcement

All personnel with access to TheKramerica information systems are required to comply with this policy and all referenced procedures. Non-compliance may result in account suspension, removal of access, and other appropriate action.

This policy is reviewed annually by the ISSO and updated as necessary to reflect changes in the threat environment, system architecture, or regulatory guidance.

---

## 5. Exceptions

Exceptions to this policy must be documented in writing and approved by the ISSO and AO. Exceptions are tracked in the POA&M system with risk acceptance documentation.

---

## 6. Approval

**Policy Owner:** Dan Borisov, ISSO
**Approving Authority:** Dan Borisov, AO, TheKramerica
**Contact:** daniel@thekramerica.com
**Effective Date:** 2026-03-09
**Next Review:** 2027-03-09
"""
    },
    {
        "doc_type": "ROB",
        "title": "Rules of Behavior — BLACKSITE",
        "content": """# Rules of Behavior (ROB)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose

These Rules of Behavior (ROB) establish the specific obligations, responsibilities, and expected behavior of all individuals who are granted access to the BLACKSITE Security Assessment Platform. By accessing BLACKSITE, you agree to these rules as a condition of access. These rules supplement the Acceptable Use Policy (AUP) with specific behavioral standards.

---

## 2. Scope and Applicability

These Rules of Behavior apply to all BLACKSITE users regardless of role, including administrators, ISSOs, ISSMs, CISOs, Authorizing Officials, Security Control Assessors, auditors, and managers. All users must acknowledge these rules upon initial access and annually thereafter.

---

## 3. Rules of Behavior

### 3.1 Authorized Use Only

I understand that BLACKSITE is an internal security compliance management system. I will use BLACKSITE only for authorized security program activities related to TheKramerica's information security mission. I will not use BLACKSITE for personal projects, entertainment, or any purpose not related to the official information security program.

### 3.2 Account and Credential Security

I will:
- Keep my BLACKSITE username and password confidential at all times
- Never share my password, session token, or MFA (TOTP) code with any other person
- Use a strong, unique password for BLACKSITE (minimum 16 characters, not reused from other systems)
- Enroll in and maintain multi-factor authentication (TOTP) using a personal, secure device
- Immediately report to the ISSO (daniel@thekramerica.com) if I suspect my credentials have been compromised, my MFA device is lost or stolen, or my account may have been accessed without my authorization

### 3.3 Access Within Authorized Bounds

I will:
- Access only those BLACKSITE functions and data that my assigned role permits
- Not attempt to access other users' accounts, sessions, or data
- Not attempt to escalate my access privileges beyond what has been formally assigned
- Not attempt to discover, exploit, or probe system vulnerabilities without explicit written authorization from the system owner
- Report any unintended access to data or functions beyond my role to the ISSO immediately

### 3.4 Data Handling and Protection

I will:
- Treat all BLACKSITE content (control narratives, assessment findings, POA&M details, system architecture information, security event data) as Unclassified // Internal Use Only
- Not export, copy, or transmit BLACKSITE data to unauthorized systems, personal email, cloud storage, or external parties without explicit ISSO authorization
- Not enter information into BLACKSITE that has a classification level higher than Unclassified // Internal Use Only
- Not store Personally Identifiable Information (PII), Protected Health Information (PHI), or other sensitive personal data in BLACKSITE
- Ensure the accuracy and integrity of information I enter; not fabricate, falsify, or manipulate assessment results, control narratives, or POA&M records

### 3.5 Incident Reporting

I will report the following to the ISSO (daniel@thekramerica.com) immediately upon discovery:
- Any suspected unauthorized access to BLACKSITE or any other TheKramerica system
- Any unexpected system behavior, error messages, or anomalies that may indicate a security issue
- Any loss, theft, or compromise of credentials (passwords, MFA devices)
- Any security vulnerability I discover in BLACKSITE, whether I was looking for it or not
- Any successful or attempted phishing, social engineering, or other attack targeting BLACKSITE or TheKramerica systems

I will not wait to confirm whether a security event is real before reporting. Timely reporting is critical to effective incident response.

### 3.6 Session Security

I will:
- Log out of BLACKSITE when I have completed my work session
- Not leave an authenticated BLACKSITE browser session unattended on an unattended or shared device
- Lock my workstation (screen lock) when stepping away from my desk
- Not access BLACKSITE from untrusted networks (public Wi-Fi) without VPN protection

### 3.7 Authorized Software and Configuration

I will:
- Not install unauthorized software on the borisov server or any system that hosts or supports BLACKSITE
- Not modify BLACKSITE application code, configuration files, or the operating environment without prior authorization from the ISSO following the change control process defined in the CMP
- Not install browser extensions or plugins on systems used to access BLACKSITE that could intercept or modify web traffic
- Report any software installations or configuration changes I observe that appear unauthorized

### 3.8 AI Assistant Use

If I use the BLACKSITE AI assistant capability to draft control narratives or other security content, I will:
- Independently verify all AI-generated content for accuracy, completeness, and appropriateness before saving it as official record
- Not submit AI-generated content as a substitute for my own professional judgment and knowledge
- Understand that AI-generated content may contain errors, omissions, or fabrications and that I am responsible for the accuracy of what I save

### 3.9 Compliance with Policies and Procedures

I will:
- Read, understand, and comply with this ROB and the BLACKSITE Acceptable Use Policy (AUP)
- Comply with the BLACKSITE Information Security Management Policy (ISMP) and all referenced procedures
- Complete required security awareness training as directed by the ISSO
- Cooperate with security audits, investigations, and assessments as requested by the ISSO

### 3.10 No Expectation of Privacy

I understand that BLACKSITE logs all security-relevant user actions including login events, data access, and configuration changes. These logs are subject to review by the ISSO for security and compliance purposes. I have no expectation of privacy for actions taken within BLACKSITE.

---

## 4. Consequences of Non-Compliance

Failure to comply with these Rules of Behavior may result in:
- Immediate suspension of BLACKSITE access pending investigation
- Permanent revocation of access privileges
- Escalation to appropriate organizational, legal, or law enforcement authorities depending on the nature and severity of the violation

---

## 5. Acknowledgment

By accessing BLACKSITE, I acknowledge that I have read and understood these Rules of Behavior and agree to comply with them as a condition of my continued access. My access to BLACKSITE constitutes my agreement to these rules.

All users are required to formally acknowledge these ROB at initial account creation and annually thereafter. The ISSO maintains records of acknowledgments.

---

## 6. Document Control

**Policy Owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, TheKramerica
**Contact:** daniel@thekramerica.com
**Effective Date:** 2026-03-09
**Next Review:** 2027-03-09
"""
    },
    {
        "doc_type": "KMP",
        "title": "Key Management Plan — BLACKSITE",
        "content": """# Key Management Plan (KMP)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-53 Rev 5 SC-12, SC-28
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This Key Management Plan (KMP) documents the cryptographic key management practices for the BLACKSITE Security Assessment Platform. It covers the lifecycle of all cryptographic keys used by BLACKSITE: generation, storage, access, rotation, and destruction. This plan satisfies NIST SP 800-53 Rev 5 control SC-12 (Cryptographic Key Establishment and Management).

---

## 2. Cryptographic Keys in BLACKSITE

BLACKSITE uses the following cryptographic keys:

### 2.1 SQLCipher Database Encryption Key (DB Key)

| Attribute | Value |
|---|---|
| Purpose | Encrypt the entire SQLCipher database (blacksite.db) at rest |
| Algorithm | AES-256-CBC (SQLCipher default) |
| Key length | 256-bit (64 hex characters) |
| Format | Hexadecimal string, passed as PRAGMA key |
| Current storage | Environment variable BLACKSITE_DB_KEY in systemd service file |
| Service file location | /etc/systemd/system/blacksite.service |
| File permissions | 0640, owned by root:root (readable only by root) |
| Backup copy | Stored in ISSO's personal secure password manager (offline, encrypted) |
| Generation method | Cryptographically secure random: python3 -c "import secrets; print(secrets.token_hex(32))" |
| Key custodian | Dan Borisov (ISSO) |

**Access control:** The systemd service file is readable only by root. The DB key is never logged, never transmitted in plaintext, and never included in application code or git commits. When the service starts, systemd passes the key as an environment variable to the application process.

**Verification:** Correct key operation verified by successful database open at application startup. If the wrong key is provided, pysqlcipher3 raises a DatabaseError and the application fails to start — providing a clear indicator of key integrity failure.

### 2.2 Session HMAC Key (Session Key)

| Attribute | Value |
|---|---|
| Purpose | Sign and verify session tokens to prevent forgery |
| Algorithm | HMAC-SHA256 (or application framework equivalent) |
| Key length | 256-bit minimum |
| Format | Arbitrary bytes, stored as file content |
| Storage location | /home/graycat/projects/blacksite/data/.app_secret |
| File permissions | 0600, owned by graycat (application user) |
| Generation method | Auto-generated at first application startup if file does not exist |
| Key custodian | Dan Borisov (ISSO) |

**Access control:** File readable only by the application user (graycat). Not included in backups transmitted to Iapetus NAS (excluded from rsync by .gitignore / backup exclusion). If the session key is rotated, all existing sessions are immediately invalidated — all users must re-authenticate.

**Backup consideration:** The session key is intentionally excluded from offsite backup. Loss of this key invalidates all sessions (users re-login) but does not result in data loss. A new key is generated automatically on next application start.

### 2.3 TLS Certificate Private Keys (Caddy/Let's Encrypt)

| Attribute | Value |
|---|---|
| Purpose | Authenticate BLACKSITE TLS endpoint (HTTPS) |
| Algorithm | ECDSA P-256 or RSA-2048 (Let's Encrypt default) |
| Storage location | Caddy certificate store (Docker volume: caddy_data) |
| Management | Fully automated by Caddy via ACME protocol |
| Renewal | Automatic; 90-day certificates renewed 30 days before expiration |
| Key custodian | Caddy (automated); Dan Borisov (overall custodian) |

**Access control:** TLS private keys are stored in the Caddy Docker volume. The volume is accessible only by the caddy container user. Keys are never exposed to application code or transmitted outside the Caddy process.

### 2.4 SSH Authentication Keys (borisov server access)

| Attribute | Value |
|---|---|
| Purpose | Authenticate administrator SSH access to borisov server |
| Algorithm | Ed25519 |
| Storage | ~/.ssh/ on client hosts; ~/.ssh/authorized_keys on borisov |
| Key custodian | Dan Borisov |

Managed per standard SSH key management practices; separate from BLACKSITE application keys but documented here for completeness.

---

## 3. Key Generation

All cryptographic keys used by BLACKSITE must be generated using a cryptographically secure pseudo-random number generator (CSPRNG). The following methods are approved:

```bash
# Generate a new DB key (256-bit hex):
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate a random session key (256-bit):
python3 -c "import secrets; print(secrets.token_bytes(32).hex())"

# Or using the OS CSPRNG directly:
dd if=/dev/urandom bs=32 count=1 2>/dev/null | xxd -p -c 64
```

Keys generated with `random` (Python stdlib non-cryptographic) or other non-CSPRNG methods are prohibited.

---

## 4. Key Storage and Protection

| Key | Storage Method | Access Control | Backup |
|---|---|---|---|
| DB Key | systemd service Environment= | root-only file (0640) | ISSO password manager (offline) |
| Session Key | File: data/.app_secret | Application user only (0600) | Not backed up (intentional) |
| TLS Keys | Caddy volume | Container only | Let's Encrypt re-issue on loss |
| SSH Keys | ~/.ssh/ | User only (0600) | ISSO backup copies |

**Prohibited storage methods:**
- In source code or git repository (any branch)
- In plaintext configuration files committed to version control
- In application logs or error output
- In environment variables visible to child processes beyond the application

---

## 5. Key Rotation Procedures

### 5.1 DB Key Rotation

DB key rotation is required:
- After actual or suspected compromise
- Upon departure of personnel who had access to the key
- At least every 3 years (aligned with ATO period)

**Procedure:**
```bash
# 1. Stop the application
sudo systemctl stop blacksite

# 2. Generate new key
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 3. Decrypt database with old key and re-encrypt with new key
# Using sqlcipher3 CLI:
sqlcipher3 /home/graycat/projects/blacksite/data/blacksite.db \
  "PRAGMA key='OLD_KEY_HERE'; ATTACH DATABASE '/tmp/blacksite_rekey.db' AS rekey KEY 'x\"$NEW_KEY\"'; SELECT sqlcipher_export('rekey'); DETACH DATABASE rekey;"

# 4. Replace database file
mv /home/graycat/projects/blacksite/data/blacksite.db /home/graycat/docs/blacksite-pre-rekey-$(date +%Y%m%d).db
mv /tmp/blacksite_rekey.db /home/graycat/projects/blacksite/data/blacksite.db

# 5. Update systemd service file with new key
sudo systemctl edit blacksite  # Add/update: Environment=BLACKSITE_DB_KEY=NEW_KEY
sudo systemctl daemon-reload

# 6. Update ISSO password manager with new key

# 7. Securely delete old key backup

# 8. Start application and verify
sudo systemctl start blacksite
curl -s http://127.0.0.1:8100/health
```

### 5.2 Session Key Rotation

Session key rotation forces all users to re-authenticate. Required after suspected session compromise.

```bash
# Simply delete the session key file; application regenerates on next start
sudo systemctl stop blacksite
rm /home/graycat/projects/blacksite/data/.app_secret
sudo systemctl start blacksite
# All existing sessions are immediately invalidated
```

### 5.3 TLS Certificate Rotation

Managed automatically by Caddy. No manual intervention required under normal circumstances. If a TLS private key is compromised:
1. Revoke certificate via Let's Encrypt: Caddy supports ACME revocation
2. Delete Caddy's certificate store for the affected domain
3. Restart Caddy to trigger re-issuance

---

## 6. Key Destruction

When cryptographic keys are no longer needed:
- **DB Key:** Delete from systemd service file; overwrite backup in password manager; securely wipe any temporary copies
- **Session Key:** Delete .app_secret file; use `shred -u` for secure deletion if needed
- **TLS Keys:** Revoke certificate and delete Caddy volume (Docker volume prune)

Secure deletion uses `shred -u` for individual files on ext4 filesystems. For SSDs (Samsung 860 EVO on borisov), file system-level secure delete may not be fully effective; full-disk encryption provides defense in depth.

---

## 7. Key Custodian Responsibilities

Dan Borisov is the sole key custodian for BLACKSITE cryptographic keys and is responsible for:
- Maintaining secure backup copies of all keys in an offline encrypted password manager
- Executing key rotation procedures per this plan
- Ensuring keys are never disclosed to unauthorized parties
- Reporting any suspected key compromise to the AO (self-reporting in this case) and initiating rotation immediately

---

## 8. Compliance

This KMP satisfies NIST SP 800-53 Rev 5 SC-12. Key management practices are consistent with NIST SP 800-57 Part 1 guidelines for symmetric key management, adapted to the scale and complexity of the BLACKSITE environment.

**Plan Owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, TheKramerica
**Effective Date:** 2026-03-09
**Next Review:** 2027-03-09
"""
    },
    {
        "doc_type": "SCRM",
        "title": "Supply Chain Risk Management Plan — BLACKSITE",
        "content": """# Supply Chain Risk Management Plan (SCRM)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-53 Rev 5 SR family, NIST SP 800-161 Rev 1
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This Supply Chain Risk Management Plan (SCRM) documents TheKramerica's approach to identifying, assessing, and mitigating risks associated with the hardware, software, and service supply chain components used in the BLACKSITE Security Assessment Platform.

BLACKSITE is a Low-impact internal tool. Supply chain risk management for this system is appropriately scaled — focused on practical controls against realistic threats without the full apparatus required for high-value or national security systems.

---

## 2. Supply Chain Components

### 2.1 Software Supply Chain

| Component | Source | Version Control | Risk |
|---|---|---|---|
| Python 3.8 runtime | Ubuntu FIPS packages (apt) | Version pinned by OS | Medium (EOL — see POA&M si-2) |
| FastAPI | PyPI (pip) | Pinned in requirements.txt | Low |
| SQLAlchemy | PyPI (pip) | Pinned in requirements.txt | Low |
| pysqlcipher3 | PyPI (pip) | Pinned in requirements.txt | Low |
| aiosqlite | PyPI (pip) | Pinned in requirements.txt | Low |
| Authelia | Docker Hub (authelia/authelia) | Tag-pinned in docker-compose.yml | Low |
| Caddy | Docker Hub (caddy) | Tag-pinned in docker-compose.yml | Low |
| Ubuntu 20.04 FIPS | Canonical apt repositories | LTS with FIPS overlay | Low |

### 2.2 Hardware Supply Chain

| Component | Source | Risk |
|---|---|---|
| Dell PowerEdge R510 (borisov) | Enterprise server market (used/refurbished) | Low (established vendor, enterprise-grade) |
| PERC H700 RAID controller | Dell OEM | Low |
| WDC WD100EMAZ drives (12×) | Established retail/wholesale channels | Low |
| Samsung 860 EVO SSDs (2×) | Established retail channels | Low |
| UniFi Dream Machine Pro | Ubiquiti (authorized reseller) | Low |
| Iapetus NAS (Windows server) | Established retail channels | Low |

### 2.3 External Service Supply Chain

| Service | Provider | Risk | Agreement |
|---|---|---|---|
| ip-api.com | ip-api.com (free tier) | Low (non-critical, fail-open) | Free tier ToS |
| NIST GitHub API | NIST / GitHub (Microsoft) | Low (public data, unauthenticated) | Public API |
| Let's Encrypt | Internet Security Research Group (ISRG) | Low (standard ACME CA) | Subscriber Agreement |
| PyPI | Python Software Foundation | Medium (dependency confusion possible) | Community |
| Docker Hub | Docker Inc. | Medium (image supply chain) | Free tier ToS |

---

## 3. Key Supply Chain Risks

### Risk SR-1: Dependency Confusion / Malicious Package

**Description:** An attacker publishes a malicious package to PyPI with the same name as an internal or legitimate dependency. pip installs the attacker's package instead of the intended one.

**Likelihood:** Low (BLACKSITE uses well-established, widely-used packages with high download counts)
**Impact:** High if exploited (code execution in application context)

**Mitigations:**
1. **Version pinning:** All packages in requirements.txt are pinned to specific versions, preventing automatic upgrade to a malicious version
2. **pip hash verification:** `pip install --require-hashes` can be enforced by generating a pip hash requirements file: `pip-compile --generate-hashes`
3. **pip audit:** Monthly scan of installed packages against PyPI advisory database catches packages with known CVEs
4. **Install only from PyPI:** No custom or alternative package indexes are configured
5. **Dependency review:** Before adding any new package, review its maintainers, download history, and GitHub repository for legitimacy

### Risk SR-2: Compromised Docker Image

**Description:** Official Docker images for Caddy or Authelia could be compromised at Docker Hub, or a version tag could be silently updated.

**Likelihood:** Very Low (official maintained images with large user communities)
**Impact:** High if exploited (full compromise of authentication layer)

**Mitigations:**
1. **Tag pinning:** docker-compose.yml references specific version tags (not `latest`) for all containers
2. **Digest pinning (recommended):** Consider pinning by image digest (SHA256) in addition to tag for highest assurance
3. **Vendor monitoring:** Subscribe to Authelia and Caddy security announcement channels; apply updates promptly per VMP
4. **Container isolation:** Containers run with least privilege; no privileged mode; no host network except where required

### Risk SR-3: Compromised Ubuntu FIPS Repository

**Description:** Ubuntu apt repository packages could be compromised via a mirror or upstream attack.

**Likelihood:** Very Low (Canonical maintains secure, signed package repositories)
**Impact:** High if exploited

**Mitigations:**
1. **APT signature verification:** Ubuntu apt is configured to verify package signatures against Canonical's GPG keys
2. **Official repositories only:** Only official Ubuntu repositories and FIPS overlay packages are enabled
3. **No PPA sources:** No Personal Package Archives or third-party apt sources are configured on borisov

### Risk SR-4: Hardware Tampering (Used Equipment)

**Description:** The Dell R510 server was procured as enterprise hardware. There is a theoretical risk of hardware-level compromise if the hardware passed through untrustworthy hands.

**Likelihood:** Very Low (enterprise servers have defined provenance; homelab procurement from reputable sources)
**Impact:** Very High if implanted hardware exists

**Mitigations:**
1. **Visual inspection:** Server was physically inspected before deployment; no unusual components observed
2. **Firmware updates:** iDRAC, BIOS, and PERC firmware are updated to current versions
3. **Software isolation:** Even if hardware were compromised at firmware level, the SQLCipher database encryption protects data at rest from physical access

---

## 4. Supply Chain Security Procedures

### 4.1 New Software Dependencies

Before adding any new Python package to requirements.txt:
1. Verify the package is published on PyPI by a legitimate, known maintainer
2. Review the package's GitHub repository for recent activity, issue history, and maintainer reputation
3. Check the package in pip audit before and after installation
4. Check snyk.io or osv.dev for known vulnerabilities in the package
5. Document the addition in the git commit message with justification

### 4.2 Dependency Updates

Before updating any pinned dependency version:
1. Review the package's changelog/release notes for the target version
2. Check if the update resolves a security vulnerability (desired) or introduces breaking changes
3. Test in blacksite-co environment before applying to production
4. Run pip audit after update to verify no new vulnerabilities introduced
5. Follow Standard change process (CMP)

### 4.3 Docker Image Updates

Before updating any container image version:
1. Review the container's release notes and security advisories
2. Check Docker Hub for image vulnerability scan results if available
3. Test in compose dev environment before production update
4. Update tag pins in docker-compose.yml; commit change to git

### 4.4 Annual Supply Chain Review

Annually, the ISSO conducts a review of all supply chain components:
1. Review all requirements.txt packages for EOL status, maintainer health, vulnerability history
2. Review Docker images for continued official support
3. Review hardware for firmware updates
4. Review external services for changes in terms, reliability, or ownership
5. Document review findings and update this SCRM plan

---

## 5. Incident Response for Supply Chain Events

If a supply chain compromise is confirmed or suspected:
1. Immediately stop affected service(s)
2. Identify what data or functions the compromised component could access
3. Rotate any credentials the component had access to
4. Replace compromised component with a clean version from a verified source
5. Review logs for evidence of exploitation during the compromise window
6. Follow Incident Response Plan (IRP) procedures

---

## 6. SCRM Governance

**SCRM Manager:** Dan Borisov, ISSO
**Review Schedule:** Annual; ad hoc after significant supply chain security event
**Approval:** Dan Borisov, AO, TheKramerica
**Effective Date:** 2026-03-09
**Next Review:** 2027-03-09
"""
    },
    {
        "doc_type": "CONMON",
        "title": "Continuous Monitoring Plan — BLACKSITE",
        "content": """# Continuous Monitoring Plan (CONMON)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-137, NIST SP 800-53 Rev 5 CA-7
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This Continuous Monitoring Plan (CONMON) establishes the ongoing monitoring strategy for the BLACKSITE Security Assessment Platform. Continuous monitoring provides the ISSO and AO with near-real-time visibility into the security posture of BLACKSITE, enabling timely detection of security control failures, configuration drift, new vulnerabilities, and security incidents.

This plan defines: monitoring activities, frequency, responsible parties, tools used, and thresholds for escalation or remediation.

---

## 2. Monitoring Strategy Overview

BLACKSITE continuous monitoring operates at three tiers:

| Tier | Frequency | Type | Activities |
|---|---|---|---|
| Automated/Continuous | Real-time to daily | Technical | Wazuh monitoring, application audit logging, backup execution, NIST catalog sync |
| Periodic | Monthly | Operational | Log review, vulnerability scan, backup verification, user access review |
| Periodic | Quarterly | Management | POA&M review, risk register review, security metrics |
| Periodic | Annual | Strategic | Full control assessment, CP test, IRP test, SSP/policy review |

---

## 3. Continuous and Automated Monitoring Activities

### 3.1 Application Audit Logging (Continuous)

**Tool:** BLACKSITE security_events table (SQLCipher encrypted)
**What is monitored:** All authentication events (success/failure), authorization failures, access to sensitive resources, administrative actions, API errors, configuration changes
**Alert threshold:** Any of the following triggers immediate ISSO review:
- Authentication failure rate > 5 in 10 minutes from same IP (brute force indicator)
- Authentication success from unexpected source IP
- Access to admin functions from non-admin account
- Database errors or integrity failures
- Unauthorized API calls

**Review:** ISSO spot-checks security_events dashboard at minimum weekly; full review monthly.

### 3.2 Host-Based Monitoring via Wazuh (Continuous)

**Tool:** Wazuh agent on borisov server
**What is monitored:** File integrity monitoring (FIM) for critical BLACKSITE files, rootkit detection, log analysis, process monitoring, package vulnerability detection
**Critical files monitored by FIM:**
- /home/graycat/projects/blacksite/app/ (application code)
- /home/graycat/projects/blacksite/config.yaml
- /home/graycat/projects/blacksite/requirements.txt
- /etc/systemd/system/blacksite.service
- /home/graycat/.docker/compose/caddy/Caddyfile

**Alert threshold:** Any unexpected file modification outside of a known change window triggers ISSO review.

### 3.3 Nightly NIST Catalog Sync (Automated, Nightly)

**Tool:** BLACKSITE built-in cron job
**What is monitored:** NIST SP 800-53 Rev 5 OSCAL catalog updates from NIST GitHub API; new publications and advisories added to nist_publications table
**Review:** ISSO reviews new nist_publications entries monthly; immediate review if a Critical advisory is flagged.

### 3.4 Systemd Service Health (Automated, Continuous)

**Tool:** systemd with Restart=on-failure
**What is monitored:** BLACKSITE process health; automatic restart on crash
**Alert threshold:** If BLACKSITE restarts more than 3 times in 1 hour, ISSO investigates root cause.
**Monitoring command:** `journalctl -u blacksite --since '1 hour ago' | grep -c 'Started'`

### 3.5 Nightly Backup Execution (Automated, Daily)

**Tool:** backup-all.sh systemd timer (daily at 03:00)
**What is monitored:** Successful execution of nightly backup to Iapetus NAS
**Alert threshold:** Backup failure logged to systemd journal; ISSO reviews backup status weekly.
**Monitoring command:** `journalctl -u backup-all --since yesterday`

---

## 4. Monthly Monitoring Activities

### 4.1 Security Event Log Review (Monthly)

**Activity:** Full review of BLACKSITE security_events for the past 30 days
**Performed by:** ISSO (Dan Borisov)
**Tool:** BLACKSITE Security Events dashboard (admin view)
**What to look for:**
- Authentication anomalies (unexpected sources, failure spikes, off-hours logins)
- Authorization failures (access denied events — potential privilege escalation attempts)
- Unusual data access patterns (bulk reads, unexpected exports)
- Administrative actions not corresponding to known changes
- API error patterns indicating potential attack or misconfiguration

**Output:** Brief written note in ISSO journal (/home/graycat/docs/) confirming review and any findings. Create POA&M items for any new findings.

### 4.2 Vulnerability Scan — Python Dependencies (Monthly)

**Activity:** Run pip audit against installed packages
**Performed by:** ISSO/Administrator (Dan Borisov)
**Command:** `cd /home/graycat/projects/blacksite && .venv/bin/pip audit`
**Response:** Per VMP severity response times (Critical=48h, High=7d, Moderate=30d, Low=90d)
**Output:** Log results to /home/graycat/docs/pip-audit-YYYY-MM.txt; create POA&M items for new findings.

### 4.3 OS Security Updates Review (Monthly, apply per VMP)

**Activity:** Review pending apt security updates
**Command:** `sudo apt-get update && apt list --upgradable 2>/dev/null | grep -i security`
**Response:** Apply per VMP severity SLA

### 4.4 Backup Integrity Spot-Check (Monthly)

**Activity:** Verify backup files exist and are current on Iapetus NAS
**Command:** `ssh iapetus ls -lt clawd/backups/borisov/ | head -10`
**Expected:** Recent timestamps; file sizes consistent with previous backups
**Escalation:** If backups older than 2 days, investigate backup-all.timer immediately.

### 4.5 User Account Review (Monthly)

**Activity:** Review all active BLACKSITE user accounts
**Tool:** BLACKSITE admin panel — Users section
**What to verify:**
- All active accounts belong to current, authorized personnel
- No accounts exist for personnel who have departed
- Role assignments are appropriate for each user's current function
- No unexpected accounts were created

---

## 5. Quarterly Monitoring Activities

### 5.1 POA&M Status Review (Quarterly)

**Activity:** Full review of all open POA&M items; update statuses; escalate overdue items
**Performed by:** ISSO (Dan Borisov); summary to AO
**Output:** Quarterly POA&M status report documenting: items closed since last review, items past due, items newly opened, overall progress toward remediation milestones

**Quarterly review dates:** June 9, September 9, December 9 (2026); March 9 (2027)

### 5.2 Risk Register Review (Quarterly)

**Activity:** Review the risks table in BLACKSITE for currency; update risk ratings if threat landscape has changed; add new risks if identified
**Output:** Updated risk register in BLACKSITE

### 5.3 Security Metrics Review (Quarterly)

**Metrics tracked:**
- Open POA&M count by severity (trend: decreasing is good)
- Controls at 'implemented' status (trend: increasing is good)
- Mean time to remediate POA&M items by severity vs. VMP SLA
- Backup success rate (target: 100%)
- Security events volume (baseline and trend)

---

## 6. Annual Monitoring Activities

### 6.1 Full Security Control Assessment (Annual)

**Activity:** Reassess a statistically significant sample of NIST Low baseline controls; update assessment results; identify any new weaknesses
**Based on:** SAP methodology; NIST SP 800-53A
**Output:** Updated SAR section; new POA&M items for new findings; updated system_controls assessment_result fields

### 6.2 Contingency Plan Test (Annual)

**Activity:** Conduct tabletop exercise (CP Section 8.1); also conduct backup restore test (CP Section 8.1)
**Target:** 2026-04-08 (first test, required by ADD Condition 3); annually thereafter in March/April
**Output:** CP test report in /home/graycat/docs/cp-test-YYYY-MM-DD.md

### 6.3 Incident Response Test (Annual)

**Activity:** Conduct tabletop exercise using IRP Playbook E (credential compromise)
**Target:** 2026-04-08 (first exercise, required by ADD Condition 2); annually thereafter
**Output:** IR exercise report; update IRP if gaps identified

### 6.4 SSP and Policy Review (Annual)

**Activity:** Review SSP, ISMP, and all supporting policy documents for currency and accuracy
**Performed by:** ISSO (Dan Borisov)
**Update triggers:** New external services, technology stack changes, organizational changes, significant new threats
**Output:** Updated documents with new version numbers and dates

### 6.5 ATO Status Review (Annual)

**Activity:** AO reviews overall security posture; confirms ATO remains valid; reviews any significant system changes; confirms POA&M progress is on track
**Performed by:** AO (Dan Borisov)
**Output:** Annual ATO status memo in ATO document library

---

## 7. Monitoring Thresholds and Escalation

| Condition | Threshold | Response |
|---|---|---|
| Authentication failures | >5 in 10 min from same IP | Investigate immediately; consider IP block |
| BLACKSITE restarts | >3 in 1 hour | Investigate crash; review logs |
| Backup failure | >1 day old on Iapetus | Investigate backup timer; restore capability check |
| Critical CVE in installed package | Any | Patch within 48 hours per VMP |
| FIM alert for critical file | Any unauthorized change | Treat as security incident; follow IRP |
| User account anomaly | Unexpected account, unexpected login | Investigate immediately |

---

## 8. Monitoring Records

ISSO maintains monitoring records in /home/graycat/docs/:
- Monthly: `conmon-YYYY-MM.md` — brief note confirming activities completed, any findings
- Quarterly: `poam-review-YYYY-QN.md` — POA&M status report
- Annual: `ato-annual-review-YYYY.md` — annual ATO status

---

## 9. Plan Governance

**Plan Owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, TheKramerica
**Effective Date:** 2026-03-09
**Next Review:** 2027-03-09
"""
    },
    {
        "doc_type": "EXT-SA",
        "title": "External Service Agreements — BLACKSITE",
        "content": """# External Service Agreements (EXT-SA)
## BLACKSITE Security Assessment Platform
**Version:** 1.0 | **Date:** 2026-03-09 | **Status:** Approved
**Based on:** NIST SP 800-53 Rev 5 CA-3, SA-9
**Classification:** Unclassified // Internal Use Only

---

## 1. Purpose and Scope

This document inventories and assesses all external services used by the BLACKSITE Security Assessment Platform. Per NIST SP 800-53 Rev 5 CA-3 (Information Exchange) and SA-9 (External System Services), organizations must document all external system connections and evaluate the risks associated with external service providers.

This document serves as the formal record of approved external service connections for BLACKSITE.

---

## 2. External Service Inventory

### Service 1: ip-api.com — Geolocation API

| Attribute | Details |
|---|---|
| **Service Name** | ip-api.com Geolocation API |
| **Provider** | ip-api.com (commercial provider, free tier) |
| **URL** | http://ip-api.com/json/{ip} |
| **Protocol** | HTTP GET (plain HTTP on free tier; Pro tier supports HTTPS) |
| **Purpose** | Geo-enrich security event records with country/city/ISP metadata for source IP addresses of authentication events |
| **Data Transmitted Outbound** | Source IP address of the authenticating user (single IP per request) |
| **Data Received** | Country, region, city, ISP/org name, latitude/longitude (approximate), timezone |
| **Sensitivity of transmitted data** | Low — internal LAN IP addresses (192.168.x.x range for local users); no PII, no authentication credentials |
| **Authentication** | None (free tier, anonymous) |
| **SLA** | None (free tier; no uptime guarantee) |
| **Failure mode** | Fail-open: if ip-api.com is unavailable, BLACKSITE logs the event without geo-enrichment; no functionality is blocked |
| **Rate limits** | 45 requests/minute on free tier; BLACKSITE respects this limit |
| **Agreement type** | Free Tier Terms of Service (no signed agreement) |
| **Annual data volume** | Low — only triggered on new authentication events; estimated < 1,000 requests/month |
| **Risk rating** | Low |
| **Approved by** | Dan Borisov, ISSO |
| **Date approved** | 2026-03-09 |

**Risk Assessment:**
- **Confidentiality:** Low risk. Only IP addresses are transmitted; no user credentials, no PII, no BLACKSITE content.
- **Integrity:** Low risk. Geo-enrichment data is informational; incorrect geo data doesn't affect security decisions.
- **Availability:** Low risk. Fail-open design means ip-api.com outages are transparent to BLACKSITE functionality.
- **Privacy:** No PII transmitted. Internal IP addresses (RFC 1918) are transmitted but do not constitute PII.

**Compensating note:** If ip-api.com were to begin logging and associating transmitted IPs with user behavior patterns, the risk would increase marginally. Mitigation: consider migrating to the Pro HTTPS tier or a self-hosted MaxMind GeoIP database in a future iteration.

---

### Service 2: NIST GitHub API — OSCAL Control Catalog

| Attribute | Details |
|---|---|
| **Service Name** | NIST SP 800-53 OSCAL Catalog via GitHub API |
| **Provider** | National Institute of Standards and Technology (NIST) / GitHub (Microsoft) |
| **URL** | https://api.github.com/repos/usnistgov/oscal-content/... |
| **Protocol** | HTTPS GET |
| **Purpose** | Nightly download of current NIST SP 800-53 Rev 5 control catalog in OSCAL JSON format; populates the controls reference library in BLACKSITE |
| **Data Transmitted Outbound** | HTTP GET request with User-Agent header; no authentication credentials; no BLACKSITE data |
| **Data Received** | NIST SP 800-53 Rev 5 control catalog (control IDs, titles, descriptions, baselines) — all public data |
| **Sensitivity of transmitted data** | None — outbound request contains no sensitive data |
| **Authentication** | None required (public GitHub API); optional GitHub token for higher rate limits |
| **SLA** | GitHub API: 99.9% uptime SLA for GitHub.com; NIST makes no SLA guarantees for this data |
| **Failure mode** | Fail-graceful: if the NIST GitHub API is unavailable during nightly sync, the existing catalog data remains valid; BLACKSITE continues operating with the most recent successfully synced catalog |
| **Rate limits** | 60 requests/hour unauthenticated; BLACKSITE catalog sync is a single API call per run, well within limits |
| **Agreement type** | Public API; GitHub Terms of Service; NIST data is public domain (US government work) |
| **Annual data volume** | Very low — single JSON file download nightly; estimated ~5MB/day |
| **Risk rating** | Low |
| **Approved by** | Dan Borisov, ISSO |
| **Date approved** | 2026-03-09 |

**Risk Assessment:**
- **Confidentiality:** No risk. No sensitive data transmitted to this service.
- **Integrity:** Low risk. If a malicious actor were able to tamper with the NIST OSCAL data on GitHub (highly unlikely given NIST's security), BLACKSITE could display incorrect control information. Mitigated by: NIST's own repository security; data is reference-only (doesn't automatically change control assessment results).
- **Availability:** Low risk. BLACKSITE functions normally with stale catalog data; nightly sync failure is non-critical.
- **Data ownership:** NIST OSCAL data is US government public domain material; no licensing concerns.

---

### Service 3: Let's Encrypt — Automated TLS Certificate Authority

| Attribute | Details |
|---|---|
| **Service Name** | Let's Encrypt ACME Certificate Authority |
| **Provider** | Internet Security Research Group (ISRG), a 501(c)(3) nonprofit |
| **URL** | https://acme-v02.api.letsencrypt.org/ |
| **Protocol** | HTTPS (ACME protocol, RFC 8555) |
| **Purpose** | Automated issuance and renewal of TLS certificates for *.borisov.network domains, including blacksite.borisov.network |
| **Data Transmitted Outbound** | Domain name (blacksite.borisov.network), public key (CSR), ACME account key public component, domain validation tokens |
| **Data Received** | Signed TLS certificate (valid 90 days) |
| **Sensitivity of transmitted data** | Low — domain name is not sensitive; public key material is intentionally public; no PII, no credentials |
| **Authentication** | ACME account key (private key stored in Caddy's certificate store, never transmitted) |
| **SLA** | Let's Encrypt posts status at letsencrypt.status.io; no formal SLA but historically > 99.9% uptime |
| **Failure mode** | Fail-graceful: certificates are renewed 30 days before expiration; brief Let's Encrypt outages do not affect certificate validity. If renewal fails, Caddy retries. BLACKSITE users are not affected until certificate actually expires (90-day window provides substantial buffer). |
| **Renewal** | Automatic by Caddy; no manual intervention required under normal circumstances |
| **Agreement type** | Let's Encrypt Subscriber Agreement (accepted by Caddy on behalf of domain owner) |
| **Annual data volume** | Minimal — 4–6 certificate operations per year per domain (renewal every 60 days with 30-day early renewal window) |
| **Risk rating** | Low |
| **Approved by** | Dan Borisov, ISSO |
| **Date approved** | 2026-03-09 |

**Risk Assessment:**
- **Confidentiality:** Very low risk. Only public key material and domain name are transmitted. Private key never leaves Caddy.
- **Integrity:** Low risk. Let's Encrypt uses a robust ACME protocol with domain validation (HTTP-01 or DNS-01 challenge); certificate issuance to unauthorized parties is very difficult.
- **Availability:** Low risk. 90-day certificate lifetime with 30-day renewal window provides substantial buffer against Let's Encrypt downtime.
- **Trust:** Let's Encrypt is trusted by all major browsers and operating systems. It is audited annually and maintains CT log transparency.
- **Alternative:** If Let's Encrypt became unavailable for an extended period, Caddy can be configured to use ZeroSSL or a self-signed certificate temporarily.

---

## 3. External Service Review Process

External services are reviewed annually as part of the continuous monitoring cycle (CONMON). Review criteria:

1. **Has the service's terms of service changed** in ways that affect data handling, logging, or privacy?
2. **Has the service's security posture changed** (known breaches, ownership changes, reliability issues)?
3. **Is the service still necessary** for BLACKSITE functionality, or can it be replaced with a local/internal alternative?
4. **Have data transmission patterns changed** in ways that increase risk?

New external services require ISSO approval and documentation in this EXT-SA before integration into BLACKSITE.

---

## 4. No Additional External Services

As of 2026-03-09, the three services above are the complete inventory of BLACKSITE external service connections. No other services are authorized.

Any future external service integration requires:
1. Security assessment of the proposed service
2. ISSO approval
3. Update to this EXT-SA document
4. Update to the SSP authorization boundary description
5. Notification to AO if the service accesses sensitive BLACKSITE data

---

## 5. Document Control

**Document Owner:** Dan Borisov, ISSO
**Approval:** Dan Borisov, AO, TheKramerica
**Effective Date:** 2026-03-09
**Next Review:** 2027-03-09
"""
    },
]

async def main():
    engine = make_engine(config)
    SessionFactory = make_session_factory(engine)

    inserted = 0
    skipped = 0

    async with SessionFactory() as s:
        for doc in NEW_DOCS:
            # Check if already exists
            result = await s.execute(text("""
                SELECT COUNT(*) FROM ato_documents
                WHERE system_id=:sid AND doc_type=:doc_type
            """), {"sid": SYSTEM_ID, "doc_type": doc["doc_type"]})
            count = result.scalar()

            if count > 0:
                print(f"  SKIP {doc['doc_type']}: already exists")
                skipped += 1
                continue

            doc_id = str(uuid.uuid4())
            await s.execute(text("""
                INSERT INTO ato_documents
                (id, system_id, doc_type, title, version, status, content, assigned_to, created_by, created_at, updated_at, source_type)
                VALUES (:id, :system_id, :doc_type, :title, :version, :status, :content, :assigned_to, :created_by, datetime('now'), datetime('now'), 'manual')
            """), {
                "id": doc_id,
                "system_id": SYSTEM_ID,
                "doc_type": doc["doc_type"],
                "title": doc["title"],
                "version": "1.0",
                "status": "approved",
                "content": doc["content"],
                "assigned_to": "dborisov",
                "created_by": "dborisov",
            })
            print(f"  INSERTED {doc['doc_type']}: {doc['title']}")
            inserted += 1

        await s.commit()

    print(f"\nStep 2 complete: {inserted} new documents inserted, {skipped} skipped (already existed).")

asyncio.run(main())
