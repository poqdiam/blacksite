# FISMA — Comprehensive Reference
## Federal Information Security Modernization Act: Requirements, Metrics, Programs, and Agency Obligations

**Primary Authority:** Federal Information Security Modernization Act of 2014 (44 U.S.C. Chapter 35, Subchapter II)
**Predecessor:** Federal Information Security Management Act of 2002 (E-Government Act of 2002, Title III)
**Key Implementing Agency:** National Institute of Standards and Technology (NIST), OMB, CISA
**Scope:** All federal agencies, federal information systems, and federal contractors operating systems on behalf of agencies

---

## Table of Contents

1. [FISMA Legislative History](#1-fisma-legislative-history)
2. [FISMA 2023 — SECURE Technology Act](#2-fisma-2023--secure-technology-act)
3. [Key Agencies and Their Roles](#3-key-agencies-and-their-roles)
4. [Mandatory Standards vs Guidelines](#4-mandatory-standards-vs-guidelines)
5. [FIPS 140-3 — Cryptographic Modules](#5-fips-140-3--cryptographic-modules)
6. [FIPS 199 — System Categorization](#6-fips-199--system-categorization)
7. [FIPS 200 — Minimum Security Requirements](#7-fips-200--minimum-security-requirements)
8. [Agency Security Program Requirements](#8-agency-security-program-requirements)
9. [FISMA Metrics — Annual Reporting](#9-fisma-metrics--annual-reporting)
10. [CyberScope and FISMA Reporting Portal](#10-cyberscope-and-fisma-reporting-portal)
11. [Inspector General Assessments](#11-inspector-general-assessments)
12. [CDM — Continuous Diagnostics and Mitigation](#12-cdm--continuous-diagnostics-and-mitigation)
13. [EINSTEIN Program](#13-einstein-program)
14. [TIC — Trusted Internet Connections](#14-tic--trusted-internet-connections)
15. [FISMA Compliance vs FedRAMP](#15-fisma-compliance-vs-fedramp)
16. [RMF Under FISMA — NIST SP 800-37](#16-rmf-under-fisma--nist-sp-800-37)
17. [OMB Circulars and Memoranda](#17-omb-circulars-and-memoranda)
18. [FISMA vs Other Frameworks](#18-fisma-vs-other-frameworks)

---

## 1. FISMA Legislative History

### E-Government Act of 2002 / FISMA 2002

The original FISMA was enacted as Title III of the **E-Government Act of 2002** (P.L. 107-347). Key provisions:

- Required each federal agency to develop, document, and implement an **agency-wide information security program**
- Established NIST's role in developing standards and guidelines for non-national security systems
- Required annual agency reports to OMB
- Required **Inspector General (IG) assessments** of agency security programs
- Required agencies to implement the NIST Risk Management Framework
- Covered all agency information and information systems, including those operated by contractors

**Weaknesses of FISMA 2002:**
- Heavy emphasis on paperwork and compliance documentation over actual security outcomes
- Annual checkbox-style reporting divorced from real-time security posture
- No emphasis on continuous monitoring
- Focus on three-year ATO cycles rather than ongoing risk management
- Did not adequately address shared systems, cloud computing, or third-party providers

### Federal Cybersecurity Enhancement Act / FISMA 2014

The **Federal Information Security Modernization Act of 2014** (P.L. 113-283) updated and largely superseded FISMA 2002:

**Key changes from 2002:**

1. **Shifted DHS role:** Gave DHS operational authority over civilian agency (CFO Act agencies) cybersecurity; NIST retained standards-setting role
2. **Codified CDM:** Authorized the Continuous Diagnostics and Mitigation program
3. **Real-time monitoring:** Emphasized automated, continuous security monitoring over paper-based assessments
4. **Incident reporting to DHS:** Required agencies to report incidents to US-CERT (now CISA)
5. **OMB oversight:** Strengthened OMB's authority to issue binding guidance
6. **National security systems:** Maintained separate oversight under NSA/CNSS

**Retained from 2002:**
- Annual IG assessments
- Annual CIO reports to OMB
- NIST as standards body
- Risk Management Framework requirements

### FISMA Implementation Project (Post-2002)

NIST developed the following foundational publications to implement FISMA:

| Publication | Title | Purpose |
|-------------|-------|---------|
| FIPS 199 | Standards for Security Categorization | Risk categorization |
| FIPS 200 | Minimum Security Requirements | Baseline security requirements |
| NIST SP 800-18 | Guide for Developing SSPs | SSP development |
| NIST SP 800-30 | Guide for Conducting Risk Assessments | Risk assessment methodology |
| NIST SP 800-37 | Risk Management Framework | Authorization process |
| NIST SP 800-53 | Security and Privacy Controls | Control catalog |
| NIST SP 800-53A | Assessing Security and Privacy Controls | Assessment procedures |
| NIST SP 800-60 | Mapping System Types to Security Categories | Categorization guidance |
| NIST SP 800-137 | Information Security Continuous Monitoring | Continuous monitoring |

---

## 2. FISMA 2023 — SECURE Technology Act

### The SECURE Technology Act

Congress passed the **Strengthening and Enhancing Cyber-capabilities by Utilizing Risk Exposure (SECURE) Technology Act** as a series of amendments to FISMA through the Consolidated Appropriations Act, 2023 and related legislation. The "FISMA 2023" label refers to these ongoing amendments and the corresponding OMB implementation guidance.

> **Note:** As of 2025, the official FISMA statute remains the 2014 act (44 U.S.C. § 3551 et seq.). "FISMA 2023" amendments were incorporated through appropriations and omnibus legislation, not a standalone reauthorization. Check current OMB guidance for the most current requirements.

### Key FISMA 2023 / Recent Amendments Provisions

1. **Modernized metrics framework:**
   - Replaced the prior 7-category metric structure with a new cybersecurity framework-aligned approach
   - Metrics now aligned to NIST CSF functions: Identify, Protect, Detect, Respond, Recover

2. **Incident reporting enhancements:**
   - Strengthened incident reporting timelines
   - Required agencies to submit initial incident reports within 1 hour of significant incidents
   - Enhanced CISA's role in coordinating federal incident response

3. **Zero Trust alignment:**
   - OMB M-22-09 (Zero Trust Strategy) issued alongside, requiring agencies to achieve specific ZT milestones
   - FISMA reporting now includes Zero Trust maturity metrics

4. **Supply chain risk:**
   - Enhanced supply chain risk management (SCRM) requirements
   - Aligned with EO 14028 (Improving the Nation's Cybersecurity, May 2021)

5. **CISA authority expansion:**
   - CISA given binding operational directive authority over civilian agencies
   - Known Exploited Vulnerabilities (KEV) catalog binding for federal agencies

### Executive Order 14028 — Improving the Nation's Cybersecurity (May 2021)

While not FISMA legislation, EO 14028 dramatically expanded federal cybersecurity requirements:

| Section | Requirement |
|---------|-------------|
| § 2 | Remove contractual barriers to threat information sharing |
| § 3 | Modernize federal government cybersecurity (Zero Trust, cloud adoption) |
| § 4 | Enhance software supply chain security (SBOMs, secure development) |
| § 5 | Establish cyber safety review board (CSRB) |
| § 6 | Standardize federal incident response playbooks |
| § 7 | Improve detection (EDR across federal agencies) |
| § 8 | Improve investigation and remediation capabilities |

---

## 3. Key Agencies and Their Roles

### National Institute of Standards and Technology (NIST)

**Role:** Standards and guidelines development for non-national security systems

**Statutory authority:** FISMA 2014 § 3553, 40 U.S.C. § 11331

**Key responsibilities:**
- Develop **FIPS** (Federal Information Processing Standards) — mandatory for federal agencies
- Develop **NIST Special Publications (SPs)** — guidance (not mandatory, but OMB/agencies make them binding through policy)
- Maintain the **Risk Management Framework (RMF)**
- Maintain the **Cybersecurity Framework (CSF)**
- Operate the **National Vulnerability Database (NVD)**
- Develop **National Checklist Program** configuration baselines

**Does NOT:**
- Enforce compliance (no enforcement authority)
- Operate security tools
- Investigate incidents

### Office of Management and Budget (OMB)

**Role:** Policy, oversight, and budget authority over civilian federal agencies

**Statutory authority:** FISMA 2014 § 3553(a); OMB Circular A-130

**Key responsibilities:**
- Issue binding **OMB Memoranda** implementing FISMA requirements
- Collect annual agency FISMA reports and IG reports
- Submit annual report to Congress on federal cybersecurity
- Coordinate with NIST, DHS/CISA, and NSA on cybersecurity policy
- Approve agency information technology budgets (affects security funding)
- Issue **OMB Circular A-130** (Managing Information as a Strategic Resource) — foundational policy

**Key OMB Memoranda:**

| Memo | Subject |
|------|---------|
| M-17-25 | Reporting Guidance for Executive Order on Strengthening the Cybersecurity of Federal Networks |
| M-19-03 | Strengthening the Cybersecurity of Federal Agencies by Enhancing the High Value Asset Program |
| M-21-31 | Improving the Federal Government's Investigative and Remediation Capabilities |
| M-22-05 | Fiscal Year 2021-2022 Guidance on Federal Information Security and Privacy Management Requirements |
| M-22-09 | Moving the U.S. Government Toward Zero Trust Cybersecurity Principles |
| M-23-10 | The Registration and Use of .gov Domains |
| M-24-04 | Memorandum on Advancing the Responsible Use of Artificial Intelligence |

### Cybersecurity and Infrastructure Security Agency (CISA)

**Role:** Operational cybersecurity support, threat information sharing, and incident coordination

**Statutory authority:** Cybersecurity and Infrastructure Security Agency Act of 2018; FISMA 2014 § 3554

**Key responsibilities:**
- Operate **US-CERT** (United States Computer Emergency Readiness Team) — federal incident reporting hub
- Issue **Binding Operational Directives (BODs)** — mandatory for civilian federal agencies
- Operate the **CDM (Continuous Diagnostics and Mitigation)** program
- Operate the **EINSTEIN** intrusion detection/prevention system
- Maintain the **Known Exploited Vulnerabilities (KEV)** catalog
- Provide **cybersecurity assessments** to agencies upon request
- Operate the **Federal Risk and Authorization Management Program (FedRAMP)** (jointly with GSA and DoD)
- Issue **Emergency Directives (EDs)** for active threats requiring immediate agency action

**CISA Binding Operational Directives (selected):**

| BOD | Title | Key Requirement |
|-----|-------|-----------------|
| BOD 18-01 | Enhance Email and Web Security | DMARC, STARTTLS, HTTPS enforcement |
| BOD 19-02 | Vulnerability Remediation | Critical vulns: 15 days; High: 30 days |
| BOD 20-01 | Develop and Publish a Vulnerability Disclosure Policy | VDP required for all agencies |
| BOD 22-01 | Reducing Significant Risk of Known Exploited Vulnerabilities | KEV catalog; 2-week remediation for most |
| BOD 23-01 | Improving Asset Visibility and Vulnerability Detection | Asset discovery; automated vuln detection |

### National Security Agency (NSA) / Committee on National Security Systems (CNSS)

**Role:** Security standards and oversight for **national security systems (NSS)**

- **NSS** are systems that handle classified information or are critical to national security functions
- NSS are excluded from NIST/FISMA civilian standards
- NSS use **CNSSI** (CNSS Instructions) and **NSA guidelines** instead
- FISMA 2014 exempts NSS from OMB/DHS oversight; DoD/IC have separate oversight chains

---

## 4. Mandatory Standards vs Guidelines

### The Distinction

Under FISMA, NIST produces two types of documents with different legal standing:

| Type | Legal Status | Example | Non-compliance Consequence |
|------|-------------|---------|---------------------------|
| **FIPS** (Federal Information Processing Standards) | **Mandatory** for federal agencies | FIPS 140-3, FIPS 199, FIPS 200 | Non-compliance = FISMA violation; can result in denial of ATO |
| **NIST Special Publications (SPs)** | **Guidelines** (advisory) | SP 800-53, SP 800-37 | Non-mandatory unless invoked by OMB policy or agency policy |
| **NIST Interagency Reports (NISTIRs)** | **Informational** | NISTIR 8011, NISTIR 8170 | Advisory only |

> **Critical nuance:** OMB often makes NIST SPs **effectively mandatory** by referencing them in binding OMB Circulars or Memoranda. For example, OMB A-130 references NIST SP 800-53, making it the de facto mandatory control catalog. Agencies may use alternative approaches if they meet or exceed the outcome requirements.

### FIPS and Their Status

| FIPS | Title | Status |
|------|-------|--------|
| FIPS 140-3 | Security Requirements for Cryptographic Modules | Mandatory |
| FIPS 197 | Advanced Encryption Standard (AES) | Mandatory |
| FIPS 198-1 | The Keyed-Hash Message Authentication Code (HMAC) | Mandatory |
| FIPS 199 | Standards for Security Categorization of Federal Information and Information Systems | Mandatory |
| FIPS 200 | Minimum Security Requirements for Federal Information and Information Systems | Mandatory |
| FIPS 201-3 | Personal Identity Verification (PIV) of Federal Employees and Contractors | Mandatory |

---

## 5. FIPS 140-3 — Cryptographic Modules

### Purpose

FIPS 140-3 specifies security requirements for **cryptographic modules** — both hardware and software — used to protect sensitive federal information. It is aligned with the international standard **ISO/IEC 19790:2012**.

FIPS 140-3 superseded FIPS 140-2 (effective September 2019; validation of new modules against 140-2 ended September 2021; 140-2 certificates remain active until sunset date).

### Security Levels

| Level | Description | Use Case |
|-------|-------------|---------|
| **Level 1** | Basic security requirements; no specific physical security | Software-only modules; general-purpose applications |
| **Level 2** | Adds tamper-evidence (coatings, seals) and role-based auth | Storage devices, smart cards |
| **Level 3** | Adds tamper-response (zeroization on tamper) and identity-based auth | Hardware security modules (HSMs), cryptographic tokens |
| **Level 4** | Highest; complete envelope of protection; detects environmental attacks | Extreme environments, military applications |

### CMVP — Cryptographic Module Validation Program

- FIPS 140-3 validation is performed under the **Cryptographic Module Validation Program (CMVP)**, jointly operated by **NIST** and the **Canadian Centre for Cyber Security (CCCS)**
- Organizations submit modules to accredited Cryptographic and Security Testing (CST) laboratories
- Validated modules are listed in the **NIST CMVP database** (csrc.nist.gov/projects/cryptographic-module-validation-program)
- Only modules on the validated list satisfy FIPS 140-3 requirements

### Federal Agency Obligations

- All federal agencies must use **FIPS-validated cryptographic modules** when protecting sensitive data
- This applies to: encryption, key management, digital signatures, random number generation, hash functions
- Applies to **all sensitive but unclassified information** — not just classified
- CMMC Level 2 requirement 3.13.11 mirrors this: "Employ FIPS-validated cryptography when used to protect CUI"

### Common FIPS 140-3 Validated Products

| Category | Examples |
|----------|----------|
| OS/Platform | Windows (via CNG/Schannel), RHEL (via NSS), OpenSSL (FIPS mode) |
| VPN | Cisco, Palo Alto, Juniper (FIPS mode firmware) |
| Full Disk Encryption | BitLocker (Windows), FileVault (macOS with FIPS configuration) |
| HSMs | Thales Luna, Entrust nShield, AWS CloudHSM |
| Databases | Oracle Database TDE (FIPS mode), SQL Server |
| Cloud | AWS GovCloud services using FIPS endpoints, Azure Government |

---

## 6. FIPS 199 — System Categorization

### Purpose

**FIPS 199** (Standards for Security Categorization of Federal Information and Information Systems) defines how federal agencies categorize their information and systems based on potential impact to national security, national interests, or the operation of government.

Categorization drives the selection of appropriate security controls under NIST SP 800-53 and is the first step in the NIST RMF.

### Impact Levels

| Level | Definition |
|-------|------------|
| **Low** | Limited adverse effect. Loss of availability, integrity, or confidentiality could cause minor damage to organizational operations, assets, or individuals |
| **Moderate** | Serious adverse effect. Could cause significant damage to organizational operations, assets, or individuals |
| **High** | Severe or catastrophic adverse effect. Could cause severe or catastrophic damage; may include loss of life |

### CIA Triad Categorization

Each system is categorized against **three security objectives**:

```
SC(system) = {(Confidentiality, Impact), (Integrity, Impact), (Availability, Impact)}
```

**Example:**
```
SC(Payroll System) = {(Confidentiality, MODERATE), (Integrity, MODERATE), (Availability, LOW)}
```

The **overall system category** is determined by the **high watermark** — the highest impact level across all three objectives:

```
Overall System Category = MAX(Confidentiality impact, Integrity impact, Availability impact)
SC(Payroll System) = MODERATE (because Confidentiality and Integrity are both Moderate)
```

### NIST SP 800-60 — Mapping Information Types

NIST SP 800-60 (Guide for Mapping Types of Information and Information Systems to Security Categories) provides:
- Pre-defined information types with recommended impact levels
- Organized by mission area (Government Resource Management, Services for Citizens, etc.)
- Agencies can adjust recommendations based on their specific circumstances

**Example mappings from SP 800-60:**

| Information Type | C | I | A |
|-----------------|---|---|---|
| Personnel Records | M | M | L |
| Financial Transaction Processing | H | H | M |
| General Public Information | L | L | L |
| Emergency Services | M | H | H |
| Criminal Investigation Records | H | H | M |

---

## 7. FIPS 200 — Minimum Security Requirements

### Purpose

**FIPS 200** (Minimum Security Requirements for Federal Information and Information Systems) establishes the **minimum security requirements** for federal information and systems based on FIPS 199 impact levels.

FIPS 200 defines 17 security-related areas and requires agencies to implement security controls from NIST SP 800-53 based on the system's FIPS 199 category.

### The 17 Security Areas

| # | Area | Description |
|---|------|-------------|
| 1 | Access Control | Limit access to authorized users and functions |
| 2 | Awareness and Training | Ensure personnel understand security responsibilities |
| 3 | Audit and Accountability | Create and protect audit records |
| 4 | Certification, Accreditation, and Security Assessments | Conduct security assessments; authorize systems |
| 5 | Configuration Management | Establish baselines; manage changes |
| 6 | Contingency Planning | Establish backup, recovery, and continuity plans |
| 7 | Identification and Authentication | Identify and authenticate users and devices |
| 8 | Incident Response | Establish incident handling capability |
| 9 | Maintenance | Perform maintenance; control maintenance tools |
| 10 | Media Protection | Protect, sanitize, and destroy storage media |
| 11 | Physical and Environmental Protection | Limit physical access; protect against environmental threats |
| 12 | Planning | Develop and maintain security plans |
| 13 | Personnel Security | Screen personnel; terminate access when needed |
| 14 | Risk Assessment | Assess risk; scan for vulnerabilities |
| 15 | Systems and Services Acquisition | Include security in acquisition; manage supply chain |
| 16 | System and Communications Protection | Monitor and protect communications |
| 17 | System and Information Integrity | Protect against malware; patch; monitor for threats |

### Relationship Between FIPS 200 and SP 800-53

FIPS 200 mandates implementation of security controls from **NIST SP 800-53** appropriate to the system's category:

| FIPS 199 Category | SP 800-53 Baseline |
|-------------------|--------------------|
| Low | SP 800-53B Low Baseline |
| Moderate | SP 800-53B Moderate Baseline |
| High | SP 800-53B High Baseline |

Agencies may **tailor** baselines (add controls, remove controls with justification, or add parameters) based on mission needs, risk assessments, and specific system context.

---

## 8. Agency Security Program Requirements

Under FISMA 2014, each federal agency must implement an **agency-wide information security program** that includes:

### Required Program Elements

| Element | Description |
|---------|-------------|
| **Periodic risk assessments** | Assess risk to operations, assets, and individuals from operation of information systems |
| **Risk-based policies and procedures** | Implement cost-effective, risk-based information security policies |
| **Security planning** | Develop security plans for all information systems |
| **Security training and awareness** | Ensure all personnel receive annual security awareness training |
| **Security assessments** | Periodically test and evaluate security controls |
| **Remediation actions** | Track and correct deficiencies; implement plans of action |
| **Incident detection and response** | Implement procedures for detecting, reporting, and responding to incidents |
| **Continuity planning** | Develop plans for continuity of operations in emergencies |
| **Contractor oversight** | Ensure contractors handling federal information comply with FISMA requirements |

### Agency CIO Responsibilities

The **Chief Information Officer (CIO)** has statutory responsibility to:
- Develop and maintain the agency information security program
- Report annually to the agency head on program effectiveness
- Ensure personnel have appropriate training and education
- Coordinate with the IG on security assessments
- Coordinate with senior officials (CISO, SAOP, etc.)

### Agency CISO Role

While FISMA does not mandate a CISO by title, OMB policy and good practice require:
- A senior official responsible for the day-to-day operations of the security program
- **SAISO (Senior Agency Information Security Officer)** — the statutory designation in FISMA 2014
- Reports to the CIO (or directly to agency head in some structures)
- Coordinates with CISA, OMB, and other federal entities

### Authorizing Official (AO)

The **Authorizing Official** (formerly called Designated Accrediting Authority / DAA):
- A senior management official with authority to accept residual risk for a system
- Signs the **Authorization to Operate (ATO)**
- Accountable for the security of the system they authorize
- ATOs are typically valid for 3 years or until significant change; some systems have ongoing authorization

---

## 9. FISMA Metrics — Annual Reporting

### Overview of FISMA Metrics Framework

OMB requires agencies to report FISMA metrics annually (and in some cases, quarterly or continuously via CyberScope/CYBER.GOV). Metrics have evolved significantly from the early checkbox-era reporting to the current framework-aligned model.

### Current FISMA Metric Domains

The current OMB/CISA FISMA metrics framework is organized into **five domains** aligned with the NIST Cybersecurity Framework:

---

#### Domain 1: Identify

Focuses on understanding the organization's assets, risks, and environment.

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Asset Management** | Percentage of agency hardware assets discovered and inventoried | % of endpoints in CDM dashboard |
| **Risk Management** | Maturity of agency risk management program | Maturity level rating |
| **Supply Chain Risk** | Implementation of SCRM program | % of high-value acquisitions with SCRM review |
| **Privileged Account Inventory** | Accounts with elevated privileges tracked | Count and % covered |
| **System Inventory** | FISMA system inventory completeness | % of systems with current authorization |

---

#### Domain 2: Protect

Focuses on implementing safeguards.

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Identity, Credential, and Access Management (ICAM)** | Implementation of ICAM capabilities | Multiple sub-metrics |
| — Strong authentication (MFA) | % of users with MFA enrolled | % |
| — PIV enforcement | % of privileged users using PIV | % |
| — Privileged account management | % of privileged accounts managed via PAM | % |
| **Device Security** | Coverage of endpoint security solutions | % of endpoints with EDR/AV coverage |
| **Data Protection** | Encryption of data at rest and in transit | % of sensitive data encrypted |
| **Configuration Management** | Compliance with security baselines | % of systems meeting configuration baseline |
| **Vulnerability Management** | Patching compliance for critical/high vulns | % remediated within BOD 19-02 timelines |
| **Training** | Annual security awareness training completion | % of personnel trained |

---

#### Domain 3: Detect

Focuses on identifying cybersecurity events.

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Continuous Monitoring** | CDM sensor coverage | % of systems covered by CDM tools |
| **Log Management** | Systems sending logs to SIEM/SOC | % of systems with centralized logging |
| **Anomaly Detection** | Capability to detect anomalous behavior | Maturity rating |
| **EINSTEIN Coverage** | Agency traffic covered by EINSTEIN 3A | % of agency traffic |
| **Vulnerability Scanning** | Frequency and coverage of vulnerability scans | % of assets scanned regularly |

---

#### Domain 4: Respond

Focuses on incident response capabilities.

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Incident Reporting Timeliness** | Incidents reported to CISA within required timelines | % within 1 hour (significant) |
| **Incident Response Plan** | Current, tested IRP | Yes/No + test date |
| **Incident Categories Handled** | Incidents by NCCIC category | Count by category |
| **Mean Time to Detect (MTTD)** | Average time to detect incidents | Days/hours |
| **Mean Time to Respond (MTTR)** | Average time to contain incidents | Days/hours |

---

#### Domain 5: Recover

Focuses on restoring capabilities after an incident.

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Continuity of Operations** | COOP plans current and tested | % of high-impact systems with tested plans |
| **Backup and Recovery** | Data backup frequency and recovery testing | % of systems with tested recovery procedures |
| **Lessons Learned** | Post-incident reviews conducted | % of significant incidents with PIR |

### High Value Asset (HVA) Metrics

**HVAs** are federal information systems that contain sensitive data or support critical government functions. OMB M-19-03 requires enhanced scrutiny:

- All agencies must identify and report their HVAs
- CISA conducts **Risk and Vulnerability Assessments (RVAs)** of HVAs
- HVAs require additional monitoring and enhanced controls
- Compromises of HVAs must be reported immediately to CISA and OMB

---

## 10. CyberScope and FISMA Reporting Portal

### CyberScope (Legacy System)

**CyberScope** was the OMB-managed system used for FISMA reporting from approximately 2010-2022. It collected:
- Annual agency CIO FISMA reports
- IG FISMA assessments
- Monthly automated data feeds from CDM tools

CyberScope was criticized for:
- Manual data entry burden
- Inconsistent data quality across agencies
- Limited real-time visibility

### CYBER.GOV / Federal Dashboard (Current)

As of 2022-2023, OMB and CISA transitioned FISMA reporting to the **FISMA portal** within the **cyber.gov** ecosystem (also referred to as the Federal Cybersecurity Dashboard):

**Functions:**
- Collects automated data from CDM dashboard
- Integrates agency self-reported FISMA metrics
- Provides OMB and CISA real-time visibility into agency posture
- Supports the annual FISMA reporting process
- Feeds the OMB FISMA Annual Report to Congress

### Annual FISMA Report to Congress

OMB submits an annual report to Congress covering:
- Agency-by-agency grades/assessments
- Government-wide trends
- Significant incidents
- Resource requirements
- Compliance gaps and remediation progress

---

## 11. Inspector General Assessments

### Statutory Requirement

FISMA 2014 § 3555 requires each agency IG to:
- Annually assess the effectiveness of the agency's information security program
- Submit the assessment to OMB
- Include the assessment in the IG Annual Report

The IG assessment is independent from the agency CIO's self-reported metrics — this dual reporting creates a checks-and-balances mechanism.

### IG Assessment Areas

The OMB/CISA provide annual guidance to IGs specifying assessment areas. Key areas include:

| Area | What IGs Evaluate |
|------|------------------|
| **Security Authorization** | Are all systems authorized? Are ATOs current? Are significant change controls working? |
| **Continuous Monitoring** | Is the agency implementing continuous monitoring? Is CDM deployed effectively? |
| **Plan of Action & Milestones (POA&M)** | Are POA&Ms comprehensive and being remediated timely? |
| **Risk Assessment** | Does the agency perform enterprise and system-level risk assessments? |
| **Incident Response** | Does the agency have a tested IRP? Are incidents reported to CISA? |
| **Security Training** | Are all personnel receiving annual training? Are role-specific trainings provided? |
| **Contractor Oversight** | Is the agency ensuring contractor systems comply with FISMA? |
| **Configuration Management** | Are configuration baselines established and maintained? |
| **Identity and Access Management** | Is MFA implemented? Are privileged accounts managed? Are access reviews conducted? |
| **Data Protection** | Is sensitive data encrypted? Are classification/CUI handling procedures followed? |

### IG Maturity Scale

IGs typically rate the effectiveness of each area on a **5-point maturity scale** derived from the OMB/DHS Cybersecurity Maturity Framework:

| Level | Rating | Description |
|-------|--------|-------------|
| 1 | **Ad Hoc** | Policies/controls are not established or are not followed |
| 2 | **Defined** | Policies/controls exist and are documented but inconsistently implemented |
| 3 | **Consistently Implemented** | Policies/controls are implemented consistently agency-wide |
| 4 | **Managed and Measurable** | Implementation measured; metrics collected; deviations identified |
| 5 | **Optimized** | Policies/controls continuously improved based on metrics and feedback |

**Target:** OMB/CISA consider Level 4 or 5 to be "effective." Agencies at Level 1 or 2 are considered ineffective and may face increased scrutiny or remediation requirements.

---

## 12. CDM — Continuous Diagnostics and Mitigation

### Program Overview

The **Continuous Diagnostics and Mitigation (CDM)** program is a CISA-managed initiative providing federal agencies with tools, capabilities, and services to strengthen cybersecurity through continuous monitoring and near-real-time visibility.

**Program goals:**
1. Reduce agency attack surface
2. Increase visibility into the federal cybersecurity posture
3. Improve federal ability to respond to cyber incidents
4. Streamline FISMA reporting with automated data feeds

### CDM Capability Layers

CDM capabilities are organized into four groups (historically called "Phases"):

| CDM Group | Focus Area | Capabilities |
|-----------|------------|--------------|
| **Group A: Manage What Is On the Network** | Asset Management | Hardware asset management; software asset management; configuration management; vulnerability management |
| **Group B: Manage Who Is On the Network** | Identity and Access Management | Account and access management; manage trust in credentials; manage security-related behavior |
| **Group C: Manage What Is Happening On the Network** | Network Security Management | Network anomaly and event management; manage security architecture |
| **Group D: How Bad Is the Situation and What To Do About It** | Data and Risk Management | Data protection management; training and awareness |

### CDM Dashboard

The **CDM Agency Dashboard** aggregates data from CDM tools at each agency and feeds to the **Federal Dashboard** for CISA/OMB visibility:

- Hardware asset inventory
- Software inventory
- Vulnerability scan results
- Account and privilege data
- Configuration compliance data

Data is updated frequently (daily for most tool types; some near-real-time).

### CDM Program Delivery

CISA provides CDM capabilities through:
- **CDM DEFEND** — blanket purchase agreements (BPAs) for agencies to procure CDM-compliant tools
- **CISA-provided tools** — some capabilities provided directly by CISA to agencies at no cost
- **CDM integration** — technical support for agencies integrating CDM tools with their environments

### CDM Requirements for Agencies

- All CFO Act agencies must participate in CDM
- Agencies must deploy CDM sensors/tools to all covered assets
- Agencies must feed CDM dashboard data to the Federal Dashboard
- CDM data feeds are a key input to FISMA metrics reporting

---

## 13. EINSTEIN Program

### Overview

**EINSTEIN** is a network monitoring and detection system operated by CISA to protect federal civilian agency (.gov) networks from cyber threats. It operates at the network perimeter — specifically at the **Trusted Internet Connection (TIC) access points** where agency traffic enters and exits the internet.

### EINSTEIN Generations

| Generation | Deployed | Capability | Type |
|------------|----------|------------|------|
| **EINSTEIN 1** | ~2004 | Flow analysis of inbound/outbound traffic | Detection |
| **EINSTEIN 2** | ~2008 | Deep packet inspection using signatures; alerts on known malicious traffic | Detection |
| **EINSTEIN 3A** | ~2013 | Intrusion prevention; ability to block/divert malicious traffic in real-time | Detection + **Prevention** |

### EINSTEIN 3A Details

EINSTEIN 3A (E3A) is the most capable and most widely deployed generation:

- Uses NSA-developed signatures for known threats (cyber threat indicators - CTIs)
- Deployed at **NCPS (National Cybersecurity Protection System)** nodes operated by managed service providers (AT&T, CenturyLink/Lumen, etc.)
- Provides **intrusion prevention** capabilities — can block or reroute malicious traffic before it reaches agency networks
- Covers both inbound and outbound traffic
- Generates alerts that feed to CISA for analysis

### Limitations of EINSTEIN

- Does not detect unknown (zero-day) threats without signatures
- Does not protect encrypted traffic (cannot inspect TLS without decryption)
- Coverage depends on agencies routing traffic through TIC points
- Cloud-hosted agency traffic may bypass EINSTEIN depending on architecture
- TIC 3.0 policy (2019) acknowledges EINSTEIN's limitations in cloud era

### EINSTEIN and TIC

EINSTEIN is closely tied to the TIC policy (see Section 14). As agencies move to cloud services, TIC 3.0 provides flexibility for cloud-hosted traffic to bypass traditional TIC points while still meeting security requirements — but this reduces EINSTEIN coverage. CISA and OMB have been developing cloud security services (CISA Cloud Security Technical Reference Architecture) to address this gap.

---

## 14. TIC — Trusted Internet Connections

### Overview

**Trusted Internet Connections (TIC)** is an OMB policy (OMB M-19-26 and successors) requiring federal agencies to consolidate and secure their external network connections to reduce the attack surface and enable consistent security monitoring.

### TIC History

| Version | Year | Key Change |
|---------|------|------------|
| TIC 1.0 | 2007 | Initial policy; reduce external connections; EINSTEIN deployment |
| TIC 2.0 | 2012 | Standardized TIC Access Points (TICAPs) and Managed Trusted Internet Protocol Services (MTIPS) |
| TIC 3.0 | 2019-2021 | Modernized for cloud era; multiple security patterns; CISA published reference architectures |

### TIC 3.0 Key Concepts

TIC 3.0 recognizes that the original TIC model (all traffic through centralized TIC access points) is incompatible with cloud-first environments. TIC 3.0 introduces:

1. **Policy Intent:** Focus on security outcomes, not perimeter-based routing
2. **Use Cases:** CISA published multiple TIC use cases with specific guidance:
   - Traditional TIC (on-premise to internet)
   - Cloud SaaS
   - Cloud IaaS
   - Branch Office (SD-WAN)
   - Remote Users
3. **Security Capabilities:** Each use case defines required security capabilities (management/monitoring, traffic filtering, DNS security, email security, etc.)
4. **Flexibility:** Agencies can choose how to implement required capabilities based on their architecture

### TIC 3.0 Security Capabilities

Agencies must implement these capabilities for each use case:

| Capability Category | Examples |
|--------------------|----------|
| **Traffic Management** | Visibility, monitoring, reporting |
| **Traffic Filtering** | Application-layer inspection, URL filtering, DPI |
| **DNS Security** | Protective DNS (block malicious domains) |
| **Email Security** | Anti-spam, anti-phishing, DMARC enforcement |
| **Credential Management** | MFA, certificate management |
| **Intrusion Detection/Prevention** | NGFW, IDS/IPS capabilities |
| **Threat Intelligence** | Integration with CISA threat feeds |

### Protective DNS

CISA operates **Protective DNS (PDNS)** for federal agencies — a resolving DNS service that blocks domains associated with malware, phishing, and other threats. Agencies are encouraged (and increasingly required) to use PDNS to prevent connections to malicious infrastructure.

---

## 15. FISMA Compliance vs FedRAMP

### Relationship Between FISMA and FedRAMP

| Aspect | FISMA | FedRAMP |
|--------|-------|---------|
| **Purpose** | Govern federal agency security programs | Govern cloud services used by federal agencies |
| **Who it applies to** | Federal agencies and contractors operating agency systems | Cloud Service Providers (CSPs) seeking to offer services to agencies |
| **Coverage** | Agency's entire information security program | A specific cloud service/system |
| **Control framework** | NIST SP 800-53 (full suite) | NIST SP 800-53 (selected controls by impact level) |
| **Authorization body** | Agency Authorizing Official (AO) | Agency AO (Agency ATO) or FedRAMP PMO (P-ATO legacy) |
| **Output** | Agency ATO for each system | FedRAMP Authorization + Agency ATO |
| **Continuous monitoring** | Agency performs ConMon for all systems | CSP performs ConMon; reports to agency AO monthly |
| **IG assessment** | Annual IG assessment of entire program | Not directly assessed by IG (but agency's use of FedRAMP services is) |
| **FISMA annual reporting** | Required for all agencies | FedRAMP status reported as part of agency cloud metrics |

### How FedRAMP Satisfies FISMA

When a federal agency uses a FedRAMP-authorized cloud service:
1. The agency **leverages the FedRAMP authorization package** (SSP, SAR, etc.)
2. The agency AO issues an **Agency ATO** specific to their use of the service
3. The agency's FISMA system inventory includes the cloud service
4. The cloud service's controls count toward the agency's FISMA posture
5. The CSP's monthly continuous monitoring reports inform agency FISMA metrics

**The agency still has FISMA responsibilities:**
- Configuring the cloud service appropriately (customer-managed controls)
- Access management for agency users
- Incident reporting
- Data classification and handling

### FedRAMP as FISMA Compliance Vehicle

OMB M-11-11 and subsequent memoranda require agencies to use FedRAMP-authorized cloud services whenever available and applicable. Using a non-FedRAMP-authorized cloud service for federal data is generally a FISMA compliance issue unless the agency has established an equivalent authorization.

---

## 16. RMF Under FISMA — NIST SP 800-37

### Risk Management Framework Overview

The **Risk Management Framework (RMF)**, defined in NIST SP 800-37 Rev 2 (December 2018), is the FISMA implementation process for federal agencies.

### Seven RMF Steps

| Step | Name | Key Activities |
|------|------|----------------|
| **Prepare** | Prepare | Establish organization-level and system-level context; identify risk tolerance; identify authorized officials; develop strategy |
| **Categorize** | Categorize | Apply FIPS 199; determine system impact level (Low/Moderate/High) |
| **Select** | Select | Choose SP 800-53 control baselines based on category; tailor controls |
| **Implement** | Implement | Implement selected controls; document implementation in SSP |
| **Assess** | Assess | Assess control effectiveness using SP 800-53A procedures |
| **Authorize** | Authorize | AO reviews risk; issues ATO or denial; documents residual risk |
| **Monitor** | Monitor | Continuously monitor controls; report to AO; update SSP; track POA&Ms |

### ATO vs Conditional ATO vs IATT

| Authorization Type | Description |
|-------------------|-------------|
| **Authorization to Operate (ATO)** | Full authorization; all controls implemented or risk formally accepted; typically 3-year validity |
| **Conditional ATO** | Authorization with specific conditions (open POA&M items that must be closed within defined time) |
| **Authorization to Test (ATT)** | Used for development/test systems that need to connect to production for testing |
| **Interim Authorization to Test (IATT)** | Temporary authorization for pre-production testing with elevated oversight |
| **Denial of Authorization to Operate (DATO)** | System cannot be authorized; must be shut down or remediated |

---

## 17. OMB Circulars and Memoranda

### OMB Circular A-130 — The Foundation

**OMB Circular A-130: Managing Information as a Strategic Resource** is the foundational policy document for federal information management. The 2016 revision significantly updated cybersecurity requirements:

**Key provisions:**
- Requires agencies to implement the NIST RMF
- Specifies use of NIST SP 800-53 and SP 800-53A
- Requires privacy protections integrated with security
- Mandates continuous monitoring
- Addresses cloud computing and shared services
- Establishes Senior Agency Official for Privacy (SAOP) role
- Requires privacy impact assessments (PIAs) for systems with PII

### OMB Circular A-11 — Budget and Performance

**Circular A-11** governs agency budget submissions and performance reporting, which includes IT and cybersecurity investment reporting. Agencies must:
- Report IT investments via the IT Dashboard
- Include cybersecurity spending in their budget submissions
- Report on cybersecurity performance metrics

### Key OMB Memoranda Timeline

| Year | Memo | Subject |
|------|------|---------|
| 2017 | M-17-25 | Implementing EO 13800 — Strengthening Cybersecurity of Federal Networks |
| 2019 | M-19-03 | Strengthening Cybersecurity of Federal Agencies — High Value Assets |
| 2019 | M-19-26 | TIC 3.0 |
| 2021 | M-21-31 | Improving Investigative and Remediation Capabilities (logging requirements) |
| 2022 | M-22-09 | Zero Trust Architecture Strategy |
| 2022 | M-22-05 | FY2021-2022 FISMA Guidance |
| 2023 | M-23-22 | FedRAMP Reform |
| 2024 | M-24-04 | AI Use in Government |

---

## 18. FISMA vs Other Frameworks

### Comparison Table

| Attribute | FISMA | FedRAMP | CMMC | ISO 27001 | SOC 2 |
|-----------|-------|---------|------|-----------|-------|
| **Jurisdiction** | US Federal | US Federal (cloud) | DoD contractors | International | US/Global (commercial) |
| **Mandatory** | Yes (federal agencies) | Yes (for CSPs selling to federal agencies) | Yes (DoD contractors with CUI) | Contractual/voluntary | Voluntary |
| **Control framework** | NIST SP 800-53 | NIST SP 800-53 | NIST SP 800-171/172 | ISO 27001 Annex A | AICPA Trust Service Criteria |
| **Assessor** | IG + 3PAO (FedRAMP) | 3PAO | C3PAO / DIBCAC | Accredited CB | CPA firm |
| **Output** | ATO | ATO | CMMC certification | ISO 27001 certificate | SOC 2 report |
| **Recurrence** | Annual metrics; 3-year ATO | Continuous monitoring | Triennial assessment | 3-year certificate + annual surveillance | Annual (Type II period) |
| **Risk focus** | Government operational risk | Cloud service risk | Defense supply chain risk | Organizational information security risk | Service reliability and security risk |
| **Continuous monitoring** | Required (CDM) | Required (monthly reports) | Limited (annual self-assessment for L1) | Not explicitly required | Not required |
| **Cost** | Agency budget | CSP cost ($500K-$2M+) | Variable ($50K-$500K+) | Lower ($20K-$200K) | Moderate ($50K-$500K) |

### FISMA and FedRAMP Integration for Agency Cloud Adoption

When a federal agency is moving a FISMA system to cloud:

1. **Agency identifies** the system and its FISMA categorization
2. **Agency evaluates** FedRAMP-authorized cloud offerings at appropriate impact level
3. **Agency leverages** existing FedRAMP authorization package (SSP, SAR, POA&M)
4. **Agency issues** an agency-level ATO referencing the FedRAMP authorization
5. **Agency configures** customer-managed controls (user access, data classification, etc.)
6. **Agency monitors** the cloud system as part of its FISMA portfolio
7. **CSP provides** monthly continuous monitoring reports per FedRAMP requirements
8. **Agency CISO** incorporates the cloud system into annual FISMA metrics reporting

---

## Summary Reference Card

| Topic | Key Points |
|-------|------------|
| **FISMA authority** | 44 U.S.C. Chapter 35, Subchapter II (2014) |
| **NIST role** | Standards (FIPS) and guidelines (SPs) |
| **OMB role** | Policy, oversight, annual reporting |
| **CISA role** | Operations, CDM, EINSTEIN, BODs |
| **NSA/CNSS role** | National security systems (separate from civilian FISMA) |
| **Mandatory standards** | FIPS 140-3, FIPS 199, FIPS 200, FIPS 201-3 |
| **Core guidelines** | NIST SP 800-37 (RMF), SP 800-53 (controls), SP 800-53A (assessment) |
| **System categories** | Low, Moderate, High (based on CIA impact per FIPS 199) |
| **ATO validity** | Typically 3 years; continuous authorization model increasingly used |
| **CDM** | CISA-operated tools for continuous asset/vuln monitoring |
| **EINSTEIN** | CISA network monitoring at TIC points |
| **TIC 3.0** | Updated connection policy for cloud environments |
| **IG assessment** | Annual, independent evaluation of agency security program |
| **FISMA metrics domains** | Identify, Protect, Detect, Respond, Recover (NIST CSF-aligned) |
| **Key OMB memos** | M-22-09 (ZTA), M-22-05 (FISMA guidance), M-21-31 (logging) |

---

*Document Version: 1.0 | Legislative Basis: FISMA 2014 (P.L. 113-283) with 2023 updates*
*Implementing Standards: FIPS 199, FIPS 200, NIST SP 800-37 Rev 2, NIST SP 800-53 Rev 5*
*Intended Use: LLM GRC Knowledge Base*
