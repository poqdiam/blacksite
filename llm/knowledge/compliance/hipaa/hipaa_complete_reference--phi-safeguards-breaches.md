# HIPAA Complete Reference: PHI, Safeguards, and Breach Notification

**Health Insurance Portability and Accountability Act of 1996 (Pub. L. 104-191)**
**Primary Implementing Regulation:** 45 CFR Parts 160, 162, and 164
**Enforcing Agency:** HHS Office for Civil Rights (OCR) for Privacy/Security/Breach; CMS for Transactions/Code Sets

---

## Table of Contents

1. [HIPAA Overview and Structure](#1-hipaa-overview-and-structure)
2. [Covered Entities and Business Associates](#2-covered-entities-and-business-associates)
3. [Protected Health Information (PHI)](#3-protected-health-information-phi)
4. [PHI De-Identification Methods](#4-phi-de-identification-methods)
5. [Privacy Rule (45 CFR Part 164 Subpart E)](#5-privacy-rule-45-cfr-part-164-subpart-e)
6. [Security Rule (45 CFR Part 164 Subpart C)](#6-security-rule-45-cfr-part-164-subpart-c)
7. [Administrative Safeguards (§164.308)](#7-administrative-safeguards-16430)
8. [Physical Safeguards (§164.310)](#8-physical-safeguards-164310)
9. [Technical Safeguards (§164.312)](#9-technical-safeguards-164312)
10. [Required vs Addressable Distinction](#10-required-vs-addressable-distinction)
11. [Breach Notification Rule (45 CFR Part 164 Subpart D)](#11-breach-notification-rule-45-cfr-part-164-subpart-d)
12. [Enforcement Rule (45 CFR Part 160 Subpart D)](#12-enforcement-rule-45-cfr-part-160-subpart-d)
13. [Penalty Tiers](#13-penalty-tiers)
14. [HITECH Act (2009) Additions](#14-hitech-act-2009-additions)
15. [State Law Preemption](#15-state-law-preemption)
16. [HIPAA and FedRAMP for Federal Health Systems](#16-hipaa-and-fedramp-for-federal-health-systems)
17. [HIPAA in BLACKSITE Context](#17-hipaa-in-blacksite-context)
18. [Quick Reference Tables](#18-quick-reference-tables)

---

## 1. HIPAA Overview and Structure

### 1.1 Legislative History

| Year | Event |
|---|---|
| 1996 | HIPAA enacted (Pub. L. 104-191) — primarily aimed at portability of health insurance coverage |
| 2000 | Privacy Rule (45 CFR Part 164 Subpart E) finalized |
| 2003 | Security Rule (45 CFR Part 164 Subpart C) finalized |
| 2006 | Enforcement Rule finalized |
| 2009 | HITECH Act (Health Information Technology for Economic and Clinical Health Act) enacted as part of ARRA — significantly strengthened HIPAA |
| 2013 | Omnibus Rule — incorporated HITECH modifications; extended BA liability; strengthened breach notification |
| 2021 | HIPAA Safe Harbor (21st Century Cures Act) — encourages cybersecurity-conscious CEs |

### 1.2 Rule Structure

| Rule | CFR Location | Primary Subject |
|---|---|---|
| Privacy Rule | 45 CFR § 164.500–§164.534 | Use and disclosure of PHI; patient rights |
| Security Rule | 45 CFR § 164.302–§164.318 | Electronic PHI (ePHI) safeguards |
| Breach Notification Rule | 45 CFR § 164.400–§164.414 | Notification requirements following breaches |
| Enforcement Rule | 45 CFR Part 160, Subpart D | Civil money penalties; investigations |
| Transactions and Code Sets Rule | 45 CFR Part 162 | Electronic transaction standards (not covered here in depth) |
| Unique Identifiers Rule | 45 CFR Part 162 | NPI, EIN standards |

### 1.3 Regulatory Framework Interaction

```
HIPAA (1996)
  ↓
Privacy Rule (2000/2003) — governs PHI use/disclosure
Security Rule (2003) — governs ePHI security
  ↓
HITECH Act (2009) — extends to BAs; strengthens penalties; mandates breach notification
  ↓
Omnibus Rule (2013) — incorporates HITECH; strengthens BA liability; revises breach standard
  ↓
21st Century Cures / Information Blocking Rule (2016/2020) — information access and anti-blocking
```

---

## 2. Covered Entities and Business Associates

### 2.1 Covered Entities (CEs)

Three types of covered entities are directly subject to HIPAA:

| Type | Definition | Examples |
|---|---|---|
| Health Plans | Individual or group plans providing or paying for medical care | Health insurance companies, HMOs, employer group health plans, Medicare, Medicaid, Medicare Advantage |
| Health Care Clearinghouses | Entities that process nonstandard health information into standard formats | Billing services, community health management information systems, repricing companies |
| Health Care Providers | Providers who transmit health information electronically in connection with covered transactions | Hospitals, physicians, clinics, psychologists, dentists, chiropractors, nursing homes, pharmacies |

**"Covered transaction" trigger for providers:** A health care provider becomes a CE only if it conducts covered electronic transactions (e.g., claims submission). A provider who only accepts cash and submits no electronic claims is technically not a CE, though this is increasingly rare.

### 2.2 Business Associates (BAs)

A Business Associate is a person or entity that performs certain functions or activities for or on behalf of a covered entity that involve the use or disclosure of PHI.

**BA functions include:**
- Claims processing or administration
- Data analysis, processing, or administration
- Utilisation review
- Quality assurance
- Patient safety activities
- Billing
- Benefits management
- Practice management
- Repricing
- Any other function where PHI is used or disclosed

**Key examples of BAs:**
- Cloud service providers storing ePHI (even if encrypted)
- EHR vendors
- Medical billing companies
- Lawyers who need access to PHI
- IT companies managing systems with PHI access
- Transcription services
- Accountants reviewing financial records with PHI
- Data analytics firms processing health data

**Not BAs:** Employees of the CE; members of the CE's workforce; conduits (e.g., postal service) that merely transmit PHI without access to it; individuals/entities who only use de-identified data.

### 2.3 Business Associate Agreements (BAAs)

Before sharing PHI with a BA, a CE must enter a BAA. The Omnibus Rule (2013) extended direct HIPAA compliance obligations to BAs even without a BAA.

**Required BAA provisions (§164.504(e)(2)):**

| Provision | Description |
|---|---|
| Permitted uses/disclosures | Specify and limit how BA may use/disclose PHI |
| BA obligations | Use appropriate safeguards; report breaches/unauthorized uses |
| Sub-BA requirements | Ensure sub-BAs agree to same restrictions |
| Return/destruction | Return or destroy PHI at end of contract |
| Government access | Allow HHS access for compliance investigations |
| Prohibition on sale | BA cannot sell PHI for its own purposes |
| Minimum necessary | Use only minimum necessary PHI |
| Individual rights | Support CE's obligations to respond to individual rights requests |

**Sub-Business Associates:** A BA that engages a subcontractor to perform functions involving PHI must enter a BAA with that subcontractor (the subcontractor becomes a sub-BA with direct HIPAA obligations).

### 2.4 Hybrid Entities

A legal entity that is both a CE and performs non-CE activities. Such an entity may designate which components are the "health care component" subject to HIPAA. The non-HIPAA components must be firewalled.

---

## 3. Protected Health Information (PHI)

### 3.1 Definition

PHI is individually identifiable health information that is:
- Created, received, maintained, or transmitted by a covered entity or BA
- Relates to the past, present, or future physical or mental health or condition of an individual; the provision of health care to an individual; or the past, present, or future payment for the provision of health care to an individual
- Identifies the individual or there is a reasonable basis to believe information can be used to identify the individual

**ePHI:** PHI that is created, received, maintained, or transmitted in electronic form. Subject to Security Rule in addition to Privacy Rule.

**Not PHI:**
- Education records under FERPA
- Employment records held by CE in its role as employer
- De-identified health information (§164.514(a))
- Records of persons deceased more than 50 years

### 3.2 The 18 PHI Identifiers (§164.514(b))

Safe Harbor de-identification requires removal of all 18 identifiers:

| # | Identifier | Description |
|---|---|---|
| 1 | Names | All names (first, last, middle, prefixes, suffixes) |
| 2 | Geographic subdivisions | All geographic data smaller than state level; zip code first 3 digits if population ≤20,000; street address, city, county, precinct |
| 3 | Dates | All dates except year — birth dates, admission dates, discharge dates, death dates; dates directly related to individual; ages over 89 (aggregate to 90+) |
| 4 | Phone numbers | All telephone numbers |
| 5 | Fax numbers | All fax numbers |
| 6 | Email addresses | All electronic mail addresses |
| 7 | Social Security numbers | All SSNs |
| 8 | Medical record numbers | All medical record numbers |
| 9 | Health plan beneficiary numbers | All health plan beneficiary numbers |
| 10 | Account numbers | All account numbers |
| 11 | Certificate/license numbers | All certificate and license numbers |
| 12 | Vehicle identifiers | Vehicle identifiers and serial numbers, including license plates |
| 13 | Device identifiers | Device identifiers and serial numbers |
| 14 | Web URLs | All web universal resource locators |
| 15 | IP addresses | All Internet Protocol address numbers |
| 16 | Biometric identifiers | Finger and voice prints |
| 17 | Full-face photographs | Full-face photographs and comparable images |
| 18 | Any other unique identifier | Any other unique identifying number, characteristic, or code |

### 3.3 PHI Categories for Risk Stratification

| Category | Sensitivity Level | Examples |
|---|---|---|
| Mental/behavioral health | Highest | Psychiatric records, substance abuse (42 CFR Part 2) |
| HIV/AIDS status | Highest | HIV test results, AIDS diagnosis |
| Genetic information | Very High | GINA-protected; genetic tests/disorders |
| Reproductive health | Very High | Abortion, fertility treatment records |
| Substance use disorder | Very High | Additional protections under 42 CFR Part 2 |
| Financial/payment | High | Insurance info, billing records |
| Standard clinical | Moderate | Diagnoses, medications, lab results |
| Demographic/contact | Lower (but still PHI) | Name + address + DOB |

---

## 4. PHI De-Identification Methods

### 4.1 Method 1: Safe Harbor (§164.514(b)(1))

De-identification is achieved by removing **all 18 identifiers** listed above AND the covered entity has **no actual knowledge** that the remaining information could be used alone or in combination to identify the individual.

**Practical steps for Safe Harbor compliance:**
1. Remove all 18 identifiers
2. Truncate zip codes: reduce to first 3 digits if the geographic unit contains >20,000 people (per Census); otherwise suppress entirely
3. Reduce ages: report as "90 or over" for individuals aged 90+
4. Suppress date elements: use only year; or if date is necessary, use shifted dates consistently
5. Document the de-identification process and all decisions
6. Implement policies preventing re-identification
7. Contractually restrict recipients from re-identifying

**Residual identifier:** Even after Safe Harbor, a "code" may be retained if it is not derived from PHI and cannot be translated back to identify the individual; the CE does not use/disclose the code with any other information that could identify; the CE does not disclose the mechanism for re-identification.

### 4.2 Method 2: Expert Determination (§164.514(b)(1)(i))

A person with appropriate knowledge of generally accepted statistical and scientific principles applies methods to verify that the risk of identifying the individual is very small.

**Expert requirements:**
- Expert knowledge of privacy-preserving technologies
- Knowledge of statistical methods for assessing re-identification risk
- Must document analysis supporting the "very small" risk determination

**Common methodologies used:**
- K-anonymity (each record matches at least k-1 others on quasi-identifiers)
- L-diversity (each equivalence class has at least l well-represented sensitive values)
- T-closeness (distribution of sensitive attribute in equivalence class close to overall distribution)
- Differential privacy (mathematical guarantee of privacy budget ε)
- Data synthesis (replace real data with statistically equivalent synthetic data)

### 4.3 Limited Data Set (§164.514(e))

A limited data set is PHI with direct identifiers removed (though it may include indirect identifiers such as city, state, zip, dates). Limited data sets may only be shared for:
- Research
- Public health
- Health care operations

Under a **data use agreement (DUA)** that prohibits re-identification and restricts use.

**Direct identifiers removed in limited data set (16 of 18 — zip codes and dates retained):**
Names, postal addresses (street), telephone, fax, email, SSN, medical record numbers, health plan beneficiary numbers, account numbers, certificate/license numbers, VINs, device identifiers, URLs, IP addresses, biometric identifiers, full-face photographs.

---

## 5. Privacy Rule (45 CFR Part 164 Subpart E)

### 5.1 General Principles

The Privacy Rule governs the use and disclosure of PHI by CEs and BAs. It establishes:
- Permitted and required uses/disclosures
- Minimum necessary standard
- Individual rights regarding PHI
- Administrative requirements

### 5.2 Permitted Uses and Disclosures (§164.502)

| Category | Authorization Required? | Description |
|---|---|---|
| Treatment, Payment, Operations (TPO) | No | Core operations; disclosure between providers for treatment |
| Required by law | No | Court orders, subpoenas, other legal requirements |
| Public health activities | No | Disease reporting, FDA reporting, child abuse |
| Victims of abuse/neglect | No | With certain conditions |
| Health oversight | No | Audits, inspections, investigations by oversight agencies |
| Judicial/administrative proceedings | No | With court order or subpoena + satisfactory assurances |
| Law enforcement | No | With court order, warrant, or for victims, suspects, deaths |
| Decedents | No | Funeral directors, coroners |
| Organ/tissue/eye donation | No | To procurement organizations |
| Research | No (with waiver/IRB approval) or Yes | Requires IRB waiver of authorization, limited data set DUA, or full authorization |
| Serious threat to health/safety | No | Consistent with applicable law and professional standards |
| National security/intelligence | No | For authorized national security activities |
| Correctional institutions | No | For provision of health care to inmates |
| Workers' compensation | No | As authorized by state law |
| Incidental uses/disclosures | No | Cannot be reasonably prevented; limited in nature |
| **All other uses/disclosures** | **Yes** | Authorization required |

### 5.3 Minimum Necessary Standard (§164.502(b))

When using/disclosing PHI or requesting PHI from another CE, a CE must make reasonable efforts to limit PHI to the **minimum necessary** to accomplish the intended purpose.

**Exceptions — minimum necessary does NOT apply to:**
- Disclosures to/requests by healthcare providers for treatment
- Uses/disclosures made pursuant to valid authorization
- Disclosures to HHS for compliance purposes
- Uses/disclosures required by law
- Uses/disclosures required for compliance with Privacy/Security/Breach Rules

**Implementing policies:**
- Identify persons/classes who need access and types of PHI
- Implement access controls limiting to minimum necessary
- Create standard protocols for routine disclosures

### 5.4 Required Disclosures (§164.502(a)(2))

A CE **must** disclose PHI when:
1. The individual requests access to their own PHI (§164.524)
2. HHS requires access for compliance and enforcement purposes (§164.502(a)(2)(ii))

### 5.5 Individual Rights Under the Privacy Rule

| Right | Section | Description |
|---|---|---|
| Access | §164.524 | Right to inspect and copy PHI maintained in a designated record set; CE has 30 days (extendable 30 more) |
| Amendment | §164.526 | Right to request amendment; CE may deny with justification; individual may submit statement of disagreement |
| Accounting of Disclosures | §164.528 | Right to list of disclosures for past 6 years (not for TPO); ePHI accounting requirements (HITECH) |
| Restriction | §164.522(a) | Right to request restrictions; CE need not agree except — must agree to restrict disclosure to health plan if individual pays out-of-pocket in full |
| Confidential Communications | §164.522(b) | Right to request PHI communicated by alternative means/location |
| Notice of Privacy Practices | §164.520 | Right to receive NPP describing CE's privacy practices |
| Complaint | §164.530(d) | Right to file complaints with CE and with HHS |

### 5.6 Notice of Privacy Practices (NPP) (§164.520)

CEs must provide an NPP that includes:
- How PHI may be used/disclosed
- Individual's rights and how to exercise them
- CE's duties to protect PHI
- How to lodge complaints
- Effective date
- Header: "This notice describes how medical information about you may be used and disclosed and how you can get access to this information. Please review it carefully."

**Distribution:** Direct treatment providers must make good-faith effort to obtain written acknowledgement of NPP receipt at first service delivery.

### 5.7 Authorization Requirements (§164.508)

Authorizations must be written and must contain:
1. Description of PHI to be used/disclosed
2. Name/class of persons authorized to use/disclose
3. Name/class of persons to whom disclosure may be made
4. Description of purpose of use/disclosure
5. Expiration date or event
6. Signature of individual and date
7. Right to revoke statement and instructions
8. Statement that CE may not condition treatment/payment on authorization (with exceptions)
9. Statement that disclosed information may be re-disclosed by recipient

**Invalid authorizations include:** Combined with another document; conditioned improperly; not complete; expired; not signed; revoked.

---

## 6. Security Rule (45 CFR Part 164 Subpart C)

### 6.1 Overview

The Security Rule establishes national standards for protecting **electronic PHI (ePHI)**. It applies to:
- Covered entities
- Business associates (extended by HITECH and Omnibus Rule 2013)

The Security Rule is **technology-neutral** — it specifies what must be protected and what types of safeguards are required, but not the specific technologies to use.

### 6.2 General Security Requirements (§164.306)

A CE/BA must:
- Ensure the **confidentiality, integrity, and availability** of all ePHI they create, receive, maintain, or transmit
- Identify and protect against reasonably anticipated threats to the security or integrity of ePHI
- Protect against reasonably anticipated impermissible uses or disclosures
- Ensure workforce compliance

### 6.3 Safeguard Categories

| Category | CFR Section | Focus |
|---|---|---|
| Administrative Safeguards | §164.308 | Policies, procedures, and management decisions |
| Physical Safeguards | §164.310 | Physical measures protecting ePHI systems |
| Technical Safeguards | §164.312 | Technology protecting ePHI access and transmission |
| Organizational Requirements | §164.314 | BAA requirements; group health plan requirements |
| Policies, Procedures, Documentation | §164.316 | Written policies; document retention (6 years) |

---

## 7. Administrative Safeguards (§164.308)

### 7.1 Risk Analysis (§164.308(a)(1)(ii)(A)) — REQUIRED

The foundational safeguard. Conduct an **accurate and thorough assessment** of potential risks and vulnerabilities to the confidentiality, integrity, and availability of ePHI.

**OCR-expected risk analysis elements:**
1. Scope — all ePHI created, received, maintained, or transmitted
2. Data collection — identify where ePHI is stored, received, maintained, transmitted
3. Identify and document potential threats and vulnerabilities
4. Assess current security measures
5. Determine likelihood of threat occurrence
6. Determine potential impact of threat occurrence
7. Determine level of risk
8. Finalize documentation
9. Periodic review and update

### 7.2 Risk Management (§164.308(a)(1)(ii)(B)) — REQUIRED

Implement security measures sufficient to reduce risks to a reasonable and appropriate level.

### 7.3 Sanction Policy (§164.308(a)(1)(ii)(C)) — REQUIRED

Apply appropriate sanctions against workforce members who fail to comply with security policies and procedures.

### 7.4 Information System Activity Review (§164.308(a)(1)(ii)(D)) — REQUIRED

Regularly review records of information system activity such as audit logs, access reports, and security incident tracking reports.

### 7.5 Assigned Security Responsibility (§164.308(a)(2)) — REQUIRED

Identify the security official responsible for developing and implementing required policies and procedures.

### 7.6 Workforce Security (§164.308(a)(3))

| Implementation Spec | R/A | Description |
|---|---|---|
| Authorization and/or Supervision | Addressable | Implement procedures for authorization/supervision of workforce access to ePHI |
| Workforce Clearance | Addressable | Determine that access of workforce members is appropriate |
| Termination Procedures | Addressable | Implement procedures for terminating access upon employment end |

### 7.7 Information Access Management (§164.308(a)(4))

| Implementation Spec | R/A | Description |
|---|---|---|
| Isolating Health Care Clearinghouse | Required | Policies to protect ePHI from larger organization (if applicable) |
| Access Authorization | Addressable | Implement policies for granting access to ePHI |
| Access Establishment and Modification | Addressable | Implement policies for establishing, documenting, reviewing, modifying access |

### 7.8 Security Awareness and Training (§164.308(a)(5))

| Implementation Spec | R/A | Description |
|---|---|---|
| Security Reminders | Addressable | Periodic security updates |
| Protection from Malicious Software | Addressable | Procedures for guarding against, detecting, and reporting malicious software |
| Log-in Monitoring | Addressable | Monitor log-in attempts and report discrepancies |
| Password Management | Addressable | Create, change, and safeguard passwords |

### 7.9 Security Incident Procedures (§164.308(a)(6))

| Implementation Spec | R/A | Description |
|---|---|---|
| Response and Reporting | Required | Identify, respond to, mitigate, document security incidents; report to appropriate person |

### 7.10 Contingency Plan (§164.308(a)(7))

| Implementation Spec | R/A | Description |
|---|---|---|
| Data Backup Plan | Required | Create and maintain retrievable exact copies of ePHI |
| Disaster Recovery Plan | Required | Restore lost data in event of emergency |
| Emergency Mode Operation Plan | Required | Continue critical business processes while protecting ePHI during emergency |
| Testing and Revision Procedures | Addressable | Implement procedures for periodic testing/revision of contingency plans |
| Applications and Data Criticality Analysis | Addressable | Assess relative criticality of applications and data |

### 7.11 Evaluation (§164.308(a)(8)) — REQUIRED

Perform periodic technical and nontechnical evaluation of security standards implementation in response to environmental or operational changes.

### 7.12 BA and Other Arrangements (§164.308(b))

Written contracts with BAs must satisfy §164.314(a) requirements. Group health plan fiduciary must ensure plan documents include BA protections.

---

## 8. Physical Safeguards (§164.310)

### 8.1 Facility Access Controls (§164.310(a)(1))

| Implementation Spec | R/A | Description |
|---|---|---|
| Contingency Operations | Addressable | Allow facility access to restore lost data under disaster recovery plan |
| Facility Security Plan | Addressable | Safeguard facility and equipment from unauthorized access, tampering, theft |
| Access Control and Validation Procedures | Addressable | Control and validate access to facilities based on role or function, including visitor control; testing of programs |
| Maintenance Records | Addressable | Document repairs/modifications to physical security (door locks, walls, etc.) |

### 8.2 Workstation Use (§164.310(b)) — REQUIRED

Implement policies specifying proper functions performed and manner in which those functions are performed on workstations with access to ePHI.

### 8.3 Workstation Security (§164.310(c)) — REQUIRED

Implement physical safeguards for all workstations with ePHI access to restrict access to authorised users only.

**Examples:** Screen locks, cable locks, positioning screens away from windows, privacy screens, locked rooms.

### 8.4 Device and Media Controls (§164.310(d)(1))

| Implementation Spec | R/A | Description |
|---|---|---|
| Disposal | Required | Implement policies for final disposition of ePHI and hardware/electronic media |
| Media Re-use | Required | Implement procedures for removal of ePHI from electronic media before re-use |
| Accountability | Addressable | Maintain record of movements of hardware/media containing ePHI and person responsible |
| Data Backup and Storage | Addressable | Create retrievable exact copy of ePHI before movement of equipment |

**Disposal methods for ePHI media:**
- HDD/SSD: NIST 800-88 compliant clearing, purging (degaussing), or destruction (shredding)
- Mobile devices: Factory reset + encryption (if encrypted first)
- Paper records with PHI: Cross-cut shredding or burning
- Never: Trash/recycling, resale without proper sanitization

---

## 9. Technical Safeguards (§164.312)

### 9.1 Access Control (§164.312(a)(1))

| Implementation Spec | R/A | Description |
|---|---|---|
| Unique User Identification | Required | Assign unique name/number to identify and track user identity |
| Emergency Access Procedure | Required | Establish procedures for obtaining ePHI during emergency when normal controls unavailable |
| Automatic Logoff | Addressable | Electronic procedures that terminate an electronic session after predetermined inactivity period |
| Encryption and Decryption | Addressable | Implement mechanism to encrypt and decrypt ePHI |

### 9.2 Audit Controls (§164.312(b)) — REQUIRED

Implement hardware, software, and/or procedural mechanisms that record and examine activity in information systems containing or using ePHI.

**Audit log elements (best practice):**
- User identification
- Date and time of access
- Type of action (create, read, update, delete)
- Resource accessed
- Success or failure of access attempt

### 9.3 Integrity (§164.312(c)(1))

| Implementation Spec | R/A | Description |
|---|---|---|
| Mechanism to Authenticate ePHI | Addressable | Implement electronic mechanisms to corroborate that ePHI has not been altered or destroyed in an unauthorized manner |

**Methods:** Checksums, hash values, digital signatures, error-correcting codes, file integrity monitoring.

### 9.4 Person or Entity Authentication (§164.312(d)) — REQUIRED

Implement procedures to verify that a person or entity seeking access to ePHI is who they claim to be.

**Authentication methods:**
- Something you know: password, PIN
- Something you have: token, smart card
- Something you are: biometric (fingerprint, retina)
- Multi-factor authentication (MFA): two or more factors (strongly recommended; required for remote access in most guidance)

### 9.5 Transmission Security (§164.312(e)(1))

| Implementation Spec | R/A | Description |
|---|---|---|
| Integrity Controls | Addressable | Implement security measures to ensure ePHI transmitted over electronic communications networks is not improperly modified without detection |
| Encryption | Addressable | Implement mechanism to encrypt ePHI in transit |

**Encryption standard guidance:** HHS recognizes NIST-validated encryption algorithms. FIPS 140-2/140-3 validated modules recommended. TLS 1.2 minimum; TLS 1.3 preferred for transmission.

---

## 10. Required vs Addressable Distinction

### 10.1 What "Required" Means

Implementation specifications marked **Required (R)** must be implemented as stated. There is no flexibility in whether to implement them — only in the specific technology or method used.

### 10.2 What "Addressable" Means

Implementation specifications marked **Addressable (A)** require a CE/BA to:
1. **Assess** whether the specification is reasonable and appropriate given the CE's size, complexity, and capabilities, technical infrastructure, security capability costs, and probability/criticality of potential risks to ePHI
2. **If reasonable and appropriate:** Implement the specification
3. **If not reasonable and appropriate:** Document why, and implement an equivalent alternative measure that achieves the same purpose; OR document why neither the specification nor any alternative is reasonable and appropriate (rare)

**Critical point:** Addressable does NOT mean optional. Failure to implement an addressable specification requires documented justification. OCR enforcement treats unimplemented addressable controls without documentation as violations.

### 10.3 Summary Table — Required vs Addressable

| Section | Implementation Specification | R/A |
|---|---|---|
| §164.308(a)(1) | Risk Analysis | R |
| §164.308(a)(1) | Risk Management | R |
| §164.308(a)(1) | Sanction Policy | R |
| §164.308(a)(1) | Information System Activity Review | R |
| §164.308(a)(2) | Assigned Security Responsibility | R |
| §164.308(a)(3) | Authorization and/or Supervision | A |
| §164.308(a)(3) | Workforce Clearance Procedure | A |
| §164.308(a)(3) | Termination Procedures | A |
| §164.308(a)(4) | Isolating Clearinghouse Function | R |
| §164.308(a)(4) | Access Authorization | A |
| §164.308(a)(4) | Access Establishment and Modification | A |
| §164.308(a)(5) | Security Reminders | A |
| §164.308(a)(5) | Protection from Malicious Software | A |
| §164.308(a)(5) | Log-in Monitoring | A |
| §164.308(a)(5) | Password Management | A |
| §164.308(a)(6) | Response and Reporting | R |
| §164.308(a)(7) | Data Backup Plan | R |
| §164.308(a)(7) | Disaster Recovery Plan | R |
| §164.308(a)(7) | Emergency Mode Operation Plan | R |
| §164.308(a)(7) | Testing and Revision Procedures | A |
| §164.308(a)(7) | Applications and Data Criticality Analysis | A |
| §164.308(a)(8) | Evaluation | R |
| §164.310(a) | Contingency Operations | A |
| §164.310(a) | Facility Security Plan | A |
| §164.310(a) | Access Control and Validation Procedures | A |
| §164.310(a) | Maintenance Records | A |
| §164.310(b) | Workstation Use | R |
| §164.310(c) | Workstation Security | R |
| §164.310(d) | Disposal | R |
| §164.310(d) | Media Re-use | R |
| §164.310(d) | Accountability | A |
| §164.310(d) | Data Backup and Storage | A |
| §164.312(a) | Unique User Identification | R |
| §164.312(a) | Emergency Access Procedure | R |
| §164.312(a) | Automatic Logoff | A |
| §164.312(a) | Encryption and Decryption | A |
| §164.312(b) | Audit Controls | R |
| §164.312(c) | Mechanism to Authenticate ePHI | A |
| §164.312(d) | Person or Entity Authentication | R |
| §164.312(e) | Integrity Controls | A |
| §164.312(e) | Encryption (Transmission) | A |

---

## 11. Breach Notification Rule (45 CFR Part 164 Subpart D)

### 11.1 Definition of Breach (§164.402)

A breach is the acquisition, access, use, or disclosure of PHI in a manner not permitted under the Privacy Rule that **compromises the security or privacy of the PHI**.

**Presumption:** An impermissible use or disclosure is presumed a breach unless the CE or BA demonstrates through a **Risk Assessment** that there is a **low probability** that PHI has been compromised.

### 11.2 Four-Factor Risk Assessment (§164.402(2))

To rebut the presumption of breach, all four factors must be assessed:

| Factor | Description |
|---|---|
| 1. Nature and extent of PHI | Types of identifiers and likelihood of re-identification |
| 2. Who used or received PHI | Was it a person obligated to protect PHI? Was PHI actually accessed/viewed? |
| 3. Whether PHI was actually acquired or viewed | Demonstrated that PHI was not actually accessed (e.g., server logs showing no access) |
| 4. Extent to which risk has been mitigated | Was PHI returned without further use/disclosure? Was satisfactory assurance obtained? |

If all four factors support low probability, no breach notification is required. If any factor is uncertain or unfavorable, notification is required.

### 11.3 Exceptions — Not a Breach (§164.402(1))

| Exception | Description |
|---|---|
| Unintentional workforce use | Unintentional access by a workforce member acting in good faith and within authority, with no further use/disclosure |
| Inadvertent disclosure between authorized persons | Inadvertent disclosure from one person authorized to access ePHI at the same CE/BA to another such person, with no further use/disclosure |
| Recipient unable to retain | CE/BA has good faith belief that the unauthorized recipient could not have retained the PHI |

### 11.4 Notification to Individuals (§164.404)

**Timeline:** Without unreasonable delay and no later than **60 calendar days** after discovery.

**Content of notice:**
- Brief description of what happened (date of breach and discovery date)
- Description of types of unsecured PHI involved (name, SSN, diagnosis, etc.)
- Steps individuals should take to protect themselves
- Brief description of CE's investigation, mitigation, and prevention steps
- Contact information for questions

**Methods:** Written notification by first-class mail to last known address; email if individual agrees electronically; telephone if urgent.

**Substitute notice:** If contact information is insufficient for <10 individuals — alternative written notice or telephone. For ≥10 individuals — notice on CE's website or media notice in relevant geographic area.

### 11.5 Notification to HHS (§164.408)

**Breaches affecting 500+ individuals:** Notify HHS simultaneously with individual notification (within 60 days). HHS posts these on the "Wall of Shame" (breach portal).

**Breaches affecting fewer than 500 individuals:** Log annually; submit to HHS no later than **60 days after the end of the calendar year**.

### 11.6 Notification to Media (§164.406)

For breaches affecting **500 or more residents** of a state or jurisdiction: notify prominent media outlets serving that state or jurisdiction without unreasonable delay and no later than 60 calendar days after discovery.

### 11.7 BA Notification to CE (§164.410)

A BA must notify the covered entity without unreasonable delay and no later than **60 calendar days** after discovering a breach. The CE then has its own 60-day clock.

**Best practice:** BAAs should specify a shorter notice period (e.g., 5, 10, or 30 days) to allow the CE adequate time to meet its own obligations.

### 11.8 Unsecured PHI

Breach notification only applies to **unsecured PHI** — PHI that has not been rendered unusable, unreadable, or indecipherable through:
- **Encryption:** Per NIST Special Publication 800-111 (for data at rest) or 800-52 (for data in transit) — if decryption key/tool not breached
- **Destruction:** Paper records (shredded); ePHI on hardware/media (purged/destroyed per NIST 800-88)

If PHI is properly encrypted and the breach does not expose the encryption key, no breach notification is required.

---

## 12. Enforcement Rule (45 CFR Part 160 Subpart D)

### 12.1 OCR Authority

The HHS Office for Civil Rights (OCR) has authority to:
- Investigate complaints
- Conduct compliance reviews (proactive investigations)
- Obtain civil money penalties (CMPs)
- Coordinate with DOJ for criminal referrals

### 12.2 Investigation Process

1. **Complaint received or compliance review initiated**
2. **OCR evaluates** jurisdiction and merit
3. **OCR notifies** CE of complaint (if from individual)
4. **CE submits** response/documentation
5. **OCR reviews** — may request additional information, conduct interviews, on-site visits
6. **Resolution:**
   - **Technical assistance:** No violation found or minor issue
   - **Informal resolution:** CE corrects violation; OCR closes
   - **Resolution agreement:** CE enters corrective action plan + payment
   - **CMPs:** If voluntary compliance not achieved or willful neglect

### 12.3 Statute of Limitations

OCR may impose CMPs for violations occurring no later than **6 years** prior to the date of violation discovery.

---

## 13. Penalty Tiers

### 13.1 Civil Money Penalty Tiers (42 U.S.C. §1320d-5)

HITECH established four tiers based on culpability. The Omnibus Rule codified these tiers:

| Tier | Culpability | Per Violation Min | Per Violation Max | Annual Cap (same type) |
|---|---|---|---|---|
| Tier 1 | Did not know (reasonable due diligence) | $100 | $50,000 | $1,500,000 |
| Tier 2 | Reasonable cause (knew or should have known, not willful neglect) | $1,000 | $50,000 | $1,500,000 |
| Tier 3 | Willful neglect, corrected within 30 days | $10,000 | $50,000 | $1,500,000 |
| Tier 4 | Willful neglect, not corrected within 30 days | $50,000 | $50,000 | $1,500,000 |

**Adjusted for inflation:** CMP amounts are adjusted periodically per Federal Civil Penalties Inflation Adjustment Act. Current amounts (2023 adjustments) may differ slightly.

**Per calendar year cap:** $1,500,000 per violation category (type of HIPAA standard violated) per year. Multiple violations of different standards can stack.

### 13.2 Factors Affecting Penalty Amount

- Nature and extent of violation
- Nature and extent of harm resulting
- History of prior compliance
- Financial condition of the entity
- Other matters as justice may require

### 13.3 Corrective Action Plans (CAPs)

Major enforcement actions typically include a multi-year CAP requiring:
- Risk analysis and risk management plan update
- Policies/procedures review and update
- Training program implementation
- Reporting to OCR for 1–3 years
- Regular compliance reports

### 13.4 Criminal Penalties (42 U.S.C. §1320d-6)

| Violation | Fine | Imprisonment |
|---|---|---|
| Obtaining/disclosing PHI | Up to $50,000 | Up to 1 year |
| Under false pretenses | Up to $100,000 | Up to 5 years |
| Commercial advantage, personal gain, or malicious harm | Up to $250,000 | Up to 10 years |

Criminal referrals made to DOJ. CEs, their officers, employees, and others can be prosecuted.

### 13.5 Notable OCR Enforcement Actions

| Organization | Year | Settlement | Root Cause |
|---|---|---|---|
| Advocate Health Care Network | 2016 | $5.55M | Unencrypted laptops stolen; missing BA agreements |
| Memorial Healthcare System | 2017 | $5.5M | Workforce members impermissibly accessed/disclosed PHI |
| Fresenius Medical Care | 2018 | $3.5M | Multiple breaches; no risk analysis; no ePHI protection policies |
| Premera Blue Cross | 2019 | $6.85M | Hacking; risk analysis failures; security vulnerabilities |
| CHSPSC (Community Health Systems) | 2020 | $2.3M | APT hacking; risk analysis/management failures |
| Peach State Health Management | 2023 | $75,000 | Right of access failure (individual) |

---

## 14. HITECH Act (2009) Additions

### 14.1 Overview

The Health Information Technology for Economic and Clinical Health (HITECH) Act was enacted as Title XIII of ARRA (American Recovery and Reinvestment Act of 2009). Key HIPAA-relevant provisions:

### 14.2 Extension to Business Associates

HITECH made BAs **directly liable** for HIPAA Security Rule requirements and breach notification (to CEs). Previously, BAs were only contractually obligated through BAAs. Now OCR can directly investigate and penalize BAs.

### 14.3 Breach Notification

HITECH mandated the Breach Notification Rule (§13402) — codified at 45 CFR Part 164 Subpart D — requiring notification to individuals, HHS, and media as described above.

### 14.4 Strengthened Penalties

HITECH established the four-tier penalty structure, increased maximum penalties, required OCR to impose penalties for willful neglect (previously discretionary), and created the annual per-category cap structure.

### 14.5 Accounting of Disclosures for ePHI

HITECH proposed expanding the right to an accounting of disclosures to include disclosures for treatment, payment, and health care operations when using an EHR (§13405(c)). This provision was proposed in a 2011 NPRM but has never been finalized, leaving the existing accounting rule in effect.

### 14.6 Minimum Necessary

HITECH required HHS to apply the minimum necessary standard to requests for PHI and directed HHS to issue guidance. The standard is currently defined as what is "limited to a 'limited data set'" or, if needed, the minimum necessary to accomplish the intended purpose.

### 14.7 Marketing and Fundraising Restrictions

HITECH tightened restrictions on using PHI for marketing communications — requiring authorization where the CE receives financial remuneration. Fundraising communications must include opt-out.

### 14.8 Sale of PHI

HITECH prohibits the sale of PHI without individual authorization (with limited exceptions).

### 14.9 EHR Incentive Programs (Meaningful Use)

HITECH created Medicare/Medicaid EHR incentive payments (Meaningful Use) — now succeeded by Promoting Interoperability — which tied payments to security risk analysis completion.

### 14.10 HIPAA Safe Harbor for Cybersecurity Practices (2021)

The HITECH Act amendment (Pub. L. 116-321, January 2021) requires HHS to consider whether a CE or BA has implemented "recognized security practices" when:
- Determining the amount of any civil money penalty
- Determining the length of a compliance audit
- Determining the extent of remediation offered in resolution agreements

**Recognized security practices:** NIST Cybersecurity Framework, HITECH-recognized practices, or other programs and practices recognised in government-published guidelines (800-series, etc.). Must be in place for at least the prior 12 months.

---

## 15. State Law Preemption

### 15.1 General Rule (45 CFR §160.203)

HIPAA generally **preempts** state privacy and security laws that are **less protective** of individual privacy. State laws that are **more stringent** (i.e., provide greater privacy protections or individual rights) are **not preempted** — they remain in effect.

### 15.2 Stricter Protections Under State Law

A state law is more stringent if it:
- Provides greater privacy rights to the individual
- Provides a greater degree of limitation on CE's use/disclosure of PHI
- Provides individuals with more access rights
- Imposes a shorter retention period

### 15.3 Notable State Law Overrides

| State | Subject | How More Restrictive Than HIPAA |
|---|---|---|
| California (CMIA/CCPA) | All medical records | CMIA has stricter consent requirements; breach notification |
| Texas | Mental health records, HIV, substance use | More restrictive access and disclosure rules |
| New York | HIV, mental health, substance use, genetics | HIV reporting without consent prohibited; mental health access limits |
| All 50 states | Breach notification | Many states have shorter notification timelines |

### 15.4 State Genetic Information Laws

Many states have genetic privacy laws more protective than HIPAA (e.g., GINA). These are not preempted.

### 15.5 42 CFR Part 2 — Substance Use Disorder Records

Records of substance use disorder treatment programs federally funded under 42 U.S.C. §290dd-2 are protected by 42 CFR Part 2, which is **more restrictive than HIPAA**:
- Requires patient consent for most disclosures (even for treatment purposes)
- Restrictions survive disclosure (recipient cannot re-disclose)
- Applies to any program receiving federal assistance

**Critical intersection:** A federally-funded SUD program must comply with both HIPAA and 42 CFR Part 2; where they conflict, Part 2 prevails.

---

## 16. HIPAA and FedRAMP for Federal Health Systems

### 16.1 Framework Interaction

Federal agencies operating health systems (VA, DoD, IHS, CMS) must comply with both HIPAA and FISMA/FedRAMP when using cloud services.

| Requirement | HIPAA | FedRAMP |
|---|---|---|
| Authority | HHS | OMB/GSA/DHS |
| Applies to | CEs and BAs | Federal agencies; cloud CSPs |
| Risk framework | HIPAA-specific safeguards | NIST RMF / 800-53 |
| Authorization | BAA | ATO (Authority to Operate) |
| Audit period | Continuous compliance | Annual assessment (3-year cycle) |

### 16.2 FedRAMP ATO Does Not Equal HIPAA Compliance

A cloud service provider with a FedRAMP authorization is **not automatically HIPAA compliant**. Reasons:
- FedRAMP assesses against NIST 800-53 — many but not all controls map to HIPAA
- FedRAMP does not audit Privacy Rule compliance
- HIPAA BAA still required separately
- Agency must conduct its own HIPAA risk analysis

### 16.3 NIST 800-53 Controls Mapping to HIPAA Security Rule

| HIPAA Safeguard | Representative NIST 800-53 Controls |
|---|---|
| Risk Analysis (§164.308(a)(1)) | RA-3, RA-5, CA-2 |
| Access Control (§164.312(a)) | AC-1, AC-2, AC-3, AC-6, AC-8 |
| Audit Controls (§164.312(b)) | AU-1 through AU-12 |
| Integrity (§164.312(c)) | SI-7, AU-10 |
| Transmission Security (§164.312(e)) | SC-8, SC-12, SC-13 |
| Person Authentication (§164.312(d)) | IA-2, IA-5, IA-8 |
| Contingency Plan (§164.308(a)(7)) | CP-1 through CP-13 |
| Workforce Training (§164.308(a)(5)) | AT-2, AT-3 |
| Physical Safeguards (§164.310) | PE-1 through PE-20 |
| Incident Response (§164.308(a)(6)) | IR-1 through IR-10 |

### 16.4 DoD Health Systems (DHA / MTFs)

DoD Medical Treatment Facilities (MTFs) operate under:
- **HIPAA** (as covered entities)
- **DoD Instruction 6025.18** (DoD HIPAA implementation)
- **FISMA/NIST RMF** (for information systems)
- **DHA Privacy and Civil Liberties Office** oversight
- **Privacy Act of 1974** (for records of service members and beneficiaries)

---

## 17. HIPAA in BLACKSITE Context

### 17.1 ePHI Flag and System Categorization

Systems processing ePHI in BLACKSITE should be documented with:
- **Boundary documentation:** Whether the system boundary includes ePHI processing
- **Data classification:** PHI elevates confidentiality impact (typically Moderate to High per FIPS 199)
- **BAA tracking:** All third-party processors of ePHI must have BAAs on record as interconnection/vendor artifacts
- **Applicable regulations field:** HIPAA should be listed in system regulation applicability

### 17.2 HIPAA-Specific Controls in System Security Plans

SSP Appendix items for HIPAA-regulated systems:
- Current risk analysis report (§164.308(a)(1))
- Sanctions policy
- Workforce HIPAA training records
- BAA inventory
- Contingency plan (backup, DR, emergency mode)
- Current audit log review process

### 17.3 Access Spot Checks for PHI Systems

BLACKSITE access spot checks should verify:
- Unique user identification (no shared accounts with ePHI access)
- Terminated employee access revoked
- Role-based access aligned with minimum necessary
- External/BA access documented and BAA current
- MFA enforced for remote access to ePHI systems

### 17.4 POA&M Items Common to HIPAA Audits

| Finding | HIPAA Reference | Typical Remediation |
|---|---|---|
| No formal risk analysis | §164.308(a)(1)(ii)(A) | Conduct and document full risk analysis |
| Incomplete BA inventory / missing BAAs | §164.308(b) | Inventory all BAs; execute BAAs |
| No workforce training program | §164.308(a)(5) | Implement annual HIPAA training; document completion |
| Unencrypted ePHI on portable media | §164.312(a)(2)(iv) | Encrypt all portable storage; policy enforcement |
| Audit logs not reviewed | §164.308(a)(1)(ii)(D) | Implement regular log review schedule |
| No sanction policy | §164.308(a)(1)(ii)(C) | Document and enforce sanctions |
| ePHI on personal devices without MDM | §164.310(b)(c) | MDM or BYOD policy prohibiting ePHI |
| Breach not reported within 60 days | §164.404(b) | Review and update incident response procedures |

### 17.5 BLACKSITE Vendor/Interconnection Records for HIPAA

For systems with ePHI:
- Vendor record type: Business Associate
- Required artifact: Signed BAA (PDF upload)
- Interconnection record: Include ePHI data flow indicator
- Data flow record: Document ePHI elements in transit
- Privacy Impact Assessment: Required before system deployment

---

## 18. Quick Reference Tables

### 18.1 HIPAA Applicability Decision Tree

```
Does the entity transmit health information electronically for covered transactions?
  → Yes: Health care provider = Covered Entity
Does the entity provide/pay for medical care (plan) or process health data (clearinghouse)?
  → Yes: Covered Entity
Does the entity perform functions for a CE involving PHI use/disclosure?
  → Yes: Business Associate
Does the entity handle ePHI on behalf of a BA?
  → Yes: Sub-Business Associate (same obligations as BA)
```

### 18.2 Breach Notification Summary

| Who Notified | Timeline | Threshold |
|---|---|---|
| Affected individuals | ≤60 days after discovery | All breaches of unsecured PHI |
| HHS (immediate) | ≤60 days after discovery | 500+ individuals affected |
| HHS (annual log) | ≤60 days after calendar year end | <500 individuals affected |
| Media | ≤60 days after discovery | 500+ residents of state/jurisdiction |
| CE (by BA) | ≤60 days after BA discovery | All breaches |

### 18.3 PHI Permitted Disclosure Summary

| Purpose | Authorization Needed |
|---|---|
| Treatment (providing, coordinating, managing) | No |
| Payment (billing, claims, collections) | No |
| Health care operations (QA, training, audits) | No |
| Public health activities | No |
| Health oversight (audits, investigations) | No |
| Research (with IRB waiver or limited data set) | No (with conditions) |
| Legal proceedings (with court order) | No (with conditions) |
| Law enforcement (with legal process) | No (with conditions) |
| Marketing (if financial remuneration involved) | Yes |
| Sale of PHI | Yes |
| Psychotherapy notes | Yes |
| All other uses | Yes |

### 18.4 De-Identification Comparison

| Method | PHI Removed | Validation | Result |
|---|---|---|---|
| Safe Harbor | All 18 identifiers | CE attests no actual knowledge of re-identification | De-identified data |
| Expert Determination | Risk-based | Qualified expert certifies very small re-identification risk | De-identified data |
| Limited Data Set | 16 of 18 identifiers (zip codes, dates retained) | Data use agreement required | Limited data set (not fully de-identified) |
| Pseudonymisation | Direct identifiers replaced with codes | Code key maintained separately | Still PHI (pseudonymous) |

---

*Document Version: 1.0*
*Regulatory Reference: 45 CFR Parts 160, 162, 164; HITECH Act (42 U.S.C. § 17901 et seq.)*
*OCR Guidance and Enforcement current through 2025*
*For authoritative interpretation, consult OCR guidance, HHS.gov, and applicable legal counsel*
