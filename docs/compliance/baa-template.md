# Business Associate Agreement — Template

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09

> **LEGAL NOTICE:** This is a template document. It requires review and execution by qualified legal counsel before it constitutes a binding agreement. This template is provided to facilitate compliance planning and should not be used as a substitute for legal advice. The operator of the BLACKSITE platform makes no warranty regarding the legal sufficiency of this template for any particular jurisdiction or use case.

---

## BUSINESS ASSOCIATE AGREEMENT

This Business Associate Agreement ("Agreement") is entered into as of **[EFFECTIVE DATE]** by and between:

**[COVERED ENTITY NAME]**, a [type of organization, e.g., "covered healthcare entity"] organized under the laws of [State/Jurisdiction], with its principal place of business at [Address] ("Covered Entity"),

and

**[BUSINESS ASSOCIATE NAME / BLACKSITE PLATFORM OPERATOR]**, with its principal place of business at [Address] ("Business Associate").

---

## RECITALS

WHEREAS, Covered Entity is a "covered entity" as defined under the Health Insurance Portability and Accountability Act of 1996, as amended ("HIPAA"), and the regulations promulgated thereunder, including the Privacy Rule (45 CFR Part 164, Subpart E) and the Security Rule (45 CFR Part 164, Subpart C);

WHEREAS, Business Associate operates the BLACKSITE GRC compliance management platform ("Platform"), a web-based application providing RMF/NIST compliance documentation, assessment workflow, and security planning tools;

WHEREAS, in the course of providing services through the Platform to Covered Entity, Business Associate may create, receive, maintain, or transmit Protected Health Information ("PHI") on behalf of Covered Entity;

WHEREAS, HIPAA requires Covered Entity to obtain satisfactory assurances from Business Associate that Business Associate will appropriately safeguard PHI;

NOW, THEREFORE, in consideration of the mutual obligations set forth herein and for other good and valuable consideration, the parties agree as follows:

---

## ARTICLE 1 — DEFINITIONS

**1.1** Terms used but not otherwise defined in this Agreement shall have the same meaning as those terms in HIPAA and the HIPAA Regulations (45 CFR Parts 160 and 164).

**1.2 "PHI"** means Protected Health Information as defined at 45 CFR § 160.103, limited to the PHI created, received, maintained, or transmitted by Business Associate on behalf of Covered Entity.

**1.3 "Breach"** has the meaning given at 45 CFR § 164.402.

**1.4 "Services"** means the compliance management and GRC platform services provided by Business Associate to Covered Entity through the BLACKSITE platform.

---

## ARTICLE 2 — PERMITTED USES AND DISCLOSURES OF PHI

**2.1 Permitted Uses.** Business Associate may use PHI only as necessary to perform the Services on behalf of Covered Entity, and for the following purposes:
- (a) Operation, maintenance, and support of the Platform for Covered Entity's use
- (b) As required by law
- (c) For the proper management and administration of Business Associate's own operations, provided such use is permitted under 45 CFR § 164.504(e)(4)

**2.2 Prohibited Uses.** Business Associate shall not use or disclose PHI in any manner that would violate HIPAA or the HIPAA Regulations if done by Covered Entity. Business Associate shall not use PHI for marketing, sale of data, or any purpose not expressly authorized in this Agreement.

**2.3 Minimum Necessary.** Business Associate shall use, disclose, and request only the minimum necessary PHI to accomplish the permitted purpose.

**2.4 De-identification.** Business Associate shall not attempt to re-identify any de-identified information without prior written authorization from Covered Entity.

---

## ARTICLE 3 — SAFEGUARDS

**3.1 Appropriate Safeguards.** Business Associate shall implement and maintain reasonable and appropriate administrative, physical, and technical safeguards to protect the confidentiality, integrity, and availability of PHI. The BLACKSITE platform implements the following controls, which constitute the minimum required safeguards under this Agreement:

- (a) **Encryption at Rest:** All data, including any PHI, stored in the Platform database is encrypted using AES-256 (via SQLCipher). The encryption key is stored only in the systemd service unit environment and is not embedded in application code or configuration files.

- (b) **Encryption in Transit:** All data transmitted to and from the Platform is protected using TLS 1.2 or higher via a Caddy reverse proxy with ACME-managed certificates.

- (c) **Access Control:** The Platform enforces role-based access control. Access to PHI is limited to authenticated users with appropriate roles. Administrative functions require elevated privilege.

- (d) **Audit Logging:** The Platform maintains an immutable audit log of all authentication events, data access, and modification events, with user identity, timestamp, and action type recorded for each event. Audit logs are retained for a minimum of 3 years.

- (e) **Authentication:** User passwords are stored only as bcrypt hashes. Session tokens are cryptographically random and server-side.

**3.2 Security Rule Compliance.** Business Associate shall comply with the requirements of the HIPAA Security Rule (45 CFR §§ 164.302–318) with respect to electronic PHI.

---

## ARTICLE 4 — SUBCONTRACTORS

**4.1 Subcontractor Agreements.** Business Associate shall ensure that any subcontractor that creates, receives, maintains, or transmits PHI on behalf of Business Associate agrees, in writing, to the same restrictions and conditions that apply to Business Associate under this Agreement.

**4.2 AI Subcontractor — Groq, Inc.** The Platform uses Groq, Inc. ("Groq") as a subcontractor to provide AI-assisted compliance query responses. **PHI must never be included in queries submitted to the AI assistant.** Business Associate and Covered Entity both acknowledge that:
- (a) AI assistant queries are transmitted to Groq's API for processing
- (b) No PHI should be included in any AI assistant query; platform policy explicitly prohibits this
- (c) Business Associate shall maintain this prohibition as a written policy and make it visible to Platform users
- (d) In the event Covered Entity's users inadvertently include PHI in AI queries, such transmission shall be treated as a potential Breach and handled under Article 5

**4.3** Business Associate represents that Groq, Inc. has agreed to data processing terms consistent with HIPAA requirements for Business Associate's use of their service.

---

## ARTICLE 5 — BREACH NOTIFICATION

**5.1 Notification to Covered Entity.** Business Associate shall notify Covered Entity without unreasonable delay, and in no case later than **sixty (60) calendar days** following discovery of a Breach of Unsecured PHI, as required by 45 CFR § 164.410.

**5.2 Content of Notification.** Notification shall include, to the extent possible:
- (a) A description of the Breach, including the date of the Breach and the date of discovery
- (b) A description of the types of Unsecured PHI involved
- (c) The identity of each individual whose PHI has been, or is reasonably believed to have been, accessed, acquired, used, or disclosed
- (d) A brief description of what Business Associate is doing to investigate the Breach, mitigate harm, and protect against further Breaches
- (e) Contact information for Covered Entity to ask questions

**5.3 Delay for Law Enforcement.** If a law enforcement official requests a delay in notification, Business Associate shall delay notification as required by 45 CFR § 164.412.

**5.4 Security Incidents.** Business Associate shall report to Covered Entity any Security Incident of which it becomes aware, including Breaches of Unsecured PHI, in accordance with Section 5.1.

---

## ARTICLE 6 — INDIVIDUAL RIGHTS

**6.1 Access.** Business Associate shall, within fifteen (15) days of a written request by Covered Entity, make PHI in a Designated Record Set available to Covered Entity for the purpose of allowing Covered Entity to respond to an individual's request for access under 45 CFR § 164.524.

**6.2 Amendment.** Business Associate shall make PHI available for amendment and incorporate any amendments in accordance with 45 CFR § 164.526 within fifteen (15) days of written request by Covered Entity.

**6.3 Accounting of Disclosures.** Business Associate shall maintain and make available information required to provide an accounting of disclosures in accordance with 45 CFR § 164.528.

---

## ARTICLE 7 — TERM AND TERMINATION

**7.1 Term.** This Agreement is effective as of the date set forth above and shall remain in effect until terminated as provided herein or until the Services Agreement between the parties expires or is terminated.

**7.2 Termination for Cause.** Either party may terminate this Agreement immediately upon written notice if the other party has materially breached a material provision of this Agreement and has failed to cure such breach within thirty (30) days of written notice of the breach.

**7.3 Automatic Termination.** This Agreement shall automatically terminate upon termination of all Services Agreements between the parties.

**7.4 Effect of Termination — Return or Destruction of PHI.** Upon termination of this Agreement for any reason, Business Associate shall, if feasible, return to Covered Entity or destroy all PHI received from, or created or received on behalf of, Covered Entity that Business Associate maintains in any form. If return or destruction is not feasible, Business Associate shall notify Covered Entity of the conditions making return or destruction infeasible, and Business Associate shall extend the protections of this Agreement to such PHI and limit further uses and disclosures to those purposes that make return or destruction infeasible.

**Return / destruction procedure:**
- Export all PHI-containing records to Covered Entity in a mutually agreed format within 30 days of termination
- Execute `DELETE` from relevant tables; run `VACUUM` on the database
- Confirm deletion to Covered Entity in writing
- Delete any backup copies containing the Covered Entity's PHI from backup storage within 60 days of termination

---

## ARTICLE 8 — MISCELLANEOUS

**8.1 Amendment.** This Agreement may be amended only by written instrument signed by authorized representatives of both parties. The parties agree to amend this Agreement as necessary to comply with changes in HIPAA and the HIPAA Regulations.

**8.2 Survival.** The obligations of Business Associate under this Agreement with respect to the use and disclosure of PHI shall survive the termination of this Agreement.

**8.3 Interpretation.** This Agreement shall be interpreted as broadly as necessary to implement and comply with HIPAA and the HIPAA Regulations. Any ambiguity shall be resolved in favor of the interpretation that most effectively implements HIPAA compliance.

**8.4 No Third-Party Beneficiaries.** Nothing in this Agreement is intended to confer rights on any person or entity other than the parties.

**8.5 Governing Law.** This Agreement shall be governed by the laws of [State], without regard to its conflict of laws principles, except to the extent that federal law (including HIPAA) governs.

---

## SIGNATURE BLOCK

**[COVERED ENTITY NAME]**

Signature: ___________________________

Printed Name: ________________________

Title: ________________________________

Date: ________________________________

---

**[BUSINESS ASSOCIATE NAME]**

Signature: ___________________________

Printed Name: ________________________

Title: ________________________________

Date: ________________________________

---

> **REMINDER:** This template requires review by qualified legal counsel before execution. The BLACKSITE platform operator does not warrant that this template satisfies all legal requirements applicable to your specific situation, jurisdiction, or covered entity type. Consult your organization's legal counsel and privacy officer before signing.
