# Data Processing Addendum (DPA)

> **IMPORTANT — LEGAL REVIEW REQUIRED**
> This is a template document. It must be reviewed and approved by qualified legal
> counsel before execution. Do not execute this document without legal review.
> Last updated: 2026-03-09.

---

## DATA PROCESSING ADDENDUM

This Data Processing Addendum ("DPA") is entered into between the parties identified
below and forms part of, and is incorporated into, the applicable service agreement,
subscription agreement, or terms of service ("Agreement") between the parties.

This DPA applies where the Controller uses the BLACKSITE platform to process personal
data of EU residents, or where the Controller is itself established in the European
Economic Area (EEA) or the United Kingdom. It implements the obligations of Article 28
of the EU General Data Protection Regulation (GDPR) (Regulation 2016/679).

---

## 1. Parties

**Controller:**
Organization Name: ___________________________________
Address: ___________________________________
Contact / DPO: ___________________________________
("Customer" or "Controller")

**Processor:**
Organization Name: BLACKSITE Platform Operator (TheKramerica)
Address: borisov.network (US-based infrastructure)
Contact: daniel@thekramerica.com
("Operator" or "Processor")

---

## 2. Subject Matter and Duration

**Subject matter:** Provision of the BLACKSITE GRC (Governance, Risk, and Compliance)
platform, including management of security compliance programs, system security plans,
POA&Ms, risk registers, audit logs, and related compliance workflows.

**Nature and purpose of processing:** Storing, organizing, retrieving, and displaying
compliance documentation and personnel activity records to support the Controller's
cybersecurity compliance program. Processing is carried out on behalf of and under the
instructions of the Controller.

**Duration:** For the term of the Agreement between the parties. Upon termination or
expiry, personal data is subject to the deletion/return procedure in §12 below.

---

## 3. Types of Personal Data Processed

The Processor processes the following categories of personal data on behalf of the
Controller:

- **Account identifiers:** Usernames, display names, email addresses
- **Authentication data:** Hashed passwords, session tokens, MFA state
- **Access and activity logs:** IP addresses, timestamps, pages accessed, actions
  performed (stored in the immutable audit log)
- **System and compliance content:** Personnel role assignments, system ownership
  records, SSP content (which may reference named individuals by role)
- **Communication records:** AI assistant query/response logs, internal chat messages
  (retained 90 days)
- **Assessment data:** Quiz responses, SSP evaluation results (where these identify
  named individuals)

---

## 4. Categories of Data Subjects

Data subjects whose personal data is processed include:

- The Controller's authorized personnel who hold accounts on the BLACKSITE platform
  (ISSOs, ISSMs, System Owners, SCAs, AOs, Auditors, and other assigned roles)
- Any individuals named within compliance documentation submitted by the Controller
  (e.g., system owners, POC contacts referenced in SSPs)

---

## 5. Processor Obligations (Article 28 GDPR)

The Processor shall:

### 5.1 Instructions
Process personal data only on documented instructions from the Controller, including
with regard to transfers of personal data to a third country or an international
organisation, unless required to do so by EU or Member State law to which the Processor
is subject (in which case the Processor shall inform the Controller before processing,
unless prohibited by law on important grounds of public interest).

### 5.2 Confidentiality
Ensure that persons authorised to process the personal data have committed themselves
to confidentiality or are under an appropriate statutory obligation of confidentiality.

### 5.3 Security (Article 32 GDPR)
Implement appropriate technical and organisational measures to ensure a level of
security appropriate to the risk, including:

- Encryption of personal data at rest (SQLCipher AES-256 for the primary database)
- Encryption of personal data in transit (TLS 1.2+ enforced via Caddy reverse proxy)
- Ongoing confidentiality, integrity, availability, and resilience of processing
  systems and services
- Ability to restore availability and access to personal data in a timely manner in
  the event of a physical or technical incident (see BCDR documentation)
- Regular testing, assessing, and evaluating the effectiveness of technical and
  organisational measures (see platform security posture dashboards)

### 5.4 Sub-processors
Not engage another processor (sub-processor) without prior specific or general written
authorisation of the Controller. Current sub-processors are listed in §8. The Processor
shall inform the Controller of any intended changes, giving the Controller the
opportunity to object within 30 days.

### 5.5 Data Subject Rights
Assist the Controller, by appropriate technical and organisational measures, insofar as
this is possible, in fulfilling the Controller's obligation to respond to requests for
exercising data subjects' rights under Chapter III of GDPR (right of access, erasure,
restriction, portability, etc.). The Processor will provide a response to data subject
rights requests directed to the Processor within 5 business days.

### 5.6 Assistance
Assist the Controller in ensuring compliance with the obligations pursuant to Articles
32–36 (security, breach notification, DPIA, prior consultation).

### 5.7 Deletion / Return
At the choice of the Controller, delete or return all personal data to the Controller
after the end of the provision of services, and delete existing copies unless EU or
Member State law requires storage of the personal data. See §12.

### 5.8 Audit Rights
Make available to the Controller all information necessary to demonstrate compliance
with the obligations laid down in Article 28 GDPR, and allow for and contribute to
audits, including inspections, conducted by the Controller or another auditor mandated
by the Controller. The Processor shall immediately inform the Controller if, in its
opinion, an instruction infringes GDPR or other applicable data protection law.

---

## 6. Controller Obligations

The Controller shall:

- Ensure it has a lawful basis for processing under Article 6 GDPR (and Article 9
  where special categories of data are involved) before instructing the Processor
- Provide appropriate privacy notices to data subjects whose data is processed via
  the platform
- Respond to data subject rights requests in accordance with GDPR timelines
- Ensure that any personal data provided to the Processor is accurate and limited to
  what is necessary for the purposes of processing
- Not instruct the Processor to process personal data in a manner that would violate
  applicable law
- Notify the Processor promptly of any changes to applicable law that may affect the
  Processor's obligations under this DPA

---

## 7. Security Incident and Breach Notification

The Processor shall notify the Controller without undue delay, and in any event within
**72 hours** of becoming aware of a personal data breach (as defined in Article 4(12)
GDPR) affecting data processed under this DPA.

Notification shall be sent to the Controller's designated contact (provided in §1) and
shall include, to the extent available:

- Nature of the breach, including categories and approximate number of data subjects
  and records concerned
- Name and contact details of the Processor's data protection contact
- Likely consequences of the breach
- Measures taken or proposed to address the breach, including mitigation measures

Where not all information is available at the time of notification, the Processor may
provide it in phases without undue further delay.

---

## 8. Sub-processors

The Controller grants general written authorisation for the Processor to engage the
following sub-processors:

| Sub-processor | Location | Purpose | Data Transferred |
|--------------|----------|---------|-----------------|
| **Groq, Inc.** | United States | AI inference for the AI assistant feature (Llama-3 / Mixtral models via Groq Cloud API) | AI chat message content submitted by users; no PII is intentionally included but the Controller is responsible for ensuring users do not submit personal data in AI queries |
| **ip-api.com** | United States | IP geolocation for demo visitor analytics and security logging | Visitor IP addresses (demo site only) |

**Opt-out / replacement procedure:** The Controller may object to a new sub-processor
by written notice within 30 days of notification. If the Controller objects and the
Processor cannot accommodate the objection, the Controller may terminate the Agreement
on 30 days' written notice without penalty.

---

## 9. International Data Transfers

The Processor's infrastructure is located in the United States. Processing of EU
resident personal data therefore constitutes a transfer to a third country under
Chapter V of GDPR.

The parties agree that, to the extent required, such transfers are subject to the EU
Standard Contractual Clauses (SCCs) adopted by Commission Implementing Decision
2021/914 (Module 2: Controller to Processor) or the UK International Data Transfer
Addendum (IDTA), as applicable. A copy of the applicable SCCs or IDTA is available
from the Processor on written request.

---

## 10. Data Protection Impact Assessments

Where a proposed processing activity is likely to result in a high risk to the rights
and freedoms of natural persons, the Controller shall conduct a Data Protection Impact
Assessment (DPIA) prior to commencing processing. The Processor shall cooperate with
and provide reasonable assistance to the Controller in conducting any required DPIA.

---

## 11. Audit and Inspection

The Processor shall, upon reasonable notice (not less than 14 calendar days except in
the case of a confirmed security incident), permit the Controller or its designated
auditor to audit the Processor's data processing activities and technical/organisational
measures for compliance with this DPA. Audits shall be conducted during normal business
hours, at the Controller's expense, and in a manner that minimises disruption to the
Processor's operations. No more than one audit per 12-month period unless a breach has
occurred.

---

## 12. Termination and Data Return / Deletion

Upon termination or expiry of the Agreement, or upon written request from the
Controller, the Processor shall:

1. Within **30 days**, provide the Controller with an export of all personal data
   processed under this DPA in a machine-readable format (JSON or CSV), or confirm
   deletion if the Controller elects deletion
2. Delete all personal data (including backup copies) within **30 days** of the export
   or deletion election, unless EU or Member State law requires continued storage
3. Provide written confirmation of deletion upon request

Data held in immutable audit logs may be retained for the shorter of (a) the retention
period specified in the Data Retention Policy or (b) 30 days post-termination, unless a
legal hold is active.

---

## 13. Governing Law

This DPA shall be governed by and construed in accordance with the laws of the
jurisdiction agreed in the main Agreement between the parties, subject to the
mandatory provisions of GDPR and applicable EU Member State law.

---

## 14. Order of Precedence

In the event of a conflict between this DPA and the main Agreement, this DPA shall
prevail to the extent of the conflict with respect to data protection matters.

---

## SIGNATURE BLOCK

**On behalf of the Controller:**

Signature: ___________________________________
Name: ___________________________________
Title: ___________________________________
Date: ___________________________________
Organization: ___________________________________

**On behalf of the Processor:**

Signature: ___________________________________
Name: ___________________________________
Title: ___________________________________
Date: ___________________________________
Organization: BLACKSITE Platform Operator (TheKramerica)

---

*This document requires legal review before execution. Contact qualified legal counsel
familiar with GDPR and applicable jurisdiction law before signing.*
