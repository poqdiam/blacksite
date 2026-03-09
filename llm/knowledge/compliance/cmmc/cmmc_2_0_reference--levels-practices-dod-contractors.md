# CMMC 2.0 — Comprehensive Reference
## Cybersecurity Maturity Model Certification for DoD Contractors

**Program:** Cybersecurity Maturity Model Certification (CMMC) 2.0
**Governing Authority:** Office of the Under Secretary of Defense for Acquisition and Sustainment (OUSD(A&S))
**Regulatory Basis:** 32 CFR Part 170 (CMMC Program rule, effective December 2024); 48 CFR Parts 204 and 252 (DFARS implementation)
**Current Version:** CMMC 2.0 (supersedes CMMC 1.0 released January 2020)
**Primary Audience:** DoD prime contractors and subcontractors in the Defense Industrial Base (DIB)

---

## Table of Contents

1. [CMMC Background and Purpose](#1-cmmc-background-and-purpose)
2. [Federal Contract Information (FCI) vs Controlled Unclassified Information (CUI)](#2-fci-vs-cui)
3. [CMMC 2.0 Level Structure](#3-cmmc-20-level-structure)
4. [Level 1 — Foundational (17 Practices)](#4-level-1--foundational)
5. [Level 2 — Advanced (110 Practices / NIST SP 800-171)](#5-level-2--advanced)
6. [Level 3 — Expert (134+ Practices / NIST SP 800-172)](#6-level-3--expert)
7. [NIST SP 800-171 Rev 2 — 14 Domains and 110 Requirements](#7-nist-sp-800-171-rev-2)
8. [SPRS Scoring System](#8-sprs-scoring-system)
9. [CUI Definition and National Archives Registry](#9-cui-definition-and-national-archives-registry)
10. [Assessment Types and Third-Party Assessment Organizations (C3PAOs)](#10-assessment-types-and-c3paos)
11. [CMMC vs FedRAMP for Cloud Services Handling CUI](#11-cmmc-vs-fedramp-for-cloud-services-handling-cui)
12. [System Security Plan (SSP) Requirements](#12-system-security-plan-ssp-requirements)
13. [POA&M Use in CMMC vs FedRAMP](#13-poam-use-in-cmmc-vs-fedramp)
14. [CMMC in Contracts — DFARS Clauses](#14-cmmc-in-contracts--dfars-clauses)
15. [CMMC Supply Chain Flow-Down Requirements](#15-cmmc-supply-chain-flow-down-requirements)
16. [Key Definitions and Acronyms](#16-key-definitions-and-acronyms)

---

## 1. CMMC Background and Purpose

### Origins

The DoD launched CMMC in response to persistent and escalating theft of sensitive defense information from the Defense Industrial Base (DIB). Prior to CMMC, contractors were required to self-attest compliance with DFARS 252.204-7012, which mandated implementation of NIST SP 800-171. However:

- Self-attestation created perverse incentives — contractors could claim compliance without verification
- Assessments found systemic gaps: average DIB contractor scored far below the maximum 110 points on NIST 800-171
- Adversaries (notably China/APT10 and others) exploited these gaps to steal technical data, weapons system designs, and military sensitive information

### CMMC 1.0 (January 2020)

The original CMMC model had:
- 5 maturity levels (1-5)
- 171 practices across levels
- 17 process capabilities woven through levels
- Mandatory third-party assessment for all levels above 1
- Criticized as overly complex and costly, particularly for small businesses

### CMMC 2.0 (November 2021; Rule Final December 2024)

CMMC 2.0 simplified the model:
- **3 levels** (down from 5)
- **Eliminated process maturity** requirements (removed the separate "maturity" layer)
- **Aligned Level 2 exactly with NIST SP 800-171** (110 practices)
- **Allowed self-assessment for some Level 2 programs** (non-prioritized acquisitions)
- **Allowed POA&Ms** with conditions (timelimited, capped at 20% of points)
- **Added government-led assessment path** for Level 3

### Timeline of Implementation

| Milestone | Date |
|-----------|------|
| CMMC 2.0 announced | November 2021 |
| CMMC Program Rule (32 CFR 170) final | December 2024 |
| DFARS rule implementation (48 CFR) | Phased through 2025 |
| CMMC requirements in new contracts | Phased starting 2025 |
| Full implementation across DIB | Estimated 2026-2028 |

---

## 2. FCI vs CUI

Understanding the distinction between FCI and CUI is foundational to determining which CMMC level applies.

### Federal Contract Information (FCI)

**Definition (FAR 4.1901):** Information provided by or generated for the Government under a contract to develop or deliver a product or service to the Government, but not intended for public release.

**Key characteristics:**
- Covers almost all federal contracting relationships
- Not as sensitive as CUI
- Minimum security baseline: 15 basic safeguarding requirements (FAR 52.204-21)
- CMMC Level 1 applies when contractor processes only FCI (not CUI)

**Examples of FCI:**
- Contract terms and pricing (not public)
- Contractor deliverables not for public release
- SOW details for development contracts
- Correspondence about contract performance

### Controlled Unclassified Information (CUI)

**Definition (EO 13556 / 32 CFR 2002):** Information the Government creates or possesses, or that an entity creates or possesses for or on behalf of the Government, that a law, regulation, or Government-wide policy requires or permits an agency to handle using safeguarding or dissemination controls.

**Key characteristics:**
- Designated by the National Archives and Records Administration (NARA)
- Required to carry CUI designation markings
- CMMC Level 2 (and sometimes Level 3) applies when contractor processes CUI
- DFARS 252.204-7012 mandates NIST SP 800-171 for CUI in contractor systems

**CUI vs Classified Information:**
- CUI is **not classified** — it does not require security clearances to access
- CUI still requires safeguarding because disclosure could damage national security, privacy, or government interests
- CUI can exist on unclassified networks; classified information requires classified networks (SIPRNet, JWICS)

---

## 3. CMMC 2.0 Level Structure

| Level | Name | Practices | Basis | Assessment Type | Assessment Frequency |
|-------|------|-----------|-------|-----------------|---------------------|
| **Level 1** | Foundational | 17 | FAR 52.204-21 | Annual self-assessment + affirmation | Annual |
| **Level 2** | Advanced | 110 | NIST SP 800-171 Rev 2 | C3PAO assessment OR annual self-assessment | Triennial (C3PAO) or Annual (self) |
| **Level 3** | Expert | 134+ | NIST SP 800-171 + selected 800-172 | Government-led assessment (DIBCAC) | Triennial |

### Level Determination

The DoD contracting officer specifies the required CMMC level in the solicitation. Level determination is based on:

1. **Does the contractor handle CUI?**
   - No: Level 1 (FCI only)
   - Yes: Level 2 minimum
2. **Is the program critical or high-priority?**
   - Yes (e.g., nuclear, advanced weapons systems, critical supply chain): Level 3

### Level 2 Self-Assessment vs C3PAO

Not all Level 2 programs require a third-party assessment. The DoD designates acquisitions as:
- **Prioritized acquisitions:** Require C3PAO assessment (third party). Applied to programs with higher CUI sensitivity or national security implications.
- **Non-prioritized acquisitions:** Allow annual self-assessment with senior official affirmation. Still requires SPRS submission.

> **Practice note:** Contractors should not assume they qualify for self-assessment. Review contract requirements carefully. Providing false affirmation of compliance is subject to the False Claims Act.

---

## 4. Level 1 — Foundational

### Overview

Level 1 represents the **minimum cybersecurity hygiene** required for any DoD contractor. It is based on the 15 basic safeguarding requirements in **FAR 52.204-21**.

### 17 Level 1 Practices

Level 1 contains 17 practices drawn from FAR 52.204-21 and mapped to NIST SP 800-171:

| # | Practice ID | Description |
|---|-------------|-------------|
| 1 | AC.L1-3.1.1 | Limit information system access to authorized users, processes acting on behalf of authorized users, and devices (including other information systems) |
| 2 | AC.L1-3.1.2 | Limit information system access to the types of transactions and functions that authorized users are permitted to execute |
| 3 | AC.L1-3.1.20 | Verify and control/limit connections to external information systems |
| 4 | AC.L1-3.1.22 | Control information posted or processed on publicly accessible information systems |
| 5 | IA.L1-3.5.1 | Identify information system users, processes acting on behalf of users, and devices |
| 6 | IA.L1-3.5.2 | Authenticate (or verify) the identities of those users, processes, or devices, as a prerequisite to allowing access to organizational information systems |
| 7 | MP.L1-3.8.3 | Sanitize or destroy information system media before disposal or reuse |
| 8 | PE.L1-3.10.1 | Limit physical access to organizational information systems to authorized individuals |
| 9 | PE.L1-3.10.3 | Escort visitors and monitor visitor activity |
| 10 | PE.L1-3.10.4 | Maintain audit logs of physical access |
| 11 | PE.L1-3.10.5 | Control and manage physical access devices |
| 12 | SC.L1-3.13.1 | Monitor, control, and protect organizational communications (i.e., information transmitted or received by organizational information systems) at the external boundaries and key internal boundaries |
| 13 | SC.L1-3.13.5 | Implement subnetworks for publicly accessible system components that are physically or logically separated from internal networks |
| 14 | SI.L1-3.14.1 | Identify, report, and correct information and information system flaws in a timely manner |
| 15 | SI.L1-3.14.2 | Provide protection from malicious code at appropriate locations within organizational information systems |
| 16 | SI.L1-3.14.4 | Update malicious code protection mechanisms when new releases are available |
| 17 | SI.L1-3.14.5 | Perform periodic scans of the information system and real-time scans of files from external sources as files are downloaded, opened, or executed |

### Level 1 Assessment Requirements

- **Self-assessment** — contractor performs their own evaluation
- **Annual affirmation** — senior official (at executive level) affirms compliance
- **SPRS submission** — results submitted to the Supplier Performance Risk System
- **No third-party verification required**

---

## 5. Level 2 — Advanced

### Overview

Level 2 maps **exactly** to the 110 security requirements in **NIST SP 800-171 Rev 2**. This alignment means organizations implementing NIST SP 800-171 are simultaneously working toward CMMC Level 2 compliance.

Level 2 applies to contractors handling **CUI** that is not associated with the most critical programs (those go to Level 3).

### Assessment Requirement

| Acquisition Type | Assessment Required | Frequency |
|-----------------|---------------------|-----------|
| Prioritized | C3PAO (third-party) | Triennial |
| Non-prioritized | Self-assessment + affirmation | Annual |

### Level 2 Domains

The 110 practices are organized into 14 domains (same as NIST SP 800-171 domains):

| Domain | NIST 800-171 Section | Practice Count |
|--------|---------------------|----------------|
| Access Control (AC) | 3.1 | 22 |
| Awareness and Training (AT) | 3.2 | 3 |
| Audit and Accountability (AU) | 3.3 | 9 |
| Configuration Management (CM) | 3.4 | 9 |
| Identification and Authentication (IA) | 3.5 | 11 |
| Incident Response (IR) | 3.6 | 3 |
| Maintenance (MA) | 3.7 | 6 |
| Media Protection (MP) | 3.8 | 9 |
| Personnel Security (PS) | 3.9 | 2 |
| Physical Protection (PE) | 3.10 | 6 |
| Risk Assessment (RA) | 3.11 | 3 |
| Security Assessment (CA) | 3.12 | 4 |
| System and Communications Protection (SC) | 3.13 | 16 |
| System and Information Integrity (SI) | 3.14 | 7 |
| **TOTAL** | | **110** |

---

## 6. Level 3 — Expert

### Overview

Level 3 is reserved for **the most critical DoD programs** — those involving advanced weapons systems, nuclear systems, critical infrastructure, and supply chains where compromise could cause catastrophic national security harm.

### Practice Count

- **134+ practices** (the 110 from NIST SP 800-171 plus additional requirements from NIST SP 800-172)
- Exact number of additional practices is established by the DoD on a program-by-program basis

### NIST SP 800-172 (Enhanced Requirements)

NIST SP 800-172 (February 2021) provides **35 enhanced security requirements** for CUI in critical programs. These requirements are a superset of NIST SP 800-171 and are designed to counter advanced persistent threats (APTs).

**Key enhanced areas in NIST SP 800-172:**

| Domain | Enhanced Focus |
|--------|---------------|
| Access Control | Attribute-based access control, dynamic access decisions |
| Awareness and Training | Advanced threat-focused training, insider threat awareness |
| Audit and Accountability | Automated anomaly detection, audit reduction tools |
| Configuration Management | Trusted software supply chain, runtime integrity |
| Identification and Authentication | Hardware token MFA, PIV/CAC enforcement |
| Incident Response | Automated incident response capabilities, coordination with DoD |
| Risk Assessment | Advanced threat modeling, adversarial simulation |
| System and Communications Protection | Isolation, information flow enforcement, encrypted communications |
| System and Information Integrity | System integrity monitoring, firmware validation |

### Level 3 Assessment

- **Government-led assessment** conducted by the **Defense Industrial Base Cybersecurity Assessment Center (DIBCAC)**
- Not conducted by commercial C3PAOs
- Triennial cycle
- Level 3 organizations must first achieve and maintain a Level 2 C3PAO assessment as a prerequisite

---

## 7. NIST SP 800-171 Rev 2 — 14 Domains and 110 Requirements

NIST SP 800-171 Rev 2 ("Protecting Controlled Unclassified Information in Nonfederal Systems and Organizations") is the technical backbone of CMMC Level 2. Each requirement is numbered in the format 3.X.Y where X is the domain number and Y is the specific requirement.

### Domain 3.1 — Access Control (22 Requirements)

Limit information system access to authorized users, processes, and devices, and to the types of transactions and functions those users are permitted to exercise.

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.1.1 | Limit access to authorized users, processes, and devices |
| 3.1.2 | Limit access to transaction types authorized users are permitted to execute |
| 3.1.3 | Control the flow of CUI in accordance with approved authorizations |
| 3.1.4 | Separate duties of individuals to reduce risk of malevolent activity |
| 3.1.5 | Employ least privilege — limit user access to what is needed |
| 3.1.6 | Use non-privileged accounts when accessing non-security functions |
| 3.1.7 | Prevent non-privileged users from executing privileged functions |
| 3.1.8 | Limit unsuccessful logon attempts |
| 3.1.9 | Provide privacy and security notices for system access |
| 3.1.10 | Use session lock after inactivity |
| 3.1.11 | Terminate sessions after defined conditions |
| 3.1.12 | Monitor and control remote access |
| 3.1.13 | Employ cryptographic mechanisms for remote access |
| 3.1.14 | Route remote access via managed access control points |
| 3.1.15 | Authorize remote execution of privileged commands only for operational needs |
| 3.1.16 | Authorize wireless access prior to allowing connections |
| 3.1.17 | Protect wireless access using authentication and encryption |
| 3.1.18 | Control connection of mobile devices |
| 3.1.19 | Encrypt CUI on mobile devices and mobile computing platforms |
| 3.1.20 | Verify and control connections to external systems |
| 3.1.21 | Limit use of portable storage devices on external systems |
| 3.1.22 | Control CUI posted or processed on publicly accessible systems |

### Domain 3.2 — Awareness and Training (3 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.2.1 | Ensure personnel are aware of security risks associated with their activities |
| 3.2.2 | Ensure personnel are trained to carry out assigned security responsibilities |
| 3.2.3 | Provide security awareness training on recognizing and reporting threats |

### Domain 3.3 — Audit and Accountability (9 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.3.1 | Create and retain system audit logs to monitor, analyze, investigate, and report unlawful or unauthorized activity |
| 3.3.2 | Ensure the actions of individual users can be traced to those users |
| 3.3.3 | Review and update logged events |
| 3.3.4 | Alert in the event of audit logging process failures |
| 3.3.5 | Correlate audit record review, analysis, and reporting processes |
| 3.3.6 | Provide audit record reduction and report generation |
| 3.3.7 | Provide a system capability that compares and synchronizes internal clocks |
| 3.3.8 | Protect audit information and tools from unauthorized access, modification, and deletion |
| 3.3.9 | Limit management of audit logging to a subset of privileged users |

### Domain 3.4 — Configuration Management (9 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.4.1 | Establish and maintain baseline configurations and inventories |
| 3.4.2 | Establish and enforce security configuration settings |
| 3.4.3 | Track, review, approve, and log changes to organizational systems |
| 3.4.4 | Analyze security impact of changes prior to implementation |
| 3.4.5 | Define, document, approve, and enforce physical and logical access restrictions |
| 3.4.6 | Employ the principle of least functionality |
| 3.4.7 | Restrict, disable, or prevent use of nonessential programs, functions, ports, protocols |
| 3.4.8 | Apply deny-by-exception (blacklisting) to prevent use of unauthorized software |
| 3.4.9 | Control and monitor user-installed software |

### Domain 3.5 — Identification and Authentication (11 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.5.1 | Identify system users, processes, and devices |
| 3.5.2 | Authenticate users, processes, and devices |
| 3.5.3 | Use multifactor authentication for local and network access |
| 3.5.4 | Employ replay-resistant authentication mechanisms |
| 3.5.5 | Employ identifier management — no identifier reuse |
| 3.5.6 | Disable identifiers after defined inactivity period |
| 3.5.7 | Enforce minimum password complexity and change requirements |
| 3.5.8 | Prohibit password reuse for specified generations |
| 3.5.9 | Allow temporary password with immediate change requirement |
| 3.5.10 | Store and transmit only cryptographically-protected passwords |
| 3.5.11 | Obscure feedback of authentication information during authentication |

### Domain 3.6 — Incident Response (3 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.6.1 | Establish an operational incident-handling capability that includes preparation, detection, analysis, containment, recovery, and user response activities |
| 3.6.2 | Track, document, and report incidents to appropriate officials and authorities |
| 3.6.3 | Test the organizational incident response capability |

### Domain 3.7 — Maintenance (6 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.7.1 | Perform maintenance on organizational systems |
| 3.7.2 | Provide controls on tools, techniques, mechanisms, and personnel for maintenance |
| 3.7.3 | Ensure equipment removed for maintenance is sanitized |
| 3.7.4 | Check media containing diagnostic programs for malicious code |
| 3.7.5 | Require MFA for remote maintenance sessions |
| 3.7.6 | Supervise maintenance activities of personnel without required access authorization |

### Domain 3.8 — Media Protection (9 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.8.1 | Protect (using physical controls) system media containing CUI |
| 3.8.2 | Limit access to CUI on system media to authorized users |
| 3.8.3 | Sanitize or destroy system media before disposal or reuse |
| 3.8.4 | Mark media with necessary CUI markings and distribution limitations |
| 3.8.5 | Control access to media containing CUI and maintain accountability |
| 3.8.6 | Implement cryptographic mechanisms to protect CUI during transport |
| 3.8.7 | Control the use of removable media on system components |
| 3.8.8 | Prohibit the use of portable storage without identified owner |
| 3.8.9 | Protect CUI during backup |

### Domain 3.9 — Personnel Security (2 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.9.1 | Screen individuals prior to authorizing access to organizational systems |
| 3.9.2 | Ensure CUI is protected during and after personnel actions such as terminations and transfers |

### Domain 3.10 — Physical Protection (6 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.10.1 | Limit physical access to organizational systems to authorized individuals |
| 3.10.2 | Protect and monitor the physical facility and support infrastructure |
| 3.10.3 | Escort visitors and monitor visitor activity |
| 3.10.4 | Maintain audit logs of physical access |
| 3.10.5 | Control and manage physical access devices |
| 3.10.6 | Enforce safeguarding measures for CUI at alternate work sites |

### Domain 3.11 — Risk Assessment (3 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.11.1 | Periodically assess the risk to operations, assets, and individuals |
| 3.11.2 | Scan for vulnerabilities in organizational systems periodically and when new vulnerabilities are identified |
| 3.11.3 | Remediate vulnerabilities in accordance with risk assessments |

### Domain 3.12 — Security Assessment (4 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.12.1 | Periodically assess the security controls in organizational systems to determine if they are effective |
| 3.12.2 | Develop and implement plans of action designed to correct deficiencies |
| 3.12.3 | Monitor security controls on an ongoing basis to ensure continued effectiveness |
| 3.12.4 | Develop, document, and periodically update system security plans |

### Domain 3.13 — System and Communications Protection (16 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.13.1 | Monitor, control, and protect communications at external boundaries and key internal boundaries |
| 3.13.2 | Employ architectural designs, software development techniques, and systems engineering principles promoting security |
| 3.13.3 | Separate user functionality from system management functionality |
| 3.13.4 | Prevent unauthorized and unintended information transfer |
| 3.13.5 | Implement subnetworks for publicly accessible system components separated from internal networks |
| 3.13.6 | Deny network communications traffic by default |
| 3.13.7 | Prevent remote devices from simultaneously using non-remote connections (split tunneling) |
| 3.13.8 | Implement cryptographic mechanisms to prevent unauthorized disclosure of CUI during transmission |
| 3.13.9 | Terminate network connections after defined period of inactivity |
| 3.13.10 | Establish and manage cryptographic keys |
| 3.13.11 | Employ FIPS-validated cryptography when used to protect CUI |
| 3.13.12 | Prohibit remote activation of collaborative computing devices and provide indication to users present |
| 3.13.13 | Control and monitor mobile code |
| 3.13.14 | Control and monitor use of VoIP technologies |
| 3.13.15 | Protect the authenticity of communications sessions |
| 3.13.16 | Protect CUI at rest |

### Domain 3.14 — System and Information Integrity (7 Requirements)

| Req ID | Requirement Summary |
|--------|---------------------|
| 3.14.1 | Identify, report, and correct system flaws in a timely manner |
| 3.14.2 | Provide protection from malicious code at appropriate locations |
| 3.14.3 | Monitor system security alerts and advisories and take action |
| 3.14.4 | Update malicious code protection mechanisms |
| 3.14.5 | Perform periodic scans and real-time scans of files |
| 3.14.6 | Monitor organizational systems to detect attacks and indicators of potential attacks |
| 3.14.7 | Identify unauthorized use of organizational systems |

---

## 8. SPRS Scoring System

### What is SPRS?

The **Supplier Performance Risk System (SPRS)** is a DoD-managed database that aggregates supplier performance information to help acquisition professionals assess contractor risk. For CMMC/NIST 800-171, SPRS is used to record contractors' self-assessed NIST SP 800-171 implementation scores.

### Scoring Range

| Score | Meaning |
|-------|---------|
| **+110** | Perfect score — all 110 requirements fully implemented |
| **0** | Neutral starting point before any assessment |
| **-203** | Worst possible score — no requirements implemented |

### How the Score Is Calculated

Each of the 110 NIST SP 800-171 requirements has a **point value** based on its assessed importance. The scoring methodology assigns point values as follows:

- **Total maximum points:** 110 (one per requirement when all are met)
- **Not implemented requirements:** Subtract from 110 based on the weight of each requirement
- Requirements are weighted from 1 to 5 points based on criticality

**Scoring formula:**
```
SPRS Score = 110 - (sum of point values for unimplemented requirements)
```

**Example:**
- 3.5.3 (MFA) has a weight of 5 points
- If MFA is not implemented: 110 - 5 = 105 (before other deficiencies)
- Additional deficiencies further reduce the score

### SPRS Score Submission Requirements

All DoD contractors handling CUI must:

1. **Conduct a self-assessment** against NIST SP 800-171 using the DoD assessment methodology
2. **Calculate the SPRS score**
3. **Submit the score to SPRS** at https://www.sprs.csd.disa.mil/
4. **Have a senior official affirm** the accuracy of the score

Submissions include:
- Score value
- Date of assessment
- Plan to achieve full score (if not at 110)
- Date of planned full implementation

### SPRS Score Visibility

Contracting officers can view SPRS scores during source selection to assess contractor cybersecurity posture risk. A very low score may disqualify a contractor or trigger additional scrutiny.

### DIBCAC Assessment and SPRS

When a C3PAO (or DIBCAC for Level 3) conducts an assessment, the assessment results are uploaded to SPRS by the assessor, not by the contractor. This creates an **official, verified score** distinct from the self-assessed score.

---

## 9. CUI Definition and National Archives Registry

### CUI Registry

The **National Archives and Records Administration (NARA)** maintains the **CUI Registry** (cui.archives.gov), which catalogues all authorized CUI categories. As of 2025, there are approximately 120+ categories organized into broader groupings.

### CUI Category Groupings Relevant to Defense

| Grouping | Description | Examples |
|----------|-------------|---------|
| **Critical Infrastructure** | Information about critical infrastructure systems and assets | Chemical Security, Energy Infrastructure |
| **Defense** | DoD-specific sensitive information | Controlled Technical Information (CTI), Naval Nuclear Propulsion |
| **Export Control** | ITAR/EAR restricted information | Export Controlled Research |
| **Intelligence** | Sensitive intelligence-related information | Intelligence (General) |
| **Law Enforcement** | Law enforcement sensitive | Sensitive Investigative Information |
| **Legal** | Attorney-client, litigation sensitive | Attorney Work Product |
| **Nuclear** | Nuclear materials and programs | Unclassified Controlled Nuclear Information — Defense |
| **Privacy** | PII and related data | Social Security Numbers, Personnel Records |
| **Procurement and Acquisition** | Source selection sensitive | Source Selection Sensitive |
| **Proprietary Business Information** | Business confidential | Proprietary Manufacturer Data |

### Controlled Technical Information (CTI)

CTI is the CUI category most commonly encountered in defense contracting:

- Technical information with military or space application subject to controls on access, use, reproduction, modification, performance, display, release, disclosure, or dissemination
- Includes: specifications, standards, drawings, engineering data, technical reports, technical orders, study/analysis reports, data sets, manuals, technical instructions

CTI triggers DFARS 252.204-7012 and CMMC Level 2 requirements.

### CUI Marking Requirements

CUI must be marked according to the CUI Registry:

```
CUI
[Category] (if specified/limited)
Controlled by: [Agency name]
Controlled by: [Office name]
CUI Category: [Specific category if applicable]
Distribution/Dissemination Control: [FEDCON, NOFORN, etc.]
```

**Handling caveats:**
- **FEDCON:** Federal contractors with need-to-know
- **NOFORN:** No Foreign Nationals
- **NOCON:** No Contractors (federal employees only)

---

## 10. Assessment Types and Third-Party Assessment Organizations (C3PAOs)

### C3PAO (CMMC Third-Party Assessment Organization)

A **C3PAO** is a company authorized by the **Cyber AB** (formerly CMMC Accreditation Body) to conduct CMMC Level 2 assessments for DoD contractors.

**C3PAO Requirements:**
- Must be authorized by the Cyber AB
- Must not have a conflict of interest with the assessed organization
- Assessors must hold appropriate certifications (CCA — CMMC Certified Assessor; CCPA — CMMC Certified Professional Assessor for lead assessors)
- Must follow the CMMC Assessment Process (CAP) methodology
- Results submitted to SPRS via eMASS or direct SPRS submission

**Finding the Assessor Marketplace:**
- Cyber AB marketplace: cyberab.org/Catalog
- Find authorized C3PAOs and individual CCA/CCPA certified assessors

### CMMC Assessment Process (CAP)

Assessments follow a defined methodology:

| Phase | Activities |
|-------|-----------|
| **Pre-Assessment** | Scope definition, SSP review, documentation request, assessment plan |
| **Assessment** | Document review, interviews, testing (observation, demonstration) |
| **Analysis** | Finding classification (MET / NOT MET), deficiency documentation |
| **Reporting** | Assessment findings report, conditional certification decision |
| **Close-Out** | POA&M tracking, conditional CMMC Level (if POA&M allowed) |

### Assessment Outcome Options

| Outcome | Meaning | Result |
|---------|---------|--------|
| **CMMC Level 2 Achieved** | All 110 practices MET | Full certification |
| **Conditional CMMC Level 2** | 1-20% of weighted score in POA&M | Conditional status; 180 days to remediate |
| **Not Achieved** | Too many deficiencies for conditional status | No CMMC Level 2; cannot bid on requiring contracts |

### Individual Certifications

| Certification | Acronym | Description |
|--------------|---------|-------------|
| CMMC Certified Professional | CCP | Entry-level; can assist with assessments but not lead |
| CMMC Certified Assessor | CCA | Can conduct and lead C3PAO assessments |
| CMMC Certified Instructor | CCI | Authorized to deliver CMMC training |
| CMMC Registered Practitioner | CRP | Advises organizations on CMMC preparation (not an assessor) |
| CMMC Registered Practitioner Organization | RPO | Company authorized to provide CMMC advisory services |

---

## 11. CMMC vs FedRAMP for Cloud Services Handling CUI

This is one of the most common questions in CMMC implementation. The answer depends on who is responsible for the cloud environment.

### FedRAMP Authorization and CUI

**DFARS 252.204-7012 Section (d)** requires contractors to use cloud services that are **FedRAMP Moderate authorized** (or meet equivalent security standards) when those cloud services process, store, or transmit CUI.

**Key rule:** If a DoD contractor uses a cloud service to store or process CUI:
- The cloud service provider (CSP) must be FedRAMP Moderate authorized, OR
- The CSP must meet equivalent security requirements approved by the DoD CIO

### FedRAMP + CMMC Relationship

| Aspect | Explanation |
|--------|-------------|
| **Who needs FedRAMP** | The CSP (cloud provider) — not the contractor |
| **Who needs CMMC** | The contractor (DIB member) |
| **FedRAMP satisfies CMMC for** | The infrastructure layer (IaaS/PaaS) inherited controls |
| **CMMC still required for** | Contractor-operated systems, processes, and personnel |
| **Hybrid environments** | Contractor must assess what is inherited from FedRAMP CSP vs. what they operate |

### Inherited Controls Under FedRAMP

When a contractor uses a FedRAMP Moderate authorized IaaS (e.g., AWS GovCloud, Azure Government), a portion of the NIST SP 800-171 requirements may be **inherited** from the cloud provider:

- Physical security (3.10.x) — largely inherited from IaaS provider
- Environmental controls — largely inherited
- Hardware maintenance (3.7.x) — largely inherited for managed services
- Cryptography (3.13.x) — partially inherited if provider manages encryption

**The contractor is still responsible for:**
- Access control for their users and administrators
- Their application layer security
- Their data classification and handling
- Their incident response procedures
- Their policies and training

### DoD IL Levels and CUI

The DoD categorizes its cloud computing requirements into **Impact Levels (IL)**:

| IL | Data Type | FedRAMP Equivalence |
|----|-----------|---------------------|
| IL2 | Public information, non-CUI | FedRAMP Moderate authorized |
| IL4 | CUI | FedRAMP Moderate + DoD SRG requirements |
| IL5 | CUI National Security Systems | FedRAMP High + additional DoD controls |
| IL6 | Classified (Secret) | Not commercially available; NSS requirements |

For most CMMC Level 2 scenarios, the contractor needs cloud services at **IL4** or above.

### Practical Guidance

1. **Inventory your cloud services** — identify which store/process/transmit CUI
2. **Verify FedRAMP status** on the FedRAMP Marketplace (marketplace.fedramp.gov)
3. **Obtain the CSP's Customer Responsibility Matrix (CRM)** — identifies which controls the CSP manages vs. which the customer manages
4. **Document inherited controls** in your SSP
5. **Implement customer-managed controls** yourself
6. **Do not assume** FedRAMP authorization satisfies all CMMC requirements — it does not

---

## 12. System Security Plan (SSP) Requirements

### SSP Requirement under NIST SP 800-171

Requirement **3.12.4** mandates:
> "Develop, document, and periodically update system security plans that describe system boundaries, system environments of operation, how security requirements are implemented, and the relationships with or connections to other systems."

### SSP Purpose

The SSP is the **primary documentation artifact** for CMMC Level 2. It serves as:
- The definitive description of the contractor's information system environment
- Documentation of how each of the 110 requirements is implemented
- The basis for assessor evaluation
- Evidence of planned remediation for unimplemented requirements

### Required SSP Sections

| Section | Content |
|---------|---------|
| **System Identification** | System name, owner, authorizing official, system category |
| **System Description** | Purpose, functionality, criticality, system boundaries |
| **CUI Description** | Types of CUI processed, stored, transmitted; CUI data flows |
| **System Environment** | Architecture description, hardware, software, firmware inventory |
| **System Boundary** | What is in scope for CMMC; authorization boundary diagram |
| **Network Diagram** | Logical network topology showing connections and data flows |
| **Data Flow Diagram** | How CUI moves through the system |
| **Users and Roles** | Types of users, privileges, authentication requirements |
| **External Systems** | Connections to external systems, cloud services, third parties |
| **Applicable Requirements** | All 110 NIST SP 800-171 requirements with implementation status |
| **Implementation Details** | For each requirement: how it is implemented, what controls are in place |
| **Inherited Controls** | Controls provided by external providers (cloud, managed services) |
| **Planned Implementation** | Requirements not yet implemented, planned completion dates |
| **POA&M Reference** | Cross-reference to open POA&M items |

### SSP Quality Requirements

A well-written SSP must be:
- **System-specific** — not generic; describes actual implementation
- **Accurate** — matches actual system configuration
- **Complete** — addresses all 110 requirements with specific, verifiable statements
- **Current** — reviewed and updated at least annually or after significant changes
- **Evidence-backed** — policies, procedures, screenshots, configurations referenced

**Common SSP deficiencies found by C3PAOs:**
- Generic language (e.g., "We comply with NIST 800-171") without specific implementation details
- Missing network/data flow diagrams
- System boundary not clearly defined (FCI/CUI systems mixed with non-CUI systems)
- Out-of-date content (references decommissioned systems or superseded policies)
- POA&M items not cross-referenced

---

## 13. POA&M Use in CMMC vs FedRAMP

### POA&M Definition

A **Plan of Action and Milestones (POA&M)** is a document that identifies security deficiencies, the resources required to correct them, and the scheduled completion dates.

### POA&M in CMMC 2.0

CMMC 2.0 allows a **conditional** CMMC certification with open POA&M items, subject to strict limitations:

**POA&M Eligibility Requirements:**
1. POA&M items cannot include requirements designated as "not allowable" — certain critical requirements must be 100% implemented at time of assessment (see below)
2. The open POA&M items cannot represent more than **20% of the total SPRS weighted score** (i.e., the score cannot be below 88/110)
3. POA&M must be closed within **180 days** of conditional certification
4. A CMMC assessor (C3PAO) must close out the POA&M via a follow-on assessment

**Requirements NOT eligible for POA&M (must be fully implemented):**
- 3.1.20 (Connections to external systems)
- 3.13.11 (FIPS-validated cryptography)
- 3.1.1 and 3.1.2 (Basic access control)
- And other high-weight requirements designated by DoD policy

### POA&M in FedRAMP

FedRAMP POA&Ms have different rules:

| Attribute | CMMC POA&M | FedRAMP POA&M |
|-----------|------------|---------------|
| **Allowed at authorization** | Yes (conditional) | Yes (risk-accepted by AO) |
| **Closure deadline** | 180 days | Risk-based; typically 30-90 days for High, 90-180 days for Moderate/Low findings |
| **Tracking** | C3PAO monitors | CSP reports monthly to agency AO |
| **Verification** | C3PAO close-out assessment | AO-reviewed; may require 3PAO verification for significant items |
| **Ongoing new items** | Accepted with remediation plan | Required — monthly updates to POA&M |
| **Reporting** | SPRS | Monthly ConMon reports to agency/JAB |
| **Risk acceptance** | Limited (< 20% score impact) | AO can accept risk explicitly |
| **Threshold for closure** | All 180-day items must be closed | Items may be accepted as "risk accepted" with justification |

### POA&M Best Practices (Common to CMMC and FedRAMP)

1. **Use standardized fields:** Weakness name, weakness description, point of contact, resources required, scheduled completion date, milestones with completion dates, changes to milestones, status, comments
2. **Link to SSP:** Each POA&M item should reference the SSP requirement it addresses
3. **Assign ownership:** Each item must have a named responsible party
4. **Track milestones:** Break larger remediations into discrete milestones with intermediate dates
5. **Document evidence:** Maintain evidence of completed remediations for assessor review
6. **Version control:** Maintain version history; date-stamp all updates

---

## 14. CMMC in Contracts — DFARS Clauses

### Relevant DFARS Clauses

| Clause | Title | What It Requires |
|--------|-------|-----------------|
| **DFARS 252.204-7012** | Safeguarding Covered Defense Information | Implement NIST SP 800-171; use FIPS-compliant encryption; report cyber incidents to DoD within 72 hours |
| **DFARS 252.204-7019** | Notice of NIST SP 800-171 DoD Assessment Requirements | Self-assessment required; SPRS submission required before award |
| **DFARS 252.204-7020** | NIST SP 800-171 DoD Assessment Requirements | Grants government right to conduct assessments; contractor must grant access |
| **DFARS 252.204-7021** | Cybersecurity Maturity Model Certification Requirements | CMMC Level requirement specified; applies to subcontractors; contractor must maintain during performance |

### FAR 52.204-21

| Clause | Title | What It Requires |
|--------|-------|-----------------|
| **FAR 52.204-21** | Basic Safeguarding of Covered Contractor Information Systems | 15 basic safeguarding requirements for FCI (the basis for CMMC Level 1) |

### DFARS 252.204-7012 — Cyber Incident Reporting Requirements

This clause imposes mandatory incident reporting obligations:

| Requirement | Timeline |
|-------------|----------|
| Report cyber incidents to DoD | Within **72 hours** of discovery |
| Report using DIBNet portal | https://dibnet.dod.mil |
| Preserve images of compromised systems | For 90 days after reporting |
| Provide malware samples | To DoD Cyber Crime Center (DC3) |
| Conduct damage assessment | Assess impact on CUI; report results |

**Incidents that trigger reporting:**
- Actual or potentially compromised CUI
- Compromise of systems used to process, store, or transmit CUI
- Successful cyber attack on contractor networks
- Discovery of previously unknown vulnerabilities being actively exploited

---

## 15. CMMC Supply Chain Flow-Down Requirements

### Prime Contractor Obligations

DFARS 252.204-7021 requires prime contractors to:
1. Identify all subcontractors that will handle CUI in performance of the prime contract
2. Flow down the CMMC requirement to those subcontractors at the appropriate level
3. Verify subcontractor CMMC compliance before allowing CUI access

### Subcontractor CMMC Levels

The required subcontractor CMMC level depends on what the subcontractor does:
- Handles CUI → Level 2 minimum
- Handles only FCI → Level 1
- Critical program role → potentially Level 3

### Supply Chain Risk Management

Primes must:
- Maintain a list of CUI-handling subcontractors
- Verify CMMC compliance status (via SPRS for self-assessed, or certification status for C3PAO-assessed)
- Include CMMC requirements in subcontract terms
- Not allow CUI access to non-compliant subcontractors

---

## 16. Key Definitions and Acronyms

| Term | Definition |
|------|------------|
| **Assessor** | Person conducting a CMMC assessment; must hold CCA or CCPA certification |
| **Authorization Boundary** | The logical perimeter that encompasses the information systems processing CUI |
| **C3PAO** | CMMC Third-Party Assessment Organization — authorized to conduct Level 2 assessments |
| **CAP** | CMMC Assessment Process — standardized assessment methodology |
| **CCA** | CMMC Certified Assessor — individual certification for assessment leads |
| **CCP** | CMMC Certified Professional — individual certification, cannot lead assessments |
| **CUI** | Controlled Unclassified Information |
| **CTI** | Controlled Technical Information — CUI subcategory common in defense contracting |
| **Cyber AB** | CMMC Accreditation Body — non-profit that manages certification ecosystem |
| **DIB** | Defense Industrial Base — the network of companies and organizations supporting national defense |
| **DIBCAC** | Defense Industrial Base Cybersecurity Assessment Center — DoD entity conducting Level 3 assessments |
| **eMASS** | Enterprise Mission Assurance Support Service — DoD system used to track assessments and authorizations |
| **FCI** | Federal Contract Information |
| **FIPS 140-3** | Federal standard for cryptographic modules — required by NIST SP 800-171 3.13.11 |
| **MFA** | Multi-Factor Authentication — required by 3.5.3 |
| **POA&M** | Plan of Action and Milestones |
| **RPO** | Registered Practitioner Organization — authorized to advise on CMMC preparation |
| **SPRS** | Supplier Performance Risk System — DoD database for contractor performance information |
| **SSP** | System Security Plan |
| **OUSD(A&S)** | Office of the Under Secretary of Defense for Acquisition and Sustainment — CMMC program owner |

---

## Summary: CMMC 2.0 Quick Reference

| Attribute | Level 1 | Level 2 | Level 3 |
|-----------|---------|---------|---------|
| **Practices** | 17 | 110 | 134+ |
| **Basis** | FAR 52.204-21 | NIST SP 800-171 Rev 2 | NIST SP 800-171 + 800-172 |
| **Data type** | FCI | CUI | CUI (critical programs) |
| **Assessment** | Self-assessment | C3PAO or self-assessment | DIBCAC (government-led) |
| **Frequency** | Annual | Triennial (C3PAO) or Annual (self) | Triennial |
| **SPRS submission** | Required | Required | Required |
| **POA&M allowed** | N/A | Yes (≤ 20% score; 180-day close) | TBD per program |
| **Certification body** | None (self) | Cyber AB accredited C3PAO | DIBCAC |
| **Subcontractor flow-down** | Required | Required | Required |

---

*Document Version: 1.0 | Framework Version: CMMC 2.0 (32 CFR 170, effective December 2024)*
*Based on: CMMC Model Version 2.13; NIST SP 800-171 Rev 2; NIST SP 800-172*
*Intended Use: LLM GRC Knowledge Base*
