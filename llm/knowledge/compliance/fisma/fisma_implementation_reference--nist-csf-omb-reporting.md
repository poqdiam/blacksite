# FISMA Implementation Reference — NIST Framework, OMB Reporting, and Continuous Monitoring

**Framework:** Federal Information Security Modernization Act (FISMA) 2014
**Governing Bodies:** OMB (policy), DHS/CISA (technical assistance), NIST (standards)
**Applicability:** Federal agencies and federal information systems; contractors operating on behalf of agencies
**Document Type:** GRC Knowledge Base — Authoritative Reference
**Last Updated:** 2026-03-01

---

## Table of Contents

1. [FISMA Overview](#fisma-overview)
2. [Key Provisions and Responsibilities](#key-provisions-and-responsibilities)
3. [FISMA Implementation Stack](#fisma-implementation-stack)
4. [OMB Circular A-130](#omb-circular-a-130)
5. [FISMA Reporting Cycle](#fisma-reporting-cycle)
6. [CyberScope and Automated Reporting](#cyberscope-and-automated-reporting)
7. [Key FISMA Metrics](#key-fisma-metrics)
8. [FISMA vs FedRAMP](#fisma-vs-fedramp)
9. [Continuous Monitoring Under FISMA](#continuous-monitoring-under-fisma)
10. [BLACKSITE Platform Mappings](#blacksite-platform-mappings)
11. [Common FISMA Findings from IG Assessments](#common-fisma-findings-from-ig-assessments)
12. [Key Agencies and Roles](#key-agencies-and-roles)
13. [Key References](#key-references)

---

## FISMA Overview

The **Federal Information Security Modernization Act (FISMA)** was originally enacted in 2002 as the Federal Information Security Management Act (Title III of the E-Government Act of 2002). It was significantly updated and renamed to the Federal Information Security Modernization Act in December 2014 (Public Law 113-283).

**FISMA 2014** made the following key changes from the 2002 act:
- Transferred primary operational cybersecurity responsibilities from OMB to **DHS**
- Strengthened the role of the **Director of National Intelligence (DNI)** for intelligence community systems
- Clarified OMB's role as policy authority while DHS provides technical assistance and coordination
- Added requirements for agencies to report on cybersecurity incidents to DHS/US-CERT
- Authorized DHS to conduct risk assessments and deploy threat detection capabilities on federal networks

**Core FISMA mandate:** Federal agencies must develop, document, and implement agency-wide programs to provide information security for the information and information systems that support the operations and assets of the agency — including systems provided by a contractor or operated on behalf of the agency.

**Scope:**
- Applies to all federal executive branch agencies
- Extends to contractors, grantees, and others who operate or use federal information systems
- Covers both classified and unclassified systems (though classified systems have additional requirements)
- Does not apply to national security systems (governed by Committee on National Security Systems — CNSS)

---

## Key Provisions and Responsibilities

### Head of Agency
- Ultimate responsibility for agency information security
- Must ensure adequate resources are allocated
- Must ensure information security risks are addressed as part of strategic and operational planning

### Chief Information Officer (CIO)
- Designated by FISMA as having agency-wide responsibility for information security
- Annually reports to OMB on the adequacy and effectiveness of the agency's information security policies, procedures, and practices
- Ensures the agency has a comprehensive information security program
- Designates a **Senior Agency Information Security Officer (SAISO)**, typically the **CISO**

### Chief Information Security Officer (CISO) / Senior Agency Information Security Officer (SAISO)
- Heads the information security program
- Oversees development and maintenance of security policies
- Manages the agency's continuous monitoring program
- Serves as the primary liaison with NIST, OMB, and DHS on security matters
- Prepares and submits FISMA metrics

### Authorizing Official (AO)
- Senior official with authority to accept risk on behalf of the agency
- Signs the **Authorization to Operate (ATO)** decision for systems under their purview
- Responsible for monitoring and understanding the security posture of authorized systems
- ATOs must be reauthorized periodically (typically every 3 years) or when significant changes occur

### System Owner
- Responsible for the development, procurement, integration, modification, operation, maintenance, and disposition of an information system
- Coordinates with the ISSO to develop and maintain the system security plan
- Ensures training for authorized users

### Information System Security Officer (ISSO)
- Principal advisor for security of an assigned system
- Maintains the system security plan and POA&M
- Performs day-to-day security oversight and monitoring
- Coordinates with system owner and ISSM on security activities

### Inspector General (IG)
- Independently evaluates agency FISMA compliance annually
- Reports findings to Congress via the FISMA IG report
- IG assessments are independent of agency self-assessments — they provide external validation

---

## FISMA Implementation Stack

FISMA mandates the use of standards and guidelines published by **NIST** and mandatory standards published by **NIST's National Institute of Standards and Technology** and **FIPS**. The implementation stack is layered:

### FIPS 199 — Standards for Security Categorization

**FIPS 199** (Standards for Security Categorization of Federal Information and Information Systems) defines the framework for categorizing federal information systems based on potential impact to confidentiality, integrity, and availability.

| Impact Level | Description |
|---|---|
| **Low** | Limited adverse effect — minor mission degradation, minor financial loss, minor harm to individuals |
| **Moderate** | Serious adverse effect — significant mission degradation, significant financial loss, significant harm |
| **High** | Severe or catastrophic adverse effect — major mission degradation, major financial loss, severe harm or death |

System categorization formula: **{(Confidentiality, Impact), (Integrity, Impact), (Availability, Impact)}**
Overall security category = **high-water mark** of the three values.

Example: A system with C=Low, I=Moderate, A=Moderate → **MODERATE** impact system.

### FIPS 200 — Minimum Security Requirements

**FIPS 200** (Minimum Security Requirements for Federal Information and Information Systems) establishes minimum security requirements for federal information systems across 17 control families. Agencies satisfy these minimum requirements by implementing the appropriate security controls in **NIST SP 800-53** based on their system's FIPS 199 categorization.

The 17 families in FIPS 200 map directly to the control families in NIST SP 800-53.

### NIST SP 800-37 — Risk Management Framework (RMF)

**NIST SP 800-37 Rev 2** (Risk Management Framework for Information Systems and Organizations) defines the six-step process that federal agencies use to authorize and maintain federal information systems:

| Step | Name | Key Activities |
|---|---|---|
| **1. Prepare** | Organizational preparation | Establish context; assign roles; identify assets; conduct risk assessment |
| **2. Categorize** | System categorization | Apply FIPS 199; document in SSP; obtain AO concurrence |
| **3. Select** | Control selection | Choose baseline controls from SP 800-53B; tailor; document in SSP |
| **4. Implement** | Control implementation | Implement controls; document implementation details in SSP |
| **5. Assess** | Control assessment | Test controls per SP 800-53A; produce SAR; identify deficiencies |
| **6. Authorize** | Authorization decision | AO reviews SSP + SAR + POA&M; accepts risk; issues ATO or DATO |
| **7. Monitor** | Continuous monitoring | Ongoing control assessment; POA&M maintenance; reporting; trigger reauthorization |

Note: Rev 2 added a "Prepare" step at the front of the framework to emphasize organizational-level preparation activities.

### NIST SP 800-53 Rev 5 — Security and Privacy Controls

**NIST SP 800-53 Rev 5** (Security and Privacy Controls for Information Systems and Organizations) provides the comprehensive catalog of security and privacy controls. Rev 5 (2020) made significant changes:
- Integrated privacy controls throughout (previously a separate appendix)
- Added supply chain risk management (SR) control family
- Made the catalog program-neutral (applicable beyond federal government)
- Separated control baselines into **SP 800-53B**

**Control families (20 in Rev 5):**

| ID | Family |
|---|---|
| AC | Access Control |
| AT | Awareness and Training |
| AU | Audit and Accountability |
| CA | Assessment, Authorization, and Monitoring |
| CM | Configuration Management |
| CP | Contingency Planning |
| IA | Identification and Authentication |
| IR | Incident Response |
| MA | Maintenance |
| MP | Media Protection |
| PE | Physical and Environmental Protection |
| PL | Planning |
| PM | Program Management |
| PS | Personnel Security |
| PT | Personally Identifiable Information Processing and Transparency |
| RA | Risk Assessment |
| SA | System and Services Acquisition |
| SC | System and Communications Protection |
| SI | System and Information Integrity |
| SR | Supply Chain Risk Management |

### NIST SP 800-53B — Control Baselines

**NIST SP 800-53B** defines three control baselines corresponding to FIPS 199 impact levels:

| Baseline | Applies To | Control Count (approx.) |
|---|---|---|
| **Low Baseline** | Low impact systems | ~100 controls |
| **Moderate Baseline** | Moderate impact systems | ~250 controls |
| **High Baseline** | High impact systems | ~330 controls |

Agencies may **tailor** baselines by adding controls (overlay) or removing controls (scoping considerations) with documented justification.

### NIST SP 800-53A Rev 5 — Assessing Controls

**NIST SP 800-53A** provides assessment procedures for each control in SP 800-53. For each control, it specifies:
- Interview procedures (who to speak with)
- Examine procedures (what documentation to review)
- Test procedures (what to technically test)

The output of assessment activities is the **Security Assessment Report (SAR)**, which documents findings, deficiencies, and recommendations.

### NIST SP 800-137 — Information Security Continuous Monitoring (ISCM)

**NIST SP 800-137** (Information Security Continuous Monitoring for Federal Information Systems and Organizations) provides guidance on establishing, implementing, and maintaining ISCM programs. ISCM is the backbone of the ongoing monitoring step of the RMF.

### NIST SP 800-39 — Managing Information Security Risk

**NIST SP 800-39** (Managing Information Security Risk: Organization, Mission, and Information System View) establishes the three-tier risk management hierarchy:
- **Tier 1:** Organization level (governance, risk tolerance, strategy)
- **Tier 2:** Mission/business process level
- **Tier 3:** Information system level (RMF application)

---

## OMB Circular A-130

**OMB Circular A-130** (Managing Information as a Strategic Resource) was updated in 2016 and is the foundational policy document governing federal information management. It establishes:

- Federal information as a **strategic government asset** requiring lifecycle management
- Requirements for agencies to protect federal information and information systems
- Privacy requirements for agencies collecting and maintaining personally identifiable information
- Integration of privacy and security as complementary disciplines (not separate programs)
- Requirements for agencies to adopt a risk management approach rather than a compliance-only mindset
- Appendix I: Responsibilities for Protecting Federal Information Resources
- Appendix II: Responsibilities for Managing Personally Identifiable Information

**Key A-130 requirements relevant to FISMA:**
- Agencies must implement the NIST Risk Management Framework
- System security plans must be developed for all information systems
- POA&Ms must be maintained for all identified security weaknesses
- Security assessments must be conducted with sufficient frequency
- Authorization decisions must be made before systems are placed into operation
- Privacy Impact Assessments (PIAs) required for systems collecting PII

---

## FISMA Reporting Cycle

### Annual CIO Report to OMB

Each year, agency CIOs submit a **FISMA report** to OMB covering:
- Number of systems requiring security authorization, number with current ATOs
- Percentage of systems covered by an incident response process
- Performance against FISMA metrics (see below)
- Status of continuous monitoring programs
- Number of open POA&M items, average age

**Submission deadline:** Typically November 15 for the prior fiscal year (October 1–September 30).

### Inspector General Annual Assessment

Agency **Inspectors General** independently evaluate the effectiveness of the agency's information security program and submit a separate FISMA IG report. Key areas assessed:
- Whether the agency has a comprehensive security program
- Quality of system security plans and risk assessments
- Currency of ATOs (expired ATOs are a common negative finding)
- POA&M quality and timeliness of remediation
- Continuous monitoring program maturity
- Security training completion rates
- Incident detection and response capabilities

**Maturity levels used by IGs (FISMA maturity model):**
| Level | Description |
|---|---|
| 1 — Ad Hoc | Unpredictable, reactive, poorly controlled |
| 2 — Defined | Planned, documented, and implemented |
| 3 — Consistently Implemented | Consistent implementation across the organization |
| 4 — Managed and Measurable | Quantitatively managed; data-driven decisions |
| 5 — Optimized | Continuous improvement; adaptive |

A rating of Level 4 or 5 is considered "Effective" by OMB.

### DHS FISMA Metrics

DHS issues annual FISMA metrics questions that agencies must answer. Metrics are organized by the NIST Cybersecurity Framework (CSF) functions:
- **Identify:** Asset management, risk management program
- **Protect:** Access management, configuration management, identity management, data protection
- **Detect:** Continuous monitoring, anomaly detection
- **Respond:** Incident response capabilities
- **Recover:** Recovery planning, improvements

---

## CyberScope and Automated Reporting

**CyberScope** is the DHS/OMB automated reporting system for FISMA data. Agencies submit FISMA metrics data directly into CyberScope via automated feeds from their security tools (SIEM, vulnerability scanners, asset inventory systems, etc.).

Key CyberScope data streams:
- **Hardware asset inventory** — all systems with categorization, ATO status
- **Software asset inventory** — approved software and versions
- **Vulnerability management data** — scan results and remediation status
- **Configuration compliance** — SCAP-compliant configuration assessment results
- **Privilege management** — privileged account counts, MFA enrollment rates

Agencies with mature continuous monitoring programs feed CyberScope automatically through integration with their monitoring platforms. This reduces manual reporting burden and provides near-real-time visibility to OMB/DHS.

---

## Key FISMA Metrics

The following metrics are most heavily weighted in annual FISMA reporting and IG assessments:

| Metric | Target | Why It Matters |
|---|---|---|
| **Systems with current ATOs** | 100% | Expired ATOs indicate systems operating without accepted risk |
| **% controls tested in current year** | Varies by tier | Demonstrates active monitoring vs one-time authorization |
| **POA&M aging** | Average age < 90 days for high findings | Old POA&Ms indicate remediation is stalled |
| **Critical/high vulnerability remediation** | Critical: 15 days; High: 30 days | Timely patching reduces attack surface |
| **Phishing simulation click rate** | < 5% industry target | Training effectiveness indicator |
| **MFA coverage for privileged users** | 100% | Identity security foundation |
| **Security awareness training completion** | 100% | Baseline compliance |
| **Incidents reported to US-CERT** | Per reporting requirements | Demonstrates functioning incident detection |
| **Systems covered by ISCM** | 100% | Ongoing monitoring vs periodic assessment |
| **PIAs completed for PII systems** | 100% | Privacy compliance indicator |

---

## FISMA vs FedRAMP

FISMA and **FedRAMP (Federal Risk and Authorization Management Program)** are closely related but serve different purposes:

| Attribute | FISMA | FedRAMP |
|---|---|---|
| **Purpose** | Govern security of federal agency-owned/operated systems | Authorize cloud services for government use |
| **Subject** | Federal agencies and their systems | Cloud Service Providers (CSPs) selling to government |
| **Who authorizes** | Agency AO | JAB (Joint Authorization Board) or Agency AO |
| **Framework** | NIST RMF (SP 800-37) | NIST RMF + FedRAMP-specific requirements |
| **Control baseline** | NIST SP 800-53B | FedRAMP baselines (derived from 800-53B with additions) |
| **Authority** | OMB FISMA statute | OMB M-11-11 memorandum; codified in FedRAMP Authorization Act (2022) |
| **Reuse** | ATOs are agency-specific | ATOs are reusable across agencies (P-ATO and Agency ATO) |
| **Continuous monitoring** | Agency-managed ISCM | FedRAMP-mandated monthly/annual ConMon deliverables to FedRAMP PMO |

**Key relationship:** When a federal agency uses a FedRAMP-authorized cloud service, the agency can leverage the FedRAMP ATO to satisfy FISMA requirements for that service. The agency still conducts a risk determination (issuing their own Agency ATO leveraging the FedRAMP package) and maintains responsibility for the controls in the customer responsibility matrix.

**Shared Responsibility:** FedRAMP and FISMA both use the concept of shared responsibility. The CSP inherits responsibility for infrastructure controls; the agency inherits responsibility for application-level and configuration controls.

---

## Continuous Monitoring Under FISMA

### What is ISCM?

**Information Security Continuous Monitoring (ISCM)** is the ongoing awareness of information security, vulnerabilities, and threats to support organizational risk management decisions. ISCM is not just running automated scans — it is a comprehensive program that includes:

- **Strategy:** Agency-level ISCM strategy document defining goals, scope, and resource requirements
- **Policies and Procedures:** Documented ISCM processes
- **Monitoring Frequency:** Defined cadence for assessing each control (continuously, monthly, quarterly, annually)
- **Metrics:** ISCM metrics collected and reported
- **Reporting:** Regular reporting to AO and organizational leadership
- **Response:** Process for acting on findings from monitoring

### ISCM Monitoring Tiers (NIST SP 800-137)

| Tier | Scope | Activities |
|---|---|---|
| **Tier 1 — Organization** | Agency-wide risk posture | Aggregate risk reporting; risk tolerance updates; program-level metrics |
| **Tier 2 — Mission/Business Process** | Mission system group risk | Cross-system risk aggregation; mission impact analysis |
| **Tier 3 — Information System** | Individual system risk | Control testing; vulnerability scanning; log review; incident monitoring |

### Ongoing Authorization

Traditional FISMA required full reauthorization every 3 years — a resource-intensive point-in-time assessment. **Ongoing Authorization** (also called **Continuous Authorization**) is an alternative where:
- Controls are assessed on a rolling basis throughout the year
- The AO maintains continuous situational awareness
- Formal reauthorization is replaced by ongoing AO review of ISCM outputs
- Significant changes still trigger targeted reassessment

**Requirements for ongoing authorization:**
- Mature ISCM program in place
- Real-time or near-real-time security metrics available to AO
- Automated vulnerability management and configuration compliance
- Defined triggers for escalation to full reauthorization (significant change events)

### Frequency Tiers for Control Monitoring

NIST SP 800-137 defines control monitoring frequencies based on risk and volatility:

| Frequency | Examples |
|---|---|
| **Continuous (near real-time)** | Vulnerability scanning, log monitoring, network traffic analysis |
| **Daily** | Backup verification, malware scan results review |
| **Weekly** | Patch status, account activity review |
| **Monthly** | Configuration compliance, privileged account review, vulnerability scan trend analysis |
| **Quarterly** | Access reviews, POA&M review, security metrics reporting to AO |
| **Annually** | Full control assessment subset, security plan update, training completion |
| **Triggered** | Significant change events, incidents, technology refreshes |

---

## BLACKSITE Platform Mappings

| BLACKSITE Feature | FISMA/RMF Component | Evidence Value |
|---|---|---|
| **RMF Tracker** | All 7 RMF steps (SP 800-37) | Documents step completion, status, and responsible parties; supports ATO package assembly |
| **ATO Package / ATO Documents** | Step 6 (Authorize) | Stores authorization decision, ATO expiration, AO signature, supporting documents (SSP, SAR, POA&M) |
| **POA&M** (Plan of Action and Milestones) | RMF Step 7 (Monitor); FISMA statutory requirement | Tracks weaknesses, remediation milestones, resource allocation, and responsible parties; supports IG review |
| **Audit Log** (all user actions) | AU (Audit and Accountability) family; SP 800-137 | Demonstrates logging and monitoring capability; supports ISCM evidence; feeds CyberScope-style reporting |
| **Daily Logbook** | SP 800-137 ISCM; ongoing monitoring evidence | Shows daily security operations activity; demonstrates monitoring is performed continuously, not episodically |
| **Control Assessment** | RMF Step 5 (Assess); SP 800-53A | Assessment tracking; SAR-supporting evidence; test results by control family |
| **System Inventory** | Step 2 (Categorize); FIPS 199 | System register with categorization; ATO status tracking; supports FISMA metric on ATO currency |
| **Observations** | SAR findings; POA&M input | Security finding documentation; links findings to controls; feeds POA&M creation |
| **Interconnection Records** | SC family; CA-3 (Connected Systems) | Documents ISAs (Interconnection Security Agreements); supports CA-3 control implementation |
| **Data Flow Records** | SC, MP, PT families; privacy program | PII data flow mapping; supports PIA; privacy control evidence |
| **Privacy Assessments** | PT (PII Processing) family; A-130 PIA requirement | Privacy Impact Assessment documentation; PII system inventory |
| **Vendor Records** | SA-9 (External System Services); SR family | Third-party risk management; supply chain control evidence |
| **Change Review Records** | CM (Configuration Management) family | Change management evidence; pre/post-change assessment documentation |
| **Incident Response Records** | IR family | IR plan testing evidence; incident log; lessons learned |
| **ISSM Portfolio** | ISSM/CISO reporting function | Multi-system overview; portfolio-level risk aggregation |

**Note for federal practitioners:** BLACKSITE's system of record approach — with full audit trail, ATO tracking, and POA&M management — aligns with the documentation requirements for both the system-level authorization package and annual FISMA reporting. Export functions should be leveraged for CyberScope feeds where applicable.

---

## Common FISMA Findings from IG Assessments

IG teams review FISMA compliance annually and report findings to Congress. The following are the most frequently cited findings across federal agencies:

### Finding 1: Systems Operating with Expired ATOs
**FISMA Requirement:** Systems may not operate without an ATO from a designated AO.
**Description:** Systems where the 3-year ATO has lapsed, or where significant changes occurred without triggering reauthorization. This is consistently the #1 FISMA finding across agencies.
**Remediation:** Implement ATO expiration tracking with automated alerts at 180/90/30/0 days; prioritize reauthorization queue; consider transition to ongoing authorization for mature systems; for systems where reauthorization is not feasible in near term, obtain AO interim authorization with documented risk acceptance.

### Finding 2: Incomplete or Stale POA&Ms
**FISMA Requirement:** Agencies must maintain POA&Ms for all identified weaknesses.
**Description:** POA&M items with no activity for 90+ days; POA&M items missing resource allocation, scheduled completion dates, or responsible parties; findings from assessments not entered into POA&M within required timeframe.
**Remediation:** Establish POA&M governance with defined entry SLAs; conduct monthly POA&M review with system owners; track average age and percentage of high-risk items overdue; ensure assessment findings are automatically linked to POA&M creation.

### Finding 3: Insufficient Control Testing Coverage
**FISMA Requirement:** Controls must be tested with sufficient frequency to support ongoing authorization.
**Description:** Agency relies solely on initial authorization assessment (potentially years old) without ongoing testing. No defined schedule for monitoring frequency by control family.
**Remediation:** Implement SP 800-137 monitoring frequencies; assign controls to automated or manual testing schedules; track testing coverage percentage as a FISMA metric; prioritize high-impact and frequently-changing controls for automated monitoring.

### Finding 4: Lack of Mature ISCM Program
**FISMA Requirement:** SP 800-137 program required by FISMA statute.
**Description:** Agency has no written ISCM strategy; monitoring activities are ad hoc rather than systematic; no defined triggers for escalation to AO; metrics not tracked or reported.
**Remediation:** Develop and approve agency ISCM strategy document; define monitoring frequencies; establish reporting cadence to AO; integrate ISCM outputs with FISMA annual reporting.

### Finding 5: Security Training Not Current
**FISMA Requirement:** Annual security awareness training required.
**Description:** Annual training completion rates below 95%; privileged users not completing role-based security training; new employees not completing training within 60 days of hire.
**Remediation:** Automate training assignments via LMS integrated with HR; track completion rates monthly; implement access controls that block login for users with overdue training.

### Finding 6: Incidents Not Reported Per Requirements
**FISMA Requirement:** Incidents must be reported to US-CERT within defined timeframes (major incidents within 1 hour for some categories).
**Description:** Incidents not documented; incidents documented but not escalated to US-CERT within required timeframe; no defined incident classification taxonomy.
**Remediation:** Implement incident response procedure with US-CERT reporting steps; train staff on reporting thresholds; conduct annual IR exercise including reporting procedure walkthrough.

### Finding 7: Privacy Program Not Integrated
**FISMA Requirement / A-130:** PIAs required; Senior Agency Official for Privacy (SAOP) responsibilities defined.
**Description:** Systems processing PII lack completed PIAs; PII not inventoried; privacy and security programs operate independently with no coordination.
**Remediation:** Conduct PII inventory; complete PIAs for all applicable systems; establish joint privacy/security working group; integrate privacy controls into system security plans.

---

## Key Agencies and Roles

| Agency / Role | Responsibility |
|---|---|
| **OMB (Office of Management and Budget)** | FISMA policy authority; issues guidance memoranda (M-series); receives annual CIO reports; sets FISMA metrics |
| **DHS / CISA** | Technical implementation support; operates US-CERT for incident reporting; deploys CDM (Continuous Diagnostics and Mitigation); issues binding operational directives (BODs) |
| **NIST** | Develops standards and guidelines (FIPS, SP 800-series); does not issue or approve ATOs; provides voluntary assistance to agencies |
| **NSA** | Security guidance for national security systems; co-authors some CNSS policies |
| **Federal CIO Council** | Cross-agency coordination on IT policy; publishes guidance and best practices |
| **Agency CIO** | Statutory role under FISMA; oversees agency information security program; reports to OMB |
| **Agency CISO / SAISO** | Operational head of security program; implements CIO direction; liaison to NIST/OMB/DHS |
| **Authorizing Official (AO)** | Accepts risk; issues ATOs; accountable for systems under their purview |
| **Inspector General (IG)** | Independent annual assessment; reports to Congress; not in agency security chain of command |
| **CDM Program (DHS)** | Continuous Diagnostics and Mitigation — provides tools and dashboards to agencies; includes asset management, identity management, network security management, data protection capabilities |

---

## Key References

- **FISMA 2014 (Public Law 113-283):** https://www.congress.gov/bill/113th-congress/senate-bill/2521
- **NIST SP 800-37 Rev 2:** Risk Management Framework — https://csrc.nist.gov/publications/detail/sp/800-37/rev-2/final
- **NIST SP 800-53 Rev 5:** Security and Privacy Controls — https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final
- **NIST SP 800-53A Rev 5:** Assessment Procedures — https://csrc.nist.gov/publications/detail/sp/800-53a/rev-5/final
- **NIST SP 800-53B:** Control Baselines — https://csrc.nist.gov/publications/detail/sp/800-53b/final
- **NIST SP 800-137:** Information Security Continuous Monitoring — https://csrc.nist.gov/publications/detail/sp/800-137/final
- **NIST SP 800-39:** Managing Information Security Risk — https://csrc.nist.gov/publications/detail/sp/800-39/final
- **FIPS 199:** Standards for Security Categorization — https://csrc.nist.gov/publications/detail/fips/199/final
- **FIPS 200:** Minimum Security Requirements — https://csrc.nist.gov/publications/detail/fips/200/final
- **OMB Circular A-130:** Managing Information as a Strategic Resource — https://www.whitehouse.gov/omb/information-for-agencies/circulars/
- **FedRAMP Program:** https://www.fedramp.gov/
- **DHS CISA CDM Program:** https://www.cisa.gov/cdm
- **NIST Cybersecurity Framework (CSF) 2.0:** https://www.nist.gov/cyberframework

---

*This document is part of the BLACKSITE GRC Platform knowledge base. It is intended as a practitioner reference for security and compliance professionals working in or with the federal government. FISMA compliance determinations require agency-level program implementation under the authority of the agency CIO and AO. This document does not constitute legal advice or official government guidance.*
