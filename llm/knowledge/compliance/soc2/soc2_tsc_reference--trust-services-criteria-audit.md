# SOC 2 Trust Services Criteria — Audit Reference

**Framework:** AICPA Trust Services Criteria (TSC)
**Applicability:** Service organizations handling customer data
**Document Type:** GRC Knowledge Base — Authoritative Reference
**Last Updated:** 2026-03-01

---

## Table of Contents

1. [SOC 2 Overview](#soc-2-overview)
2. [Type I vs Type II](#type-i-vs-type-ii)
3. [SOC 1 vs SOC 2 vs SOC 3](#soc-1-vs-soc-2-vs-soc-3)
4. [Five Trust Services Categories](#five-trust-services-categories)
5. [CC6 — Logical and Physical Access Controls](#cc6--logical-and-physical-access-controls)
6. [CC7 — System Operations](#cc7--system-operations)
7. [CC8 — Change Management](#cc8--change-management)
8. [CC9 — Risk Mitigation](#cc9--risk-mitigation)
9. [Common Controls Tested](#common-controls-tested)
10. [Evidence Requirements](#evidence-requirements)
11. [BLACKSITE Platform Mappings](#blacksite-platform-mappings)
12. [Relationship to NIST 800-53](#relationship-to-nist-800-53)
13. [Common Audit Findings and Remediation](#common-audit-findings-and-remediation)
14. [Key References](#key-references)

---

## SOC 2 Overview

**SOC 2** (System and Organization Controls 2) is an auditing framework developed by the **American Institute of Certified Public Accountants (AICPA)** to evaluate the information security controls of service organizations. It is governed by the **Trust Services Criteria (TSC)**, which replaced the older Trust Services Principles in 2017.

SOC 2 is not a certification — it is an **attestation report** issued by a licensed CPA firm after an audit. The report describes the service organization's system, the criteria applicable, management's assertions, and the auditor's opinion on whether controls were suitably designed (Type I) and/or operating effectively (Type II) during the audit period.

**Who needs SOC 2?**
- SaaS providers, cloud infrastructure companies, managed service providers (MSPs), data processors, and any service organization whose services affect the security, availability, processing integrity, confidentiality, or privacy of customer data.
- SOC 2 reports are commonly required by enterprise customers during vendor due diligence, and are frequently referenced in contractual obligations.

**Governing body:** AICPA — the report is issued under **AT-C Section 205** (Examination Engagements) of the Statements on Standards for Attestation Engagements (SSAE 18).

---

## Type I vs Type II

| Attribute | SOC 2 Type I | SOC 2 Type II |
|---|---|---|
| **Point in time vs period** | Point-in-time (single date) | Observation period (typically 6–12 months) |
| **What is tested** | Design of controls (are they suitable?) | Design AND operating effectiveness |
| **Evidence required** | Description of system + control design | Evidence of control operation over the period |
| **Auditor opinion** | Controls are suitably designed | Controls operated effectively throughout the period |
| **Market acceptance** | Lower — considered preliminary | Higher — standard expectation from enterprise customers |
| **Time to obtain** | Weeks | 6–12 months minimum |
| **Common use** | First-year programs, initial customer requests | Ongoing annual commitment; required by most enterprise contracts |

**Key distinction:** A Type II report is far more meaningful because it demonstrates that controls were not just designed but actually worked consistently over an extended period. "Suitably designed" means a control, if operating as described, would achieve its objective. "Operating effectively" means it actually did so throughout the period, with only minor exceptions.

---

## SOC 1 vs SOC 2 vs SOC 3

| Report Type | Scope | Primary Users | Governing Standard |
|---|---|---|---|
| **SOC 1** | Controls over financial reporting (ICFR) | User entity auditors, CFOs | SSAE 18 AT-C 320 |
| **SOC 2** | Security, Availability, PI, Confidentiality, Privacy | Customers, prospects, regulators | SSAE 18 AT-C 205 + TSC |
| **SOC 3** | Same criteria as SOC 2, general use summary | General public, marketing | SSAE 18 AT-C 205 + TSC |

**SOC 1** evaluates controls at a service organization that are relevant to a user entity's **internal control over financial reporting**. A payroll processor, for example, would need a SOC 1 because errors in payroll data affect a customer's financial statements. SOC 1 uses **SSAE 18 AT-C Section 320** and maps to the **COSO Internal Control framework**.

SOC 1 and SOC 2 can coexist — a company processing financial data and holding sensitive security data may issue both.

**SOC 3** is a public-facing summary version of SOC 2. The organization may display the SOC 3 seal on its website; the full SOC 2 report is restricted to customers and NDA-protected parties.

---

## Five Trust Services Categories

The TSC is organized into five categories. **Security (CC)** is mandatory. The others are **optional** and added based on the service organization's commitments to customers.

### 1. Security (Common Criteria — CC)

The mandatory baseline. Covers the controls that protect against unauthorized access, unauthorized disclosure, and damage to systems. Organized into nine control criteria families (CC1–CC9). Applicable to all SOC 2 engagements regardless of other categories included.

**Focus areas:** Entity-level controls (tone at the top, governance), risk assessment processes, logical and physical access, system operations, change management, risk mitigation.

### 2. Availability (A)

**Availability** criteria address whether systems are available for operation and use as committed. Relevant for organizations where downtime affects customers (e.g., uptime SLAs).

| Criterion | Description |
|---|---|
| A1.1 | Availability commitments and SLAs documented |
| A1.2 | Environmental protections, redundancy, and backup |
| A1.3 | Recovery testing and procedures |

### 3. Processing Integrity (PI)

**Processing Integrity** addresses whether system processing is complete, valid, accurate, timely, and authorized. Relevant for payment processors, data pipelines, financial services.

| Criterion | Description |
|---|---|
| PI1.1 | Procedures to initiate, authorize, record inputs |
| PI1.2 | Processing is accurate and complete |
| PI1.3 | Outputs are distributed only to intended recipients |
| PI1.4 | Records retained per commitment |
| PI1.5 | Quality assurance activities |

### 4. Confidentiality (C)

**Confidentiality** criteria cover whether information designated as confidential is protected as committed. Relevant for organizations handling trade secrets, NDA-protected data, or any data contractually obligated to be held confidential.

| Criterion | Description |
|---|---|
| C1.1 | Confidential information is identified and protected |
| C1.2 | Confidential information is disposed of when no longer needed |

### 5. Privacy (P)

**Privacy** addresses the collection, use, retention, disclosure, and disposal of **personal information** in accordance with the organization's privacy notice and applicable law (GDPR, CCPA, etc.). Relevant for B2C companies or any organization that collects and processes personal data.

| Criterion | Description |
|---|---|
| P1.x | Notice and communication of objectives |
| P2.x | Choice and consent |
| P3.x | Collection |
| P4.x | Use, retention, and disposal |
| P5.x | Access |
| P6.x | Disclosure and notification |
| P7.x | Quality |
| P8.x | Monitoring and enforcement |

---

## CC6 — Logical and Physical Access Controls

CC6 is the most heavily tested criterion family in SOC 2. Auditors spend significant time here because access controls are foundational to preventing unauthorized disclosure, modification, and destruction.

### CC6.1 — Registration and Authorization

The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events to meet the entity's objectives.

**Key controls tested:**
- Unique user IDs assigned to all individuals
- Access provisioning process requires formal request and approval
- Role-based access control (RBAC) implemented
- Access to production systems restricted by job function
- Separation of duties enforced (developers do not deploy to production)
- Privileged access (admin) requires separate elevated account
- Service accounts inventoried and managed

**Common evidence:** Access provisioning tickets, RBAC matrix, list of privileged accounts, screenshots of access control configuration.

### CC6.2 — Prior to Issuance of Access Credentials

Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users.

**Key controls tested:**
- Background checks for employees with privileged access
- New hire provisioning workflow (manager approval)
- Contractor access provisioning with defined scope and expiry

### CC6.3 — Internal Users: Remove Access Promptly

The entity removes system access when no longer needed.

**Key controls tested:**
- Offboarding procedures — access revoked within defined SLA (typically same day or within 24 hours for high-risk roles)
- Quarterly or semi-annual **access reviews** — managers certify that employees still need their access
- User access reports reviewed and exceptions investigated

**Common evidence:** Offboarding tickets, access review results, terminated user reports, HR-to-IT termination notification log.

### CC6.4 — Restricts Physical Access

Physical access to facilities and protected information assets (including hardware and data storage) is restricted to authorized personnel.

**Key controls tested:**
- Data center physical access controls (badge readers, biometrics)
- Physical access logs reviewed
- Visitor access procedures
- Clean desk policy
- Lock and key management for server rooms

### CC6.5 — Disposal of Assets

Logical and physical protections are maintained when disposing of assets.

**Key controls tested:**
- Media sanitization procedure (NIST 800-88)
- Certificate of destruction for retired hardware
- Mobile device management (MDM) remote wipe capability

### CC6.6 — Logical Access Restrictions from External Sources

Logical access security measures to protect against threats from sources outside its system boundaries.

**Key controls tested:**
- Firewall rules documented and reviewed
- VPN required for remote access to internal systems
- Multi-factor authentication (**MFA**) for all external-facing access
- Remote access session timeout
- Intrusion detection/prevention systems (IDS/IPS)

**Common evidence:** Firewall configuration documentation, VPN configuration, MFA enrollment reports.

### CC6.7 — Transmission and Movement of Data

The entity restricts the transmission, movement, and removal of information to authorized internal and external users and processes.

**Key controls tested:**
- Encryption in transit (TLS 1.2 minimum, TLS 1.3 preferred)
- Data loss prevention (DLP) tools
- Prohibition of email transmission of sensitive data
- USB/removable media controls
- Secure file transfer protocols enforced

### CC6.8 — Prevent or Detect Unauthorized Software

The entity implements controls to prevent or detect and act upon the introduction of unauthorized or malicious software.

**Key controls tested:**
- Endpoint detection and response (EDR) / antivirus deployed
- Software installation restricted to approved applications
- Code signing requirements for production deployments
- Application allowlisting in high-risk environments
- Vulnerability scanning for software components

---

## CC7 — System Operations

CC7 addresses ongoing monitoring and detection of security events during system operations.

| Criterion | Description | Key Controls |
|---|---|---|
| **CC7.1** | Detect vulnerabilities and threats | Vulnerability management program, scanning schedule, patch SLAs |
| **CC7.2** | Monitor for anomalies and indicators of compromise | SIEM, log aggregation, alerting rules, threat intelligence feeds |
| **CC7.3** | Evaluate and resolve security events | Incident triage process, severity classification, escalation paths |
| **CC7.4** | Respond to identified security incidents | Incident response plan, IR tabletop exercises, lessons learned |
| **CC7.5** | Recover from identified security incidents | Recovery procedures, RTO/RPO objectives, post-incident review |

**Evidence for CC7:**
- Audit logs showing continuous monitoring activity
- Vulnerability scan reports with remediation status
- Incident register (even if no incidents occurred — shows process exists)
- SIEM alert rule documentation
- Penetration test reports
- Patch management reports showing timely remediation

---

## CC8 — Change Management

CC8 controls ensure that changes to systems, infrastructure, and software are authorized, tested, and documented to prevent unauthorized or unintended modifications.

| Criterion | Description | Key Controls |
|---|---|---|
| **CC8.1** | Manage changes to infrastructure, data, and software | Change management policy, change tickets, CAB approval process, emergency change procedures |

**Key sub-controls under CC8.1:**
- Changes require documented approval before implementation
- Testing performed in non-production environment before deployment
- Change rollback procedures defined
- Code review process (peer review or automated)
- Production deployments logged with change ticket reference
- Segregation of development and production environments
- Release management procedures

**Evidence for CC8:**
- Change tickets (Jira, ServiceNow, etc.) showing approval workflow
- Deployment logs
- Code review records (pull request approvals)
- Test results attached to change records
- Rollback procedure documentation

---

## CC9 — Risk Mitigation

CC9 addresses identification and management of risks related to business disruption and vendor relationships.

| Criterion | Description |
|---|---|
| **CC9.1** | Identify, select, and develop risk mitigation activities for risks arising from potential business disruptions |
| **CC9.2** | Assess and manage risks associated with vendors and business partners |

**CC9.2 — Vendor Risk Management key controls:**
- Vendor inventory / third-party register maintained
- Vendor risk assessments performed before onboarding critical vendors
- Contracts include security requirements and right-to-audit clauses
- Critical vendor SOC 2 reports reviewed annually
- Sub-service organization controls (carve-in vs carve-out scope decisions)
- Annual vendor review cadence

**Evidence for CC9:**
- Vendor register
- Completed vendor risk assessments
- Vendor SOC 2 report review records
- Business continuity plan (BCP)
- Business impact analysis (BIA)
- BCP/DR test results

---

## Common Controls Tested

The following controls appear across nearly every SOC 2 engagement regardless of Trust Services Categories selected:

| Control Area | Common Test Procedures |
|---|---|
| **Access Reviews** | Inspect quarterly/semi-annual user access reviews; verify manager sign-off; verify exceptions remediated |
| **Multi-Factor Authentication** | Verify MFA enforced on VPN, cloud consoles, email, and admin portals; check enrollment reports |
| **Encryption at Rest** | Verify database and storage encryption enabled; review key management procedures |
| **Encryption in Transit** | Verify TLS 1.2+ enforced; check certificate management; test for deprecated protocols |
| **Backup and Recovery** | Verify backups run on schedule; verify restore tests performed; review RTO/RPO documentation |
| **Vulnerability Management** | Review scan frequency and coverage; verify critical/high findings remediated within SLA |
| **Incident Response** | Review IR plan currency; inspect incident log; verify tabletop or drill conducted |
| **Security Awareness Training** | Verify all employees completed training; phishing simulation results |
| **Endpoint Protection** | Verify EDR/AV deployed on all endpoints; verify signature updates; alert review |
| **Logging and Monitoring** | Verify audit logs enabled, centrally collected, protected from tampering, retained per policy |

---

## Evidence Requirements

### Type I Evidence
- System description document
- Control design documentation (policies, procedures)
- Screenshots or configuration exports showing controls are in place as of the report date

### Type II Evidence
Evidence must demonstrate **consistent operation** of controls throughout the audit period (typically 6–12 months):

| Evidence Category | Examples |
|---|---|
| **Policies and Procedures** | Information security policy, access management policy, change management policy, incident response policy |
| **Access Control Evidence** | Quarterly access review logs, user provisioning/deprovisioning tickets for sampled employees |
| **Monitoring Evidence** | SIEM alert reports, vulnerability scan reports (monthly or weekly depending on policy), patch management reports |
| **Change Management Evidence** | Change tickets for sampled production changes during the period, showing approval and test evidence |
| **Incident Evidence** | Incident log (all incidents during period), IR reports for any significant events |
| **Training Evidence** | LMS completion reports for all employees during the period |
| **Vendor Evidence** | Vendor risk assessments, third-party SOC 2 reports reviewed during the period |
| **Backup Evidence** | Automated backup success/failure logs, restore test documentation |

**Sampling:** Auditors typically use attribute sampling. For a 12-month period with daily controls, expect samples of 25–60 items. For monthly controls, all instances may be examined. Higher deviation rates in samples lead to more testing and potential qualified opinions.

---

## BLACKSITE Platform Mappings

BLACKSITE provides features that directly support SOC 2 evidence collection and audit readiness:

| BLACKSITE Feature | SOC 2 Criterion | Evidence Value |
|---|---|---|
| **Audit Log** (all user actions timestamped) | CC7.1, CC7.2, CC7.3 | Demonstrates continuous monitoring; log review activity; event detection trail |
| **Daily Logbook** (ISSO daily operations log) | CC7.2, CC7.3 | Shows ongoing monitoring discipline; supports Type II operating effectiveness |
| **Access Spot Check** (scheduled access reviews) | CC6.3, CC6.7 | User access review evidence; manager certifications tracked |
| **Vendor Records** (vendor inventory + risk assessments) | CC9.2 | Third-party risk management; vendor register; assessment history |
| **POA&M** (Plan of Action and Milestones) | CC7.4, CC4.2 | Deficiency tracking; remediation timelines; risk acceptance documentation |
| **System Inventory** | CC6.1, CC9.1 | Authoritative asset register; system boundary documentation |
| **Interconnection Records** | CC6.6, CC6.7 | Data flow documentation; external connection inventory |
| **Observations** | CC7.3, CC4.2 | Security event log; finding severity classification |
| **Control Assessment** | CC4.1 | Evidence of control testing; CAAT documentation |
| **RMF Tracker** | CC3.1, CC3.2 | Formal risk assessment documentation; risk register |
| **Incident Response Records** | CC7.3, CC7.4, CC7.5 | IR process evidence; response timelines; lessons learned |
| **Change Review Records** | CC8.1 | Change management evidence; approval workflow documentation |

**Note for auditors:** BLACKSITE exports are timestamped and include user attribution, making them suitable as primary evidence. Supplement with underlying system logs for completeness.

---

## Relationship to NIST 800-53

SOC 2 TSC and NIST SP 800-53 share many underlying control objectives. The mapping is not one-to-one, but the following table provides approximate alignment:

| SOC 2 Criterion | NIST 800-53 Control Family |
|---|---|
| CC1.x (Control Environment) | PM (Program Management), PL (Planning) |
| CC2.x (Communication and Information) | AT (Awareness and Training), PL |
| CC3.x (Risk Assessment) | RA (Risk Assessment) |
| CC4.x (Monitoring Activities) | CA (Assessment, Authorization, Monitoring) |
| CC5.x (Control Activities) | SA (System and Services Acquisition), PL |
| CC6.1–CC6.3 (Logical Access) | AC (Access Control), IA (Identification and Authentication) |
| CC6.4 (Physical Access) | PE (Physical and Environmental Protection) |
| CC6.5 (Disposal) | MP (Media Protection) |
| CC6.6 (External Threats) | SC (System and Communications Protection), SI |
| CC6.7 (Data Transmission) | SC (System and Communications Protection) |
| CC6.8 (Malicious Software) | SI-3 (Malicious Code Protection) |
| CC7.1 (Vulnerability Detection) | RA-5 (Vulnerability Monitoring and Scanning) |
| CC7.2 (Monitoring) | AU (Audit and Accountability), SI-4 |
| CC7.3–CC7.5 (Incident Response) | IR (Incident Response) |
| CC8.1 (Change Management) | CM (Configuration Management), SA |
| CC9.1 (Business Risk) | CP (Contingency Planning), RA |
| CC9.2 (Vendor Risk) | SA-9 (External System Services) |
| A1.x (Availability) | CP (Contingency Planning), SC |
| C1.x (Confidentiality) | SC, MP, AC |
| P1–P8 (Privacy) | PT (Personally Identifiable Information Processing) |

Organizations pursuing both SOC 2 and FedRAMP or FISMA compliance can leverage significant control overlap. NIST 800-53 controls implemented for federal compliance often satisfy corresponding SOC 2 criteria with minimal additional effort.

---

## Common Audit Findings and Remediation

### Finding 1: Access Reviews Not Performed Consistently
**Criterion:** CC6.3
**Description:** Quarterly access reviews were not completed for all systems or were not completed within required timeframes. Terminated users retained access beyond the 24-hour policy window.
**Remediation:** Implement automated offboarding triggers integrated with HR system; schedule access reviews as recurring tasks with tracking in GRC tool; document exceptions with risk acceptance.

### Finding 2: MFA Not Enforced on All In-Scope Systems
**Criterion:** CC6.6
**Description:** MFA was configured but not enforced (users could bypass), or was not applied to all systems accessing cardholder/sensitive data.
**Remediation:** Enforce MFA at the identity provider level; verify conditional access policies block non-MFA sessions; document any approved exceptions with compensating controls.

### Finding 3: Patch Management SLAs Not Met
**Criterion:** CC7.1
**Description:** Critical vulnerabilities identified in scanning were not remediated within the policy-defined SLA. Evidence of remediation not documented in vulnerability management system.
**Remediation:** Implement ticketing integration with vulnerability scanner; define escalation path for SLA breaches; review and tighten SLAs if currently unrealistic.

### Finding 4: Change Tickets Lacking Approvals or Test Evidence
**Criterion:** CC8.1
**Description:** Sampled production changes did not have documented approvals, or test results were not attached to the change record.
**Remediation:** Gate deployments on approved change ticket in CI/CD pipeline; require test evidence to be uploaded before ticket can move to "approved" state.

### Finding 5: Vendor Risk Assessments Not Performed or Not Current
**Criterion:** CC9.2
**Description:** Critical sub-processors lacked current (within 12 months) risk assessments. Vendor SOC 2 reports not reviewed or not available for all critical vendors.
**Remediation:** Maintain vendor register with assessment due dates; require new vendor risk assessment before contract signature; document review of vendor SOC 2 reports annually.

### Finding 6: Audit Logs Not Retained Per Policy
**Criterion:** CC7.2
**Description:** Logs older than 30 days were not retained; policy required 12-month retention. Log integrity could not be verified.
**Remediation:** Configure log aggregation platform with appropriate retention policy; enable log immutability/tamper detection (WORM storage); document log retention in security policy.

### Finding 7: Incident Response Plan Not Tested
**Criterion:** CC7.4
**Description:** IR plan existed but no tabletop exercise or drill was conducted during the audit period.
**Remediation:** Schedule annual tabletop exercise (minimum); document participants, scenario, and lessons learned; update IR plan based on findings.

---

## Key References

- **AICPA TSC 2017 (with 2022 points of focus update):** https://www.aicpa-cima.com/resources/landing/trust-services-criteria
- **AICPA SOC 2 Guide:** *Reporting on an Examination of Controls at a Service Organization Relevant to Security, Availability, Processing Integrity, Confidentiality, or Privacy*
- **SSAE 18 AT-C Section 205:** Statements on Standards for Attestation Engagements No. 18
- **NIST SP 800-53 Rev 5:** Security and Privacy Controls for Information Systems and Organizations
- **NIST SP 800-53A Rev 5:** Assessing Security and Privacy Controls
- **Cloud Security Alliance CCM:** Cloud Controls Matrix (maps SOC 2 to cloud security controls)
- **SOC 2 to ISO 27001 Mapping:** AICPA and ISO provide guidance on cross-framework alignment

---

*This document is part of the BLACKSITE GRC Platform knowledge base. It is intended as a practitioner reference and does not constitute legal or audit advice. Consult a licensed CPA firm for SOC 2 examination services.*
