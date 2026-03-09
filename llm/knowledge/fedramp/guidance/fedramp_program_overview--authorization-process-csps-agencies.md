# FedRAMP Program Overview — Authorization Process for CSPs and Agencies

**Document type:** GRC knowledge base reference
**Applies to:** ISSOs, ISSMs, SCAs, System Owners, AOs using cloud services
**Source:** Federal Risk and Authorization Management Program (FedRAMP), GSA-managed
**Status in BLACKSITE:** Authoritative reference for inherited control documentation, vendor records, and cloud service SSP sections

---

## Overview

The **Federal Risk and Authorization Management Program (FedRAMP)** is a U.S. government-wide program that provides a standardized approach to security assessment, authorization, and continuous monitoring for cloud products and services used by federal agencies.

FedRAMP is managed by the **General Services Administration (GSA)** through the FedRAMP Program Management Office (PMO). It is grounded in FISMA, OMB policy, and NIST standards, particularly NIST SP 800-53 and FIPS 199/200.

### The Core Value Proposition: "Authorize Once, Use Many"

Before FedRAMP, every federal agency independently assessed the same cloud services — creating massive duplication of effort, inconsistent security requirements, and delays. A large cloud provider might receive dozens of separate security assessments for the same product.

FedRAMP solves this by establishing a common baseline, a common assessment methodology, and a central repository of authorization packages. An agency can review an existing FedRAMP authorization package and issue a system-level ATO based on inherited controls — dramatically reducing the assessment burden.

The **FedRAMP Marketplace** is the public catalog of all FedRAMP-authorized, FedRAMP Ready, and FedRAMP In Process cloud services. Agencies are directed to search the Marketplace before initiating a new cloud service acquisition.

---

## Why FedRAMP Matters to ISSOs

If your system uses any cloud service — SaaS email, cloud storage, a hosted application, an IaaS infrastructure provider — you may be using a FedRAMP-authorized service. As an ISSO, you must:

1. **Identify all cloud services** used by your system (including shadow IT)
2. **Verify FedRAMP authorization status** of each service (Marketplace lookup)
3. **Obtain the Customer Responsibility Matrix (CRM)** from the CSP for each authorized service
4. **Document inherited controls** in your SSP — what the CSP implements on your behalf
5. **Implement customer-responsible controls** — what your agency must do on top of the CSP baseline
6. **Track CSP continuous monitoring** — CSPs must maintain their authorization; check for advisories

An agency cannot simply say "we use AWS, therefore our security is covered." The CSP covers infrastructure-level controls; you still own application-level security, access management, data classification, and many other controls.

---

## FedRAMP vs. FISMA

These two frameworks are related but distinct. Understanding the difference is critical for accurate SSP documentation.

| Dimension | FISMA | FedRAMP |
|---|---|---|
| **Applies to** | All federal information systems, including agency-operated systems | Cloud services (SaaS, IaaS, PaaS) used by federal agencies |
| **Framework** | NIST SP 800-37 RMF; SP 800-53 controls | NIST SP 800-53 controls at FedRAMP-defined baselines |
| **Authorization issuer** | Agency AO | FedRAMP JAB (P-ATO) or Agency AO (Agency ATO) |
| **Scope** | Agency's own systems | CSP's cloud product or service offering |
| **Inherited controls** | Can inherit from other agency systems | Agencies inherit from FedRAMP-authorized CSPs |
| **Continuous monitoring** | Agency-managed per NIST SP 800-137 | CSP-managed ConMon; reports submitted to FedRAMP PMO and sponsoring agency |

A system subject to FISMA that also uses a FedRAMP-authorized cloud service operates under both frameworks simultaneously. The FISMA ATO covers the agency system; the inherited FedRAMP controls are a component of that system's security posture.

---

## FedRAMP Authorization Paths

There are three main authorization paths. Each results in different artifacts and has different applicability.

### Path 1: Agency Authorization (Sponsor Model)

The most common path. A federal agency sponsors a CSP through the FedRAMP authorization process.

**Process:**
1. Agency and CSP agree on sponsorship; CSP begins authorization preparation
2. CSP completes system description, FIPS 199 categorization, and SSP
3. CSP engages an accredited **3PAO** (Third Party Assessment Organization) to perform independent assessment
4. 3PAO produces a Security Assessment Report (SAR)
5. CSP produces a POA&M addressing SAR findings
6. Agency AO reviews the complete authorization package and issues an **ATO** (Authority to Operate)
7. Package is uploaded to FedRAMP and published on the Marketplace
8. Other agencies can reuse the package without repeating the full assessment (leveraging approach)

**Outcome:** Agency ATO — the sponsoring agency owns the authorization; other agencies issue their own ATOs based on the reviewed package.

**Best for:** CSPs with a primary federal customer; mid-size cloud services seeking broad federal adoption.

### Path 2: JAB Provisional Authorization (P-ATO)

The **Joint Authorization Board (JAB)** consists of the Chief Information Officers of the **Department of Defense (DoD)**, the **Department of Homeland Security (DHS)**, and the **General Services Administration (GSA)**. The JAB reviews and authorizes cloud services with the highest federal demand and broadest applicability.

**JAB Prioritization:** Not all CSPs can pursue JAB authorization. The FedRAMP PMO prioritizes CSPs based on the number of federal agencies that plan to use the service and the potential government-wide impact.

**Process:**
1. CSP applies for JAB authorization; FedRAMP PMO reviews and prioritizes
2. JAB kick-off: CSP, JAB technical reviewers, and 3PAO align on scope and schedule
3. CSP completes SSP; 3PAO completes assessment
4. JAB technical review: detailed review of all documentation
5. JAB issues **P-ATO** (Provisional Authority to Operate) if package meets requirements
6. Agencies using the service must still issue their own ATO leveraging the JAB P-ATO

**Outcome:** JAB P-ATO — a provisional authorization that agencies can use as the basis for their own ATO without repeating the full assessment.

**Best for:** Large, widely-used cloud platforms (major IaaS, enterprise SaaS) seeking government-wide adoption.

### Path 3: FedRAMP Ready

**FedRAMP Ready** is a preliminary designation indicating that a CSP has documented capabilities that meet FedRAMP requirements, as verified by a 3PAO, but has not yet received a full authorization.

- Does NOT constitute an authorization to operate for federal systems
- Indicates CSP is "ready" to begin the authorization process with an agency sponsor
- Listed on the Marketplace as "FedRAMP Ready" — not "FedRAMP Authorized"
- Valid for 12 months; CSP must progress to authorization or re-validate

**ISSOs should not count FedRAMP Ready as an authorization** when documenting inherited controls. A FedRAMP Ready CSP used by your system should be flagged in your SSP as a pending authorization — requiring agency-level risk acceptance.

---

## Impact Levels

FedRAMP uses FIPS 199 impact levels to determine which baseline applies. The CSP's authorization is tied to a specific impact level.

| Impact Level | FIPS 199 | Description | Number of Controls (approx.) | Common Use Cases |
|---|---|---|---|---|
| **FedRAMP Low** | Low | Systems where loss of confidentiality, integrity, or availability would have limited adverse effects | ~125 controls | Public-facing websites, low-sensitivity collaboration tools |
| **FedRAMP Moderate** | Moderate | Systems where loss could have serious adverse effects; most common federal cloud use case | ~325 controls | Most agency SaaS, HR systems, general collaboration |
| **FedRAMP High** | High | Systems where loss could have severe or catastrophic effects; law enforcement, emergency services, financial, health data | ~421 controls | Law enforcement databases, sensitive financial systems, clinical health records |

**Note on impact level matching:** An agency with a High-impact system cannot use a FedRAMP Moderate-authorized CSP for the core processing of that system. The CSP's authorization level must match or exceed the data sensitivity being processed.

---

## Authorization Package Components

A complete FedRAMP authorization package includes the following documents. These are the same documents an ISSO encounters when leveraging a FedRAMP authorization.

| Document | Purpose |
|---|---|
| **System Security Plan (SSP)** | Complete description of the system, security controls, and their implementation; the primary authorization artifact |
| **Security Assessment Plan (SAP)** | 3PAO's plan for conducting the independent assessment; scope, methodology, test cases |
| **Security Assessment Report (SAR)** | 3PAO's findings from the assessment; risk ratings for each finding |
| **Plan of Action and Milestones (POA&M)** | CSP's plan to remediate all open findings from the SAR; tracked through ConMon |
| **FIPS 199 Categorization** | Official impact level determination for the cloud service |
| **e-Authentication Threshold Analysis** | Assessment of identity verification requirements for system users |
| **Control Implementation Summary (CIS)** | Quick-reference summary of which controls the CSP implements vs. what is customer responsibility |
| **Customer Responsibility Matrix (CRM)** | Detailed breakdown of every control: CSP-implemented, customer-implemented, or shared |
| **User Guide** | Documentation for agency administrators on configuring the service securely |
| **Rules of Behavior (RoB)** | Acceptable use requirements for agency users of the cloud service |
| **Incident Response Plan** | CSP's IR procedures; includes how CSP notifies agencies of incidents |
| **Configuration Management Plan** | CSP's approach to configuration management and change control |

---

## Third Party Assessment Organizations (3PAOs)

A **3PAO** is an independent organization accredited to perform security assessments for FedRAMP. Accreditation is granted through the **American Association for Laboratory Accreditation (A2LA)** under the FedRAMP 3PAO Recognition Program.

Key 3PAO responsibilities:
- Conduct independent assessment of CSP systems against the applicable FedRAMP baseline
- Produce the Security Assessment Plan (SAP) and Security Assessment Report (SAR)
- Perform annual assessment activities as part of continuous monitoring
- Report significant findings to the FedRAMP PMO

**Agencies and CSPs cannot self-assess** for FedRAMP purposes. The 3PAO requirement ensures independent verification of security claims. When an ISSO reviews a CSP's authorization package, the 3PAO's involvement is the assurance that the SSP claims have been tested.

---

## Continuous Monitoring (ConMon) Requirements

FedRAMP authorization is not a one-time event. CSPs must maintain their authorization through ongoing continuous monitoring activities, reporting to both the FedRAMP PMO and all authorizing/leveraging agencies.

### Monthly ConMon Deliverables

| Deliverable | Frequency | Description |
|---|---|---|
| **Vulnerability scan results** | Monthly | Authenticated scans of OS, databases, web applications, containers |
| **POA&M update** | Monthly | Updated status of all open findings; new findings added within 30 days of discovery |
| **Inventory update** | Monthly | Current asset inventory confirming scope has not changed |
| **ConMon report** | Monthly | Summary of scan results, findings, remediation status |

### Annual ConMon Deliverables

| Deliverable | Frequency | Description |
|---|---|---|
| **Annual assessment** | Annual | 3PAO-conducted assessment of a subset of controls (rotating schedule + triggered by changes) |
| **Updated SAR** | Annual | Findings from annual assessment |
| **Updated SSP** | Annual | Reflects system changes, control updates, and finding resolutions |
| **Penetration test** | Annual | External penetration test; findings addressed in POA&M |

### Significant Change Notifications

CSPs must notify the FedRAMP PMO and all leveraging agencies of **significant changes** before implementing them. A significant change is any modification that could affect the security posture of the system:
- New services or features added to authorization boundary
- Changes to underlying infrastructure (new cloud regions, new data centers)
- Changes to key security controls (authentication mechanisms, encryption implementations)
- Acquisition or change of subservice organizations

---

## FedRAMP Vulnerability Remediation Timelines

FedRAMP imposes specific remediation timelines for vulnerabilities based on severity, which are stricter than many agency-level policies:

| Severity | CVSS Score Range | Required Remediation Time |
|---|---|---|
| **Critical** | 9.0–10.0 | 30 days |
| **High** | 7.0–8.9 | 30 days |
| **Medium** | 4.0–6.9 | 90 days |
| **Low** | 0.1–3.9 | 180 days |

Vulnerabilities not remediated within these windows must have POA&M entries with a documented remediation plan and may require agency risk acceptance.

---

## FedRAMP for ISSOs: Inherited Controls

The most important daily-practice implication of FedRAMP for ISSOs is the **inherited control** concept. When your system uses a FedRAMP-authorized cloud service, some security controls are implemented by the CSP rather than your agency.

### How to Document Inherited Controls in Your SSP

1. **Identify all cloud services** in scope for your system boundary
2. **Verify authorization status** for each service on the FedRAMP Marketplace
3. **Obtain the CRM** from each CSP (or download from the authorization package)
4. For each control in the CRM marked "CSP Responsible" or "Shared":
   - In your SSP, mark the control as "Inherited" or "Hybrid"
   - Reference the CSP name and FedRAMP authorization ID
   - Document what the CSP implements (brief description from their SSP or CRM)
   - For shared controls: document your agency's portion of the implementation
5. **Do not claim credit for CSP-implemented controls** without verifying the CSP's implementation in their SSP

### What You Still Own After Inheriting

Even with a fully FedRAMP-authorized IaaS provider, your agency retains full responsibility for:
- Application-level access controls (who can log into your application)
- Data classification and handling within the application
- Configuration of CSP services your application uses (S3 bucket permissions, security groups)
- Incident response for your application layer
- Audit logging at the application level (CSP covers infrastructure logging)
- User training and awareness
- Your agency's Rules of Behavior

### Common Mistake: Assuming Full Inheritance

ISSOs frequently over-inherit — assuming a FedRAMP Moderate authorization means all Moderate controls are covered. In reality:
- Most IaaS authorizations cover infrastructure controls (physical, environmental, some network)
- Application-layer controls (most of AC, IA, AU at the application level) remain customer responsibility
- The CRM is the authoritative source — review it for every CSP and every control family

---

## Common FedRAMP Assessment Findings

These findings recur in FedRAMP assessments and in agency SSP reviews of inherited controls:

| Finding | Typical Cause | Remediation |
|---|---|---|
| **Access management gaps** | Shared accounts; no MFA for privileged users; excessive permissions; orphaned accounts | Implement MFA; enforce least privilege; automate account review quarterly |
| **Patch management failures** | Scan results show vulnerabilities beyond remediation windows; no patch SLA | Automate patching; track patch compliance in ConMon dashboard; prioritize Critical/High |
| **Logging completeness gaps** | Not all required log types enabled; log retention below 1 year; no centralized SIEM | Enable all required log sources; configure centralized log aggregation; set 1-year minimum retention |
| **SSP accuracy issues** | SSP does not reflect actual implementation; stale diagrams; missing services in boundary | Quarterly SSP accuracy review; update with every significant change |
| **POA&M management** | Findings with past-due dates and no updates; no evidence of active remediation | Monthly POA&M review; assign owners; document actual progress |
| **Significant changes not reported** | New features deployed without notifying FedRAMP PMO | Implement change management gate requiring FedRAMP significance review before deployment |
| **Vendor dependency gaps** | Subservice organizations not assessed; supply chain risk not documented | Enumerate all subservice organizations; obtain their compliance documentation |

---

## FedRAMP Rev 5 Baselines

FedRAMP released updated baselines aligned to **NIST SP 800-53 Revision 5** (Rev 5 baselines). Key changes from the Rev 4-era baselines:

- New control families from SP 800-53 Rev 5 are incorporated: Supply Chain Risk Management (SR), Privacy (PT)
- Updated control parameters reflecting Rev 5 enhancements
- Increased emphasis on supply chain security, software provenance, and zero trust alignment
- Stronger requirements around insider threat programs
- Updated parameter values for several existing controls (particularly AU logging, IR response times, CM configuration management)

CSPs that authorized under Rev 4 baselines are subject to transition timelines published by the FedRAMP PMO. New authorizations use Rev 5 baselines. **ISSOs leveraging existing authorizations should verify whether the CSP has transitioned to Rev 5** and whether the gap affects any controls relevant to your system.

---

## BLACKSITE Platform Mappings

The following table maps BLACKSITE platform features to FedRAMP program requirements.

| FedRAMP Requirement | BLACKSITE Feature | Evidence Path / Usage |
|---|---|---|
| Inherited control documentation in SSP | **System control table** | For each control: set implementation status to "Inherited" or "Hybrid"; note CSP name and FedRAMP authorization ID in implementation narrative |
| Vendor FedRAMP authorization tracking | **Vendor Records** | `/vendors/` — create a vendor record for each CSP; include FedRAMP Marketplace ID, impact level, authorization date, last ConMon date |
| CSP finding remediation | **POA&M module** | Open findings from CSP-leveraged service assessments → POAM items tagged with CSP name; track agency-responsible remediation |
| Interconnection dependencies on CSP | **Interconnection Records** | Document API connections and data flows to/from FedRAMP-authorized services; note inherited boundary |
| Annual 3PAO assessment evidence | **ATO document package** | Upload CSP's annual SAR as supporting document; reference in SSP inherited control narrative |
| ConMon monthly deliverable review | **Daily Logbook** | ISSO rotation includes tracking CSP ConMon deliverable receipt; log in observations if deliverable is late or findings are elevated |
| Significant change notifications | **System change log / ATO documents** | Upload CSP significant change notices as ATO documents; note any control impact |
| FedRAMP Rev 5 transition tracking | **POAM module** | Open transition gap items as POAM entries; track CSP Rev 5 transition milestone as milestone |

### SSP Inherited Control Entry — Recommended Format

When documenting an inherited control from a FedRAMP-authorized CSP in the BLACKSITE system control table, use this structure in the implementation narrative field:

```
Control Type: Inherited (from [CSP Name])
FedRAMP Authorization ID: [Marketplace authorization ID]
FedRAMP Impact Level: [Low / Moderate / High]
CRM Reference: [CRM version / date]
CSP Implementation Summary: [Brief description of what the CSP implements for this control, drawn from CRM or SSP]
Agency Responsibilities: [Any customer-responsible actions required under this control — or "None; fully CSP-implemented"]
```

This format ensures assessors and auditors can quickly locate the source of the inherited control claim and verify it against the CSP's authorization package.

---

## Key References

- **FedRAMP Program Management Office (PMO)**: managed by GSA; establishes baselines, accredits 3PAOs, manages the Marketplace
- **FedRAMP Marketplace**: public catalog of all FedRAMP-authorized, Ready, and In Process cloud services; primary lookup tool for ISSOs verifying CSP status
- **NIST SP 800-53 Rev 5**: Security and Privacy Controls for Information Systems — the control catalog on which FedRAMP baselines are built
- **NIST SP 800-37 Rev 2**: Risk Management Framework — the authorization process that both FISMA and FedRAMP follow
- **FIPS 199**: Standards for Security Categorization — determines Low/Moderate/High impact level for the cloud service
- **FIPS 200**: Minimum Security Requirements — establishes minimum control baselines by impact level
- **OMB Memorandum M-23-22**: Updated FedRAMP policy memorandum establishing requirements for agency cloud service authorization
- **OMB Circular A-130**: Managing Information as a Strategic Resource — policy basis for FedRAMP mandate
- **FedRAMP Authorization Act**: codified FedRAMP into law (FY2023 NDAA), formalizing the "authorize once, use many" model
- **A2LA FedRAMP 3PAO Accreditation Program**: American Association for Laboratory Accreditation — accredits 3PAOs; current list maintained on FedRAMP website
- **NIST SP 800-171**: Protecting Controlled Unclassified Information — relevant for CSPs handling CUI; often paired with FedRAMP for DoD cloud use cases
- **CMMC (Cybersecurity Maturity Model Certification)**: DoD-specific cloud and contractor framework that complements FedRAMP for defense industrial base
