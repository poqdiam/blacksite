# SOC 2 Complete Reference: Trust Service Criteria, Type 1 and Type 2

**AICPA System and Organization Controls (SOC) 2**
**Standard:** AICPA Trust Services Criteria (TSC), April 2017 (updated 2022)
**Applicable Framework:** COSO 2013 Internal Control — Integrated Framework
**Regulatory Body:** American Institute of Certified Public Accountants (AICPA)

---

## Table of Contents

1. [SOC Reports Overview](#1-soc-reports-overview)
2. [SOC 2 vs SOC 1 vs SOC 3](#2-soc-2-vs-soc-1-vs-soc-3)
3. [Trust Service Criteria — Overview](#3-trust-service-criteria--overview)
4. [Security (Common Criteria) — CC Series](#4-security-common-criteria--cc-series)
5. [Availability Criteria (A Series)](#5-availability-criteria-a-series)
6. [Processing Integrity Criteria (PI Series)](#6-processing-integrity-criteria-pi-series)
7. [Confidentiality Criteria (C Series)](#7-confidentiality-criteria-c-series)
8. [Privacy Criteria (P Series)](#8-privacy-criteria-p-series)
9. [Type 1 vs Type 2 Reports](#9-type-1-vs-type-2-reports)
10. [SOC 2 Audit Process](#10-soc-2-audit-process)
11. [Report Structure and Contents](#11-report-structure-and-contents)
12. [Complementary User Entity Controls (CUECs)](#12-complementary-user-entity-controls-cuecs)
13. [Complementary Subservice Organization Controls (CSOCs)](#13-complementary-subservice-organization-controls-csocs)
14. [Carve-Out vs Inclusive Methods](#14-carve-out-vs-inclusive-methods)
15. [SOC 2 vs FedRAMP](#15-soc-2-vs-fedramp)
16. [SOC 2 vs ISO 27001](#16-soc-2-vs-iso-27001)
17. [SOC 2 in BLACKSITE/GRC Context](#17-soc-2-in-blacksitegrc-context)
18. [Quick Reference Tables](#18-quick-reference-tables)

---

## 1. SOC Reports Overview

### 1.1 Background

SOC (System and Organization Controls) reports are auditing standards developed by the AICPA to enable service organizations to communicate about their controls to customers (user entities) and their auditors. They replaced the older SAS 70 standard in 2011.

### 1.2 SOC Report Family

| Report Type | Subject | Audience | Distribution |
|---|---|---|---|
| SOC 1 | Controls over financial reporting (ICFR) | User entities and their auditors | Restricted — user entities and auditors only |
| SOC 2 | Controls relevant to security, availability, processing integrity, confidentiality, or privacy | Customers, prospects, regulators | Restricted — specified parties |
| SOC 3 | Same as SOC 2 but summary only | General public | Unrestricted — freely distributed |
| SOC for Cybersecurity | Entity-level cybersecurity risk management | Broad audience | General use; can be restricted or public |
| SOC for Supply Chain | Controls relevant to production, manufacturing, distribution | Supply chain partners | Restricted or general use |

---

## 2. SOC 2 vs SOC 1 vs SOC 3

### 2.1 SOC 1 — Internal Control over Financial Reporting

**Purpose:** Reports on controls at a service organization that are relevant to user entities' internal control over financial reporting (ICFR).

**Standard:** SSAE No. 18 (AT-C Section 320)

**Typical users:** Payroll processors, loan servicers, custody banks, claims processing companies

**Key question:** "Do the service organization's controls affect the accuracy of my financial statements?"

**Types:**
- **Type 1:** Description of controls and whether they are suitably designed as of a point in time
- **Type 2:** Description, design, AND operating effectiveness over a period of time

### 2.2 SOC 2 — Trust Services Criteria

**Purpose:** Reports on controls relevant to the security, availability, processing integrity, confidentiality, or privacy of customer data processed by a service organization.

**Standard:** AT-C Section 205 + AICPA Trust Services Criteria (2017)

**Typical users:** Cloud providers, SaaS companies, data centers, managed security service providers, colocation facilities

**Key question:** "Does the service organization have appropriate controls to protect my data and ensure system availability?"

**Types:**
- **Type 1:** Design of controls as of a specific date
- **Type 2:** Design and operating effectiveness over a review period (typically 6–12 months)

### 2.3 SOC 3 — Publicly Available Trust Services Report

**Purpose:** Same scope as SOC 2 but presented as a summary report suitable for general distribution. Contains the auditor's opinion and management's assertion but not the detailed description of controls or test results.

**Use case:** Seals and badges on websites; marketing to prospects who cannot receive restricted SOC 2

**Note:** A SOC 3 does not replace SOC 2 for due diligence — it provides no detailed control information.

### 2.4 Comparison Table

| Dimension | SOC 1 | SOC 2 | SOC 3 |
|---|---|---|---|
| Standard | SSAE 18 AT-C 320 | AT-C 205 + TSC | AT-C 205 + TSC |
| Focus | Financial controls | Security/data controls | Security/data controls (summary) |
| Distribution | Restricted | Restricted | Unrestricted |
| Detail level | Full | Full | Summary (no test details) |
| Type 1 available | Yes | Yes | Yes (less common) |
| Type 2 available | Yes | Yes | Yes |
| Use for vendor DD | Not directly | Yes | No (marketing only) |

---

## 3. Trust Service Criteria — Overview

### 3.1 The Five Trust Service Categories

| Category | Abbreviation | Applicability |
|---|---|---|
| Security | CC (Common Criteria) | Mandatory for all SOC 2 reports |
| Availability | A | Optional — selected by service organization |
| Processing Integrity | PI | Optional — selected by service organization |
| Confidentiality | C | Optional — selected by service organization |
| Privacy | P | Optional — based on personal information handling |

### 3.2 Selecting Applicable Trust Service Categories

The service organization selects which categories are in scope based on:
- The commitments made to user entities (system description, contracts, SLAs)
- The nature of the service (e.g., uptime SLAs require Availability; handling PII requires Privacy)
- Regulatory requirements of user entities (e.g., health care customers may require Privacy)
- Competitive positioning (broader scope = more assurance)

**Security (CC) is always in scope.** Other categories are additive.

### 3.3 COSO Framework Alignment

The Trust Service Criteria are mapped to the **COSO 2013 Internal Control — Integrated Framework** components:
- Control Environment
- Risk Assessment
- Control Activities
- Information and Communication
- Monitoring Activities

---

## 4. Security (Common Criteria) — CC Series

The Common Criteria (CC) apply to all five trust service categories. They are organized into nine criterion groups.

### 4.1 CC1 — Control Environment

The control environment sets the tone of the organization regarding integrity, ethical values, and competence.

| Criterion | Description |
|---|---|
| CC1.1 | COSO Principle 1: The entity demonstrates a commitment to integrity and ethical values |
| CC1.2 | COSO Principle 2: The board of directors demonstrates independence from management and exercises oversight of the development and performance of internal control |
| CC1.3 | COSO Principle 3: Management establishes, with board oversight, structures, reporting lines, and appropriate authorities and responsibilities |
| CC1.4 | COSO Principle 4: The entity demonstrates a commitment to attract, develop, and retain competent individuals in alignment with objectives |
| CC1.5 | COSO Principle 5: The entity holds individuals accountable for their internal control responsibilities |

**Key control evidence:**
- Code of conduct / ethics policy
- Organizational charts with clear reporting lines
- Background check procedures
- Performance management linked to control responsibilities
- Board/audit committee minutes demonstrating oversight

### 4.2 CC2 — Communication and Information

| Criterion | Description |
|---|---|
| CC2.1 | COSO Principle 13: Obtain or generate relevant, quality information to support the functioning of internal controls |
| CC2.2 | COSO Principle 14: Internally communicate information, including objectives and responsibilities for internal controls |
| CC2.3 | COSO Principle 15: Communicate with external parties regarding matters affecting the functioning of other components |

**Key control evidence:**
- Security policies communicated to workforce
- Privacy and security notices on website
- SLA/contractual commitments to user entities
- Reporting mechanisms for suspected violations
- Status page or availability communications

### 4.3 CC3 — Risk Assessment

| Criterion | Description |
|---|---|
| CC3.1 | COSO Principle 6: Specify objectives with sufficient clarity to enable the identification and assessment of risks |
| CC3.2 | COSO Principle 7: Identify risks to achievement of objectives across the entity and analyze risks as a basis for determining how they should be managed |
| CC3.3 | COSO Principle 8: Consider the potential for fraud in assessing risks |
| CC3.4 | COSO Principle 9: Identify and assess changes that could significantly impact the system of internal controls |

**Key control evidence:**
- Annual risk assessments
- Risk register/risk treatment plans
- Fraud risk assessment
- Change impact assessments
- Threat modeling documentation

### 4.4 CC4 — Monitoring Activities

| Criterion | Description |
|---|---|
| CC4.1 | COSO Principle 16: Select, develop, and perform ongoing and/or separate evaluations to ascertain whether components of internal control are present and functioning |
| CC4.2 | COSO Principle 17: Evaluate and communicate deficiencies in a timely manner to parties responsible for taking corrective action |

**Key control evidence:**
- Internal audit program
- Vulnerability management reports
- Penetration test results and remediation tracking
- Control effectiveness monitoring
- Deficiency tracking and escalation procedures

### 4.5 CC5 — Control Activities

| Criterion | Description |
|---|---|
| CC5.1 | COSO Principle 10: Select and develop control activities that contribute to the mitigation of risks |
| CC5.2 | COSO Principle 11: Select and develop general control activities over technology to support the achievement of objectives |
| CC5.3 | COSO Principle 12: Deploy control activities through policies that establish what is expected and procedures that put policies into action |

**Key control evidence:**
- Written information security policies
- Technology control standards (encryption, patching, hardening)
- Policy acknowledgment records
- Procedure documentation
- Policy exception management process

### 4.6 CC6 — Logical and Physical Access Controls

This is typically the most evidence-intensive CC category. It covers the full lifecycle of access control.

| Criterion | Description |
|---|---|
| CC6.1 | Implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events |
| CC6.2 | Prior to issuing system credentials and granting system access, register and authorize new internal and external users |
| CC6.3 | Remove access to protected information assets when appropriate |
| CC6.4 | Restrict physical access to facilities and protected information assets to authorized personnel |
| CC6.5 | Dispose of data assets and facilities that hold sensitive information in a manner to prevent unauthorized access |
| CC6.6 | Implement logical access security measures to protect against threats from sources outside its system boundaries |
| CC6.7 | Restrict transmission, movement, and removal of information to authorized internal and external users and processes |
| CC6.8 | Implement controls to prevent or detect and act upon the introduction of unauthorized or malicious software |

**Key control evidence for CC6:**
- Access provisioning/deprovisioning procedures and records
- User access reviews (quarterly or semi-annual)
- MFA implementation (especially for privileged and remote access)
- Firewall rules and network diagrams
- Physical access control systems (badge logs, visitor logs)
- Data disposal procedures and certificates
- Anti-malware solution configuration
- Endpoint detection and response (EDR) deployment
- VPN/zero trust architecture documentation

### 4.7 CC7 — System Operations

| Criterion | Description |
|---|---|
| CC7.1 | Use detection and monitoring procedures to identify changes to configurations or the environment that would have a negative effect on system security, availability, processing integrity, or confidentiality |
| CC7.2 | Monitor system components and the operation of those components for anomalies that are indicative of malicious acts, natural disasters, and errors affecting the entity's ability to meet its objectives |
| CC7.3 | Evaluate security events to determine whether they could or have resulted in a failure of the entity to meet its objectives and, if so, take actions to prevent or address such failures |
| CC7.4 | Respond to identified security incidents by executing a defined incident management plan |
| CC7.5 | Identify, develop, and implement activities to recover from identified security incidents |

**Key control evidence:**
- SIEM/log management system
- Alerting thresholds and escalation procedures
- Security incident response plan and runbooks
- Incident log demonstrating incidents were detected, investigated, and closed
- Post-incident reviews
- Disaster recovery test results

### 4.8 CC8 — Change Management

| Criterion | Description |
|---|---|
| CC8.1 | Authorize, design, develop or acquire, configure, document, test, approve, and implement changes to infrastructure, data, software, and procedures to meet its objectives |

**Key control evidence:**
- Change management policy
- Change request ticketing system
- Change Advisory Board (CAB) meeting minutes
- Separation of duties between development and production
- Code review and testing procedures
- Change approval records
- Deployment/rollback procedures
- Configuration management database (CMDB)

### 4.9 CC9 — Risk Mitigation

| Criterion | Description |
|---|---|
| CC9.1 | Identify, select, and develop risk mitigation activities for risks arising from potential business disruptions |
| CC9.2 | Assess and manage risks associated with vendors and business partners |

**Key control evidence:**
- Business continuity / disaster recovery plans and test results
- Vendor risk management program
- Third-party security assessments
- Vendor questionnaires and contractual security requirements
- Insurance coverage documentation
- Business impact analysis (BIA)

---

## 5. Availability Criteria (A Series)

Availability addresses whether the system is available for operation and use as committed or agreed.

| Criterion | Description |
|---|---|
| A1.1 | Current processing capacity and usage are maintained, managed, and evaluated to develop capacity forecasts |
| A1.2 | Environmental protections, software, data backup processes, and recovery infrastructure are designed, developed, implemented, and operated to meet the entity's availability commitments and system requirements |
| A1.3 | Recovery plan objectives and recovery capabilities are tested on a periodic basis to ensure that systems can return to processing operations, and commitments are met |

**Key control evidence:**
- Capacity monitoring and reporting
- Uptime/availability SLA commitments vs actuals
- Redundant infrastructure documentation (failover, load balancing)
- Data backup procedures, schedules, and restoration tests
- DR plan with defined RTOs and RPOs
- DR test results with documented outcomes
- UPS, generator, and environmental monitoring
- Environmental controls (temperature, humidity, flood/fire suppression)

**Common Availability metrics:**
- Recovery Time Objective (RTO): Maximum acceptable downtime
- Recovery Point Objective (RPO): Maximum acceptable data loss
- MTBF (Mean Time Between Failures)
- MTTR (Mean Time to Repair)
- Uptime percentage (often 99.9% / 99.95% / 99.99% / 99.999% SLAs)

---

## 6. Processing Integrity Criteria (PI Series)

Processing integrity addresses whether system processing is complete, valid, accurate, timely, and authorized.

| Criterion | Description |
|---|---|
| PI1.1 | Obtain or generate relevant data to support the use of quality information in the production of reports and data |
| PI1.2 | Obtain or generate relevant data to support the use of quality information in the production of reports and data |
| PI1.3 | Process system inputs completely, accurately, and timely |
| PI1.4 | Process inputs to generate outputs that are complete, accurate, and timely |
| PI1.5 | Deliver outputs to the intended recipients completely, accurately, and timely |

**Key control evidence:**
- Input validation controls (field validation, format checking)
- Batch processing controls (record counts, hash totals, control totals)
- Error handling and exception reporting
- Data quality monitoring
- Output reconciliation procedures
- Transaction logging and reconciliation
- SLA metrics for processing timeliness

**Typical industries:** Payment processors, financial data services, benefit administrators, payroll processors, reporting services.

---

## 7. Confidentiality Criteria (C Series)

Confidentiality addresses whether information designated as confidential is protected as committed or agreed.

| Criterion | Description |
|---|---|
| C1.1 | Identify and maintain confidential information to meet the entity's objectives related to confidentiality |
| C1.2 | Dispose of confidential information to meet the entity's objectives related to confidentiality |

**Key control evidence:**
- Data classification policy and scheme
- Confidentiality labeling/handling procedures
- Encryption of confidential data (at rest and in transit)
- DLP (Data Loss Prevention) controls
- Non-disclosure agreements (NDAs) with employees and vendors
- Confidential data inventory
- Secure disposal procedures (media sanitization)
- Access restrictions to confidential data

**Note on Confidentiality vs Privacy:**
- **Confidentiality** in TSC refers to information marked or designated as confidential (e.g., trade secrets, proprietary business information)
- **Privacy** refers specifically to personal information of individuals and involves use/disclosure obligations, individual rights, and consent

---

## 8. Privacy Criteria (P Series)

Privacy addresses whether personal information is collected, used, retained, disclosed, and disposed of in conformity with commitments in the entity's privacy notice and with AICPA privacy criteria.

The Privacy criteria are based on the **AICPA Generally Accepted Privacy Principles (GAPP)**, which themselves align closely with OECD Privacy Principles.

### 8.1 Privacy Criteria Summary

| Criterion Group | Description |
|---|---|
| P1 — Privacy Notices | Notice of privacy practices is provided |
| P2 — Choice and Consent | Choices are offered and consents obtained |
| P3 — Collection | Personal information is collected only for stated purposes |
| P4 — Use, Retention, Disposal | Personal information is used only for stated purposes; retained and disposed appropriately |
| P5 — Access | Individual access to their personal information is provided |
| P6 — Disclosure and Notification | Personal information is disclosed only with consent or as permitted; breach notification |
| P7 — Quality | Personal information is accurate, complete, and relevant |
| P8 — Monitoring and Enforcement | Privacy program is monitored and enforced |

### 8.2 Selected Specific Privacy Criteria

| Criterion | Description |
|---|---|
| P1.1 | Privacy notice is communicated to individuals prior to or at time of collection |
| P2.1 | Choices are offered and consents are obtained as required |
| P3.1 | Personal information is collected only for identified purposes |
| P3.2 | Methods used to collect personal information and resulting risk are documented |
| P4.1 | Personal information is limited to what is necessary to meet stated purposes |
| P4.2 | Retention of personal information complies with retention schedules |
| P4.3 | Personal information is destroyed using media sanitation procedures |
| P5.1 | An individual has the right to access personal information about themselves |
| P5.2 | An individual has the right to correct or update personal information |
| P6.1 | Personal information is disclosed only with consent or required by law |
| P6.6 | Individuals are notified in a timely manner of breaches |
| P7.1 | Personal information is accurate, complete, current, relevant |
| P8.1 | Privacy practices are reviewed and compared against privacy notice |

---

## 9. Type 1 vs Type 2 Reports

### 9.1 Type 1 Report

**Definition:** An examination of the **design and implementation** of controls as of a **specific date** (point-in-time).

**What it proves:**
- Controls are suitably designed to meet the applicable trust service criteria
- Controls were in place as of the report date

**What it does NOT prove:**
- That controls operated effectively over time
- That controls would prevent or detect errors/anomalies consistently

**When Type 1 is used:**
- New organization seeking first SOC 2 report
- After major control environment changes
- When a Type 2 period has not yet been established
- As a bridge before a Type 2 is issued
- Internal readiness validation

**Typical effort:** 2–4 months from engagement start to issuance

### 9.2 Type 2 Report

**Definition:** An examination of the **design, implementation, and operating effectiveness** of controls over a **period of time** (minimum 6 months; typically 12 months).

**What it proves:**
- Controls are suitably designed to meet the applicable criteria
- Controls operated effectively throughout the review period
- Operating effectiveness is tested through evidence inspection, observation, reperformance, and inquiry

**When Type 2 is required:**
- Customer/enterprise vendor due diligence
- Contractual requirements
- Regulatory requirements (SOC 2 Type 2 is often specified in contracts)
- FedRAMP supplemental assurance (see Section 15)

**Typical review periods:** 1 January – 31 December (calendar year) or rolling 12 months

**Testing approaches used by auditors:**
- **Inquiry:** Asking management/staff
- **Observation:** Watching a process performed
- **Inspection:** Reviewing documents, logs, records
- **Reperformance:** Auditor re-executes control to verify result

### 9.3 Type 1 to Type 2 Progression

```
Readiness Assessment (optional) → Type 1 (point-in-time) → Type 2 (6-12 month period)
                                           ↑                          ↑
                               Good for new programs         Required by most customers
```

**Typical timeline:**
- Month 1–2: Readiness assessment; gap remediation begins
- Month 3: Type 1 examination date (if pursued)
- Month 3–14: Type 2 observation period
- Month 15–16: Auditor fieldwork, testing, report drafting
- Month 17: Type 2 report issued

---

## 10. SOC 2 Audit Process

### 10.1 Phase 1 — Scoping

1. **Define system description:** The service organization describes the services provided, system components (infrastructure, software, people, procedures, data), and the boundaries of the system
2. **Select trust service categories:** Based on commitments to customers
3. **Select review period:** Start and end dates for Type 2
4. **Identify relevant subservice organizations:** Cloud providers, co-location facilities, etc.
5. **Agree on carve-out vs inclusive method** for subservice organizations

### 10.2 Phase 2 — Readiness Assessment (Optional but Recommended)

An internal or third-party readiness assessment identifies:
- Control gaps against the selected TSC criteria
- Missing evidence or documentation
- Immature controls that need remediation time
- Training needs

Output: Remediation roadmap with prioritized items.

### 10.3 Phase 3 — System Description Drafting

Management prepares the system description (Section IV of the final report) covering:
- Nature of services
- System components
- Complementary user entity controls
- Complementary subservice organization controls
- System boundaries
- Changes to the system during the period

### 10.4 Phase 4 — Observation Period (Type 2)

Controls must operate throughout the period. Key activities:
- Evidence collection and management (tickets, logs, screenshots, reports)
- Continuous monitoring of control operation
- Tracking exceptions and investigating anomalies
- Maintaining audit trail of all evidence

### 10.5 Phase 5 — Fieldwork

The CPA auditor (must be a licensed CPA firm) performs:
- Control documentation walkthrough
- Design effectiveness testing
- Operating effectiveness testing (Type 2 only) — sampling based on population size and risk

**Sampling approach (Type 2):**
- Low volume transactions: Test all or most instances
- High volume daily controls: Sample ~25 occurrences
- Automated controls: Test the automation (configuration) once + IT general controls
- Manual controls: Sample 25–60 depending on frequency and risk

### 10.6 Phase 6 — Reporting

The auditor issues a report containing:
- Independent service auditor's report (opinion)
- Management's assertion
- Description of the service organization's system
- Description of controls and tests of controls (Type 2)
- Other information (management responses, etc.)

### 10.7 Opinion Types

| Opinion | Meaning |
|---|---|
| Unmodified (Clean) | Controls are suitably designed (Type 1) and operating effectively (Type 2) |
| Qualified | Except for specific exceptions, controls are adequate |
| Adverse | Controls are not adequate (rare; usually not published) |
| Disclaimer of Opinion | Auditor unable to form an opinion (very rare) |

### 10.8 Exceptions and Deviations

**Exceptions** are instances where a control did not operate as described. The auditor notes:
- The control that had exceptions
- The number of exceptions out of population tested
- Nature of the deviation
- Whether the deviation is a design or operating effectiveness issue

**Management response:** Management may provide responses to exceptions explaining root cause, remediation, and compensating controls.

**Customer consideration:** A Type 2 report with a small number of exceptions and strong management response is generally acceptable. Multiple exceptions across critical controls warrants deeper investigation.

---

## 11. Report Structure and Contents

### 11.1 Standard Report Sections

| Section | Contents |
|---|---|
| Section I | Independent service auditor's report — opinion and scope |
| Section II | Management's assertion — management representation of system and controls |
| Section III | Description of the service organization's system — the "system description" |
| Section IV | Description of tests of controls and results (Type 2 only) — each control, test procedures, and results |
| Section V | Other information (optional) — management responses, additional context |

### 11.2 Section III — System Description Elements

The system description is management's narrative covering:
- **Service and service commitments:** What the organization does and promises to customers
- **System components:** Infrastructure (hardware, networks, data centers), software (applications, OSes, utilities), people (roles, governance), procedures (automated and manual), data (types, classification)
- **Boundaries of the system:** What is in scope; what is excluded
- **Principal service commitments and system requirements:** SLAs, contractual commitments, regulatory requirements
- **Relevant aspects of risk assessment process:** How risks are identified and addressed
- **Complementary controls:** CUECs and CSOCs noted

### 11.3 Security and Availability Disclosures

The description should address:
- Infrastructure components and redundancy
- Change management process summary
- Incident response overview
- Backup and recovery procedures
- Access control philosophy

---

## 12. Complementary User Entity Controls (CUECs)

### 12.1 Definition

CUECs are controls that the service organization assumes user entities (customers) will implement. The service organization's controls are designed with the assumption that certain complementary controls exist at the user entity.

If a user entity does not implement the CUECs, the overall control environment may be deficient even if the service organization's controls are operating effectively.

### 12.2 Common CUEC Examples

| CUEC | Description |
|---|---|
| User access management | Customer is responsible for provisioning/deprovisioning their own users in the service |
| Privileged access review | Customer is responsible for reviewing privileged access granted to their users |
| Password policies | Customer enforces their own password policies for users authenticating to the service |
| Data classification | Customer classifies and marks their own data appropriately |
| Incident reporting | Customer reports suspected security incidents to the service organization promptly |
| Data backup | Customer maintains independent backups of critical data |
| Network security | Customer secures their own network connecting to the service |
| Physical security | Customer secures their physical endpoints accessing the service |
| Training | Customer trains their employees on appropriate use of the service |
| Configuration review | Customer reviews configuration settings for security (if configurable) |

### 12.3 CUEC Implications for User Entity Auditors

When a user entity's auditor reviews a SOC 2 report, they must:
1. Identify all CUECs listed in the service organization's report
2. Verify that the user entity has implemented each applicable CUEC
3. Test the operating effectiveness of those CUECs as part of the user entity's own controls assessment
4. Note any gaps between the stated CUECs and the user entity's actual controls

---

## 13. Complementary Subservice Organization Controls (CSOCs)

### 13.1 Definition

CSOCs are controls that the service organization assumes its subservice organizations (sub-vendors) will implement. Similar to CUECs but apply to the service organization's supply chain.

### 13.2 Common Subservice Organizations

- Infrastructure-as-a-Service (IaaS) providers (AWS, Azure, GCP)
- Co-location data center providers
- Managed security service providers
- Payroll processors
- Background check services
- Email/communication platform providers

### 13.3 CSOCs and Carve-Out Method

When using the carve-out method (see Section 14), the service organization relies on the subservice organization's controls but does not include them in the scope of the SOC 2 examination. CSOCs describe what the subservice organization must do.

The user entity and its auditors must separately obtain and review the subservice organization's own SOC report to validate that CSOCs are operating.

---

## 14. Carve-Out vs Inclusive Methods

### 14.1 Inclusive Method

The subservice organization's controls are **included** in the scope of the service organization's SOC 2 examination. The service organization's auditor tests the subservice organization's controls directly (or relies on a SOC report obtained as a component auditor).

**Use case:** When the service organization has strong contractual rights to audit the subservice organization.

**Advantage:** Single report covers the full system including subservice organization controls.

**Disadvantage:** Complex, expensive; requires coordination with subservice organization's auditor.

### 14.2 Carve-Out Method

The subservice organization's controls are **excluded** from the service organization's SOC 2 examination. The service organization's report describes what the subservice organization does (CSOCs) but does not test those controls.

**Use case:** Most common — used when subservice organizations have their own SOC reports (e.g., AWS, Azure).

**User entity responsibility:** Must obtain and review the subservice organization's SOC report independently to validate CSOCs.

**Disclosure in report:** The system description must identify subservice organizations used under the carve-out method and identify the CSOCs.

---

## 15. SOC 2 vs FedRAMP

### 15.1 Overview Comparison

| Dimension | SOC 2 | FedRAMP |
|---|---|---|
| Purpose | Service organization assurance for customers | Cloud service authorization for federal government use |
| Authority | AICPA (private standard) | OMB/GSA/DHS (federal mandate) |
| Mandatory for federal use | No | Yes (for cloud services to federal agencies) |
| Control framework | AICPA TSC | NIST SP 800-53 Rev 5 (moderate/high/low) |
| Report type | SOC 2 report (Type 1 or 2) | Security Assessment Report (SAR) |
| Auditor | Licensed CPA firm | 3PAO (Third-Party Assessment Organization) |
| Authorization | N/A — no formal "authorization" | ATO (Authority to Operate) issued by agency or JAB |
| Review period (Type 2) | 6–12 months | Annual assessment + continuous monitoring |
| Public disclosure | Report restricted; SOC 3 can be public | FedRAMP marketplace public listing; reports restricted |
| Scope | Service organization's own system | All components of the cloud offering |

### 15.2 Control Overlap

SOC 2 Common Criteria have significant overlap with NIST 800-53 controls used in FedRAMP:

| SOC 2 Category | NIST 800-53 Control Families |
|---|---|
| CC1 (Control Environment) | PL, PM, SA |
| CC2 (Communication) | AC, AT, CP, PL |
| CC3 (Risk Assessment) | RA, PM |
| CC4 (Monitoring) | CA, AU, SI |
| CC5 (Control Activities) | CM, SA, PL |
| CC6 (Logical/Physical Access) | AC, IA, PE, MA |
| CC7 (System Operations) | IR, SI, AU |
| CC8 (Change Management) | CM, SA |
| CC9 (Risk Mitigation) | CP, SR (Supply Chain) |
| Availability | CP, IR |
| Confidentiality | SC, MP, RA |
| Privacy | PT, AR, IP (Privacy controls) |

### 15.3 FedRAMP Does Not Replace SOC 2

A CSP with a FedRAMP ATO:
- Provides strong assurance for NIST 800-53 technical controls
- Does not address AICPA Trust Service Criteria directly
- Does not demonstrate SOC 2 compliance to commercial customers
- Does not provide the CPA-attested report that commercial procurement processes often require

Conversely, a SOC 2 Type 2 report:
- Does not satisfy FedRAMP requirements for federal cloud deployments
- Is not recognized by the FedRAMP PMO as an authorization
- May be used as supplemental evidence during FedRAMP readiness reviews

### 15.4 Dual Compliance Strategy

Many CSPs pursue both FedRAMP and SOC 2:
- FedRAMP for US federal agency customers
- SOC 2 for commercial/international customers
- Leverage overlapping evidence where possible (access reviews, pen test, vulnerability scans, change management)
- Use a unified GRC platform to map controls to both frameworks

---

## 16. SOC 2 vs ISO 27001

### 16.1 Overview Comparison

| Dimension | SOC 2 | ISO/IEC 27001:2022 |
|---|---|---|
| Purpose | Service organization controls report | Information security management system (ISMS) certification |
| Standard body | AICPA (US) | ISO/IEC (international) |
| Outcome | Report (auditor opinion) | Certificate (conformity to standard) |
| Geographic recognition | Primarily US/North America | International (140+ countries) |
| Mandatory for US federal | No | No |
| Attestation type | Assurance engagement (CPA) | Third-party certification (accredited CB) |
| Control framework | AICPA TSC (COSO-based) | ISO 27001 Annex A (93 controls in 4 domains) |
| Review cycle | Annual (Type 2) | 3-year certificate + annual surveillance audits |
| Public report | SOC 3 summary only | Certificate publicly verifiable; audit report restricted |
| Scope flexibility | Service organization defines system | Organisation defines ISMS scope |

### 16.2 ISO 27001:2022 Annex A to SOC 2 CC Mapping

| ISO 27001 Domain | SOC 2 CC Criteria |
|---|---|
| 5 — Organizational Controls | CC1, CC2, CC5, CC9 |
| 6 — People Controls | CC1.4, CC6.2 |
| 7 — Physical Controls | CC6.4, CC6.5 |
| 8 — Technological Controls | CC6.1, CC6.6, CC6.7, CC6.8, CC7, CC8 |

### 16.3 Key Conceptual Differences

**SOC 2 is an attestation; ISO 27001 is a certification:**
- SOC 2 results in a CPA firm's **opinion** on controls — not a pass/fail certification
- ISO 27001 results in a **certificate** stating conformity — binary pass/fail
- SOC 2 reports contain detailed control descriptions and test results; ISO certificates do not

**SOC 2 is evidence-focused; ISO 27001 is process-focused:**
- SOC 2 Type 2 requires evidence that controls operated effectively
- ISO 27001 requires evidence that ISMS processes and policies exist and are followed — fewer transaction-level tests

**SOC 2 scope is per service; ISO 27001 scope is per ISMS:**
- A company may have multiple SOC 2 reports for different services
- ISO 27001 ISMS scope can cover the whole organization or specific units

### 16.4 Dual Certification Strategy

Many organisations pursue both to serve different customer bases:
- ISO 27001 for European/international customers and RFPs
- SOC 2 Type 2 for US commercial customers
- Evidence reuse: access reviews, risk assessment, vulnerability management, training records
- Consider integrated audit program with shared evidence repository

---

## 17. SOC 2 in BLACKSITE/GRC Context

### 17.1 Vendor Due Diligence Using SOC 2 Reports

When reviewing a vendor's SOC 2 as part of GRC due diligence:

**Step 1 — Verify report currency:** Ensure the report covers a recent period (within 12 months). A report more than 18 months old requires a bridge letter or updated report.

**Step 2 — Verify auditor credentials:** Confirm the issuing firm is a licensed CPA firm with SOC 2 expertise.

**Step 3 — Verify scope alignment:** Confirm the trust service categories and system description cover the services you are purchasing.

**Step 4 — Review the opinion:** Is it unmodified? If qualified, what are the exceptions?

**Step 5 — Review exceptions:** Analyze all deviations — assess materiality and whether management response is adequate.

**Step 6 — Review CUECs:** Document which CUECs apply to your organization and verify your own controls address them.

**Step 7 — Review CSOCs:** Identify subservice organizations under carve-out and obtain their SOC reports if they are critical to your data.

**Step 8 — Document findings:** Create vendor risk record; note any open exceptions; establish follow-up plan.

### 17.2 BLACKSITE Interconnection/Vendor Records for SOC 2

For vendors with ePHI or sensitive data access:
- Upload SOC 2 report PDF as artifact (type: Vendor Assessment)
- Note report period, scope categories, and opinion in vendor record
- Flag any exceptions relevant to data security or availability
- Set review reminder for 12 months or when new report issued
- Map CUECs to internal BLACKSITE controls (access review, incident notification, etc.)

### 17.3 SOC 2 Self-Assessment for BLACKSITE

If BLACKSITE itself were seeking SOC 2 (as a platform handling user data):

**Applicable categories:** Security (mandatory), Confidentiality (user system records), Availability (uptime for ISSO operations), Privacy (user profile data)

**Key control gaps to address pre-audit:**
- Formal risk assessment documentation
- Vendor management program
- Formal SDLC/change management process documentation
- User access reviews (quarterly)
- Security awareness training records
- Incident response plan and test
- Penetration test (annual)
- Disaster recovery test results

---

## 18. Quick Reference Tables

### 18.1 SOC 2 Trust Service Category Selection Guide

| If you commit to... | Include category |
|---|---|
| Protecting all data from unauthorized access | Security (always) |
| System uptime / availability SLAs | Availability |
| Accurate and complete transaction processing | Processing Integrity |
| Protecting customer's confidential business data | Confidentiality |
| Handling personal information of individuals | Privacy |

### 18.2 Type 1 vs Type 2 Decision Guide

| Situation | Recommended |
|---|---|
| First-time SOC 2, no controls history | Type 1, then Type 2 |
| Customer contractually requires SOC 2 | Type 2 |
| Vendor questionnaire due diligence | Type 2 (Type 1 acceptable initially) |
| FedRAMP supplemental evidence | Type 2 |
| After significant system changes | Type 1 for changed components; continue Type 2 for stable components |

### 18.3 Common SOC 2 Audit Evidence Checklist

| Control Area | Evidence Examples |
|---|---|
| Access provisioning | Onboarding tickets with approval; access provisioning system logs |
| Access deprovisioning | Offboarding tickets; HR termination reports; deactivation records |
| Access reviews | Quarterly access review reports with reviewer signatures |
| MFA enforcement | Configuration screenshots; enrollment reports |
| Vulnerability management | Scan reports; remediation tickets; SLA metrics |
| Penetration testing | Engagement report; remediation tracking |
| Change management | Change request tickets; CAB approvals; deployment records |
| Incident response | IR ticket log; post-incident reviews |
| Business continuity | DR plan; test results; RTO/RPO evidence |
| Security training | Training completion records; LMS reports |
| Risk assessment | Risk register; annual assessment report |
| Background checks | Policy + sample results (redacted) |
| Encryption | Configuration documentation; certificate management |
| Audit logging | SIEM configuration; log retention policy; sample reviews |

### 18.4 SOC 2 Exception Severity Assessment

| Severity | Criteria | Customer Impact |
|---|---|---|
| Low | Isolated, low-risk, remediated | Acceptable; note for follow-up |
| Moderate | Multiple occurrences; moderate risk; being remediated | Discuss with vendor; obtain management response |
| High | Systemic failure; high-risk control; unclear remediation | Escalate to CISO/legal; evaluate risk acceptance |
| Critical | Fundamental control breakdown; no compensating controls | May preclude vendor approval; legal review required |

### 18.5 Glossary of SOC 2 Terms

| Term | Definition |
|---|---|
| Service Organization | The entity (vendor) being examined |
| User Entity | A customer of the service organization who relies on the service |
| Subservice Organization | A vendor used by the service organization |
| CPA / Service Auditor | The independent CPA firm conducting the SOC 2 examination |
| System Description | Management's narrative of the services and controls |
| Assertion | Management's formal representation that the description is accurate |
| Trust Service Criteria (TSC) | The AICPA criteria against which controls are measured |
| COSO | Committee of Sponsoring Organizations — internal control framework |
| CUEC | Complementary User Entity Control |
| CSOC | Complementary Subservice Organization Control |
| Carve-Out Method | Excluding subservice organization controls from scope |
| Inclusive Method | Including subservice organization controls in scope |
| Deviation | Instance where a control did not operate as described |
| Sampling | Auditor selection of a subset of a population for testing |
| Operating Effectiveness | Controls consistently function as designed throughout the period |
| Design Effectiveness | Controls are suitably designed to meet criteria if operated as intended |

---

*Document Version: 1.0*
*Standard Reference: AICPA Trust Services Criteria (2017, updated 2022); AT-C Section 205 and 320*
*For authoritative guidance, consult current AICPA publications and engage a licensed CPA firm*
