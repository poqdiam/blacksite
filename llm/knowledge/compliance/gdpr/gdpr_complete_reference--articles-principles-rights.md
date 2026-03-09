# GDPR Complete Reference: Articles, Principles, and Rights

**Regulation (EU) 2016/679 — General Data Protection Regulation**
**Effective Date:** 25 May 2018
**Scope:** European Union and European Economic Area (EEA); extra-territorial reach

---

## Table of Contents

1. [Overview and Structure](#1-overview-and-structure)
2. [Territorial and Material Scope](#2-territorial-and-material-scope)
3. [Key Definitions](#3-key-definitions)
4. [Seven Principles (Article 5)](#4-seven-principles-article-5)
5. [Lawful Bases for Processing (Article 6)](#5-lawful-bases-for-processing-article-6)
6. [Special Categories of Data (Articles 9–10)](#6-special-categories-of-data-articles-910)
7. [Data Subject Rights (Articles 12–23)](#7-data-subject-rights-articles-1223)
8. [Controller and Processor Obligations (Articles 24–28)](#8-controller-and-processor-obligations-articles-2428)
9. [Data Protection by Design and Default (Article 25)](#9-data-protection-by-design-and-default-article-25)
10. [Records of Processing Activities (Article 30)](#10-records-of-processing-activities-article-30)
11. [Security of Processing (Article 32)](#11-security-of-processing-article-32)
12. [Data Protection Impact Assessment (Articles 35–36)](#12-data-protection-impact-assessment-articles-3536)
13. [Data Protection Officer (Articles 37–39)](#13-data-protection-officer-articles-3739)
14. [Breach Notification (Articles 33–34)](#14-breach-notification-articles-3334)
15. [Transfers to Third Countries (Articles 44–49)](#15-transfers-to-third-countries-articles-4449)
16. [Supervisory Authorities and Enforcement (Articles 51–84)](#16-supervisory-authorities-and-enforcement-articles-5184)
17. [Penalties (Article 83)](#17-penalties-article-83)
18. [Intersection with HIPAA, CCPA, and US Federal Law](#18-intersection-with-hipaa-ccpa-and-us-federal-law)
19. [Relationship to NIST Privacy Framework](#19-relationship-to-nist-privacy-framework)
20. [GDPR in BLACKSITE / RMF Context](#20-gdpr-in-blacksite--rmf-context)
21. [Quick Reference Tables](#21-quick-reference-tables)

---

## 1. Overview and Structure

### 1.1 Legislative History

The GDPR was adopted on 27 April 2016 and repealed Directive 95/46/EC (the Data Protection Directive). Unlike a Directive, the GDPR is a Regulation — it is directly binding in all EU member states without requiring national transposing legislation, though member states retain limited derogations.

### 1.2 Document Structure

| Component | Count | Description |
|---|---|---|
| Chapters | 11 | Logical groupings of articles |
| Articles | 99 | Binding legal provisions |
| Recitals | 173 | Non-binding interpretive guidance |
| Annexes | 0 | (None — detail is in articles/recitals) |

### 1.3 Chapter Summary

| Chapter | Articles | Subject Matter |
|---|---|---|
| I | 1–4 | General provisions: subject matter, scope, definitions |
| II | 5–11 | Principles; lawfulness; consent; special categories |
| III | 12–23 | Rights of data subjects |
| IV | 24–43 | Controller and processor obligations |
| V | 44–49 | Transfers to third countries and international organisations |
| VI | 51–59 | Independent supervisory authorities |
| VII | 60–76 | Cooperation and consistency (one-stop shop) |
| VIII | 77–84 | Remedies, liabilities, and penalties |
| IX | 85–91 | Provisions for specific processing situations (journalism, research, archives) |
| X | 92–93 | Delegated and implementing acts |
| XI | 94–99 | Final provisions, repeal of Directive 95/46/EC |

### 1.4 Key Recitals for Practitioners

| Recital | Topic |
|---|---|
| 4 | Right to data protection as a fundamental right |
| 14–15 | Natural persons; excludes legal persons and deceased |
| 26 | Anonymous data is outside GDPR scope |
| 30 | Online identifiers (cookies, IP addresses) can be personal data |
| 32 | Consent requirements — freely given, specific, informed, unambiguous |
| 47 | Legitimate interests balancing test |
| 65 | Right to erasure and public interest exceptions |
| 75 | Types of risk: discrimination, identity theft, financial loss, reputational damage |
| 78 | Privacy by Design |
| 83 | Security measures proportionate to risk |
| 148 | Supervisory authority discretion on administrative fines |

---

## 2. Territorial and Material Scope

### 2.1 Material Scope (Article 2)

GDPR applies to the **processing of personal data** wholly or partly by automated means, or to the processing other than by automated means of personal data which form part of a filing system.

**Excluded:**
- Processing by natural persons in purely personal or household activity
- Processing for national security / common foreign and security policy
- Law enforcement processing (covered by Law Enforcement Directive 2016/680)
- Processing by deceased persons (recital 27)
- Anonymous data (recital 26) — but pseudonymous data IS in scope (Art 4(5))

### 2.2 Territorial Scope (Article 3)

GDPR has three hooks for jurisdiction:

**Establishment Principle:** Any controller or processor with an establishment in the EU, regardless of where processing takes place.

**Targeting Principle (Extra-territorial):** Controllers/processors not established in the EU but who process data of data subjects in the EU when:
- Offering goods or services to EU data subjects (even free services), OR
- Monitoring the behaviour of EU data subjects within the EU (e.g., tracking, profiling)

**International Law Principle:** Where member state law applies by virtue of public international law (e.g., diplomatic missions).

**Practical implication:** A US company with no EU office that runs a website accepting EU customers and tracking their behaviour is fully subject to GDPR.

---

## 3. Key Definitions (Article 4)

| Term | Article 4 Ref | Definition |
|---|---|---|
| Personal data | 4(1) | Any information relating to an identified or identifiable natural person |
| Data subject | 4(1) | The natural person to whom personal data relates |
| Processing | 4(2) | Any operation on personal data: collection, recording, storage, use, disclosure, erasure, etc. |
| Pseudonymisation | 4(5) | Processing such that data can no longer be attributed to a specific person without additional information held separately |
| Filing system | 4(6) | Structured set of personal data accessible by specific criteria |
| Controller | 4(7) | Natural/legal person that determines the purposes and means of processing |
| Processor | 4(8) | Natural/legal person that processes personal data on behalf of the controller |
| Recipient | 4(9) | Natural/legal person to whom data is disclosed |
| Third party | 4(10) | A person other than the data subject, controller, processor, or persons authorised by them |
| Consent | 4(11) | Freely given, specific, informed, unambiguous indication of agreement |
| Personal data breach | 4(12) | Breach of security leading to accidental/unlawful destruction, loss, alteration, unauthorised disclosure of, or access to personal data |
| Genetic data | 4(13) | Personal data relating to inherited or acquired genetic characteristics |
| Biometric data | 4(14) | Personal data from specific technical processing of physical, physiological, or behavioural characteristics uniquely identifying a natural person |
| Data concerning health | 4(15) | Personal data related to physical/mental health, including provision of health care services |
| Main establishment | 4(16) | For controller: place of central administration; for processor: central administration or place where main processing decisions are taken |
| Representative | 4(17) | Natural/legal person in the EU designated by non-EU controller/processor under Art 27 |
| Enterprise | 4(18) | A natural/legal person engaged in economic activity, irrespective of legal form |
| Group of undertakings | 4(19) | Controlling undertaking and its controlled undertakings |
| Binding corporate rules | 4(20) | Internal personal data protection policies for group transfers |
| Supervisory authority | 4(21) | An independent public authority established by a member state |
| Cross-border processing | 4(23) | Processing in more than one member state, or affecting data subjects in more than one member state |
| Relevant and reasoned objection | 4(24) | Objection to a draft decision on GDPR infringement |
| Information society service | 4(25) | Service provided for remuneration, at a distance, by electronic means (per Directive 2015/1535) |
| International organisation | 4(26) | Organisation subject to public international law |

---

## 4. Seven Principles (Article 5)

Article 5 is the cornerstone of GDPR. All processing must comply with all seven principles simultaneously. Violation of any principle can trigger enforcement action independently of whether specific provisions were breached.

### 4.1 Principle 1: Lawfulness, Fairness, and Transparency

**Lawfulness:** Processing must have at least one valid legal basis from Article 6 (or Article 9 for special categories). There is no lawful processing without a lawful basis.

**Fairness:** Processing must not be deceptive, coercive, or have unjustified adverse effects on data subjects. Processing must meet data subjects' reasonable expectations.

**Transparency:** Data subjects must be informed about the processing in a way that is concise, intelligible, clearly written, and easily accessible. This triggers the Article 13/14 notice obligations.

**Accountability hook:** Accountability requires the controller to be able to demonstrate compliance with all principles (Art 5(2)).

### 4.2 Principle 2: Purpose Limitation

Personal data must be collected for **specified, explicit, and legitimate purposes** and not further processed in a manner incompatible with those purposes.

**Compatible further processing test (Art 6(4)):** Compatibility is assessed by examining:
- The link between original and new purpose
- Context of collection and reasonable expectations
- Nature of the data (especially if special category)
- Possible consequences of further processing
- Existence of appropriate safeguards

**Exceptions:** Further processing for archiving in the public interest, scientific/historical research, or statistical purposes is not incompatible if appropriate safeguards are in place (Art 89).

### 4.3 Principle 3: Data Minimisation

Personal data must be **adequate, relevant, and limited to what is necessary** in relation to the purposes for which it is processed.

Practical requirement: Collect only the data you need, disable collection of unnecessary fields, delete data when it exceeds its purpose. Do not collect "just in case."

### 4.4 Principle 4: Accuracy

Personal data must be **accurate and, where necessary, kept up to date**. Every reasonable step must be taken to ensure inaccurate data is erased or rectified without delay.

This principle supports the data subject's right to rectification (Art 16) and must be built into processes for data maintenance.

### 4.5 Principle 5: Storage Limitation

Personal data must be kept in a form which permits identification of data subjects for **no longer than is necessary** for the purposes for which it is processed.

**Exceptions:** Longer retention is permitted for:
- Archiving in the public interest
- Scientific or historical research
- Statistical purposes
(Subject to appropriate safeguards per Art 89 — e.g., pseudonymisation)

**Practical requirement:** Define and enforce retention schedules. Data that has met its purpose must be deleted or anonymised.

### 4.6 Principle 6: Integrity and Confidentiality (Security)

Personal data must be processed with **appropriate security**, including protection against:
- Unauthorised or unlawful processing
- Accidental loss, destruction, or damage

Using appropriate technical and organisational measures. This principle underpins the security obligations in Article 32.

### 4.7 Principle 7: Accountability

The controller is responsible for, and must be able to **demonstrate compliance** with, all other principles.

Accountability requires:
- Implementing appropriate policies
- Training staff
- Conducting DPIAs where required
- Maintaining records of processing (Art 30)
- Appointing a DPO where required (Art 37)
- Entering DPAs with processors (Art 28)
- Privacy by Design/Default (Art 25)

---

## 5. Lawful Bases for Processing (Article 6)

A lawful basis must be identified **before** processing begins. The basis cannot be changed post-hoc.

### 5.1 The Six Lawful Bases

| Basis | Art 6(1) | Description | Key Conditions |
|---|---|---|---|
| Consent | (a) | Data subject freely gives specific, informed, unambiguous agreement | Must be withdrawable; burden on controller to demonstrate consent; pre-ticked boxes invalid |
| Contract | (b) | Processing necessary for performance of contract with data subject, or pre-contractual steps at their request | Data subject must be party to contract; "necessary" is strictly interpreted |
| Legal obligation | (c) | Processing necessary for compliance with a legal obligation to which the controller is subject | Obligation must be in EU or member state law; controller cannot self-impose |
| Vital interests | (d) | Processing necessary to protect vital interests of data subject or another natural person | Emergency situations only; cannot be relied upon if other bases exist |
| Public task | (e) | Processing necessary for performance of a task carried out in the public interest or in the exercise of official authority | Must be laid down in EU or member state law |
| Legitimate interests | (f) | Processing necessary for legitimate interests of controller or third party, unless overridden by data subject's interests or rights | Three-part test: identify legitimate interest; necessity; balancing test. NOT available to public authorities in performance of tasks |

### 5.2 Consent in Detail (Articles 6(1)(a) and 7)

Consent must be:
- **Freely given:** No imbalance of power; no conditioning on consent for unnecessary processing; no detriment for refusal
- **Specific:** Separate consent for each distinct purpose
- **Informed:** Must know who is the controller, what purposes, right to withdraw
- **Unambiguous:** Clear affirmative action (no silence, pre-ticked boxes, or inactivity)

**Children (Article 8):** For information society services, consent from children under 16 requires parental authorisation. Member states may lower this to 13.

**Withdrawal:** Data subjects must be able to withdraw consent at any time, as easily as it was given. Withdrawal does not affect lawfulness of prior processing.

### 5.3 Legitimate Interests Balancing Test (Article 6(1)(f))

The three-step test:

1. **Purpose test:** Is there a legitimate interest? (Commercial interests, fraud prevention, IT security, intragroup transfers, direct marketing — Recital 47)
2. **Necessity test:** Is processing necessary for that interest? Could a less invasive means achieve the same result?
3. **Balancing test:** Do the data subject's interests or rights override? Consider: reasonable expectations, nature of data, potential harm, safeguards available.

A Legitimate Interests Assessment (LIA) should be documented.

---

## 6. Special Categories of Data (Articles 9–10)

### 6.1 Special Category Data (Article 9)

Processing of special category data is **prohibited** unless one of ten exceptions applies.

**The eight special categories:**

1. Racial or ethnic origin
2. Political opinions
3. Religious or philosophical beliefs
4. Trade union membership
5. Genetic data
6. Biometric data (where processed for uniquely identifying a natural person)
7. Data concerning health
8. Data concerning a natural person's sex life or sexual orientation

### 6.2 Exceptions Permitting Special Category Processing (Art 9(2))

| Exception | Description |
|---|---|
| (a) Explicit consent | Freely given, specific, informed, unambiguous AND explicit (higher bar than standard consent) |
| (b) Employment/social security | Processing necessary under employment law, social security law, with suitable safeguards |
| (c) Vital interests | Data subject physically/legally incapable of giving consent |
| (d) Legitimate activities | Non-profit bodies with political, philosophical, religious, trade-union aim; members/former members; no data disclosed outside |
| (e) Manifestly made public | Data subject has manifestly made the data public |
| (f) Legal claims | Establishing, exercising, or defending legal claims |
| (g) Substantial public interest | Under EU or member state law, proportionate to aim, with suitable safeguards |
| (h) Health/social care | Medical diagnosis, health/social care, treatment, management of health systems — under obligation of professional secrecy |
| (i) Public health | Protecting against cross-border health threats, professional secrecy |
| (j) Research/statistics | Under EU or member state law, Art 89 safeguards |

### 6.3 Criminal Convictions and Offences (Article 10)

Processing of personal data relating to **criminal convictions and offences** may only be carried out under the control of official authority, or when authorised by EU or member state law. A comprehensive register of criminal convictions may only be kept under official authority control.

---

## 7. Data Subject Rights (Articles 12–23)

### 7.1 Obligations for Exercising Rights (Article 12)

The controller must:
- Provide information on rights in a **concise, transparent, intelligible, easily accessible** form using **clear and plain language**
- Respond to rights requests **without undue delay** and within **one month** of receipt
- Extend by two additional months for complex/numerous requests, with notification within one month
- Provide information free of charge; charge a reasonable fee only for manifestly unfounded or excessive requests
- Refuse manifestly unfounded/excessive requests with reasons
- Request additional information to confirm identity when reasonable doubt exists (Art 12(6))

### 7.2 Right to Information — Data Collected Directly (Article 13)

When personal data is collected directly from the data subject, the controller must provide at time of collection:

**Always required:**
- Identity and contact details of controller (and representative if applicable)
- Contact details of DPO (if applicable)
- Purposes and lawful basis for processing
- Legitimate interests pursued (if Art 6(1)(f) basis)
- Recipients or categories of recipients
- Transfers to third countries and safeguards

**Where applicable:**
- Retention periods (or criteria for determining them)
- Existence of rights (access, rectification, erasure, restriction, portability, object)
- Right to withdraw consent (if processing based on consent)
- Right to lodge a complaint with supervisory authority
- Whether provision of data is statutory/contractual and consequences of not providing
- Existence of automated decision-making including profiling

### 7.3 Right to Information — Data Not Collected Directly (Article 14)

When data was not collected from the data subject, the same information as Art 13 plus the **source of data** must be provided within one month of obtaining the data (or at first communication, or at disclosure to another recipient, whichever is earlier).

**Exceptions:** Provision is not required if data subject already has the information, impossible or disproportionate effort (appropriate safeguards required), or legal obligation prohibits disclosure.

### 7.4 Right of Access (Article 15)

Data subjects have the right to obtain from the controller:
- Confirmation of whether personal data is being processed
- If so, access to that personal data
- The following information: purposes; categories; recipients; retention period; rights available; right to lodge complaint; source of data; existence of automated decision-making

**Format:** Must be provided in a commonly used electronic format if requested electronically.

**Copy:** First copy is free. Subsequent copies may incur a reasonable fee.

**Limits:** Access may be refused if it would adversely affect the rights of others (e.g., trade secrets, third-party data).

### 7.5 Right to Rectification (Article 16)

Data subjects have the right to obtain rectification of inaccurate personal data without undue delay. Taking into account the purposes of processing, data subjects have the right to have incomplete data completed, including by means of a supplementary statement.

### 7.6 Right to Erasure ("Right to be Forgotten") (Article 17)

Data subjects have the right to obtain erasure of personal data without undue delay where one of the following grounds applies:

**Grounds for erasure:**
1. Data is no longer necessary for the purpose for which it was collected/processed
2. Data subject withdraws consent (and no other legal basis exists)
3. Data subject objects under Art 21(1) and no overriding legitimate grounds exist
4. Data subject objects under Art 21(2) (direct marketing)
5. Personal data was unlawfully processed
6. Erasure required for compliance with EU or member state law
7. Data was collected in relation to information society services to a child (Art 8)

**Exceptions — erasure is NOT required when processing is necessary for:**
- Exercising the right to freedom of expression and information
- Compliance with a legal obligation
- Reasons of public interest in public health
- Archiving, research, or statistical purposes in public interest (Art 89)
- Establishment, exercise, or defence of legal claims

**Third-party notification:** If data has been made public, the controller must take reasonable steps to inform other controllers processing that data that erasure has been requested.

### 7.7 Right to Restriction of Processing (Article 18)

Data subjects have the right to obtain restriction of processing where:
1. The accuracy of the data is contested (for the period needed to verify accuracy)
2. Processing is unlawful but the data subject opposes erasure and requests restriction instead
3. The controller no longer needs the data but the data subject needs it for legal claims
4. The data subject has objected under Art 21(1) pending verification of whether legitimate grounds override

**Effect of restriction:** Restricted data may only be stored; other processing requires consent or legal claims justification.

**Notification:** Controller must notify the data subject before lifting a restriction.

### 7.8 Notification Obligation (Article 19)

The controller must communicate any rectification, erasure, or restriction to each recipient to whom personal data has been disclosed, unless impossible or disproportionate effort. The controller must inform the data subject of those recipients if the data subject requests it.

### 7.9 Right to Data Portability (Article 20)

Data subjects have the right to receive personal data they have provided in a **structured, commonly used, machine-readable format** and to transmit it to another controller, where:
- Processing is based on consent (Art 6(1)(a)) or contract (Art 6(1)(b)), AND
- Processing is carried out by automated means

**Direct transmission:** Where technically feasible, data subjects may request direct transmission from one controller to another.

**Scope:** Only data the subject has "provided" (i.e., does not include derived or inferred data).

**Non-derogation:** Must not adversely affect the rights of others.

### 7.10 Right to Object (Article 21)

**General right to object (Art 21(1)):**
Data subjects may object at any time to processing based on Art 6(1)(e) (public task) or Art 6(1)(f) (legitimate interests), on grounds relating to their particular situation. The controller must stop processing unless it demonstrates compelling legitimate grounds that override the data subject's interests, rights, and freedoms, or processing is for establishment, exercise, or defence of legal claims.

**Direct marketing (Art 21(2)):**
Data subjects may object at any time to processing for direct marketing purposes, including profiling related to direct marketing. Once an objection is made, processing for that purpose must cease absolutely — no overriding grounds can justify continuation.

**Research/statistics (Art 21(6)):**
Data subjects may object to processing for scientific/historical research or statistical purposes unless processing is necessary for public interest reasons.

**Information obligation:** The right to object must be explicitly brought to the attention of data subjects at the latest at first communication, clearly and separately from other information.

### 7.11 Rights Related to Automated Decision-Making and Profiling (Article 22)

Data subjects have the right **not to be subject to a decision based solely on automated processing**, including profiling, which produces **legal or similarly significant effects** on them.

**Exceptions — automated processing IS permitted when:**
1. Necessary for entering into or performance of a contract
2. Authorised by EU or member state law with suitable safeguards
3. Based on explicit consent

**Safeguards required for exceptions (1) and (3):**
- Right to obtain human intervention
- Right to express point of view
- Right to contest the decision

**Special category data:** Automated decisions involving special category data require explicit consent or substantial public interest grounds (Art 22(4)).

**Summary of Rights and Response Times:**

| Right | Article | Response Time | Fee |
|---|---|---|---|
| Access | 15 | 1 month (extendable by 2) | Free (first copy) |
| Rectification | 16 | Without undue delay | Free |
| Erasure | 17 | Without undue delay | Free |
| Restriction | 18 | Without undue delay | Free |
| Portability | 20 | 1 month (extendable by 2) | Free |
| Object | 21 | On receipt | Free |
| Automated decisions | 22 | 1 month (extendable by 2) | Free |

---

## 8. Controller and Processor Obligations (Articles 24–28)

### 8.1 Responsibility of the Controller (Article 24)

The controller must implement **appropriate technical and organisational measures** to ensure processing is performed in accordance with GDPR, taking into account:
- Nature, scope, context, and purposes of processing
- Risks of varying likelihood and severity to data subjects' rights

Measures must be reviewed and updated where necessary.

**Data protection policies:** Where proportionate, the controller shall implement appropriate data protection policies.

### 8.2 Joint Controllers (Article 26)

Where two or more controllers jointly determine purposes and means, they are **joint controllers**. They must determine their respective responsibilities by arrangement, transparently — in particular specifying who fulfils Art 13/14 transparency obligations.

The essence of the arrangement must be available to data subjects. Data subjects may exercise rights against each controller regardless of the arrangement.

### 8.3 Representatives of Non-EU Controllers (Article 27)

Controllers/processors not established in the EU who are subject to GDPR by virtue of Art 3(2) must designate a representative in the EU in writing.

**Exceptions:** Not required if processing is occasional, does not involve large-scale processing of special category data, and is unlikely to result in risk to natural persons.

### 8.4 Processors (Article 28)

**Controller obligations before engaging processor:**
- Use only processors providing sufficient guarantees
- Ensure processor implements appropriate technical/organisational measures
- Bind processor by contract (Data Processing Agreement/DPA)

**DPA Required Contents (Art 28(3)):**

The DPA must stipulate that the processor:
1. Only processes on documented instructions from the controller
2. Ensures persons authorised to process are committed to confidentiality
3. Implements appropriate security measures (Art 32)
4. Respects conditions for engaging sub-processors (Art 28(2)(4))
5. Assists the controller in fulfilling data subject rights obligations
6. Assists the controller with security, breach notification, DPIA obligations
7. Deletes or returns all personal data upon termination of services
8. Provides all information necessary to demonstrate compliance; allows audits and inspections

**Sub-processors (Art 28(2)(4)):** Processor may not engage sub-processor without prior specific or general written authorisation of the controller. With general authorisation, processor must inform controller of changes, giving controller opportunity to object.

**Processor acting as controller:** If a processor determines purposes/means outside the controller's instructions, they become a controller for that processing and incur full controller liability.

### 8.5 Processing Under Authority of Controller/Processor (Article 29)

The processor, and any person acting under the authority of the controller or processor, shall process personal data only on instructions from the controller.

---

## 9. Data Protection by Design and Default (Article 25)

### 9.1 Privacy by Design (Art 25(1))

Both at the time of the determination of the means for processing and at the time of processing itself, the controller shall implement **appropriate technical and organisational measures** — taking into account the state of the art, cost, nature, scope, context, and purposes of processing, and the risks of varying likelihood and severity — designed to implement the data protection principles in an effective manner and to integrate the necessary safeguards into the processing.

**Practical requirements:**
- Data minimisation must be built into systems from design stage
- Pseudonymisation should be applied by default where possible
- Privacy-enhancing technologies (PETs) preferred
- Access controls limiting data to minimum necessary

### 9.2 Privacy by Default (Art 25(2))

The controller shall implement appropriate technical and organisational measures to ensure that, **by default**, only personal data which are necessary for each specific purpose are processed. That obligation applies to:
- Amount of personal data collected
- Extent of processing
- Period of storage
- Accessibility

In particular, by default, personal data shall not be made accessible without human intervention to an indefinite number of natural persons.

---

## 10. Records of Processing Activities (Article 30)

### 10.1 Controller Records (Art 30(1))

Each controller must maintain a record containing:
- Name and contact details of controller (and joint controllers, representative, DPO)
- Purposes of processing
- Categories of data subjects and personal data
- Categories of recipients (including third countries)
- Transfers to third countries and safeguards
- Retention schedules (where possible)
- General description of technical and organisational security measures (where possible)

### 10.2 Processor Records (Art 30(2))

Each processor must maintain a record containing:
- Name and contact details of processor and each controller on whose behalf the processor acts (and representative, DPO)
- Categories of processing carried out for each controller
- Transfers to third countries and safeguards
- General description of security measures (where possible)

### 10.3 Exemption

Records are not required for organisations with fewer than **250 employees** unless:
- Processing is likely to result in a risk to rights and freedoms
- Processing is not occasional
- Processing includes special categories of data or criminal data

**Practical note:** Most controllers should maintain records regardless of size given the broad exception carve-outs.

---

## 11. Security of Processing (Article 32)

### 11.1 Requirement

The controller and processor shall implement **appropriate technical and organisational measures** to ensure a level of security appropriate to the risk, including as appropriate:

| Measure | Description |
|---|---|
| Pseudonymisation and encryption | Of personal data |
| Ongoing confidentiality | Ensuring ongoing confidentiality, integrity, availability, and resilience of processing systems and services |
| Restoration capability | Ability to restore availability and access in timely manner after physical/technical incident |
| Testing and evaluation | Regular testing, assessing, and evaluating effectiveness of technical/organisational measures |

### 11.2 Risk Assessment for Security

In assessing appropriate level of security, account shall be taken of risks presented, in particular from:
- Accidental or unlawful destruction
- Loss or alteration
- Unauthorised disclosure of or access to personal data transmitted, stored, or otherwise processed

### 11.3 Processor Obligations

Processors shall not engage a sub-processor without prior written authorisation. Processing by a processor shall be governed by a DPA binding the processor under the same obligations as the controller (Art 28(3)).

---

## 12. Data Protection Impact Assessment (Articles 35–36)

### 12.1 When a DPIA is Required (Article 35)

A DPIA is **mandatory** where processing is likely to result in a **high risk** to the rights and freedoms of natural persons, and in particular:

1. **Systematic and extensive profiling** with significant effects: Systematic and extensive evaluation of personal aspects, including profiling, producing significant legal or similarly significant effects
2. **Large-scale special category data:** Processing special category data (Art 9) or criminal data (Art 10) on a large scale
3. **Systematic public monitoring:** Systematic monitoring of a publicly accessible area on a large scale

### 12.2 Other High-Risk Indicators

Supervisory authorities publish lists of processing operations requiring DPIAs (Art 35(4)). WP29 Guidelines on DPIA (adopted by EDPB) identify nine criteria — two or more suggest a DPIA is needed:
1. Evaluation or scoring
2. Automated decision-making with legal or significant effects
3. Systematic monitoring
4. Sensitive data or data of a highly personal nature
5. Data processed on a large scale
6. Matching or combining datasets
7. Data concerning vulnerable data subjects (children, employees, patients)
8. Innovative use or applying new technological or organisational solutions
9. Processing preventing data subjects from exercising a right or using a service or contract

### 12.3 DPIA Content Requirements (Art 35(7))

A DPIA shall contain at minimum:
- Systematic description of envisaged processing operations and purposes, including legitimate interests
- Assessment of the necessity and proportionality of processing in relation to purposes
- Assessment of risks to data subjects' rights and freedoms
- Measures envisaged to address the risks, including safeguards, security measures, and mechanisms

### 12.4 Consulting the DPO

The controller must seek advice from the DPO when conducting a DPIA (Art 35(2)).

### 12.5 Prior Consultation with Supervisory Authority (Article 36)

Where a DPIA indicates processing would result in **high risk absent mitigating measures**, the controller must consult the supervisory authority **before** processing. The supervisory authority has 8 weeks (extendable by 6 weeks) to provide written advice, and may prohibit the processing.

---

## 13. Data Protection Officer (Articles 37–39)

### 13.1 When a DPO is Mandatory (Article 37)

Controllers and processors must designate a DPO where:
1. Processing is carried out by a **public authority or body** (except courts acting in judicial capacity)
2. Core activities consist of **large-scale systematic monitoring** of data subjects
3. Core activities consist of **large-scale processing of special category data** or criminal data

**Core activities:** Primary activities, not ancillary processing (e.g., HR payroll is not a "core activity" of a hospital — medical records processing is).

**Large scale:** No bright-line definition. WP29 guidelines consider: number of data subjects, volume of data, duration/permanence, geographical extent.

Multiple controllers/processors within a group may designate a single DPO (Art 37(2)).

### 13.2 DPO Position Requirements (Article 37(5)–(7))

- Must be designated based on **professional qualities** — expert knowledge of data protection law and practice
- May be a staff member or service provider under a contract
- Contact details must be published and communicated to supervisory authority
- Must not be subject to instructions regarding exercise of DPO tasks
- **Conflict of interest prohibition:** DPO cannot hold positions that determine purposes/means of processing

### 13.3 DPO Tasks (Article 39)

The DPO is responsible for at minimum:
1. **Informing and advising** the controller, processor, and employees on GDPR obligations
2. **Monitoring compliance** with GDPR, EU/member state data protection law, and the organisation's data protection policies — including managing responsibilities, raising awareness and training staff, and conducting audits
3. **Advising on DPIAs** and monitoring their performance (Art 35)
4. **Cooperating with supervisory authority** and acting as contact point
5. **Handling queries** from data subjects

### 13.4 DPO Independence

The controller/processor must ensure the DPO:
- Receives resources to carry out tasks and maintain expert knowledge
- Is not dismissed or penalised for performing tasks
- Reports directly to the highest management level
- Is not bound by instructions in exercise of DPO function

---

## 14. Breach Notification (Articles 33–34)

### 14.1 Notification to Supervisory Authority (Article 33)

In the event of a personal data breach, the controller must notify the competent supervisory authority **without undue delay and, where feasible, not later than 72 hours** after becoming aware of it.

**Exception:** Notification is not required if the breach is **unlikely to result in a risk** to the rights and freedoms of natural persons.

**Content of notification (Art 33(3)):**
1. Nature of the breach (categories and approximate number of data subjects and records affected)
2. Name and contact details of DPO or other contact point
3. Likely consequences of the breach
4. Measures taken or proposed to address the breach, including mitigation measures

**Phased notification:** Where full information is not available within 72 hours, the notification may be provided in phases with further information provided later without undue delay.

**Processor obligations (Art 33(2)):** Processor must notify the controller without undue delay after becoming aware of a breach — no 72-hour period for processor-to-controller notification.

**Documentation (Art 33(5)):** Controllers must document all personal data breaches, whether or not notified — including facts, effects, and remedial actions.

### 14.2 Communication to Data Subjects (Article 34)

Where a breach is **likely to result in a high risk** to data subjects' rights and freedoms, the controller must communicate it to the affected data subjects **without undue delay**.

**Content of communication (Art 34(2)):** Must describe in clear and plain language:
- Nature of the breach
- DPO contact details
- Likely consequences
- Measures taken or proposed

**Exceptions — no communication required if:**
1. Controller implemented appropriate technical/organisational measures (e.g., encryption) making data unintelligible to unauthorised persons
2. Controller has taken subsequent measures ensuring high risk is no longer likely
3. Communication would involve disproportionate effort — instead, a public communication or similar measure ensuring equal effectiveness

**Supervisory authority override:** The supervisory authority may require communication even where an exception applies.

### 14.3 Breach Risk Assessment Matrix

| Risk Level | Supervisory Authority Notification | Data Subject Notification |
|---|---|---|
| No risk | Not required | Not required |
| Risk (not high) | Required within 72 hours | Not required |
| High risk | Required within 72 hours | Required without undue delay |

---

## 15. Transfers to Third Countries (Articles 44–49)

### 15.1 General Principle (Article 44)

A transfer of personal data to a third country (outside EU/EEA) or international organisation may only take place if:
- The conditions laid down in Chapter V are complied with
- This applies even to onward transfers from the third country

### 15.2 Adequacy Decisions (Article 45)

The European Commission may decide that a third country, territory, sector, or international organisation ensures an **adequate level of protection**. No specific authorisation is required for transfers to adequate countries.

**Current adequacy decisions (as of 2025):**
- Andorra, Argentina, Canada (commercial organisations), Faroe Islands, Guernsey, Isle of Man, Israel, Japan, Jersey, New Zealand, Republic of Korea, Switzerland, Uruguay, UK (post-Brexit GDPR adequacy)
- US: EU-US Data Privacy Framework (DPF) — adopted July 2023 (replacing invalidated Privacy Shield)

**Periodic review:** Adequacy decisions must be reviewed at least every four years. The Commission monitors ongoing developments in the third country.

### 15.3 Appropriate Safeguards (Article 46)

Where no adequacy decision exists, transfers may take place where the controller/processor has provided appropriate safeguards and enforceable data subject rights are available. Safeguards include:

| Safeguard | Requires Prior Authorisation? |
|---|---|
| Legally binding and enforceable instrument between public authorities | No |
| Binding Corporate Rules (Art 47) | No (must be approved by SA) |
| Standard Contractual Clauses (SCCs) adopted by Commission | No |
| SCCs adopted by supervisory authority (Art 46(2)(d)) | No |
| Approved code of conduct (Art 40) + binding commitments | No |
| Approved certification mechanism (Art 42) + binding commitments | No |
| Ad hoc contractual clauses | Yes |
| Administrative arrangements between public authorities | Yes |

**Current SCCs:** Two sets — controller-to-controller and controller-to-processor — replaced 2021. Legacy SCCs required updating by December 2022.

**Transfer Impact Assessment (TIA):** Post-Schrems II (CJEU C-311/18, July 2020), exporters must conduct a TIA to verify the law of the destination country does not impair the effectiveness of SCCs in practice.

### 15.4 Binding Corporate Rules (Article 47)

BCRs allow intragroup transfers within a multinational group. They must be:
- Legally binding on all group members
- Conferring enforceable rights on data subjects
- Containing specific elements (Art 47(2)) including: structure, DPP principles, access rights, complaints mechanism, DPA cooperation

BCRs must be approved by the lead supervisory authority under the consistency mechanism.

### 15.5 Derogations (Article 49)

In the absence of adequacy decision or safeguards, transfers may exceptionally occur where:
1. Data subject has given explicit informed consent to the transfer
2. Transfer necessary for contract performance with data subject
3. Transfer necessary for public interest reasons
4. Transfer necessary for legal claims
5. Transfer necessary to protect vital interests of data subject or others (when incapacitation prevents consent)
6. Transfer from a public register
7. Transfer necessary for compelling legitimate interests of controller (only where other derogations unavailable, not repetitive, and appropriate safeguards in place) — with supervisory authority notification

---

## 16. Supervisory Authorities and Enforcement (Articles 51–84)

### 16.1 National Supervisory Authorities (Articles 51–59)

Each member state must establish at least one independent supervisory authority (SA). The SA must act with complete independence, be financed adequately, and members must act without instruction.

**Powers of the SA (Articles 57–58):**
- **Investigative powers:** Access to personal data, premises, information
- **Corrective powers:** Warn; reprimand; impose temporary/permanent ban on processing; order compliance; order erasure/rectification; suspend data flows; impose administrative fines
- **Advisory powers:** Advise national parliament/government; issue opinions; issue guidelines and recommendations
- **Authorisation powers:** Approve BCRs; approve SCCs; accredit certification bodies

### 16.2 One-Stop-Shop (Article 60)

Where a controller/processor has cross-border processing, the SA in the country of the **main establishment** (lead SA) takes primary jurisdiction. Other concerned SAs cooperate and may raise objections. The consistency mechanism resolves disagreements.

**European Data Protection Board (EDPB):** Independent EU body composed of heads of all national SAs and the European Data Protection Supervisor. Adopts binding decisions, guidelines, and recommendations (Art 65–70).

---

## 17. Penalties (Article 83)

### 17.1 Tiered Fine Structure

GDPR establishes a two-tier maximum fine structure. Fines must be **effective, proportionate, and dissuasive**.

| Tier | Maximum | Triggering Violations |
|---|---|---|
| Tier 1 | Up to €10,000,000 or 2% of total worldwide annual turnover (whichever is higher) | Processor/controller obligations (Arts 8, 11, 25–39, 42, 43); certification body (Arts 42, 43); monitoring body (Art 41(4)) |
| Tier 2 | Up to €20,000,000 or 4% of total worldwide annual turnover (whichever is higher) | Basic processing principles (Arts 5, 6, 7, 9); data subject rights (Arts 12–22); transfers to third countries (Arts 44–49); specific member state derogations; non-compliance with SA orders |

### 17.2 Factors in Determining Fine Amount (Art 83(2))

| Factor | Description |
|---|---|
| Nature, gravity, duration | Duration and number of data subjects affected, damage suffered |
| Intentionality | Whether infringement was intentional or negligent |
| Actions to mitigate | Steps taken to mitigate damage |
| Degree of responsibility | Taking into account technical/organisational measures |
| Relevant prior infringements | |
| Cooperation with SA | Degree of cooperation |
| Categories of data | Special category data breaches are more severe |
| Notification | Whether SA was informed proactively |
| Codes of conduct/certification | Adherence or non-adherence |
| Any other aggravating/mitigating factors | |

### 17.3 Notable Enforcement Actions

| Organisation | Year | Fine | Basis |
|---|---|---|---|
| Meta (Facebook) | 2023 | €1.2 billion | Transfers to US without adequate safeguards |
| Amazon | 2021 | €746 million | Unlawful processing for advertising |
| WhatsApp | 2021 | €225 million | Transparency/privacy notice failures |
| Google (France) | 2019 | €50 million | Consent violations for Android personalisation |
| Marriott International | 2020 | £18.4 million (UK) | Data breach affecting 339 million guests |
| British Airways | 2020 | £20 million (UK) | Data breach affecting 400,000 customers |

### 17.4 Other Sanctions (Article 84)

Member states may also establish rules on penalties for infringements not subject to Art 83 administrative fines, including criminal penalties. These must be effective, proportionate, and dissuasive.

**Civil liability (Article 82):** Any person who has suffered material or non-material damage as a result of a GDPR infringement has the right to receive compensation from the controller or processor. Processors are only liable if they have not complied with Art 28 obligations or have acted outside or contrary to lawful instructions.

---

## 18. Intersection with HIPAA, CCPA, and US Federal Law

### 18.1 GDPR vs HIPAA

| Dimension | GDPR | HIPAA |
|---|---|---|
| Jurisdiction | EU/EEA + extraterritorial | US federal |
| Sector | Cross-sector; all personal data | Health sector; PHI only |
| Lawful basis | Required for all processing | Permitted uses/disclosures model |
| Data subject rights | Comprehensive (8 rights) | Limited (access, amendment, accounting) |
| Breach notification | 72 hours to SA; without undue delay to subjects | 60 days to HHS; 60 days to individuals |
| Security requirements | Risk-appropriate, principles-based | Addressable/required safeguards (prescriptive) |
| Enforcement | SAs + civil courts | OCR administrative; civil + criminal penalties |
| DPO/Privacy officer | DPO required in some cases | Privacy Officer required for all CEs |

**Dual compliance:** An organisation processing EU patient data that is also a HIPAA Covered Entity must comply with both. GDPR is generally the stricter standard. Areas requiring attention:
- HIPAA permits disclosure without consent for treatment/payment/operations; GDPR requires a lawful basis for each purpose
- GDPR data portability rights exceed HIPAA access rights
- GDPR erasure rights may conflict with HIPAA records retention requirements
- HIPAA de-identification (Safe Harbor / Expert Determination) may not meet GDPR anonymisation standards

### 18.2 GDPR vs CCPA/CPRA

| Dimension | GDPR | CCPA/CPRA |
|---|---|---|
| Jurisdiction | EU/EEA | California; extraterritorial as to CA residents |
| Applies to | Any processor of EU personal data | Businesses meeting revenue/volume thresholds |
| Lawful basis | Required | Not required (opt-out model for most uses) |
| Data subject rights | Access, rectification, erasure, portability, object, restrict, no automated decisions | Access, deletion, opt-out of sale/sharing, correct, limit use of sensitive PI |
| Sensitive categories | 8 special categories | 11 sensitive PI categories (partially overlapping) |
| Sale of data | Transfer under SCCs/adequacy needed | Opt-out right for sale/sharing |
| Breach liability | Compensatory + administrative fines | Civil penalty $7,500/intentional violation; private right of action for breaches |

**Key difference:** GDPR is an opt-in/lawful basis model; CCPA is an opt-out model for most processing. Organisations serving both EU and California residents need layered compliance programmes.

### 18.3 GDPR and US Federal Law

**No omnibus US federal privacy law** equivalent to GDPR exists (as of 2025). US federal sectoral laws that interact with GDPR:
- **HIPAA** (health data): See above
- **FERPA** (student records): Education sector; limited individual rights
- **GLBA** (financial data): Financial institutions; privacy notices; safeguards rule
- **COPPA** (children under 13): Parental consent for online collection
- **FTC Act Section 5**: Unfair/deceptive acts; FTC enforces privacy promises
- **CLOUD Act**: US government access to data held by US companies abroad — potential conflict with GDPR; Schrems II implications

**FISA/EO12333:** US foreign intelligence surveillance of non-US persons was the basis for Schrems II invalidating Privacy Shield. EU-US DPF (2023) attempts to address through Executive Order 14086 creating redress mechanism.

---

## 19. Relationship to NIST Privacy Framework

### 19.1 NIST Privacy Framework Overview

Published January 2020. Voluntary framework for managing privacy risk. Structure parallels NIST Cybersecurity Framework. Core Functions:

| Function | Description |
|---|---|
| Identify-P | Develop organisational understanding to manage privacy risk |
| Govern-P | Develop and implement organisational governance structure for privacy risk management |
| Control-P | Develop and implement activities to enable organisations and individuals to manage data with sufficient granularity |
| Communicate-P | Develop and implement activities to enable organisations and individuals to have reliable understanding of privacy practices |
| Protect-P | Develop and implement safeguards for data processing to prevent privacy risks |

### 19.2 GDPR–NIST Privacy Framework Mapping

| GDPR Requirement | NIST PF Category/Subcategory |
|---|---|
| Art 5 principles | ID.IM-P1 (data inventory); GV.PO-P1 (policy); CT.DP-P5 (minimisation) |
| Art 6 lawful basis | CT.DM-P1 (consent); GV.RM-P1 (risk strategy) |
| Arts 13/14 transparency | CM.PO-P1 (communication); CT.DM-P3 (notice) |
| Art 15 access | CT.DM-P2 (individual access) |
| Art 17 erasure | CT.DM-P4 (data quality/deletion) |
| Art 25 privacy by design | GV.PO-P2; PR.PO-P1 (data processing policies) |
| Art 30 records | ID.IM-P2 (data processing inventory) |
| Art 32 security | PR.DS-P1 (data at rest); PR.DS-P2 (data in transit) |
| Art 35 DPIA | ID.RA-P2 (privacy risk assessment) |
| Art 33/34 breach | RS.CO-P2 (incident reporting) |

### 19.3 NIST SP 800-53 Rev 5 — Privacy Controls Alignment

NIST SP 800-53 Rev 5 includes 20 privacy control families. Key GDPR mappings:

| NIST 800-53 Privacy Control | GDPR Articles |
|---|---|
| AP-1 (Authority to Collect) | Art 6 lawful basis |
| AP-2 (Purpose Specification) | Art 5(1)(b) purpose limitation |
| AR-1 (Governance/Privacy Program) | Art 24; Art 37 DPO |
| AR-2 (Privacy Impact and Risk Assessment) | Art 35 DPIA |
| AR-3 (Privacy Requirements for Contractors) | Art 28 processor obligations |
| DM-1 (Data Minimisation/Retention) | Art 5(1)(c)(e); Art 25 |
| DM-2 (Data Quality) | Art 5(1)(d) accuracy |
| IP-1 (Consent) | Art 7; Art 6(1)(a) |
| IP-2 (Individual Access) | Art 15 access right |
| IP-3 (Redress) | Art 77 right to lodge complaint |
| IP-4 (Complaint Management) | Art 12 response obligations |
| SE-1 (Inventory of PII) | Art 30 records |
| SE-2 (Privacy Incident Response) | Arts 33–34 |
| UL-1 (Internal Use) | Art 5(1)(b) purpose limitation |

---

## 20. GDPR in BLACKSITE / RMF Context

### 20.1 Applicability to Federal Information Systems

Federal US government systems are **not directly subject to GDPR** unless they process EU residents' personal data. However, GDPR concepts inform several overlapping frameworks:

- **Privacy Act of 1974:** US analog; applies to federal agency records on US persons; SORNs parallel Art 30 records; individual access/correction rights parallel GDPR rights
- **E-Government Act / FISMA PIA requirements:** Privacy Impact Assessments required before developing new systems containing PII — conceptually parallel to DPIA
- **OMB Circular A-130:** Managing Federal Information as a Strategic Resource; includes privacy provisions requiring CIOs to ensure PII protections

### 20.2 GDPR Controls in BLACKSITE System Records

For systems processing EU personal data or requiring GDPR compliance documentation:

| BLACKSITE Field | GDPR Requirement |
|---|---|
| System classification / impact level | Risk level for breach notification threshold |
| Data owner assignment | Controller identification (Art 24) |
| Interconnection records | Third-party processors (Art 28) |
| Privacy Impact Assessment | DPIA documentation (Art 35) |
| Access spot checks | Data minimisation/access control (Art 5(1)(c); Art 32) |
| Artifact: DPA/BAA | Processor contracts (Art 28(3)) |
| Incident response records | Breach notification documentation (Art 33(5)) |
| Retention schedules | Storage limitation (Art 5(1)(e)) |

### 20.3 POA&M Mapping for GDPR Findings

| Finding Type | Typical GDPR Article | Suggested Control ID Prefix |
|---|---|---|
| No lawful basis documented | Art 6 | GDPR-LB- |
| Missing privacy notice | Arts 13/14 | GDPR-TR- |
| DPIA not conducted | Art 35 | GDPR-IA- |
| No DPA with processor | Art 28 | GDPR-PR- |
| Breach not notified within 72h | Art 33 | GDPR-BR- |
| Transfer without safeguards | Arts 44-49 | GDPR-TR- |
| Data retained beyond retention schedule | Art 5(1)(e) | GDPR-SL- |

---

## 21. Quick Reference Tables

### 21.1 GDPR Timelines

| Obligation | Deadline |
|---|---|
| Respond to data subject request | 1 month (extendable to 3 months) |
| Notify supervisory authority of breach | Within 72 hours of becoming aware |
| Notify data subjects of high-risk breach | Without undue delay |
| Respond to SA complaints | Within 1 month |
| Prior consultation response (SA) | 8 weeks (extendable by 6 weeks) |
| Review adequacy decisions | At least every 4 years |

### 21.2 Controller vs Processor Comparison

| Obligation | Controller | Processor |
|---|---|---|
| Identify lawful basis | Yes | No |
| Provide privacy notices | Yes | No (but controller's obligation) |
| Respond to data subject rights | Yes | Must assist controller |
| Conduct DPIA | Yes | Must assist controller |
| Maintain records of processing | Yes | Yes |
| Appoint DPO (where required) | Yes | Yes |
| Security of processing | Yes | Yes |
| Notify controller of breach | N/A | Yes, without undue delay |
| Notify SA of breach | Yes | No |
| Enter DPA with processor | Yes (as data exporter) | Yes (as data importer) |
| Sub-processor authorisation | Must approve | Must obtain approval from controller |

### 21.3 High-Risk Processing Requiring DPIA

| Scenario | DPIA Required |
|---|---|
| Systematic profiling for credit scoring | Yes |
| Large-scale processing of health data | Yes |
| CCTV monitoring of public spaces | Yes |
| Processing children's special category data | Yes |
| Matching/combining datasets from different sources | Consider (if 2+ criteria met) |
| Biometric access control system | Yes |
| AI-based recruitment screening | Yes |
| Smart city IoT monitoring | Yes |

### 21.4 Lawful Basis Selection Guide

| Processing Scenario | Recommended Basis | Notes |
|---|---|---|
| Newsletter subscription | Consent (Art 6(1)(a)) | Must be able to demonstrate; freely withdrawable |
| Employee payroll | Contract (Art 6(1)(b)) + Legal obligation (Art 6(1)(c)) | Employment contract + tax law |
| Fraud detection | Legitimate interests (Art 6(1)(f)) | LIA required; balance against data subject rights |
| Public health surveillance | Public task (Art 6(1)(e)) | Must be in law |
| Emergency medical treatment | Vital interests (Art 6(1)(d)) | Only when incapacitated |
| Tax records retention | Legal obligation (Art 6(1)(c)) | Tax law requirement |
| B2B direct marketing | Legitimate interests (Art 6(1)(f)) | Recital 47; right to object must be offered |

---

*Document Version: 1.0*
*Regulatory Reference: Regulation (EU) 2016/679, as applied from 25 May 2018*
*EDPB Guidelines current through 2025*
*For authoritative interpretation, consult the official EUR-Lex text and applicable EDPB/WP29 guidelines*
