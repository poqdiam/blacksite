# NIST SP 800-61 Rev 3 — Computer Security Incident Handling Guide

**Document type:** GRC knowledge base reference
**Applies to:** ISSOs, ISSMs, Incident Responders, SCAs, AOs
**Source publication:** NIST Special Publication 800-61 Revision 3
**Status in BLACKSITE:** Authoritative reference for IR lifecycle tracking, observations, and daily logbook Task 1

---

## Overview

**NIST SP 800-61 Rev 3** is the authoritative federal guidance for establishing and operating a computer security incident response capability. It defines what constitutes an incident, how to detect and analyze security events, how to contain and recover from incidents, and how to improve over time.

An **incident** is defined as a violation or imminent threat of violation of computer security policies, acceptable use policies, or standard security practices. This is distinct from an **event** (any observable occurrence) and a **precursor** (a sign that an incident may occur in the future) or **indicator** (a sign that an incident may have occurred or is currently occurring).

SP 800-61 Rev 3 aligns with the broader NIST Cybersecurity Framework (CSF) and the Risk Management Framework (SP 800-37). It is required reading for systems with IR-4 (Incident Handling) control implementation and directly informs the IR control family.

---

## The Incident Response Lifecycle

SP 800-61 defines four phases that form a continuous cycle. Each phase feeds into the next, and lessons from post-incident activity improve preparation for future incidents.

```
Preparation → Detection & Analysis → Containment, Eradication & Recovery → Post-Incident Activity
      ↑_______________________________________________________________↓
```

---

## Phase 1: Preparation

**Preparation** is the foundation of every effective IR program. Incident response cannot be improvised; it must be planned, resourced, and practiced before an incident occurs.

### IR Policy and Plan

Every organization must have a written **Incident Response Policy** (required by IR-1) that defines:

- Scope: which systems and data types are covered
- Authority: who can declare an incident and authorize containment actions
- Roles and responsibilities: who does what during an incident
- Escalation thresholds: when to involve law enforcement, legal counsel, or executive leadership
- Retention requirements: how long IR records and evidence must be kept

The **Incident Response Plan** (required by IR-8) operationalizes the policy. It must be reviewed annually and updated after major incidents or significant organizational changes.

### Incident Response Team (IRT)

| Role | Responsibilities |
|---|---|
| **IR Lead / Incident Commander** | Coordinates response, makes containment decisions, interfaces with management |
| **IR Analyst** | Triage, log analysis, indicator correlation, timeline reconstruction |
| **Forensics Specialist** | Evidence preservation, disk/memory imaging, chain of custody |
| **System/Network SME** | Deep knowledge of affected systems; assists with containment and recovery |
| **Legal / Privacy Counsel** | Advises on disclosure obligations, law enforcement referral, privilege |
| **Public Affairs / Communications** | Manages external communications, press inquiries, regulatory notifications |
| **Executive Sponsor** | Authorizes extraordinary containment actions (e.g., taking systems offline) |

### Tools and Infrastructure

A prepared IR team maintains:

- **Jump kit**: laptop with IR tools (forensic imaging, log analysis, packet capture) not connected to the corporate network
- **Secure out-of-band communications**: encrypted messaging or phone bridge not dependent on potentially compromised infrastructure
- **Contact lists**: vendors, ISPs, CISA, US-CERT, law enforcement liaisons
- **Documentation templates**: incident tracking forms, chain of custody forms, timeline worksheets
- **Backup authentication**: emergency accounts not stored in potentially compromised directory services

### Training and Testing

- **IR-2 (Incident Response Training)**: role-based training for all personnel with IR responsibilities; must occur at hire and annually thereafter
- **IR-3 (Incident Response Testing)**: exercises must test the plan; types include tabletop exercises, functional drills, and full-scale simulations
- Tabletop exercises are minimum acceptable for Moderate systems; High systems require functional exercises at minimum

### Communications Plan

Define in advance:
- Internal notification chain (IR Lead → ISSO → ISSM → AO → Legal)
- External reporting obligations (CISA 1-hour notification for significant incidents, US-CERT reporting)
- Law enforcement contacts (FBI Cyber Division, USSS)
- Sector-specific reporting (HHS for HIPAA, SEC for financial sector, etc.)

---

## Phase 2: Detection and Analysis

### Indicators of Compromise (IoCs)

**Precursors** suggest an attack is being planned or staged:
- Scanning activity against organization systems
- Threat intelligence indicating targeting of your sector
- Vulnerability announcements for software in use without patches applied

**Indicators** suggest an attack is underway or has occurred:
- Alerts from SIEM, IDS/IPS, EDR tools
- Antivirus or anti-malware detections
- Unexpected outbound connections or data transfers
- Unusual authentication activity (off-hours, geographic anomalies, failed logins followed by success)
- Hash matches against known malware databases (VirusTotal, MISP)
- Log entries showing exploitation of known CVEs

### Incident Categories (CISA/US-CERT Taxonomy)

| Category | Code | Description | Examples |
|---|---|---|---|
| **Denial of Service** | CAT 1 | Attack that prevents or impairs authorized use of resources | DDoS, SYN flood, ransomware encryption locking systems |
| **Malicious Code** | CAT 2 | Malware installed or executing on systems | Ransomware, trojans, rootkits, worms, spyware |
| **Unauthorized Access** | CAT 3 | Gaining logical or physical access without permission | Exploited vulnerability, stolen credentials, insider threat |
| **Inappropriate Usage** | CAT 4 | Person violates acceptable use policy | Exfiltration of PII by employee, prohibited software installation |
| **Scans / Probes / Attempted Access** | CAT 5 | Reconnaissance that does not result in unauthorized access | Port scans, vulnerability scans, failed exploitation attempts |
| **Investigation** | CAT 6 | Unconfirmed incident; investigation in progress | Anomalous behavior with unclear cause |

### Incident Prioritization and Severity

Prioritization must account for functional impact, information impact, and recoverability.

| Severity | Criteria | Response SLA |
|---|---|---|
| **Critical** | Active exfiltration of classified/sensitive data; ransomware impacting mission-critical systems; confirmed APT activity; complete loss of system availability for high-impact system | Immediate — within 1 hour; executive notification within 2 hours |
| **High** | Unauthorized access confirmed; malware active on multiple systems; significant data breach suspected; partial loss of critical system availability | Within 4 hours; management notification same business day |
| **Medium** | Malware isolated to single endpoint; policy violation with data exposure; scanning from known malicious IP; suspected (unconfirmed) unauthorized access | Within 24 hours; standard IR workflow |
| **Low** | Policy violations with no data exposure; isolated scanning; spam with malicious attachment (not opened); precursor activity only | Within 72 hours; routine tracking |

### Documentation Requirements

Every incident must be documented from first notification through closure. The incident record must capture:

- **Incident ID**: unique identifier (link to BLACKSITE Incidents module)
- First observed timestamp (UTC)
- Reporting source (user, automated alert, external tip)
- Affected systems (hostnames, IPs, asset IDs)
- Incident category (CISA taxonomy)
- Severity level and justification
- Chronological timeline of all actions taken
- Personnel involved in response
- Containment and eradication actions with timestamps
- Final disposition and closure criteria

---

## Phase 3: Containment, Eradication, and Recovery

### Containment Strategies

**Short-term containment** stops the bleeding without preserving forensic evidence of activity:
- Network isolation (VLAN quarantine, ACL changes, firewall rules)
- Account disablement (compromised credentials)
- Process termination (malicious process on endpoint)
- System shutdown (last resort — destroys volatile evidence)

**Long-term containment** maintains operations while full remediation is prepared:
- Deploy patched/hardened system images to maintain availability
- Implement enhanced monitoring and alerting on affected segments
- Use alternate systems or manual workarounds for critical functions

**Decision factors for containment approach:**
- Need to keep attacker unaware while forensics is conducted
- Potential damage if system remains operational
- Need to preserve evidence (volatile vs. non-volatile)
- Service availability requirements
- Time and resources available

### Evidence Collection

**Chain of custody** must be maintained from the moment evidence is collected. Every transfer must be documented with:
- Who collected the evidence, when, and where
- Hash values (SHA-256) of disk images and file copies at time of collection
- Storage location and access controls
- Any subsequent access events

**Volatile data** (lost on shutdown — collect FIRST):
- Running processes and network connections (`ps`, `netstat`, `ss`)
- Logged-in users
- System time (record against UTC reference)
- Loaded kernel modules
- RAM contents (memory dump with tools like Volatility or WinPmem)
- ARP cache and routing table
- Open files and file handles

**Non-volatile data** (persists after shutdown):
- Disk images (use write blockers; image to separate media)
- Event logs (export before imaging — may be cleared)
- Firewall and network device logs
- Email server logs
- Backup copies of affected data

**Legal considerations:**
- Obtain written authorization before accessing user data (legal or policy authority)
- Do not access personal devices without appropriate legal process
- Preserve attorney-client privilege by involving legal counsel early in significant incidents
- Law enforcement involvement changes evidence handling requirements — coordinate before collecting

### Eradication Steps

1. Identify the root cause (vulnerability exploited, compromised credential, misconfiguration)
2. Remove all malicious artifacts: malware files, persistence mechanisms (registry keys, cron jobs, services), backdoors, attacker-created accounts
3. Patch or remediate the vulnerability or misconfiguration that enabled the incident
4. Rebuild systems from known-good images where full confidence in clean state cannot be achieved
5. Reset all credentials on affected systems (and potentially lateral movement targets)
6. Verify eradication through scanning and forensic review before returning to production

### Recovery Procedures

1. Restore from known-good backups (verify backup integrity before restoration)
2. Validate system functionality against pre-incident baseline
3. Implement enhanced monitoring on recovered systems (minimum 30 days post-recovery)
4. Gradually restore network connectivity (staged — not immediate full restoration)
5. Confirm with system owner and ISSO that system is ready to return to production
6. Document recovery completion and resume normal operations with documented lessons

---

## Phase 4: Post-Incident Activity

### Lessons Learned

A **Post-Incident Review (PIR)** or "after-action review" must be conducted after every significant incident, typically within two weeks of closure while details are fresh.

The PIR must address:
- Exact timeline of the incident from initial compromise to detection to containment
- What worked well in the response
- What did not work; what gaps were identified
- Whether the IR plan was followed; where it was insufficient
- Recommended improvements to detection, processes, tools, or training
- Whether controls (technical or procedural) should be updated

PIR findings must be tracked as action items and fed back into the **Preparation** phase.

### Evidence Retention

| Evidence Type | Retention Period | Notes |
|---|---|---|
| Incident records and reports | Minimum 3 years (federal systems) | Check system-specific records retention schedule |
| Disk images and forensic copies | Duration of any legal proceedings + 1 year | Do not destroy if litigation hold is in place |
| System and network logs | Minimum 1 year (NIST recommendation) | High-impact systems: 3+ years |
| Chain of custody documentation | Same as associated evidence | Must accompany all physical evidence |

---

## Ransomware Response Checklist

Ransomware is the most common high-severity incident type in federal and healthcare environments. The following checklist reflects CISA and FBI guidance.

**Immediate (0–1 hour):**
- [ ] Isolate affected systems from the network (do NOT power off unless directed — preserve forensics)
- [ ] Identify the scope: which systems are encrypted, which are not yet affected
- [ ] Identify the ransomware variant (ransom note, encrypted file extension, known IoCs)
- [ ] Preserve volatile evidence on unencrypted systems before isolation
- [ ] Notify IR Lead, ISSO, ISSM — escalate per severity matrix

**Short-term (1–24 hours):**
- [ ] Determine if backups are intact and not encrypted (test restore — do not assume)
- [ ] Identify patient zero: initial infection vector (phishing email, RDP exploitation, vulnerable service)
- [ ] Determine if data was exfiltrated before encryption (check egress logs, DNS logs, DLP alerts)
- [ ] Report to CISA (mandatory for federal agencies within 1 hour of identification for significant incidents)
- [ ] Engage FBI Cyber Division if data exfiltration confirmed or ransom demand received
- [ ] Do NOT pay ransom without legal and executive approval — payment does not guarantee decryption and may violate OFAC sanctions

**Eradication and Recovery:**
- [ ] Rebuild affected systems from clean images
- [ ] Patch the initial access vector before reconnecting
- [ ] Restore from verified clean backups
- [ ] Implement additional controls (MFA, network segmentation, EDR) before full restoration
- [ ] Monitor for re-infection aggressively for 30+ days

---

## IR Metrics

Track these metrics to measure and improve IR program effectiveness:

| Metric | Definition | Target |
|---|---|---|
| **MTTD** (Mean Time to Detect) | Average time from incident start to detection | Reduce over time; <24 hours for High/Critical |
| **MTTR** (Mean Time to Respond/Recover) | Average time from detection to full recovery | Reduce over time; <72 hours for High |
| **Incidents per month by category** | Volume trend by CISA category | Baseline, then trend analysis |
| **False positive rate** | Alerts investigated that were not incidents | <20% indicates well-tuned detection |
| **PIR completion rate** | Significant incidents with documented PIR | 100% |
| **IR plan test frequency** | Annual minimum; semi-annual for High systems | On schedule |
| **Repeat incidents** | Same root cause recurring | Target zero |

---

## HIPAA Breach Notification Integration

For systems handling **Protected Health Information (PHI)**, HIPAA's Breach Notification Rule (45 CFR §§ 164.400–414) imposes specific notification requirements that operate in parallel with FISMA/NIST IR requirements.

- **60-day notification deadline**: covered entities must notify affected individuals within 60 days of discovery of a breach (not discovery of the incident — discovery of whether a breach occurred)
- **HHS reporting**: breaches affecting 500+ individuals in a state must be reported to HHS simultaneously with individual notification; breaches affecting <500 individuals are reported on an annual log
- **Business associate breaches**: BAs must notify covered entities without unreasonable delay and within 60 days; the covered entity's clock does not start until the BA notifies them
- **Unsecured PHI threshold**: if PHI was encrypted with NIST-approved encryption and the key was not compromised, it is not considered "unsecured" and breach notification is not required
- **Risk assessment**: before concluding a breach occurred, perform a 4-factor risk assessment (nature/extent of PHI, who accessed it, whether data was actually acquired, risk mitigation extent)

---

## IR Control Family Reference

| Control | Name | Key Requirement |
|---|---|---|
| **IR-1** | Incident Response Policy and Procedures | Written IR policy; procedures for all IR phases; reviewed annually |
| **IR-2** | Incident Response Training | Role-based training at hire, annually, and after significant changes |
| **IR-3** | Incident Response Testing | Annual testing; tabletop minimum for Moderate; functional for High |
| **IR-4** | Incident Handling | IR capability covering preparation, detection, containment, eradication, recovery, PIR |
| **IR-5** | Incident Monitoring | Track and document incidents; maintain statistics |
| **IR-6** | Incident Reporting | Report to CISA/US-CERT; internal reporting chain defined |
| **IR-7** | Incident Response Assistance | Technical assistance resources available to users |
| **IR-8** | Incident Response Plan | Written IRP; distributed to stakeholders; updated after incidents and annually |
| **IR-9** | Information Spillage Response | Procedures for handling classified or sensitive information spillage |
| **IR-10** | Integrated Information Security Analysis Team | Coordination with government-wide IR analysis capability |

---

## BLACKSITE Platform Mappings

The following table maps BLACKSITE platform features to SP 800-61 requirements. Use this when building evidence packages for IR controls.

| SP 800-61 Requirement | BLACKSITE Feature | Evidence Path |
|---|---|---|
| IR-4: Incident handling lifecycle tracking | **Incidents module** | `/systems/{id}/incidents/` — create, categorize, track through lifecycle |
| IR-5: Incident monitoring and statistics | **Incidents module** (status dashboard, category breakdown) | Incident count by category and severity; trend data |
| IR-5: Precursor/indicator tracking | **Observations** | Security observations linked to systems; flagged as precursors or indicators |
| IR-4/IR-5: Detection evidence | **Audit log** | Platform audit trail captures who did what and when; admissible as detection timeline |
| IR-5: Daily security event triage | **Daily Logbook Task 1** (ISSO rotation Day 1) | Evidence label: "Security event triage log — [date]"; maps to IR-5 |
| IR-3: Exercise documentation | **Reports module** | Generate IR exercise report; upload to ATO document package |
| IR-8: IR Plan maintenance | **ATO document package** | Upload IRP as ATO document; version control tracked |
| POAM: Incident-driven findings | **POA&M module** | Incidents that identify control gaps → POAM items with IR root cause tag |
| PIR action items | **POAM module** | Post-incident review action items tracked as POAM entries |
| HIPAA breach tracking | **Incidents module** + custom fields | Incident record captures breach determination, HHS reporting status |

### Daily Logbook — IR Evidence Coverage

The ISSO rotation Day 1 task "Security Event Triage" generates direct evidence for IR-5 (Incident Monitoring). When completing this task in BLACKSITE:

1. Review open incidents and update status
2. Check new observations for escalation to incident status
3. Document triage decisions in the logbook entry
4. Attach any IoC hashes or detection signatures reviewed

This daily record, when consistent and complete, satisfies continuous monitoring evidence requirements for IR-5 at Moderate and High impact levels.

---

## Key References

- **NIST SP 800-61 Rev 3**: Computer Security Incident Handling Guide — primary source for all content in this document
- **NIST SP 800-86**: Guide to Integrating Forensic Techniques into Incident Response — evidence collection procedures
- **NIST SP 800-137**: Information Security Continuous Monitoring (ISCM) — detection and monitoring program integration
- **CISA Federal Incident Notification Guidelines**: mandatory reporting thresholds and timelines for federal agencies
- **CISA Ransomware Guide**: joint CISA-MS-ISAC guidance; updated guidance for federal environments
- **FBI Internet Crime Complaint Center (IC3)**: reporting mechanism for cyber crimes
- **US-CERT (CISA)**: national IR coordination body; receives mandatory incident reports from federal agencies
- **HIPAA Breach Notification Rule**: 45 CFR §§ 164.400–414 — parallel notification requirements for PHI
- **NIST SP 800-53 Rev 5, IR Control Family**: normative control requirements that this guidance implements
- **Executive Order 14028** (Improving the Nation's Cybersecurity): mandates IR improvements including logging, playbooks, and standardized reporting for federal agencies
