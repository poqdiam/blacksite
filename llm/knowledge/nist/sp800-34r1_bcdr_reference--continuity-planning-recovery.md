# NIST SP 800-34 Rev 1 — Contingency Planning Guide for Federal Information Systems

**Document type:** GRC knowledge base reference
**Applies to:** BCDR Coordinators, ISSOs, ISSMs, System Owners, SCAs
**Source publication:** NIST Special Publication 800-34 Revision 1
**Status in BLACKSITE:** Authoritative reference for contingency planning, restore test records, backup checks, and BCDR coordinator rotation tasks

---

## Overview

**NIST SP 800-34 Rev 1** provides comprehensive guidance for developing, testing, and maintaining contingency plans for federal information systems. A **contingency plan** is a management policy and procedure document used to guide an organization through the steps required to resume operations after a disruptive event.

SP 800-34 distinguishes between disruptions at different layers — the organization, the facility, and the IT system — and provides a hierarchy of plan types to address each. For most ISSO and BCDR coordinator work, the **IT Contingency Plan (ITCP)** is the primary artifact, but it must align with and reference the broader organizational continuity plans.

The overarching goal is ensuring **mission-essential functions** can continue or be rapidly restored following a disruptive event, whether caused by a natural disaster, cyberattack, hardware failure, or human error.

---

## Seven Contingency Plan Types

SP 800-34 defines seven distinct plan types. Each addresses a different scope of disruption. Organizations must maintain all applicable types and ensure they are coordinated and cross-referenced.

| Plan Type | Abbreviation | Scope | Primary Owner |
|---|---|---|---|
| **Business Continuity Plan** | BCP | Overall business operations continuity during a disruption | Senior management / COOP coordinator |
| **Continuity of Operations Plan** | COOP | Continuation of mission-essential functions during emergency relocation | Executive leadership / COOP coordinator |
| **Continuity of Government Plan** | COG | Preserving constitutional government during a catastrophic emergency | Federal executive bodies |
| **Crisis Communications Plan** | CCP | Internal and external communications during and after a crisis | Public affairs / communications team |
| **Cyber Incident Response Plan** | CIRP | Response to cybersecurity incidents affecting information systems | ISSO / IR Team |
| **IT Contingency Plan** | ITCP | Recovery of specific IT systems after a disruption | ISSO / System Owner / BCDR Coordinator |
| **Occupant Emergency Plan** | OEP | Procedures for protecting life and property at a physical facility | Facility manager / security officer |

---

## IT Contingency Plan (ITCP) — Primary Focus

The **ITCP** is the plan most directly controlled by ISSOs and BCDR coordinators. It addresses the recovery of a specific information system and must be tailored to that system's FIPS 199 impact level, criticality to the mission, and operational dependencies.

### Business Impact Analysis (BIA)

The **Business Impact Analysis** is the analytical foundation of the ITCP. Without a current BIA, RTO/RPO values are guesses rather than requirements.

The BIA process:

1. **Identify mission-essential functions** that depend on the system
2. **Identify system resources** required to support each function (data, applications, infrastructure, personnel, physical facilities)
3. **Determine Maximum Tolerable Downtime (MTD)** for each function — the absolute maximum time the function can be unavailable before mission failure or unacceptable harm
4. **Derive RTO and RPO** from the MTD (RTO must be less than MTD; RPO defines acceptable data loss)
5. **Document system interdependencies** — other systems that feed into or depend on the subject system
6. **Prioritize recovery** — not all systems recover at once; BIA drives recovery sequence

#### BIA Output: RTO/RPO Table Template

| System / Function | FIPS 199 Impact | MTD | RTO | RPO | Recovery Priority |
|---|---|---|---|---|---|
| Core authentication (AD/LDAP) | High | 4 hours | 2 hours | 15 minutes | 1 — recover first |
| Case management application | Moderate | 72 hours | 24 hours | 4 hours | 2 |
| Email / communications | Moderate | 48 hours | 8 hours | 1 hour | 3 |
| Reporting / analytics | Low | 30 days | 7 days | 24 hours | 4 |
| Archival storage | Low | 90 days | 14 days | 72 hours | 5 |

### Key Terms Defined

**MTD (Maximum Tolerable Downtime)**: The maximum time a system can be unavailable before the disruption causes unacceptable consequences to the mission. MTD is derived from mission/business impact analysis, not from technical capability. It is the upper bound — all recovery objectives must fall within it.

**RTO (Recovery Time Objective)**: The targeted time within which a system must be restored to operational status following a disruption. RTO is set during the BIA and drives recovery strategy selection. RTO < MTD always.

**RPO (Recovery Point Objective)**: The maximum acceptable amount of data loss measured in time. An RPO of 4 hours means the organization can tolerate losing up to 4 hours of transactions. RPO drives backup frequency — if your backup window is daily but your RPO is 4 hours, you have a gap.

**MTTR (Mean Time to Recover)**: The actual average time it takes to restore a system. MTTR is a measured metric used to validate that RTO targets are achievable. If MTTR consistently exceeds RTO, the recovery strategy must be improved.

---

## Recovery Strategies

### Alternative Processing Sites

| Site Type | Description | Activation Time | Cost | Best For |
|---|---|---|---|---|
| **Hot Site** | Fully operational duplicate environment; data replicated in near real-time | Minutes to hours | Highest | High-impact systems; RTOs <4 hours |
| **Warm Site** | Pre-configured environment; requires data restoration before use | Hours to days | Moderate | Moderate-impact systems; RTOs 4–72 hours |
| **Cold Site** | Physical space with power/connectivity; no equipment or data pre-staged | Days to weeks | Lowest | Low-impact systems; RTOs >7 days |
| **Mobile Site** | Trailer-based pre-configured site that can be deployed to a location | Days | Moderate-High | Organizations with geographic flexibility needs |
| **Mirrored Site** | Exact real-time duplicate; full operational capacity immediately | Seconds to minutes | Highest | Mission-critical systems; near-zero RTO |
| **Cloud-based Recovery** | Recovery to IaaS/PaaS; spin up on demand | Hours (first activation) | Variable | Modern systems with cloud-compatible architecture |

### Backup Methods

| Method | Description | RPO Support | Recovery Speed |
|---|---|---|---|
| **Full backup** | Complete copy of all data | Up to backup interval | Fastest restore (single backup set) |
| **Incremental backup** | Only data changed since last backup (full or incremental) | Up to backup interval | Slower — must restore full + all incrementals in sequence |
| **Differential backup** | Data changed since last full backup | Up to backup interval | Moderate — restore full + latest differential only |
| **Continuous Data Protection (CDP)** | Real-time or near-real-time replication | Near-zero RPO | Fast — point-in-time restore |
| **Snapshot** | Point-in-time copy at storage layer | Up to snapshot frequency | Fast — restore from snapshot |

**3-2-1 Backup Rule**: 3 copies of data, on 2 different media types, with 1 copy off-site. This is the minimum acceptable backup strategy for Moderate-impact systems.

### Redundancy Approaches

- **Geographic redundancy**: primary and backup sites in different seismic/weather zones
- **Network redundancy**: multiple ISPs or circuit paths to avoid single points of failure
- **Power redundancy**: UPS + generator for facility power; redundant PDUs for rack-level
- **Storage redundancy**: RAID configurations, replicated SAN/NAS
- **Application redundancy**: clustering, load balancing, failover configurations

---

## ITCP Document Structure

A complete ITCP must include these sections:

1. **Purpose and Scope**: what systems are covered; what disruption scenarios the plan addresses
2. **Applicable Regulations and Policies**: FISMA, SP 800-34, agency-specific policies, HIPAA if applicable
3. **Concept of Operations**: high-level description of how the plan works; decision authorities
4. **System Description and Architecture**: current system configuration, dependencies, data flows
5. **Activation and Notification**: criteria for activating the plan; notification tree with names, roles, and contact information
6. **Recovery Procedures**: step-by-step procedures for each disruption scenario; organized by priority (most critical systems first)
7. **Reconstitution Procedures**: steps to validate full recovery and return to normal operations; testing that primary site is safe before deactivating alternate site
8. **Maintenance Schedule**: plan review frequency, testing schedule, update triggers
9. **Appendices**: contact lists, system inventory, vendor contacts, backup schedules, network diagrams

---

## FIPS 199 Impact Level → Contingency Planning Requirements

The system's FIPS 199 impact level drives the rigor of contingency planning and testing requirements.

| Requirement | LOW | MODERATE | HIGH |
|---|---|---|---|
| Written ITCP required | Yes | Yes | Yes |
| BIA required | Yes | Yes | Yes |
| Minimum testing type | Checklist review | Tabletop exercise | Parallel or full interruption |
| Testing frequency | Annual | Annual | Annual (semi-annual recommended) |
| Off-site backup required | Yes | Yes | Yes |
| Alternate processing site required | No (recommended) | Yes | Yes |
| Hot site required | No | No (warm acceptable) | Yes (or equivalent) |
| Recovery time target range | 7–30 days | 24 hours–7 days | <24 hours (often <4 hours) |

---

## Testing Requirements (CP-4)

**CP-4 (Contingency Plan Testing)** requires annual testing of the contingency plan. The type of test must be appropriate to the system's impact level.

| Test Type | Description | Suitable For |
|---|---|---|
| **Checklist Review** | Plan reviewed by key personnel for completeness and currency; no operational test | LOW systems; minimum acceptable |
| **Tabletop Exercise** | Facilitated walk-through of the plan using a simulated scenario; no actual systems activated | LOW-MODERATE systems |
| **Functional Exercise** | Simulated activation of the alternate site and key recovery procedures; systems may be partially activated in test environment | MODERATE-HIGH systems |
| **Parallel Test** | Alternate site activated and validated while primary site remains operational; production load split or mirrored | HIGH systems |
| **Full Interruption Test** | Primary site taken offline; full failover to alternate site; production operations run from alternate site | HIGH systems; highest confidence; highest risk |

### Testing Documentation Requirements

After every test, document:
- Date and type of test
- Participants and their roles
- Scenario used (for tabletop/functional)
- Procedures tested and results for each step
- Issues identified (deviations from expected, failures, gaps)
- Corrective actions required, with owners and due dates
- Confirmation that the plan was updated based on test results

Test results must be retained and provided as evidence for CP-4 during assessments.

---

## CP Control Family Reference

| Control | Name | Key Requirement |
|---|---|---|
| **CP-1** | Contingency Planning Policy and Procedures | Written policy; procedures for all CP activities; reviewed annually |
| **CP-2** | Contingency Plan | Documented ITCP; BIA; RTO/RPO defined; reviewed annually; distributed |
| **CP-3** | Contingency Training | Role-based training for contingency plan personnel; annual |
| **CP-4** | Contingency Plan Testing | Annual test; appropriate type for impact level; results documented; plan updated |
| **CP-6** | Alternate Storage Site | Off-site backup storage; separation distance from primary; protection equivalent to primary |
| **CP-7** | Alternate Processing Site | Alternate site for processing if primary site unavailable; agreements in place |
| **CP-8** | Telecommunications Services | Primary and alternate telecom providers; priority restoration agreements |
| **CP-9** | System Backup | Regular backups; test restores; off-site storage; backup integrity verification |
| **CP-10** | System Recovery and Reconstitution | Full recovery capability; reconstitution to known secure state |
| **CP-11** | Alternate Communications Protocols | Alternate protocols if primary protocols are unavailable |
| **CP-12** | Safe Mode | System operates in degraded safe mode when components fail |
| **CP-13** | Alternative Security Mechanisms | Alternate security mechanisms when primary mechanisms are unavailable |

---

## HIPAA Contingency Plan Requirements

For systems processing **Electronic Protected Health Information (ePHI)**, HIPAA's Security Rule at **45 CFR § 164.308(a)(7)** mandates a contingency plan with five required implementation specifications:

| HIPAA Specification | Required or Addressable | Description |
|---|---|---|
| **Data Backup Plan** | Required | Procedures to create and maintain exact retrievable copies of ePHI |
| **Disaster Recovery Plan** | Required | Procedures to restore lost data; covers hardware and software |
| **Emergency Mode Operations Plan** | Required | Procedures to enable continuation of critical business processes for protection of ePHI security during operation in emergency mode |
| **Testing and Revision Procedures** | Addressable | Procedures for periodic testing and revision of contingency plans |
| **Applications and Data Criticality Analysis** | Addressable | Assessment of the relative criticality of applications and data in support of contingency plan components |

"Addressable" under HIPAA does not mean optional — it means the covered entity must assess whether the specification is reasonable and appropriate and either implement it or document why an equivalent alternative measure was used instead.

**HIPAA Contingency Plan + SP 800-34 Alignment**: A well-constructed ITCP under SP 800-34 satisfies all five HIPAA contingency plan requirements. When writing the ITCP for a HIPAA-covered system, explicitly cite the HIPAA specifications each section addresses.

---

## BCDR in Cloud Environments

Cloud adoption adds complexity to contingency planning. Key considerations:

### Shared Responsibility for Availability

Cloud Service Providers (CSPs) are responsible for infrastructure availability (data center uptime, network backbone, physical hardware). However:
- The **agency or system owner** is responsible for application-level availability, data backup configuration, and recovery procedures
- CSP SLAs define uptime guarantees (typically 99.9%–99.99%) but do not guarantee recovery from data deletion, misconfiguration, or ransomware
- **RPO and RTO must be explicitly negotiated** in cloud service contracts; do not assume CSP defaults align with mission requirements

### FedRAMP Cloud Services

If using a **FedRAMP-authorized CSP**, that CSP's authorization package includes contingency planning controls. Review the CSP's SSP and Customer Responsibility Matrix to understand:
- Which CP controls the CSP implements (inherited controls)
- Which CP controls the agency must implement (customer-responsible controls)
- CSP's documented RTO/RPO for infrastructure services

### Cloud BCDR Best Practices

- Enable **cross-region replication** for critical data stores
- Use **infrastructure as code (IaC)** to enable rapid re-deployment of application environments
- Test **failover to secondary region** as part of annual contingency plan test
- Verify **backup restore** in secondary region — do not assume replication equals recovery
- Document **cloud account access during a crisis** — who has credentials, how are they stored, how are they recovered if the identity provider is unavailable

---

## Common CP Findings in Assessments

These findings recur frequently in SP 800-34 / CP control family assessments:

| Finding | Risk | Remediation |
|---|---|---|
| No tested contingency plan (plan exists but was never tested) | HIGH | Schedule and execute tabletop exercise within 30 days; document results |
| RPO/RTO not defined in BIA or ITCP | HIGH | Conduct or update BIA; derive RTO/RPO from MTD analysis; update ITCP |
| Hot site required but not tested in 12 months | HIGH | Schedule parallel or functional test; renegotiate hot site agreement if lapsed |
| Backups not tested for restorability | HIGH | Conduct documented restore test; verify data integrity; schedule quarterly restore tests |
| Alternate processing site agreement expired | MODERATE | Renew agreement; verify site readiness before agreement expires |
| ITCP not updated after significant system changes | MODERATE | Update ITCP within 30 days of significant change; establish change-triggered review process |
| CP training not completed for all contingency personnel | MODERATE | Schedule training; document completion; include in annual training plan |
| ITCP not distributed to all key personnel | LOW | Update distribution list; verify current personnel have current plan version |
| BIA does not reflect current mission dependencies | MODERATE | Re-conduct BIA with current system owners and mission stakeholders; update annually |

---

## BLACKSITE Platform Mappings

The following table maps BLACKSITE platform features to SP 800-34 / CP control requirements.

| SP 800-34 / CP Requirement | BLACKSITE Feature | Evidence Path |
|---|---|---|
| CP-4: Annual contingency plan test | **Restore Test Records** (Day 9 rotation) | `/systems/{id}/restore-tests/` — log test type, scenario, results, issues found |
| CP-9: System backup verification | **Backup Check Records** (Daily Task 4) | Daily logbook Task 4 "Backup status check"; evidence label "Backup verification log — [date]" |
| CP-2: Contingency plan currency | **ATO document package** | Upload ITCP as ATO document; track version and annual review date |
| CP-3: Contingency training records | **Reports module** | Upload training completion certificates; reference in system report |
| CP-2: RTO/RPO documentation | **System record fields** | System detail view — capture RTO/RPO values; reference BIA document |
| BCDR coordinator role | **BCDR Coordinator duty assignment** | Assigned via DutyAssignment; daily rotation includes CP-focused tasks (Days 4, 8, 9) |
| CP-4 evidence package | **Reports / BCDR evidence pack** | Generate BCDR compliance report; includes restore test history, backup check history, plan currency |
| Vendor/CSP contingency SLAs | **Vendor Records** | `/vendors/` — document FedRAMP authorization status; note CSP RTO/RPO in vendor record |
| Interconnection contingency dependencies | **Interconnection Records** | Capture system dependencies that affect recovery sequencing |

### BCDR Coordinator Daily Rotation Coverage

The BCDR Coordinator rotation in BLACKSITE includes tasks that directly generate CP control evidence:

| Rotation Day | Task | CP Control Mapped |
|---|---|---|
| Day 4 | Contingency plan currency check | CP-2 (plan review) |
| Day 8 | Backup check and verification | CP-9 (system backup) |
| Day 9 | Restore test execution or scheduling | CP-4 (testing) |

Each completed rotation task with evidence attached satisfies continuous monitoring requirements for the corresponding CP control. Assessors look for consistent, dated entries — a 12-month history of completed tasks is strong evidence of an operational CP program.

---

## Key References

- **NIST SP 800-34 Rev 1**: Contingency Planning Guide for Federal Information Systems — primary source for all content in this document
- **NIST SP 800-53 Rev 5, CP Control Family**: normative control requirements implemented through SP 800-34 guidance
- **NIST SP 800-184**: Guide for Cybersecurity Event Recovery — complements SP 800-34 with recovery strategy detail
- **FIPS 199**: Standards for Security Categorization of Federal Information and Information Systems — impact level determination driving CP requirements
- **FIPS 200**: Minimum Security Requirements for Federal Information and Information Systems — baseline CP control requirements by impact level
- **HIPAA Security Rule, 45 CFR § 164.308(a)(7)**: Contingency plan requirements for ePHI systems
- **OMB Circular A-130**: Managing Information as a Strategic Resource — federal information management policy including continuity requirements
- **CISA Continuity Guidance**: federal guidance on COOP and contingency planning for civilian agencies
- **FedRAMP Customer Responsibility Matrix**: defines CSP vs. customer responsibilities for CP controls in cloud environments
- **ISO/IEC 22301**: International standard for Business Continuity Management Systems — reference for aligning NIST BCDR with international frameworks
