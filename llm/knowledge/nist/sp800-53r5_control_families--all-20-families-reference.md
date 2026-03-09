# NIST SP 800-53 Rev 5 — Control Families Reference
## All 20 Control Families with Key Controls and GRC Guidance

Source: NIST Special Publication 800-53 Revision 5 (September 2020, updated 2022)
"Security and Privacy Controls for Information Systems and Organizations"

---

## Overview

NIST 800-53 Rev 5 contains **1,007 controls and enhancements** across 20 families.
Rev 5 additions over Rev 4: added Privacy controls (PT family), Supply Chain Risk Management (SR), extended Program Management (PM).

**Control ID Format**: `XX-N(N)` where XX=family, N=control number, (N)=enhancement
Example: `AC-2(1)` = Access Control family, control 2, enhancement 1

**Control Baselines** (from NIST 800-53B):
- Low: ~128 controls
- Moderate: ~323 controls
- High: ~421 controls
- Privacy: Separate overlay

---

## AC — Access Control (25 controls)

**Purpose**: Limit access to authorized users, processes, and devices, and to the types of transactions and functions authorized users are permitted to exercise.

| Control | Title | Baseline |
|---------|-------|---------|
| AC-1 | Policy and Procedures | L/M/H |
| AC-2 | Account Management | L/M/H |
| AC-3 | Access Enforcement | L/M/H |
| AC-4 | Information Flow Enforcement | M/H |
| AC-5 | Separation of Duties | M/H |
| AC-6 | Least Privilege | M/H |
| AC-7 | Unsuccessful Logon Attempts | L/M/H |
| AC-8 | System Use Notification | L/M/H |
| AC-11 | Device Lock | M/H |
| AC-12 | Session Termination | M/H |
| AC-14 | Permitted Actions Without ID | L/M/H |
| AC-17 | Remote Access | L/M/H |
| AC-18 | Wireless Access | L/M/H |
| AC-19 | Access Control for Mobile Devices | L/M/H |
| AC-20 | Use of External Systems | L/M/H |
| AC-21 | Information Sharing | M/H |
| AC-22 | Publicly Accessible Content | L/M/H |

**Key Controls for GRC**:
- **AC-2**: Account lifecycle management — provisioning, review, deprovisioning. BLACKSITE: UserProfile, RemovedUserReservation
- **AC-3**: Role-based access control enforcement. BLACKSITE: RBAC engine, role checks
- **AC-5**: Separation of duties — no single user can perform conflicting actions (e.g., approve own changes)
- **AC-6**: Least privilege — users get minimum rights needed. BLACKSITE: Role-specific dashboards
- **AC-17**: Remote access security (VPN, MFA, encrypted channels)

---

## AT — Awareness and Training (5 controls)

**Purpose**: Ensure personnel are aware of security risks and have skills to perform security responsibilities.

| Control | Title | Baseline |
|---------|-------|---------|
| AT-1 | Policy and Procedures | L/M/H |
| AT-2 | Literacy Training and Awareness | L/M/H |
| AT-3 | Role-Based Training | L/M/H |
| AT-4 | Training Records | L/M/H |

**Key Controls**: AT-2 requires annual security awareness training for all users. AT-3 requires specialized training for privileged users, ISSOs, and system administrators.

---

## AU — Audit and Accountability (16 controls)

**Purpose**: Create, protect, and retain system audit records to enable monitoring, analysis, investigation, and reporting.

| Control | Title | Baseline |
|---------|-------|---------|
| AU-1 | Policy and Procedures | L/M/H |
| AU-2 | Event Logging | L/M/H |
| AU-3 | Content of Audit Records | L/M/H |
| AU-4 | Audit Log Storage Capacity | L/M/H |
| AU-5 | Response to Audit Processing Failures | L/M/H |
| AU-6 | Audit Record Review, Analysis, and Reporting | L/M/H |
| AU-7 | Audit Record Reduction and Report Generation | M/H |
| AU-8 | Time Stamps | L/M/H |
| AU-9 | Protection of Audit Information | L/M/H |
| AU-10 | Non-Repudiation | M/H |
| AU-11 | Audit Record Retention | L/M/H |
| AU-12 | Audit Record Generation | L/M/H |

**Key Controls for GRC**:
- **AU-2**: What events to log — successful/failed logins, privilege escalation, data access, system changes
- **AU-3**: Each log record must include: date/time, user/process, event type, outcome, source location
- **AU-6**: Regular review of audit logs for suspicious activity
- **AU-9**: Protect logs from modification — write-once, hashed, or separate system
- **AU-11**: Retention period — minimum 3 years for federal systems

**BLACKSITE Mapping**: `AuditLog` model, `admin_audit` route, `_log_audit()` function

---

## CA — Assessment, Authorization, and Monitoring (9 controls)

**Purpose**: Assess controls, authorize system operation, and continuously monitor.

| Control | Title | Baseline |
|---------|-------|---------|
| CA-1 | Policy and Procedures | L/M/H |
| CA-2 | Control Assessments | L/M/H |
| CA-3 | Information Exchange | L/M/H |
| CA-5 | Plan of Action and Milestones | L/M/H |
| CA-6 | Authorization | L/M/H |
| CA-7 | Continuous Monitoring | L/M/H |
| CA-8 | Penetration Testing | H |
| CA-9 | Internal System Connections | L/M/H |

**Key Controls**:
- **CA-2**: Security assessments — frequency, scope, who performs, results
- **CA-5**: POA&M — track all open findings with milestones and responsible parties. BLACKSITE: `PoamItem` model
- **CA-6**: Authorization — ATO process, documentation. BLACKSITE: `AtoDocument`, `ato_date`, `ato_expiry`
- **CA-7**: Continuous monitoring strategy — what, how often, who reviews. BLACKSITE: DailyLogbook, rotation

---

## CM — Configuration Management (12 controls)

**Purpose**: Establish and maintain baseline configurations and inventories of systems, and control changes to configurations.

| Control | Title | Baseline |
|---------|-------|---------|
| CM-1 | Policy and Procedures | L/M/H |
| CM-2 | Baseline Configuration | L/M/H |
| CM-3 | Configuration Change Control | M/H |
| CM-4 | Impact Analyses | M/H |
| CM-5 | Access Restrictions for Change | M/H |
| CM-6 | Configuration Settings | L/M/H |
| CM-7 | Least Functionality | L/M/H |
| CM-8 | System Component Inventory | L/M/H |
| CM-9 | Configuration Management Plan | M/H |
| CM-10 | Software Usage Restrictions | L/M/H |
| CM-11 | User-Installed Software | L/M/H |

**Key Controls**:
- **CM-3**: Change management process — CAB, approval workflow, rollback plans
- **CM-8**: System inventory — all hardware, software, firmware components documented
- **CM-6**: STIG/CIS benchmark compliance; hardened configurations

---

## CP — Contingency Planning (13 controls)

**Purpose**: Establish contingency plans for effective response to system disruptions, corruptions, or failures.

| Control | Title | Baseline |
|---------|-------|---------|
| CP-1 | Policy and Procedures | L/M/H |
| CP-2 | Contingency Plan | L/M/H |
| CP-3 | Contingency Training | L/M/H |
| CP-4 | Contingency Plan Testing | L/M/H |
| CP-6 | Alternate Storage Site | M/H |
| CP-7 | Alternate Processing Site | M/H |
| CP-8 | Telecommunications Services | M/H |
| CP-9 | System Backup | L/M/H |
| CP-10 | System Recovery and Reconstitution | L/M/H |

**Key Controls**:
- **CP-2**: COOP/BCDR plan — BIA, recovery strategies, roles, procedures
- **CP-4**: Tabletop exercises (annually), functional exercises (for M/H)
- **CP-9**: Backups — frequency (daily/weekly/monthly), offsite storage, encryption, tested restoration
- **CP-10**: RTO/RPO defined; restoration procedures documented and tested

---

## IA — Identification and Authentication (12 controls)

**Purpose**: Identify system users, processes, or devices and authenticate those identities before allowing access.

| Control | Title | Baseline |
|---------|-------|---------|
| IA-1 | Policy and Procedures | L/M/H |
| IA-2 | Identification and Authentication (Org Users) | L/M/H |
| IA-3 | Device Identification and Authentication | M/H |
| IA-4 | Identifier Management | L/M/H |
| IA-5 | Authenticator Management | L/M/H |
| IA-6 | Authentication Feedback | L/M/H |
| IA-7 | Cryptographic Module Authentication | L/M/H |
| IA-8 | ID and Auth (Non-Org Users) | L/M/H |
| IA-11 | Re-Authentication | L/M/H |
| IA-12 | Identity Proofing | M/H |

**Key Controls**:
- **IA-2**: MFA required for privileged accounts (M/H); for all accounts (H). IA-2(1): MFA for privileged network access. IA-2(2): MFA for non-privileged accounts
- **IA-5**: Password management — complexity, history, maximum age, minimum length. IA-5(1): Automated authenticator management
- **IA-4**: No reuse of identifiers; disabled accounts retain ID for 90 days before reassignment

---

## IR — Incident Response (10 controls)

**Purpose**: Establish operational incident-handling capability for detecting, containing, and recovering from security incidents.

| Control | Title | Baseline |
|---------|-------|---------|
| IR-1 | Policy and Procedures | L/M/H |
| IR-2 | Incident Response Training | L/M/H |
| IR-3 | Incident Response Testing | M/H |
| IR-4 | Incident Handling | L/M/H |
| IR-5 | Incident Monitoring | L/M/H |
| IR-6 | Incident Reporting | L/M/H |
| IR-7 | Incident Response Assistance | L/M/H |
| IR-8 | Incident Response Plan | L/M/H |
| IR-10 | Integrated Information Security Analysis Team | H |

**Key Controls**:
- **IR-4**: Incident response capability — detection, analysis, containment, eradication, recovery
- **IR-6**: Report incidents to US-CERT within 1 hour of detection (federal systems)
- **IR-8**: IRP document — roles, communication, evidence preservation, chain of custody

---

## MA — Maintenance (6 controls)

**Purpose**: Perform maintenance on systems and provide effective controls on the tools, techniques, mechanisms, and personnel that conduct maintenance.

Key: MA-2 (scheduled maintenance), MA-4 (nonlocal maintenance via encrypted channels), MA-5 (maintenance personnel screening)

---

## MP — Media Protection (9 controls)

**Purpose**: Protect system media, limit access to information on media, and sanitize before disposal or reuse.

Key: MP-2 (media access), MP-6 (media sanitization — NIST SP 800-88), MP-7 (media use restrictions)

---

## PE — Physical and Environmental Protection (20 controls)

**Purpose**: Limit physical access to systems, protect supporting infrastructure, and provide facilities with appropriate environmental controls.

Key: PE-2 (physical access authorizations), PE-3 (physical access control), PE-6 (monitoring), PE-13 (fire protection), PE-14 (temperature/humidity)

---

## PL — Planning (11 controls)

**Purpose**: Develop, document, and periodically update security and privacy plans describing the security and privacy controls in place.

Key: PL-2 (SSP — System Security Plan), PL-4 (rules of behavior / acceptable use), PL-8 (security and privacy architectures), PL-10 (baseline selection), PL-11 (baseline tailoring)

**BLACKSITE Mapping**: The SSP is the primary artifact. BLACKSITE's SSP route, SSP analyzer, and SSP two-mode output implement this control family.

---

## PM — Program Management (32 controls)

**Purpose**: Organization-wide information security and privacy program. Applied at the organization level, not individual systems.

Key: PM-1 (security program plan), PM-9 (risk management strategy), PM-10 (authorization process), PM-11 (mission/business process), PM-28 (risk framing), PM-30 (supply chain risk management strategy)

---

## PS — Personnel Security (9 controls)

**Purpose**: Ensure individuals occupying positions of responsibility are trustworthy and meet established security criteria.

Key: PS-3 (personnel screening), PS-4 (personnel termination — access removal within 24 hours), PS-5 (personnel transfer), PS-6 (access agreements), PS-7 (external personnel security)

---

## PT — Personally Identifiable Information Processing and Transparency (8 controls) [NEW in Rev 5]

**Purpose**: Implement the fair information practice principles and manage PII throughout the information lifecycle.

Key: PT-1 (policy), PT-2 (authority to process PII), PT-3 (purpose specification), PT-4 (consent), PT-5 (privacy notice), PT-6 (privacy preferences), PT-7 (specific categories of PII)

**Relationship to GDPR**: PT controls map closely to GDPR principles:
- PT-3 → GDPR Purpose Limitation (Art 5(1)(b))
- PT-4 → GDPR Consent (Art 6(1)(a))
- PT-5 → GDPR Transparency (Art 13-14)
- PT-7 → GDPR Special categories (Art 9)

---

## RA — Risk Assessment (10 controls)

**Purpose**: Assess security and privacy risks to operations, assets, individuals, and other organizations.

| Control | Title | Baseline |
|---------|-------|---------|
| RA-1 | Policy and Procedures | L/M/H |
| RA-2 | Security Categorization | L/M/H |
| RA-3 | Risk Assessment | L/M/H |
| RA-5 | Vulnerability Monitoring and Scanning | L/M/H |
| RA-7 | Risk Response | L/M/H |
| RA-9 | Criticality Analysis | M/H |

**Key Controls**:
- **RA-3**: Formal risk assessment — threats, vulnerabilities, likelihood, impact, risk level
- **RA-5**: Vulnerability scanning — weekly for internet-facing, monthly for internal; authenticated scans; false positive tracking

---

## SA — System and Services Acquisition (23 controls)

**Purpose**: Allocate sufficient resources to protect information systems, employ system development life cycle processes, and employ software development and system management practices.

Key: SA-3 (SDLC security integration), SA-4 (acquisition process), SA-8 (security engineering principles), SA-11 (developer testing), SA-15 (development process standards), SA-22 (unsupported components)

---

## SC — System and Communications Protection (51 controls)

**Purpose**: Monitor, control, and protect communications at the external boundaries and key internal boundaries.

Key: SC-7 (boundary protection — firewall, DMZ), SC-8 (transmission confidentiality — TLS), SC-12 (cryptographic key management), SC-13 (cryptographic protection — FIPS 140-3), SC-28 (data at rest protection — encryption), SC-39 (process isolation)

---

## SI — System and Information Integrity (23 controls)

**Purpose**: Identify, report, and correct information and information system flaws in a timely manner; provide protection from malicious code; and monitor system security alerts.

Key: SI-2 (flaw remediation — patching), SI-3 (malicious code protection), SI-4 (system monitoring — SIEM, IDS/IPS), SI-7 (software, firmware, and information integrity — FIPS 140-3 signed updates), SI-10 (information input validation), SI-12 (information management and retention)

---

## SR — Supply Chain Risk Management (12 controls) [NEW in Rev 5]

**Purpose**: Protect against supply chain risks by establishing supply chain risk management processes and practices.

Key: SR-1 (policy), SR-2 (supply chain risk management plan), SR-3 (supply chain controls and processes), SR-6 (supplier assessments and reviews), SR-8 (notification agreements), SR-11 (component authenticity)

---

## Control Status in BLACKSITE

BLACKSITE tracks control implementation through:
- `system_controls` table: `control_id`, `status`, `implementation_status`, `notes`
- Statuses: `not_started`, `in_progress`, `implemented`, `not_applicable`, `inherited`
- Implementation states: `planned`, `partially_implemented`, `implemented`, `alternative_implemented`, `not_implemented`
- SSP narratives: linked to controls with implementation descriptions

**POA&M ID Format**: `{ABBREVIATION}{YYYYMM}-{NNNN}AC{NN}` (e.g., `BSV022826-1001AC01`)

---

## References

- NIST SP 800-53 Rev 5 Full Text: https://doi.org/10.6028/NIST.SP.800-53r5
- NIST SP 800-53B (Baselines): https://doi.org/10.6028/NIST.SP.800-53Br5
- NIST 800-53 OSCAL Catalog: https://github.com/usnistgov/oscal-content/
- Control Overlay Repository: https://csrc.nist.gov/projects/cprt/catalog
