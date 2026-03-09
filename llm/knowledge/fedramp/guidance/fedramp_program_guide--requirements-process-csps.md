# FedRAMP Program Guide — Comprehensive Reference
## Requirements, Authorization Process, and Guidance for Cloud Service Providers

**Program:** Federal Risk and Authorization Management Program (FedRAMP)
**Managing Entities:** General Services Administration (GSA) — FedRAMP PMO; OMB; CISA; DoD (JAB legacy)
**Statutory Basis:** FedRAMP Authorization Act (enacted December 2022 as part of the FY2023 NDAA)
**Primary Audience:** Cloud Service Providers (CSPs), federal agency security teams, 3PAOs, GRC practitioners

---

## Table of Contents

1. [FedRAMP Overview and Mission](#1-fedramp-overview-and-mission)
2. [FedRAMP Program Management Office (PMO)](#2-fedramp-program-management-office-pmo)
3. [FedRAMP Authorization Types](#3-fedramp-authorization-types)
4. [FedRAMP Ready, In Process, Authorized](#4-fedramp-ready-in-process-authorized)
5. [Impact Levels — Low, Moderate, High](#5-impact-levels--low-moderate-high)
6. [Cloud Service Provider (CSP) Requirements](#6-cloud-service-provider-csp-requirements)
7. [Third Party Assessment Organizations (3PAOs)](#7-third-party-assessment-organizations-3paos)
8. [Agency Authorization Sponsor Process](#8-agency-authorization-sponsor-process)
9. [FedRAMP Documentation Requirements](#9-fedramp-documentation-requirements)
10. [FedRAMP Continuous Monitoring Requirements](#10-fedramp-continuous-monitoring-requirements)
11. [FedRAMP Marketplace](#11-fedramp-marketplace)
12. [OMB Memo M-23-22 — FedRAMP Reform](#12-omb-memo-m-23-22--fedramp-reform)
13. [FedRAMP vs DoD Impact Levels (IL2/IL4/IL5/IL6)](#13-fedramp-vs-dod-impact-levels)
14. [FedRAMP OSCAL and Automation](#14-fedramp-oscal-and-automation)
15. [Control Inheritance from FedRAMP-Authorized Providers](#15-control-inheritance-from-fedramp-authorized-providers)
16. [FedRAMP and FISMA Integration](#16-fedramp-and-fisma-integration)
17. [Common Challenges and Pitfalls](#17-common-challenges-and-pitfalls)
18. [Key Definitions and Acronyms](#18-key-definitions-and-acronyms)

---

## 1. FedRAMP Overview and Mission

### What is FedRAMP?

The **Federal Risk and Authorization Management Program (FedRAMP)** is a US government program that provides a standardized approach to security assessment, authorization, and continuous monitoring for cloud products and services used by federal agencies.

### The "Do Once, Use Many" Principle

FedRAMP's core value proposition is **reuse of security assessments** across multiple agencies:

- Without FedRAMP: Each agency would conduct its own security assessment of every cloud service — duplicating effort and creating inconsistent standards
- With FedRAMP: A cloud service is assessed **once** against a standardized control set, and the authorization package is reused by **many** agencies
- Result: Agencies save time and money; CSPs gain access to the entire federal market with one assessment

### Legislative Basis

The **FedRAMP Authorization Act** (enacted December 2022, Title II, FY2023 NDAA):
- Codified FedRAMP into law for the first time (previously operated under OMB policy)
- Requires GSA to establish and update FedRAMP standards and processes
- Directs OMB to issue guidance on agency use of FedRAMP
- Requires agencies to use FedRAMP for cloud services unless an exception is granted
- Establishes the FedRAMP Board (replaces JAB for governance)

### Prior Authority: OMB M-11-11

Before codification, FedRAMP operated under **OMB Memorandum M-11-11** (2011):
> "Effective immediately, agencies shall use FedRAMP when conducting risk assessments, security authorizations, and granting ATOs for all Executive Branch Federal information systems that use cloud services."

### Scale of FedRAMP

As of 2025:
- **300+** FedRAMP-authorized cloud services
- **50+** CSPs with authorized services
- **200+** active 3PAOs
- Estimated **$50 billion** in annual federal cloud spending going through FedRAMP-authorized services

---

## 2. FedRAMP Program Management Office (PMO)

### Location and Structure

The **FedRAMP PMO** is housed within the **General Services Administration (GSA)**, specifically within GSA's Technology Transformation Services (TTS).

### PMO Responsibilities

| Function | Description |
|----------|-------------|
| **Program governance** | Maintain FedRAMP policy, standards, and processes |
| **Marketplace management** | Operate the FedRAMP Marketplace (marketplace.fedramp.gov) |
| **3PAO accreditation** | Partner with A2LA for 3PAO accreditation |
| **Template and template maintenance** | Maintain SSP, SAP, SAR, POA&M, and other document templates |
| **Reviewing authorization packages** | Review packages submitted for FedRAMP Ready and (for agency ATOs) package quality |
| **Training and outreach** | Provide training for agencies, CSPs, and 3PAOs |
| **Continuous monitoring oversight** | Monitor CSP ConMon reports; escalate non-compliance |
| **OSCAL development** | Lead development of FedRAMP OSCAL templates and tooling |
| **Agency liaison** | Support agencies leveraging FedRAMP authorizations |

### FedRAMP Board (Successor to JAB)

The **FedRAMP Authorization Act** established the **FedRAMP Board** to replace the Joint Authorization Board (JAB):

**Composition:**
- CISA Director (or designee)
- DoD CIO (or designee)
- GSA Administrator (or designee)
- NSF Director (or designee)
- Other members as designated by OMB

**Responsibilities:**
- Approve FedRAMP framework changes
- Serve as the primary governance authority
- Issue guidance on standards and requirements
- No longer directly issues P-ATOs (JAB P-ATO path is legacy/closed to new applicants)

### Joint Authorization Board (JAB) — Legacy

The **JAB** was the original governance body composed of:
- DoD CIO
- DHS CIO
- GSA CIO

The JAB issued **Provisional Authority to Operate (P-ATO)** for high-priority, widely-used cloud services. The JAB P-ATO program was effectively closed to new authorizations in 2023 as part of the FedRAMP reform.

---

## 3. FedRAMP Authorization Types

### Current Authorization Paths

| Authorization Type | Description | Who Issues | Current Status |
|-------------------|-------------|------------|----------------|
| **Agency ATO** | Individual agency issues ATO for CSP offering | Agency Authorizing Official | Active — primary path |
| **FedRAMP Tailored (Li-SaaS)** | Lightweight baseline for low-risk SaaS | Agency AO | Active — for qualifying services |
| **JAB P-ATO** | Provisional ATO from Joint Authorization Board | JAB | **Legacy** — closed to new applicants |

### Agency ATO Path

The **Agency ATO** is now the primary and preferred path for FedRAMP authorization.

**Process overview:**

1. **CSP selects agency sponsor** — an agency willing to sponsor the authorization
2. **CSP engages 3PAO** — selects and contracts with a FedRAMP-accredited 3PAO
3. **CSP prepares documentation** — SSP, policies, procedures, architecture diagrams
4. **3PAO conducts assessment** — Security Assessment Plan (SAP) → assessment activities → Security Assessment Report (SAR)
5. **CSP remediates findings** — address any vulnerabilities or gaps found during assessment
6. **Agency reviews package** — agency AO reviews SSP, SAR, POA&M
7. **Agency issues ATO** — Agency AO signs the ATO memo
8. **Package submitted to FedRAMP PMO** — PMO reviews and lists on Marketplace
9. **Other agencies can reuse** — additional agencies issue their own ATOs based on existing package

**Timeline:** Typically 12-24 months from engagement to authorization

**Cost to CSP:**
- 3PAO assessment: $500,000 - $2,000,000+ depending on service complexity
- Internal preparation costs: $200,000 - $1,000,000+
- Ongoing continuous monitoring: $200,000 - $500,000+ per year

### JAB P-ATO (Legacy)

Previously, the JAB would issue a **Provisional ATO (P-ATO)** that gave agencies confidence the service met government-wide security standards. Benefits included:
- Recognized government-wide, not just by one agency
- Often perceived as more rigorous than agency ATOs

**Why it was closed:**
- JAB backlog — could not keep pace with demand
- Reform effort directed resources toward agency ATOs
- OMB M-23-22 directed shift to agency-sponsored model

Existing JAB P-ATOs remain valid and are maintained. New applicants cannot enter the JAB path.

### FedRAMP Tailored (Low Impact SaaS — Li-SaaS)

**FedRAMP Tailored** is a simplified authorization path for low-risk SaaS applications that:
- Process only publicly available information (Low impact data)
- Are used for **collaboration** or **productivity** (not core mission systems)
- Have a limited attack surface
- Rely heavily on the underlying infrastructure provider's FedRAMP authorization

**Li-SaaS Criteria (all must be met):**
1. Information processed, stored, and transmitted is CUI or low-impact
2. The service does not host federal data that qualifies as Moderate or High impact
3. No personally identifiable information (PII) beyond the minimum needed for user authentication
4. The service serves no operational mission-critical function for the federal government
5. Data is correctable, replaceable, or not tied to government operations

**Li-SaaS Process:**
- Simplified control set (~37 controls)
- Agency sponsors the authorization
- No mandatory 3PAO involvement (agency may use an independent assessor)
- Agency issues ATO and submits package to FedRAMP

**Li-SaaS vs Moderate ATO:**

| Attribute | Li-SaaS | Moderate ATO |
|-----------|---------|--------------|
| Controls | ~37 | 323 |
| 3PAO required | No | Yes |
| Cost | Much lower | $500K-$2M+ |
| Applicable to | Low-risk collaboration tools | Mission-critical systems with CUI |

---

## 4. FedRAMP Ready, In Process, Authorized

### Designation Definitions

| Status | Meaning | How Obtained |
|--------|---------|--------------|
| **FedRAMP Ready** | Package reviewed by FedRAMP PMO; meets minimum documentation standards; ready for agency sponsorship | CSP submits package to PMO; PMO reviews and designates |
| **FedRAMP In Process** | CSP has an active agency sponsor and is working toward authorization | CSP + agency notify PMO; PMO lists status |
| **FedRAMP Authorized** | Authorization has been granted and is active | Agency (or JAB legacy) issues ATO; PMO lists on Marketplace |

### FedRAMP Ready — What It Means

"FedRAMP Ready" does NOT mean the service is authorized. It means:
- The service has been vetted for minimum documentation quality
- The PMO has reviewed the SSP and supporting materials
- The service is ready to find an agency sponsor and proceed to full assessment
- Designation is valid for **1 year** (renewable)

**Common misconception:** Agencies sometimes incorrectly believe FedRAMP Ready means FedRAMP Authorized. This is incorrect and can create compliance issues.

### FedRAMP In Process

When a CSP and agency sponsor are actively working toward authorization, the service can be listed as "In Process":
- **Use by sponsoring agency:** Allowed with risk acceptance
- **Use by other agencies:** Generally not allowed; must wait for authorization
- **Duration:** No formal time limit, but PMO monitors progress and may remove listing if stalled

### FedRAMP Authorized

An authorized service:
- Has been fully assessed by a 3PAO
- Has an active ATO from at least one federal agency
- Is listed on the FedRAMP Marketplace
- Maintains continuous monitoring obligations
- Authorization remains valid as long as ConMon requirements are met

---

## 5. Impact Levels — Low, Moderate, High

FedRAMP impact levels map directly to FIPS 199 system categorization.

### Low Impact

**Data type:** Publicly available or low-sensitivity government information

**Control count:** Approximately **127 controls** from NIST SP 800-53 Low Baseline

**Use cases:**
- Public-facing websites
- Open government data portals
- Internal productivity tools with no sensitive data
- Development/test environments

**Common authorizations:** Many collaboration and productivity SaaS tools

### Moderate Impact

**Data type:** Controlled Unclassified Information (CUI) and sensitive government data; loss could cause serious adverse effects

**Control count:** Approximately **323 controls** from NIST SP 800-53 Moderate Baseline

**Use cases:**
- Systems processing CUI
- Email and collaboration platforms with government data
- Financial systems
- Human Resources systems
- Most general-purpose government cloud systems

**Most common impact level** — approximately 80% of FedRAMP authorizations are at Moderate

### High Impact

**Data type:** Information where breach could cause severe or catastrophic effects; may include law enforcement, critical infrastructure, financial systems

**Control count:** Approximately **421 controls** from NIST SP 800-53 High Baseline

**Use cases:**
- Law enforcement data
- Criminal justice information
- Emergency services
- Financial market regulation
- Defense data (not classified — classified uses NSS paths)
- Health records systems at scale

**Examples of authorized High offerings:** AWS GovCloud (US), Microsoft Azure Government, Google Cloud (for specific services)

### Control Count Breakdown

| Impact Level | NIST SP 800-53 Rev 5 Control Families | Approximate Control Count |
|-------------|--------------------------------------|--------------------------|
| Low | All 20 families, Low baseline parameters | ~127 |
| Moderate | All 20 families, Moderate baseline parameters | ~323 |
| High | All 20 families, High baseline parameters | ~421 |

> Note: Exact counts vary with FedRAMP overlays and tailoring. The FedRAMP-specific baseline adds requirements beyond the NIST baseline in some areas (e.g., incident reporting timelines, ConMon requirements).

### FedRAMP Baseline Overlays

FedRAMP applies **overlays** on top of NIST 800-53 baselines to address cloud-specific requirements:

1. **FedRAMP-specific parameter values** — more prescriptive than NIST baseline (e.g., specific password length requirements)
2. **Additional controls** — requirements specific to cloud environments
3. **Conditional requirements** — apply based on CSP deployment model (SaaS vs IaaS vs PaaS)
4. **Agency-specific overlays** — some agencies require additional controls beyond FedRAMP baseline

---

## 6. Cloud Service Provider (CSP) Requirements

### Who Needs FedRAMP Authorization?

A CSP must be FedRAMP authorized if **any federal agency** intends to use their service to:
- Process, store, or transmit federal information
- Operate on behalf of a federal agency
- Provide infrastructure, platform, or software services to federal systems

### CSP Eligibility

Any organization offering a cloud service can pursue FedRAMP authorization, but practically:
- Must have a service that meets the definition of "cloud computing" per NIST SP 800-145
- Must be able to sustain the significant investment required
- Must have a willing federal agency sponsor (or pursue FedRAMP Ready designation first)
- Must engage an accredited 3PAO

### CSP Organizational Requirements

Before pursuing authorization, a CSP must establish:

1. **Defined cloud service offering boundary** — what is included in the FedRAMP assessment scope
2. **System Security Plan (SSP)** — comprehensive documentation of the system
3. **Information System Owner** — organizational responsibility for the service
4. **Authorizing Official Designated Representative (AODR)** — works with agency AO
5. **Information System Security Officer (ISSO)** — day-to-day security management
6. **Policies and procedures** for all required FedRAMP control areas
7. **Configuration management** — documented baselines for all components
8. **Incident response capability** — 24/7 ability to detect, respond, and report incidents
9. **Vulnerability management program** — regular scanning, timely remediation

### CSP Service Model Implications

| Service Model | CSP Responsibility | Customer (Agency) Responsibility |
|--------------|-------------------|----------------------------------|
| **IaaS** | Physical security, hypervisor, networking, storage | OS, applications, data, access management |
| **PaaS** | IaaS + OS, middleware, runtime | Applications, data, access management |
| **SaaS** | IaaS + PaaS + applications | Data, access management, configuration |

The **customer responsibility matrix** (sometimes called **CRM** or **RACI matrix**) in the CSP's SSP documents exactly which controls are managed by the CSP vs. the agency customer.

### CSP Deployment Models

| Deployment | Description | FedRAMP Implications |
|-----------|-------------|---------------------|
| **Public Cloud** | Shared infrastructure serving multiple customers | Must use logical isolation; shared responsibility well-documented |
| **Government Community Cloud** | Dedicated to government customers only | Less concern about commercial co-mingling |
| **Private Cloud** | Dedicated to single organization | Often not subject to FedRAMP if agency-owned |
| **Hybrid Cloud** | Mix of cloud and on-premise | Boundary definition critical; may require separate authorizations |

### CSP Continuous Monitoring Obligations

After authorization, CSPs must maintain the following ongoing obligations (see Section 10 for full details):
- Monthly vulnerability scanning
- Monthly ConMon report to sponsoring agency
- Annual penetration test
- Annual security assessment of a subset of controls
- Significant change requests (SCR) before major changes
- Incident reporting within defined timelines
- Annual update of core documentation

### CSP Responsibilities for Incident Reporting

| Incident Type | Reporting Timeline |
|--------------|--------------------|
| **Breach of federal data (High/Moderate)** | Within **1 hour** of discovery (to agency and US-CERT) |
| **Security incident (significant)** | Within **24 hours** (to agency AO) |
| **Operational incident** | Within **72 hours** |
| **Monthly reporting** | All incidents in monthly ConMon report |

---

## 7. Third Party Assessment Organizations (3PAOs)

### What is a 3PAO?

A **Third Party Assessment Organization (3PAO)** is an organization independently accredited to conduct FedRAMP security assessments. 3PAOs are the neutral evaluators that provide the technical assessment underpinning FedRAMP authorizations.

### 3PAO Accreditation

**Accreditation body:** **A2LA (American Association for Laboratory Accreditation)**
- Accredits 3PAOs against ISO/IEC 17020 (Requirements for the operation of various types of bodies performing inspection)
- FedRAMP-specific criteria applied in addition to ISO 17020
- 3PAO accreditation is valid for 2 years; renewed through reassessment

**Finding accredited 3PAOs:** Listed on the FedRAMP Marketplace at marketplace.fedramp.gov (search for "3PAO")

### 3PAO Independence Requirements

A 3PAO must be independent from the CSP they assess:
- No financial relationship or ownership ties
- No prior consulting work on the system being assessed (typically 1 year cooling-off period)
- Assessors must have no conflicts of interest
- Must sign conflict of interest attestation

### 3PAO Assessment Activities

A FedRAMP assessment by a 3PAO involves:

**1. Security Assessment Plan (SAP) Development**
- Define scope of assessment
- Select controls to test
- Define testing methods for each control (examine, interview, test)
- Define sampling approach for large control families
- Agree on assessment schedule and logistics with CSP

**2. Assessment Execution**
- **Document review:** Review SSP, policies, procedures, configurations
- **Interviews:** Interview personnel responsible for control implementation
- **Technical testing:** Vulnerability scanning, penetration testing, configuration review
- **Observation:** Watch control processes in action where applicable

**3. Security Assessment Report (SAR) Development**
- Document findings for each tested control
- Risk ratings: Critical, High, Moderate, Low, Informational
- Identify false positives vs. actual findings
- Provide remediation recommendations
- Calculate overall risk posture

**4. Remediation Validation**
- CSP remediates findings
- 3PAO validates remediation (retest critical/high findings)
- Update SAR with remediation status

### 3PAO Assessment Methods

| Method | Description | Used For |
|--------|-------------|---------|
| **Examine** | Review documents, configurations, logs | Policy review, configuration baseline review |
| **Interview** | Question personnel | Understanding processes, training, procedures |
| **Test** | Execute technical procedures | Vulnerability scanning, pen testing, actual control testing |

NIST SP 800-53A defines the specific assessment procedures for each control using these three methods.

### Annual vs. Full Assessment

| Assessment Type | Scope | Frequency |
|----------------|-------|-----------|
| **Initial (Full) Assessment** | All applicable controls | Once (for initial authorization) |
| **Annual Assessment** | Subset of controls (approximately one-third) | Annually during ConMon |
| **Significant Change Assessment** | Controls affected by the change | As needed per SCR |
| **Penetration Test** | Red team / pen test against boundary | Annually |

---

## 8. Agency Authorization Sponsor Process

### Why Agencies Sponsor CSPs

Agencies sponsor CSP authorizations when:
- The agency wants to use a cloud service that is not yet FedRAMP authorized
- The agency has resources to invest in the authorization process
- The agency will be a primary user of the service and has leverage with the CSP

Sponsoring an authorization benefits the federal government broadly — the resulting authorization can be reused by all agencies.

### Agency Responsibilities as Sponsor

| Responsibility | Description |
|---------------|-------------|
| **Assess the package** | Agency security team (and/or 3PAO) reviews SSP, SAR, POA&M |
| **Issue the ATO** | Agency AO signs ATO based on acceptable residual risk |
| **Accept open risks** | AO accepts residual risk from open POA&M items |
| **Receive ConMon reports** | Monthly ConMon reports from CSP; review and respond |
| **Participate in significant changes** | Review and approve/deny significant change requests |
| **Notify FedRAMP PMO of incidents** | Coordinate incident notification |
| **Revoke ATO if needed** | If CSP fails ConMon requirements, agency may revoke |

### Leveraging an Existing Authorization (Non-Sponsoring Agency)

When an agency wants to use a FedRAMP-authorized service without sponsoring a new authorization:

1. **Review the FedRAMP Marketplace listing** for the service
2. **Request the authorization package** from the CSP (agencies have a right to the package under FedRAMP policy)
3. **Review the package** — SSP, SAR, POA&M, and recent ConMon reports
4. **Complete agency-specific configuration** — configure the service for their use
5. **Complete customer responsibilities** from the CRM — implement agency-managed controls
6. **Issue an agency ATO** — agency AO signs ATO; references FedRAMP authorization
7. **Notify FedRAMP PMO** — register as an agency using the service
8. **Receive ongoing ConMon updates** — subscribe to CSP monthly reports

**Timeline for leveraging an existing authorization:** 1-3 months (vs. 12-24 months for new authorization)

### High-Value Leveragers

When a FedRAMP-authorized service is used by many agencies, this creates significant value:
- The CSP's ongoing ConMon costs are shared across agencies
- Improvements to the service's security posture benefit all leveraging agencies
- Widely-used services receive more scrutiny, potentially improving quality

---

## 9. FedRAMP Documentation Requirements

### Core Documentation Package

The FedRAMP authorization package consists of the following core documents:

| Document | Acronym | Description |
|----------|---------|-------------|
| **System Security Plan** | SSP | Master document describing the system, its controls, and implementation |
| **Security Assessment Plan** | SAP | 3PAO plan for the assessment (scope, methods, schedule) |
| **Security Assessment Report** | SAR | 3PAO findings from the assessment |
| **Plan of Action and Milestones** | POA&M | Tracking of open vulnerabilities and remediation plans |
| **Incident Response Plan** | IRP | Procedures for detecting, reporting, and responding to incidents |
| **Configuration Management Plan** | CMP | How the CSP manages configurations and changes |
| **Information Security Policies** | — | All topic-specific policies supporting control implementation |

### System Security Plan (SSP)

The SSP is the **cornerstone document** — typically hundreds of pages. It includes:

| Section | Content |
|---------|---------|
| **System Description** | Purpose, users, data types, criticality |
| **System Environment** | Architecture, components, boundaries |
| **Boundary Definition** | What is in scope for assessment |
| **Data Flow Diagrams** | How data flows within and between components |
| **Network Architecture Diagrams** | Logical and physical network topology |
| **Ports, Protocols, Services** | All PPS in use; justifications for risky PPS |
| **User Types and Privileges** | All user categories, roles, and access levels |
| **External Systems and Connections** | All external systems connected; interconnection security agreements |
| **Control Implementation Narratives** | For each applicable control: how it is implemented |
| **Customer Responsibility Matrix** | Which controls are CSP-managed vs. customer-managed |
| **Attachments** | Policies, procedures, evidence referenced in narratives |

### Security Assessment Plan (SAP)

The SAP documents the 3PAO's testing approach:
- Scope of assessment (which systems, components, locations)
- Controls to be tested and testing methods
- Sampling approach
- Assessment schedule
- Rules of engagement (for penetration testing)
- Risk rating methodology

### Security Assessment Report (SAR)

The SAR is the 3PAO's output:
- Executive summary and overall risk posture
- For each tested control: result (Satisfied / Other Than Satisfied), evidence reviewed, findings
- Risk ratings for each finding (Critical, High, Moderate, Low, Informational)
- Remediation recommendations
- Summary of open vs. closed findings

### POA&M

The FedRAMP POA&M tracks all open risks:

**Required fields:**
- Weakness ID (POA&M ID)
- Control ID (which control is affected)
- Weakness name
- Weakness description
- Detection source (scan, assessment, pen test, etc.)
- Weakness impact (CIA)
- Risk rating (Critical, High, Moderate, Low)
- Point of contact for remediation
- Resources required
- Scheduled completion date
- Milestones with completion dates
- Status (Open, In Progress, Delayed, Closed — Risk Accepted)
- Comments
- Deviation requests (if remediation not feasible)

**POA&M management rules:**
- **Critical and High findings** must be remediated within defined timelines or receive risk acceptance
- **Critical:** 30 days from discovery
- **High:** 90 days from discovery
- **Moderate:** 180 days from discovery
- **Low:** 365 days from discovery
- Risk acceptance is available for findings that cannot be remediated; requires agency AO approval

### Required Supporting Documentation

Beyond the core package, FedRAMP requires:

| Document | Purpose |
|----------|---------|
| **Interconnection Security Agreements (ISAs)** | Governs connections to external systems |
| **Memoranda of Understanding/Agreement (MOU/MOA)** | Governs relationships with external organizations |
| **Rules of Behavior (ROB)** | User acknowledgment of security responsibilities |
| **IT Contingency Plan** | System-level BCP/DR plan |
| **Privacy Impact Assessment (PIA)** | Required if system processes PII |
| **Personnel security procedures** | Background investigation requirements |
| **Vulnerability scanning procedures** | How scans are conducted, frequency, tools |
| **Penetration test report** | Annual pen test results |

---

## 10. FedRAMP Continuous Monitoring Requirements

Continuous monitoring (ConMon) is one of the most operationally demanding aspects of FedRAMP. It ensures that authorized cloud services maintain their security posture over time.

### ConMon Obligations Overview

| Activity | Frequency | Deliverable |
|----------|-----------|-------------|
| Vulnerability scanning — OS/network | Monthly | Scan results |
| Vulnerability scanning — web applications | Monthly | Scan results |
| Vulnerability scanning — databases | Monthly | Scan results |
| POA&M updates | Monthly | Updated POA&M |
| Inventory updates | Monthly | Updated inventory |
| ConMon report | Monthly | Compiled ConMon report to agency |
| Control review | Annually | Annual assessment of ~1/3 of controls |
| Penetration test | Annually | Pen test report |
| SAR update | Annually | Updated SAR reflecting current assessment |
| SSP update | Annually or upon significant change | Updated SSP |
| Policies/procedures review | Annually | Updated documentation |

### Monthly Vulnerability Scanning Requirements

**Scope:**
- All operating systems (servers, workstations, network devices)
- All web applications
- All databases
- All container images (increasingly required)

**Tools:** Must use approved vulnerability scanning tools (listed in FedRAMP Marketplace)

**Common tools:**
- Tenable Nessus / Tenable.io
- Qualys VMDR
- Rapid7 InsightVM
- For containers: Aqua Security, Twistlock/Prisma Cloud

**Scan results handling:**
- Raw scan results uploaded to FedRAMP repository (Secure File Repository)
- Results reviewed by CSP security team
- New findings entered in POA&M with remediation timelines
- False positives documented with evidence

### Monthly ConMon Report

Each month, the CSP submits a ConMon report to their sponsoring agency (and other leveraging agencies who have subscribed) containing:

1. **Updated inventory** — all hardware and software assets
2. **Vulnerability scan results** — raw results + summary
3. **Updated POA&M** — current status of all open items
4. **Open high/critical vulnerabilities** — special section with justification for any open beyond 30/90 days
5. **Changes since last report** — operational or configuration changes
6. **Incident summary** — any incidents since last report
7. **Deviation requests** — any requests to not remediate per standard timelines

### Annual Assessment

The annual assessment conducted by the 3PAO covers:
- Approximately **one-third** of all controls each year
- Over a three-year cycle, all controls are reassessed
- Penetration test (annual)
- Review of any significant changes implemented since last assessment
- Updated SAR

**Annual assessment focus areas rotate through:**
- Year 1: Access control, incident response, configuration management, risk assessment
- Year 2: Audit/accountability, identification/authentication, system integrity, media protection
- Year 3: Planning, personnel security, physical/environmental, system/services acquisition, communications

(Exact rotation varies by CSP agreement)

### Significant Change Requests (SCR)

Before making **significant changes** to an authorized system, the CSP must submit an SCR to the agency AO and FedRAMP PMO:

**Significant changes include:**
- Adding new services or capabilities that expand the authorization boundary
- Changing the underlying cloud platform (e.g., moving from bare metal to containers)
- Upgrading operating systems across the fleet
- Changing authentication mechanisms
- Adding new external connections or integrations
- Changes that affect FIPS-validated cryptography

**SCR Process:**
1. CSP submits SCR request describing the change and impact analysis
2. Agency AO reviews and approves/denies
3. FedRAMP PMO may review for high-impact changes
4. 3PAO assesses affected controls
5. Updated SSP/SAR reflect the change

**Not significant changes (no SCR required):**
- Routine patching within approved baselines
- Replacing like-for-like hardware without architectural changes
- Minor software updates that don't change security posture
- Configuration changes within approved boundaries

### ConMon Non-Compliance Consequences

If a CSP fails ConMon requirements:
- Agency AO notified
- FedRAMP PMO notified
- CSP given opportunity to remediate
- If not remediated: ATO may be revoked
- Service removed from FedRAMP Marketplace as "Authorized"

---

## 11. FedRAMP Marketplace

### What is the Marketplace?

The **FedRAMP Marketplace** (marketplace.fedramp.gov) is the official catalog of:
- FedRAMP-authorized cloud services
- FedRAMP Ready services
- FedRAMP In Process services
- Accredited 3PAOs

### Marketplace Information Per Service

For each listed service, the Marketplace shows:
- CSP name and service name
- Service description
- Impact level (Low / Moderate / High)
- Authorization status (Ready / In Process / Authorized)
- Authorization date
- Service model (IaaS / PaaS / SaaS)
- Deployment model (Public / Government Community / Hybrid)
- Leveraging agencies (agencies that have issued ATOs)
- 3PAO who conducted the assessment
- Package access information

### Accessing Authorization Packages

Authorized personnel (federal employees) can access full authorization packages through:
- **Direct request to CSP** — CSPs must provide packages to agencies upon request
- **OMB MAX.gov repository** (legacy system)
- Some packages are available via the FedRAMP Secure Repository

**Package contents that are publicly available:**
- SSP front matter
- Service description
- Boundary diagrams (often)

**Package contents that are NOT public:**
- Detailed control implementation narratives
- Vulnerability scan results
- Penetration test reports
- Full SAR findings

---

## 12. OMB Memo M-23-22 — FedRAMP Reform

### Overview

**OMB Memorandum M-23-22** ("Delivering a Digital-First Public Experience") was issued October 2023 and included significant FedRAMP reform provisions.

**Key FedRAMP reform provisions:**

### 1. Shift from JAB to Agency-Sponsored Model

- Formally ended JAB P-ATO for new authorizations
- All new authorizations must go through agency sponsorship
- Existing JAB P-ATOs remain valid

### 2. Faster Authorization Goal

- OMB directed FedRAMP to reduce time-to-authorization
- Target: Average authorization time below 6 months (from 12-24 months historically)
- Process improvements: more upfront engagement, cleaner templates, better PMO review turnaround

### 3. Reciprocity with Other Frameworks

- OMB directed FedRAMP to explore reciprocity with ISO 27001, SOC 2, and other frameworks
- Aim: Reduce duplicative assessment for CSPs already holding other authorizations
- **Note:** As of 2025, full reciprocity has not been implemented; FedRAMP assessments still required

### 4. OSCAL-First

- New authorization packages must use **OSCAL (Open Security Controls Assessment Language)** formats
- OSCAL machine-readable formats replace manual Word/Excel templates
- FedRAMP PMO developing OSCAL tooling

### 5. Enhanced Automation

- FedRAMP directed to automate more of the review process
- Machine-readable security data to enable automated compliance checking
- Integration with CDM and agency dashboards

### 6. "Presumption of Adequacy"

- Agencies directed to presume that FedRAMP-authorized services are adequate
- Reduces agency-level re-review of already-authorized services
- Agencies still issue their own ATOs but should not require re-assessment of already-tested controls

---

## 13. FedRAMP vs DoD Impact Levels

The Department of Defense uses its own **Impact Levels (IL)** system for classifying cloud services based on the sensitivity of data handled. DoD IL maps to FedRAMP but adds DoD-specific requirements.

### DoD Impact Level Summary

| IL | Data Types | FedRAMP Equivalence | Additional DoD Requirements |
|----|------------|--------------------|-----------------------------|
| **IL2** | Non-controlled public information; non-CUI | FedRAMP Moderate authorized (minimum) | None beyond FedRAMP |
| **IL4** | CUI; not national security | FedRAMP Moderate + DoD SRG controls | DoD SRG Impact Level 4 STIG compliance; DoD CAC/PIV enforcement |
| **IL5** | CUI National Security Systems; higher sensitivity CUI | FedRAMP High + DoD SRG controls | IL4 requirements + additional NSS controls; dedicated government infrastructure preferred |
| **IL6** | Classified Secret information | Not commercially available; NSS | Requires IC/DoD classification-specific infrastructure (C2S, milCloud) |

### DoD SRG (Security Requirements Guide)

The **DoD Cloud Computing SRG** defines requirements for cloud services operating at each IL:
- Defines security requirements for IL2, IL4, IL5, IL6
- Published by DISA (Defense Information Systems Agency)
- CSPs seeking DoD business must comply with the relevant SRG

**DoD Provisional Authorization (PA):**
- For IL2-IL5, DISA can issue a DoD PA based on a FedRAMP authorization plus additional controls
- A DoD PA is required for CSPs serving DoD at IL4+
- Separate from civilian agency FedRAMP authorizations

### Impact Level Use Case Examples

| Use Case | IL Required |
|----------|------------|
| DoD public website hosting | IL2 |
| Unclassified email for DoD contractors | IL4 |
| Defense acquisition systems with technical data | IL4 |
| Tactical military planning systems | IL5 |
| Joint Chiefs strategic communications | IL6 |

### Major IL4/IL5 Authorized Cloud Providers

| Provider | Service | Impact Level |
|----------|---------|--------------|
| AWS | GovCloud (US) | IL2, IL4, IL5 |
| Microsoft | Azure Government | IL2, IL4, IL5 |
| Google | Google Cloud (GovCloud regions) | IL2, IL4 (selective IL5) |
| Oracle | Oracle Government Cloud | IL2, IL4 |
| IBM | IBM Cloud for Government | IL2, IL4 |

---

## 14. FedRAMP OSCAL and Automation

### What is OSCAL?

**OSCAL (Open Security Controls Assessment Language)** is a machine-readable format developed by NIST for expressing security documentation — policies, plans, assessments, and results — in standardized XML, JSON, or YAML formats.

FedRAMP is moving to OSCAL-native documentation, which enables:
- Automated review by FedRAMP PMO tools
- Machine validation of completeness and consistency
- Interoperability between CSP tools, 3PAO tools, and government systems
- Reduced manual effort for creating and maintaining documentation

### OSCAL Models Relevant to FedRAMP

| OSCAL Model | FedRAMP Document | Description |
|-------------|-----------------|-------------|
| **Catalog** | NIST SP 800-53 controls | Machine-readable control definitions |
| **Profile** | FedRAMP baselines | Selection and tailoring of controls from catalog |
| **System Security Plan (SSP)** | SSP | System characteristics and control implementation |
| **Assessment Plan (AP)** | SAP | Planned assessment activities and methods |
| **Assessment Results (AR)** | SAR | Assessment findings and observations |
| **Plan of Action and Milestones (POAM)** | POA&M | Open findings and remediation tracking |

### FedRAMP OSCAL Templates

The FedRAMP PMO publishes OSCAL templates for all required documents:
- Available at: github.com/GSA/fedramp-automation
- Updated as FedRAMP requirements change
- Include FedRAMP-specific extensions beyond base OSCAL schema

### Current OSCAL Adoption Status (2025)

- New FedRAMP authorization submissions **increasingly required** to use OSCAL formats
- FedRAMP PMO built automated validation tooling for OSCAL packages
- Existing authorized packages being converted to OSCAL over time
- Many CSPs use tools like Telos Ghost, Xacta, Archer GRC, or OSCAL-native tools to generate OSCAL documents

### Benefits of OSCAL for CSPs

1. **Automation:** Generate SSP content programmatically from infrastructure-as-code
2. **Consistency:** Machine-readable format prevents manual errors
3. **Inheritance:** Inherited controls from cloud provider automatically propagate through the hierarchy
4. **Change management:** Changes to control implementation update documentation automatically
5. **Reduced review time:** Automated PMO validation catches errors before human review

---

## 15. Control Inheritance from FedRAMP-Authorized Providers

### The Inheritance Model

One of the most significant efficiency gains in FedRAMP is **control inheritance** — when a higher-level cloud provider (IaaS or PaaS) has FedRAMP authorization, services built on top of that provider can **inherit** many of the provider's already-tested controls.

### Inheritance Terminology

| Term | Definition |
|------|------------|
| **Leveraged Authorization** | The underlying FedRAMP-authorized IaaS/PaaS that provides inherited controls |
| **Inherited Control** | A control fully implemented by the underlying provider; no additional action required by the CSP building on top |
| **Customer Responsibility** | A control that must be implemented by the CSP or end-user agency |
| **Shared Responsibility** | A control where both the provider and the CSP/agency share implementation responsibilities |
| **Hybrid Control** | Combination of inherited and customer-implemented portions |

### Example: SaaS Built on AWS GovCloud

A SaaS CSP (call it "ContosoApp") builds their application on AWS GovCloud (US), which has a FedRAMP High authorization.

| Control | Responsibility Assignment |
|---------|--------------------------|
| PE-1 (Physical & Environmental Policy) | **Inherited** from AWS — AWS manages all data center physical security |
| PE-2 (Physical Access Authorizations) | **Inherited** from AWS |
| CM-8 (System Component Inventory) | **Shared** — AWS inventories their components; ContosoApp inventories their application components |
| AC-2 (Account Management) | **Customer (ContosoApp)** — ContosoApp manages user accounts in their application |
| IA-2 (Multi-Factor Authentication) | **Customer (ContosoApp)** — ContosoApp must implement MFA for their users |
| SC-28 (Protection of Info at Rest) | **Shared** — AWS provides encryption capability; ContosoApp must enable it and manage keys |

### Customer Responsibility Matrix (CRM)

Every FedRAMP-authorized IaaS/PaaS provider publishes a **Customer Responsibility Matrix (CRM)** that documents for each control:
- Provider fully manages (inherited)
- Customer fully manages
- Shared responsibility (with description of each party's role)

**Where to find CRMs:**
- AWS: Customer Responsibility Matrix available in AWS Artifact
- Azure: Azure Security and Compliance Blueprint (FedRAMP documentation)
- Google Cloud: Google Cloud FedRAMP Customer Responsibility Matrix

### Impact on Assessment

When a CSP inherits controls from a FedRAMP-authorized provider:
- Those inherited controls **do not need to be re-tested** by the 3PAO for the CSP's own assessment
- The 3PAO reviews the inheritance relationship and verifies the inheritance is properly documented
- The 3PAO focuses testing effort on customer-managed and shared controls

**This significantly reduces assessment scope and cost for SaaS CSPs** built on FedRAMP-authorized IaaS.

### Inheritance Documentation in SSP

The SSP must document:
- The name and FedRAMP ID of the leveraged authorization
- For each control: inheritance status (Inherited / Customer Responsibility / Shared)
- For shared controls: description of CSP's portion of implementation
- Reference to the leveraged provider's authorization package

### Inheritance Limitations

- Inheritance is only valid if the **leveraged provider's authorization is active and current**
- If the leveraged provider's authorization lapses or is revoked, inherited controls are no longer valid
- CSPs building on non-FedRAMP-authorized infrastructure cannot claim inheritance
- The CSP remains responsible for ensuring the inherited controls are properly configured for their use case

---

## 16. FedRAMP and FISMA Integration

### How FedRAMP Fits Into the FISMA Framework

FedRAMP is an implementation of the **NIST RMF** specifically for cloud services:

| RMF Step | FedRAMP Implementation |
|----------|----------------------|
| **Prepare** | FedRAMP PMO engagement; CSP defines service boundary |
| **Categorize** | Impact level determination (Low/Moderate/High) per FIPS 199 |
| **Select** | FedRAMP baseline selection + tailoring |
| **Implement** | CSP implements controls; documents in SSP |
| **Assess** | 3PAO conducts assessment; produces SAR |
| **Authorize** | Agency AO issues ATO based on SAR and risk acceptance |
| **Monitor** | CSP performs monthly ConMon; annual reassessment |

### FISMA Metrics and Cloud Systems

Agency CISO/CIO teams must include FedRAMP-authorized cloud systems in their FISMA reporting:
- Cloud systems counted in system inventory
- FedRAMP authorization counts as the ATO for FISMA purposes
- ConMon data from CSPs feeds agency FISMA metrics
- Any cloud incidents reported by CSPs must be included in agency incident reporting

### When FedRAMP Authorization Is Not Required

FedRAMP authorization is NOT required when:
- The cloud service processes only publicly available, non-sensitive information
- The agency operates a private cloud exclusively for their own use (no external CSP)
- The cloud service is not processing, storing, or transmitting federal information
- An exception is granted by OMB (rare and requires strong justification)

---

## 17. Common Challenges and Pitfalls

### CSP Common Pitfalls

| Pitfall | Description | Mitigation |
|---------|-------------|------------|
| **Boundary creep** | Including too many components in the authorization boundary | Define minimum necessary boundary; clearly separate FedRAMP-scope from non-scope |
| **Inherited control confusion** | Claiming inheritance without documentation | Obtain provider CRM; document clearly in SSP |
| **Inadequate SSP narratives** | Generic or copy-paste control descriptions | Be specific about actual implementation; reference specific configurations |
| **Underestimating ConMon burden** | Not staffing for monthly reporting | Budget for dedicated ConMon staff before pursuing authorization |
| **Scope creep after authorization** | Adding features/services outside the authorization boundary without SCR | Establish change management process; train engineering teams |
| **Patch compliance failures** | Not meeting remediation timelines | Automate patch management; track in POA&M rigorously |
| **FIPS 140-3 gaps** | Using non-FIPS-validated cryptographic modules | Audit all crypto use; replace with FIPS-validated alternatives |

### Agency Common Pitfalls

| Pitfall | Description | Mitigation |
|---------|-------------|------------|
| **Assuming FedRAMP Ready = FedRAMP Authorized** | FedRAMP Ready is a pre-authorization status | Check Marketplace for "Authorized" status |
| **Not completing customer responsibilities** | Relying entirely on inherited controls | Review and implement CRM responsibilities |
| **Not reviewing ConMon reports** | Treating CSP's authorization as set-and-forget | Assign agency staff to review monthly ConMon reports |
| **Not issuing agency ATO** | Using an authorized service without issuing own ATO | Every agency must issue its own ATO |
| **Scope confusion** | Not understanding what the FedRAMP authorization covers | Review service boundary carefully; additional systems need separate ATOs |

### 3PAO Common Pitfalls

| Pitfall | Description | Mitigation |
|---------|-------------|------------|
| **Inadequate testing** | Relying on examination without sufficient testing | Follow NIST SP 800-53A assessment procedures rigorously |
| **Under-reporting findings** | Downgrading finding severity under CSP pressure | Maintain independence; calibrate ratings objectively |
| **Sampling errors** | Testing too few instances to be statistically valid | Follow FedRAMP sampling guidance |
| **Stale assessment** | Assessments based on outdated environments | Ensure assessment scope reflects current production environment |

---

## 18. Key Definitions and Acronyms

| Term | Definition |
|------|------------|
| **3PAO** | Third Party Assessment Organization — FedRAMP-accredited assessor |
| **A2LA** | American Association for Laboratory Accreditation — accredits 3PAOs |
| **AO** | Authorizing Official — agency official who signs the ATO |
| **ATO** | Authority to Operate — formal authorization to operate a system |
| **AODR** | Authorizing Official Designated Representative |
| **Boundary** | The logical/physical perimeter of the FedRAMP-assessed system |
| **CMP** | Configuration Management Plan |
| **ConMon** | Continuous Monitoring |
| **CRM** | Customer Responsibility Matrix |
| **CSP** | Cloud Service Provider |
| **DISA** | Defense Information Systems Agency — publishes DoD SRG |
| **FedRAMP** | Federal Risk and Authorization Management Program |
| **FedRAMP Board** | Governance body established by FedRAMP Authorization Act 2022 |
| **GSA** | General Services Administration — houses FedRAMP PMO |
| **IaaS** | Infrastructure as a Service |
| **IL** | Impact Level (DoD designation — IL2 through IL6) |
| **IRP** | Incident Response Plan |
| **ISA** | Interconnection Security Agreement |
| **JAB** | Joint Authorization Board — legacy governance body (JAB P-ATOs grandfathered) |
| **Li-SaaS** | Low Impact SaaS — FedRAMP Tailored baseline |
| **OSCAL** | Open Security Controls Assessment Language |
| **P-ATO** | Provisional Authority to Operate (legacy JAB designation) |
| **PaaS** | Platform as a Service |
| **PIA** | Privacy Impact Assessment |
| **PMO** | Program Management Office (FedRAMP PMO at GSA) |
| **POA&M** | Plan of Action and Milestones |
| **SaaS** | Software as a Service |
| **SAP** | Security Assessment Plan |
| **SAR** | Security Assessment Report |
| **SCR** | Significant Change Request |
| **SRG** | Security Requirements Guide (DoD) |
| **SSP** | System Security Plan |

---

## Summary: FedRAMP Authorization Quick Reference

| Attribute | Agency ATO | FedRAMP Tailored | JAB P-ATO (Legacy) |
|-----------|-----------|-----------------|-------------------|
| **Path status** | Active | Active | Closed to new applicants |
| **Issuing body** | Agency AO | Agency AO | Joint Authorization Board |
| **Impact levels** | Low, Moderate, High | Low only | Moderate, High |
| **3PAO required** | Yes (Moderate/High) | Recommended; not mandatory | Yes |
| **Controls assessed** | 127-421 | ~37 | 323-421 |
| **Timeline** | 12-24 months | 3-6 months | 18-36 months (legacy) |
| **Cost to CSP** | $500K-$2M+ | $50K-$200K | $750K-$2.5M (legacy) |
| **ConMon required** | Yes | Yes | Yes |
| **Reuse by other agencies** | Yes | Yes | Yes |

---

*Document Version: 1.0 | FedRAMP Framework based on FedRAMP Authorization Act (December 2022)*
*Aligned to: NIST SP 800-53 Rev 5; NIST SP 800-37 Rev 2; OMB M-23-22; FedRAMP Rev 5 Baselines*
*Intended Use: LLM GRC Knowledge Base*
