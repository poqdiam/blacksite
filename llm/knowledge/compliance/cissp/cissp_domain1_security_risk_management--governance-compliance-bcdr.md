# CISSP Domain 1: Security and Risk Management
## Governance, Compliance, and Business Continuity/Disaster Recovery

**CBK Domain Weight:** 15% (highest single domain)
**Exam Focus:** Conceptual, managerial, and governance-level thinking — not technical implementation

---

## Table of Contents

1. [Information Security Governance Frameworks](#1-information-security-governance-frameworks)
2. [Security Policy Hierarchy](#2-security-policy-hierarchy)
3. [Risk Management Concepts](#3-risk-management-concepts)
4. [Quantitative Risk Analysis](#4-quantitative-risk-analysis)
5. [Qualitative Risk Analysis](#5-qualitative-risk-analysis)
6. [Risk Treatment Options](#6-risk-treatment-options)
7. [Due Care vs. Due Diligence](#7-due-care-vs-due-diligence)
8. [Legal and Regulatory Landscape](#8-legal-and-regulatory-landscape)
9. [Privacy Principles](#9-privacy-principles)
10. [Business Continuity Planning](#10-business-continuity-planning)
11. [Ethics](#11-ethics)
12. [Personnel Security](#12-personnel-security)
13. [Key Terms Quick Reference](#13-key-terms-quick-reference)

---

## 1. Information Security Governance Frameworks

### What Is Security Governance?

Security governance is the set of organizational structures, accountability mechanisms, processes, and policies that direct and control an organization's information security activities. Governance answers the question: **Who is responsible, to whom, for what, and with what authority?**

Governance is distinct from management:
- **Governance** = direction, accountability, oversight (board-level, executive-level)
- **Management** = implementation, operations, measurement (CISO, security teams)

### COSO — Committee of Sponsoring Organizations of the Treadway Commission

**Primary use:** Internal control framework; originally developed for financial reporting integrity; widely used in SOX compliance

**Three-dimensional COSO Cube:**

| Dimension | Components |
|-----------|-----------|
| **Objectives** | Operations, Reporting, Compliance |
| **Components** | Control Environment, Risk Assessment, Control Activities, Information & Communication, Monitoring |
| **Organizational Units** | Entity-level, Division, Operating Unit, Function |

**Key COSO principles for security governance:**
- Control environment establishes tone at the top — leadership must visibly support security
- Risk assessment identifies and analyzes risks relevant to achieving objectives
- Control activities are the policies and procedures that help ensure management directives are carried out
- Monitoring assesses the quality of internal control performance over time
- Information and communication supports all other components

**COSO ERM (Enterprise Risk Management) 2017 Update:**
- Integrates ERM with strategy setting
- Emphasizes risk culture and governance
- 20 principles organized under 5 components: Governance & Culture, Strategy & Objective-Setting, Performance, Review & Revision, Information, Communication & Reporting

### COBIT 5 and COBIT 2019

**Primary use:** IT governance and management; connects business objectives to IT controls; widely used in SOX, SOC 2, and ISO 27001 contexts

**COBIT 5 (legacy, still tested):**

Five key principles:
1. Meeting stakeholder needs
2. Covering the enterprise end-to-end
3. Applying a single integrated framework
4. Enabling a holistic approach
5. Separating governance from management

Seven enablers (resources that make governance possible):
- Principles, Policies, and Frameworks
- Processes
- Organizational Structures
- Culture, Ethics, and Behavior
- Information
- Services, Infrastructure, and Applications
- People, Skills, and Competencies

**COBIT 2019 (current):**
- Replaces the fixed 5 principles with 6 governance/management objectives principles
- Introduces **design factors** that customize the governance system to organizational context (enterprise strategy, risk profile, compliance requirements, etc.)
- Introduces **focus areas** (cloud computing, cybersecurity, DevOps, privacy) as specialized extensions
- Core model: 40 governance and management objectives organized into 5 domains:
  - EDM: Evaluate, Direct, Monitor (governance domain — board-level)
  - APO: Align, Plan, Organize
  - BAI: Build, Acquire, Implement
  - DSS: Deliver, Service, Support
  - MEA: Monitor, Evaluate, Assess

**COBIT APO12: Manage Risk** — the risk management process within COBIT:

```
APO12.01 — Collect data
APO12.02 — Analyze risk
APO12.03 — Maintain a risk profile
APO12.04 — Articulate risk
APO12.05 — Define a risk management action portfolio
APO12.06 — Respond to risk
```

### ISO 38500 — Corporate Governance of Information Technology

**Primary use:** Board-level IT governance; provides principles for directors and executives

**Six principles:**
1. **Responsibility** — Individuals and groups should understand and accept their responsibilities for IT supply and demand
2. **Strategy** — Business strategy should account for current and future IT capabilities
3. **Acquisition** — IT acquisitions should be made based on sound analysis
4. **Performance** — IT should be fit for purpose and deliver what is needed
5. **Conformance** — IT should comply with mandatory legislation and regulations
6. **Human behavior** — IT policies and decisions should respect human needs

**Three governance tasks** for directors under ISO 38500:
- **Evaluate:** Current and future use of IT
- **Direct:** Preparation and implementation of plans and policies
- **Monitor:** Conformance to policies and performance against plans

### NIST Risk Management Framework (RMF) — NIST SP 800-37 Rev 2

**Primary use:** Federal information systems; increasingly adopted in critical infrastructure and defense industrial base

**Seven RMF Steps:**

```
Step 1: PREPARE
  └── Establish organizational risk management roles, strategy, and processes

Step 2: CATEGORIZE
  └── Categorize system and information using FIPS 199 / NIST SP 800-60
      (Low / Moderate / High for Confidentiality, Integrity, Availability)

Step 3: SELECT
  └── Select appropriate baseline controls from NIST SP 800-53
      (Low, Moderate, or High baseline) + tailor/supplement as needed

Step 4: IMPLEMENT
  └── Implement selected controls; document in System Security Plan (SSP)

Step 5: ASSESS
  └── Assess control effectiveness; Security Assessment Report (SAR)

Step 6: AUTHORIZE
  └── Authorizing Official (AO) makes risk-based authorization decision
      (ATO, IATO, DATO, or denial)

Step 7: MONITOR
  └── Continuously monitor controls; report status; respond to changes
```

---

## 2. Security Policy Hierarchy

### The Four-Level Hierarchy

Security documentation follows a strict hierarchy from broad strategic direction down to specific operational instructions. Each level has different characteristics, audiences, and update frequencies.

```
POLICY
  └── STANDARD
       └── PROCEDURE
            └── GUIDELINE
```

### Policy

**Definition:** High-level management statement of direction, objectives, and intent regarding security

**Characteristics:**
- Mandatory — compliance is required
- Technology-neutral — does not specify specific products or implementations
- Approved by senior management or board
- Changes infrequently (typically reviewed annually)
- Addresses the "what" and "why" — not the "how"

**Types of security policies:**
- **Organizational/Master Security Policy:** Overall information security program direction
- **Issue-specific policies:** Focused on a particular topic (acceptable use, remote access, mobile devices, encryption, incident response)
- **System-specific policies:** Rules governing a specific system or class of systems

**Example policy statement:**
> "All information classified as Confidential or above must be encrypted at rest using approved cryptographic algorithms."

### Standard

**Definition:** Mandatory requirements specifying how the policy is to be implemented; more specific than policy

**Characteristics:**
- Mandatory — compliance is required (unlike guidelines)
- Technology-specific or process-specific
- Provides measurable, auditable requirements
- Changes more frequently than policy as technology evolves
- Addresses the "what must be done" specifically

**Example standard statement:**
> "Encryption of Confidential data at rest must use AES-256-GCM. Key management must comply with NIST SP 800-57 recommendations. Keys must be stored in a FIPS 140-2 Level 2 validated HSM."

### Procedure

**Definition:** Step-by-step instructions for implementing a standard; operational in nature

**Characteristics:**
- Mandatory for the activity being performed
- Highly specific — includes exact steps, commands, forms, tools
- Written for practitioners who perform the task
- Changes frequently as systems and processes evolve
- Addresses "how" to do something

**Example procedure excerpt:**
> "1. Open the key management console. 2. Navigate to Keys > Create New Key. 3. Select AES-256-GCM as the algorithm. 4. Set the expiration date to 1 year from today. 5. Assign the key to the target data store..."

### Guideline

**Definition:** Recommended (optional) practices for achieving policy and standard compliance; not mandatory

**Characteristics:**
- Optional — provides recommendations, not requirements
- Offers flexibility where multiple acceptable approaches exist
- Useful for areas where a single mandatory approach would be overly restrictive
- Addresses "suggested" approaches

**Example guideline:**
> "When creating passwords for personal accounts that are not subject to the organizational password standard, it is recommended to use a passphrase of at least 20 characters."

### Policy Hierarchy Comparison Table

| Level | Mandatory? | Specificity | Audience | Change Frequency | Example |
|-------|-----------|------------|---------|-----------------|---------|
| Policy | Yes | Low | All personnel | Annual | "Data must be protected" |
| Standard | Yes | Medium | Technical leads, managers | Semi-annual | "Use AES-256" |
| Procedure | Yes (for the task) | High | Practitioners | As needed | "Step 1: Open console..." |
| Guideline | No | Variable | Anyone needing guidance | As needed | "It is recommended to..." |

### Policy Management Best Practices

- **Policy ownership:** Each policy must have a named owner accountable for its maintenance
- **Review cycle:** Policies should be reviewed at least annually and after significant changes to the organization, threat landscape, or regulatory environment
- **Exception process:** A formal exception process should exist for cases where compliance with a policy creates unacceptable operational burden; exceptions must be documented, risk-accepted, and time-limited
- **Communication:** Policies must be communicated to all covered personnel; training and awareness programs reinforce policy compliance
- **Enforcement:** Without enforcement, policies are merely wishes; disciplinary procedures for policy violations must be defined and consistently applied

---

## 3. Risk Management Concepts

### Core Risk Terminology

**Asset:** Anything of value to the organization that must be protected. Assets include:
- Information assets (databases, intellectual property, customer data)
- Software assets (applications, operating systems, utilities)
- Physical assets (hardware, facilities, infrastructure)
- Service assets (cloud services, utilities)
- Personnel (skills, knowledge, capabilities)
- Intangibles (brand reputation, customer trust)

**Threat:** Any potential cause of an unwanted incident that may result in harm to a system or organization. Threats are external to controls — they exist whether or not controls are in place.

**Threat agent / Threat actor:** The entity that carries out the threat (e.g., nation-state APT, cybercriminal group, disgruntled insider, natural disaster, hardware failure)

**Vulnerability:** A weakness in a system, control, or process that could be exploited by a threat agent to cause harm. Vulnerabilities are characteristics of the asset or its environment.

**Exposure:** The degree to which an asset is susceptible to loss or damage from a threat; the condition of being open to attack.

**Risk:** The likelihood that a threat agent will exploit a vulnerability, combined with the potential impact on the organization.

```
Risk = f(Threat, Vulnerability, Impact)
```

Or more precisely:
```
Risk = Threat Probability × Impact × Exposure
```

**Control (Safeguard/Countermeasure):** A measure that reduces risk by reducing threat likelihood, reducing vulnerability, or reducing impact.

**Residual risk:** The risk that remains after controls are applied. Residual risk is never zero — the goal is to reduce risk to an acceptable level.

```
Inherent Risk (no controls) → Apply Controls → Residual Risk
```

**Total risk:** Risk before any controls are applied (also called inherent risk).

### Risk Management Process (NIST SP 800-30 / ISO 31000)

```
1. CONTEXT ESTABLISHMENT
   └── Define scope, boundaries, organizational context, risk criteria

2. RISK IDENTIFICATION
   └── Identify assets, threats, and vulnerabilities

3. RISK ANALYSIS
   ├── Quantitative: ALE = ARO × SLE
   └── Qualitative: Risk matrices, heat maps

4. RISK EVALUATION
   └── Compare analyzed risks against risk criteria; prioritize

5. RISK TREATMENT
   ├── Accept (tolerate)
   ├── Avoid (eliminate)
   ├── Transfer (insure, contract)
   └── Mitigate (implement controls)

6. MONITORING AND REVIEW
   └── Continuous monitoring; reassess periodically and after changes

7. COMMUNICATION AND CONSULTATION
   └── Stakeholder communication throughout the entire process
```

### Threat Modeling Approaches

**STRIDE (per threat source):**
- **S**poofing: Impersonating something or someone else
- **T**ampering: Modifying data or code without authorization
- **R**epudiation: Denying actions without others being able to prove otherwise
- **I**nformation Disclosure: Exposing information to unauthorized parties
- **D**enial of Service: Deny or degrade service to legitimate users
- **E**levation of Privilege: Gaining capabilities without proper authorization

**DREAD (risk rating):**
- **D**amage potential
- **R**eproducibility
- **E**xploitability
- **A**ffected users
- **D**iscoverability

**Attack trees:** Hierarchical diagrams showing how an attacker can achieve a goal; root node = attacker objective; child nodes = sub-goals or techniques; leaf nodes = specific attack actions.

---

## 4. Quantitative Risk Analysis

### Core Formulas

Quantitative risk analysis uses objective, numeric values to express risk. It requires historical data and is more precise but also more time-consuming and data-intensive than qualitative analysis.

#### Asset Value (AV)

The monetary value of an asset. Includes:
- Purchase price + replacement cost
- Business impact of loss (lost revenue, recovery costs, reputation damage)
- May be determined by business owners, finance, or insurance valuation

#### Exposure Factor (EF)

The percentage of asset value lost if a specific threat event occurs. Expressed as a decimal between 0 and 1.

- If a fire destroys a data center, EF might be 1.0 (100% loss)
- If a ransomware attack encrypts 40% of data and the rest is recoverable, EF might be 0.4

#### Single Loss Expectancy (SLE)

The expected monetary loss from a **single occurrence** of a threat event.

```
SLE = AV × EF

Example:
  AV = $1,000,000 (value of the server and its data)
  EF = 0.30 (30% of asset value lost per event)
  SLE = $1,000,000 × 0.30 = $300,000
```

#### Annualized Rate of Occurrence (ARO)

The estimated frequency with which a threat is expected to occur in a one-year period. Based on historical data, threat intelligence, industry statistics, or expert judgment.

```
Examples:
  ARO = 0.5 → expected to occur once every 2 years
  ARO = 1   → expected to occur once per year
  ARO = 4   → expected to occur 4 times per year
  ARO = 0.1 → expected to occur once every 10 years
```

#### Annualized Loss Expectancy (ALE)

The expected monetary loss from a threat over a **one-year period**. The primary metric for risk prioritization and cost-benefit analysis of controls.

```
ALE = ARO × SLE
    = ARO × AV × EF

Example:
  ARO = 0.5 (once every 2 years)
  SLE = $300,000
  ALE = 0.5 × $300,000 = $150,000 per year
```

### Cost-Benefit Analysis of Controls

A control is worth implementing if its annual cost is less than the risk reduction it provides.

```
Value of Control = ALE (before control) - ALE (after control) - ACS

Where:
  ACS = Annual Cost of Safeguard (purchase, maintenance, staff time)

If (Value of Control > 0), the control is cost-justified.
If (Value of Control < 0), implementing the control costs more than the risk it reduces.
```

**Example:**

| Metric | Value |
|--------|-------|
| ALE before control | $150,000 |
| ALE after control (residual) | $30,000 |
| Risk reduction | $120,000 |
| Annual Cost of Safeguard (ACS) | $50,000 |
| Net value of control | $70,000 (worth implementing) |

### Worked Example: Full Quantitative Assessment

**Scenario:** A web application serves 500,000 customers. A SQL injection vulnerability exists. Historical breach data shows similar vulnerabilities result in breach events with the following characteristics:

```
Asset Value (AV):
  - Customer records value: $200 per record × 500,000 = $100,000,000
  - Regulatory fines (GDPR): estimated $2,000,000
  - Reputational damage: estimated $5,000,000
  Total AV = $107,000,000

Exposure Factor (EF):
  - Estimated 10% of records exposed in a typical SQL injection breach
  EF = 0.10

SLE = AV × EF = $107,000,000 × 0.10 = $10,700,000

ARO:
  - Industry statistics show 1 major SQL injection breach per 5 years for similar orgs
  ARO = 0.20

ALE = ARO × SLE = 0.20 × $10,700,000 = $2,140,000

Control: Web Application Firewall (WAF) + parameterized query training
  - ACS = $120,000/year
  - Expected to reduce ARO to 0.05 (1 per 20 years after control)

ALE after control = 0.05 × $10,700,000 = $535,000

Value of control = $2,140,000 - $535,000 - $120,000 = $1,485,000

Decision: Control is highly cost-justified.
```

### Limitations of Quantitative Analysis

- Requires high-quality historical data that may not exist
- ARO estimates are inherently uncertain
- Asset valuation can be subjective (especially intangibles like reputation)
- Can create false precision — numbers appear authoritative even when estimates are rough
- Time-consuming and expensive to perform rigorously
- Best used for high-value decisions where investment in data collection is warranted

---

## 5. Qualitative Risk Analysis

### Overview

Qualitative risk analysis uses descriptive scales (low/medium/high, 1-5, red/yellow/green) rather than monetary values. It is faster, requires less data, and is more widely used in practice — especially for initial risk assessments and when precise data is unavailable.

### Risk Matrix (Heat Map)

The most common qualitative tool. Likelihood and impact are rated on scales, and their combination produces a risk rating.

**5×5 Risk Matrix:**

```
         |  IMPACT
         | Negligible | Minor | Moderate | Major | Catastrophic
---------|-----------|-------|----------|-------|-------------
Almost   |   Medium  | High  | Critical |Critical| Critical
Certain  |           |       |          |       |
---------|-----------|-------|----------|-------|-------------
Likely   |    Low    |Medium |   High   |Critical|Critical
---------|-----------|-------|----------|-------|-------------
Possible |    Low    | Low   |  Medium  | High  | Critical
---------|-----------|-------|----------|-------|-------------
Unlikely |    Low    | Low   |   Low    |Medium | High
---------|-----------|-------|----------|-------|-------------
Rare     |    Low    | Low   |   Low    |  Low  | Medium
```

**Likelihood Scale:**
- Almost Certain: >90% probability per year
- Likely: 50-90%
- Possible: 10-50%
- Unlikely: 1-10%
- Rare: <1%

**Impact Scale:**
- Negligible: Minimal disruption, <$10K loss
- Minor: Some disruption, $10K-$100K loss
- Moderate: Significant disruption, $100K-$1M loss
- Major: Serious harm, $1M-$10M loss
- Catastrophic: Existential threat, >$10M loss

### Qualitative Rating Systems

**Ordinal scales:** Rank-ordered but not mathematically precise (Low < Medium < High)

**Descriptive categories:** Some organizations use named tiers (Critical, High, Medium, Low, Informational — matching CVSSv3 severity ratings)

**Color coding:** Red/Yellow/Green (traffic light) for executive dashboards

### Advantages of Qualitative Analysis

- Fast to complete; good for initial triage
- Doesn't require historical loss data
- Accessible to non-technical stakeholders
- Good for comparing risks across different categories (operational, reputational, compliance)
- Allows for expert judgment and consensus building

### Delphi Technique

A structured expert elicitation method used in qualitative risk analysis:
1. Anonymous experts independently estimate risk levels
2. Facilitator aggregates responses and shares summary with group
3. Experts revise their estimates based on group feedback
4. Process repeats until consensus emerges

Eliminates anchoring bias and groupthink that occur when experts discuss openly first.

---

## 6. Risk Treatment Options

### The Four Risk Treatment Strategies

**CISSP exam terminology:** Accept, Avoid, Transfer, Mitigate (also called: Tolerate, Terminate, Transfer, Treat)

#### Accept (Tolerate)

**Definition:** Acknowledge the risk and consciously decide to live with it without implementing additional controls.

**When appropriate:**
- Cost of control exceeds the value of the asset or the ALE
- Risk falls within the organization's defined risk tolerance
- Control options are not feasible given operational constraints
- Risk is unlikely enough that control investment is not justified

**Requirements for proper risk acceptance:**
- Formal, documented risk acceptance decision
- Approved by appropriate authority (usually data/system owner + risk management function)
- Time-limited: acceptance should be reviewed at defined intervals
- Documented in a risk register

**IMPORTANT distinction:** Risk acceptance is a **deliberate, informed decision** — it is not the same as ignoring a risk or being unaware of it. Accepting risk without documentation or management approval is negligence, not a treatment strategy.

#### Avoid (Terminate/Eliminate)

**Definition:** Eliminate the activity or asset that creates the risk.

**Examples:**
- Stop accepting credit card payments (eliminates PCI DSS scope)
- Discontinue a product line that processes sensitive data
- Shut down a vulnerable legacy system that cannot be patched
- Don't launch into a market with unacceptable regulatory requirements

**When appropriate:**
- Risk is unacceptably high and cannot be reduced to tolerable levels
- The activity generating the risk does not provide sufficient business value
- No viable mitigation or transfer options exist

**Limitation:** Avoidance often means forgoing business opportunities or capabilities. It is sometimes the correct choice, but must be weighed against business impact.

#### Transfer (Share)

**Definition:** Shift the financial consequences of a risk to a third party.

**Common transfer mechanisms:**
- **Cyber insurance:** Covers financial losses from breaches, ransomware, business interruption
- **Contractual transfer:** Liability clauses in vendor agreements; indemnification provisions
- **Outsourcing:** Moving a function to a managed service provider who accepts the risk
- **Service level agreements (SLAs):** Third party accepts financial penalties for failures

**Critical limitation — risk transfer does NOT transfer:**
- Reputational damage (your brand suffers even if a vendor is at fault)
- Legal/regulatory liability (GDPR fines hit the data controller, not just the processor)
- The underlying vulnerability (transfer covers consequences; the weakness remains)

**Insurance terminology:**
- **Deductible:** Amount the organization pays before insurance kicks in
- **Coverage limit:** Maximum the insurer will pay
- **Exclusions:** Events or conditions not covered (read policies carefully — many exclude war, nation-state attacks, or negligence)

#### Mitigate (Treat/Reduce)

**Definition:** Implement controls to reduce the likelihood of the threat occurring, reduce the vulnerability, or reduce the impact if the event occurs.

**Types of controls by objective:**
- **Preventive:** Stop the event from occurring (firewalls, encryption, access controls)
- **Detective:** Identify that an event has occurred or is occurring (IDS, log monitoring, audits)
- **Corrective:** Restore the system after an event (backup restoration, patch deployment)
- **Deterrent:** Discourage threat actors from attempting an attack (warning banners, visible cameras)
- **Compensating:** Alternative control when the primary control cannot be implemented
- **Recovery:** Restore capabilities after an incident (DR plans, alternate processing sites)

**Control categories:**
- **Administrative/Managerial:** Policies, procedures, training, background checks
- **Technical/Logical:** Firewalls, encryption, access control systems
- **Physical/Operational:** Locks, guards, CCTV, mantraps

### Risk Response Decision Matrix

| Risk Level | Typical Response |
|-----------|----------------|
| Critical | Avoid or mitigate immediately; escalate to executive leadership |
| High | Mitigate or transfer; assign owner and remediation timeline |
| Medium | Mitigate or transfer; track in risk register; prioritize appropriately |
| Low | Accept or mitigate; monitor periodically |
| Informational | Accept; document; review in next assessment cycle |

---

## 7. Due Care vs. Due Diligence

### Definitions

**Due Care:** Performing the actions that a reasonably prudent person would take in similar circumstances. Doing the right thing to protect assets and stakeholders. This is about **taking action**.

> "We implemented a firewall, encrypted sensitive data, and trained employees on phishing because those are reasonable security measures for an organization handling this type of data."

**Due Diligence:** Investigating, researching, or verifying before making a decision or taking action. Ensuring decisions are based on appropriate inquiry and analysis. This is about **verifying before acting**.

> "Before selecting this vendor to process patient data, we reviewed their SOC 2 Type 2 report, assessed their security controls, verified their data processing agreement, and confirmed their breach notification capabilities."

### The Critical Distinction

| Concept | Focus | Action | Timing |
|---------|-------|--------|--------|
| Due Care | Doing what's right | Implementing controls | Ongoing operations |
| Due Diligence | Knowing before doing | Research, audit, verify | Before decisions |

**Memory aid:** Due **C**are = **C**ontinual protection. Due **D**iligence = **D**ata gathering before decisions.

### Legal Significance

Both concepts have legal significance in establishing whether an organization acted reasonably:

- **Failure of due care:** Organization knew a risk existed but failed to implement reasonable controls → negligence
- **Failure of due diligence:** Organization made decisions (hired a vendor, deployed a system) without adequate investigation → negligence

**Prudent person rule:** Courts evaluate whether an organization's security measures were those that a reasonably prudent person in the same circumstances would have taken. This standard is flexible — it scales with the sensitivity of the data, the sophistication of the organization, and the known threat environment.

### Liability and Negligence Framework

```
Negligence = Duty + Breach + Causation + Damages

Duty:       Organization had a legal obligation to protect assets/individuals
Breach:     Organization failed to meet the standard of care (due care / due diligence)
Causation:  The breach caused the harm
Damages:    Quantifiable harm resulted
```

If all four elements are present, the organization may be held legally liable.

### Corporate Governance Accountability

- **Board of Directors:** Accountable for ensuring due diligence in setting risk appetite and governance structures; cannot claim ignorance of known material risks
- **C-Suite (CEO, CISO, CIO):** Accountable for due care in implementing security programs commensurate with organizational risk
- **Security Managers:** Accountable for due diligence in selection and implementation of controls

---

## 8. Legal and Regulatory Landscape

### Overview of Law Types

**Criminal law:** Government prosecutes individuals or organizations for violations; penalties include fines, imprisonment; requires "beyond reasonable doubt" standard of proof

**Civil law:** Private parties seek remedies for harm; damages are monetary; lower "preponderance of evidence" standard

**Administrative/Regulatory law:** Government agencies create and enforce regulations; penalties include fines, license revocation, consent decrees

**Private (contract) law:** Enforceable agreements between parties; breach remedies defined in the contract

### FISMA — Federal Information Security Modernization Act (2014)

**Scope:** All federal agencies and federal contractors handling federal information

**Key requirements:**
- Implement NIST RMF (SP 800-37) for all federal information systems
- Categorize systems using FIPS 199 (Low/Moderate/High)
- Select and implement controls from NIST SP 800-53
- Conduct annual security reviews
- Report to OMB and Congress annually
- Continuous monitoring programs (ISCM per NIST SP 800-137)

**FISMA 2014 updates over 2002 version:**
- Shifted authority from OMB to DHS for operational aspects
- Required automated continuous monitoring tools
- Established Government-wide security incident reporting to US-CERT

**Authorizing Official (AO):** Senior federal official accountable for accepting residual risk and issuing Authorization to Operate (ATO)

**Annual FISMA reporting metrics (OMB M-23-10 and successors):**
- % systems with current ATO
- % staff completing security training
- Incident response statistics
- Continuous monitoring coverage

### GDPR — General Data Protection Regulation (EU) 2016/679

**Scope:** Any organization that processes personal data of EU/EEA residents, regardless of where the organization is located (extraterritorial reach)

**Key definitions:**
- **Personal data:** Any information relating to an identified or identifiable natural person (data subject)
- **Processing:** Any operation performed on personal data (collection, storage, use, disclosure, erasure)
- **Controller:** Entity that determines purposes and means of processing
- **Processor:** Entity that processes data on behalf of the controller
- **Data Protection Officer (DPO):** Required for public authorities, large-scale systematic processing, or processing of special categories of data

**Six lawful bases for processing (Article 6):**
1. Consent (freely given, specific, informed, unambiguous)
2. Contract performance
3. Legal obligation
4. Vital interests
5. Public task
6. Legitimate interests (with balancing test)

**Data subject rights (Articles 12-23):**
- Right to be informed (Articles 13, 14)
- Right of access (Article 15)
- Right to rectification (Article 16)
- Right to erasure / "right to be forgotten" (Article 17)
- Right to restrict processing (Article 18)
- Right to data portability (Article 20)
- Right to object (Article 21)
- Rights related to automated decision-making and profiling (Article 22)

**Security requirements (Article 32):**
- Appropriate technical and organizational measures
- Pseudonymization and encryption
- Confidentiality, integrity, availability, and resilience
- Ability to restore data after incidents (backups)
- Regular testing and evaluation of controls

**Breach notification (Articles 33-34):**
- Controller notifies supervisory authority within 72 hours of becoming aware
- If high risk to individuals: notify affected individuals "without undue delay"
- Processor notifies controller without undue delay

**Penalties:**
- Up to €10M or 2% of global annual turnover (lower tier — procedural violations)
- Up to €20M or 4% of global annual turnover (upper tier — core principle violations)

### HIPAA — Health Insurance Portability and Accountability Act (1996)

**Scope:** Covered entities (healthcare providers, health plans, healthcare clearinghouses) and their business associates

**Key rules:**

**Privacy Rule (2003):**
- Regulates use and disclosure of Protected Health Information (PHI)
- PHI = identifiable health information in any form (paper, electronic, oral)
- Minimum Necessary standard: only disclose the minimum PHI needed for the purpose
- Patient rights: access, amendment, accounting of disclosures, confidential communications
- Authorizations required for non-treatment, non-payment, non-operations disclosures

**Security Rule (2003; HITECH 2009):**
- Covers only Electronic PHI (ePHI)
- Three safeguard categories:
  - Administrative: security officer, workforce training, access management, incident response, BCP
  - Physical: facility access, workstation use, device disposal
  - Technical: access control, audit controls, integrity controls, transmission security (encryption)
- **Required vs. Addressable:** Some safeguards are required (must implement); addressable (must implement or document why equivalent alternative is used)

**HITECH Act (2009) enhancements:**
- Extended HIPAA directly to Business Associates (BAs)
- Required breach notification: notify HHS, individuals, and media (if breach affects 500+ in a state)
- Increased penalties (tiered: $100 to $50,000 per violation; $1.5M annual cap per category)
- Strengthened enforcement

**Breach Notification Rule:**
- Notify individuals within 60 days of discovery
- Notify HHS simultaneously
- If 500+ individuals: notify HHS immediately and prominent media in affected area
- "Breach" is presumed unless covered entity/BA can demonstrate low probability of PHI compromise (4-factor risk assessment)

### SOX — Sarbanes-Oxley Act (2002)

**Scope:** Publicly traded companies listed on US stock exchanges and their auditors

**Why IT security professionals care:**
- Section 302: CEO and CFO personally certify financial statement accuracy — they can be held criminally liable
- Section 404: Management must assess internal controls over financial reporting (ICFR); external auditor must attest to management's assessment
- Section 409: Material events must be disclosed to investors rapidly
- IT general controls (ITGCs) are a major component of SOX compliance:
  - Access control to financial systems
  - Change management for financial applications
  - IT operations (backup, disaster recovery)
  - Program development controls

**Common frameworks for SOX ITGC compliance:**
- COSO internal control framework
- COBIT for IT governance
- PCAOB auditing standards (AS 2201)

### PCI DSS — Payment Card Industry Data Security Standard (v4.0)

**Scope:** Any entity that stores, processes, or transmits cardholder data (CHD) or sensitive authentication data (SAD)

**12 Requirements (PCI DSS v4.0):**

| Req | Category | Description |
|-----|----------|------------|
| 1 | Network Security | Install and maintain network security controls |
| 2 | Network Security | Apply secure configurations to all system components |
| 3 | Account Data Protection | Protect stored account data |
| 4 | Account Data Protection | Protect cardholder data with strong cryptography during transmission |
| 5 | Vulnerability Management | Protect all systems from malicious software |
| 6 | Vulnerability Management | Develop and maintain secure systems and software |
| 7 | Access Control | Restrict access to system components and CHD by business need to know |
| 8 | Access Control | Identify users and authenticate access to system components |
| 9 | Access Control | Restrict physical access to cardholder data |
| 10 | Monitoring | Log and monitor all access to system components and CHD |
| 11 | Testing | Test security of systems and networks regularly |
| 12 | Information Security Policy | Support information security with organizational policies and programs |

**Validation levels (Merchant):**
- Level 1: >6M transactions/year → Annual QSA on-site assessment
- Level 2: 1M-6M → Annual SAQ + quarterly network scans
- Level 3: 20K-1M e-commerce → Annual SAQ + quarterly scans
- Level 4: <20K e-commerce or any merchant <1M → Annual SAQ

**Key data protection rules:**
- Primary Account Number (PAN): must be rendered unreadable in storage (hashing, tokenization, encryption)
- CVV/CVC: MUST NEVER be stored after authorization
- Track data (magnetic stripe): MUST NEVER be stored after authorization
- Network segmentation strongly recommended to limit scope

### GLBA — Gramm-Leach-Bliley Act (1999)

**Scope:** Financial institutions (banks, insurance companies, securities firms, financial advisors) — broadly defined

**Three key rules:**

**Financial Privacy Rule (FTC):**
- Requires annual privacy notices to customers
- Customers can opt out of sharing with non-affiliated third parties
- "Non-public personal information" (NPI) must be protected

**Safeguards Rule (FTC, updated 2023):**
- Financial institutions must develop, implement, and maintain a comprehensive information security program
- Designate a qualified individual responsible for security program
- Conduct risk assessments
- Implement safeguards: access controls, encryption, multi-factor authentication, audit trails, incident response plan
- Oversee service providers
- Annual reporting to the Board

**Pretexting Provision:**
- Prohibits social engineering to obtain customer financial information

### Regulatory Landscape Summary Table

| Regulation | Sector | Key Security Requirement | Enforcement Agency |
|-----------|--------|------------------------|-------------------|
| FISMA | Federal government | NIST RMF implementation | OMB, DHS, CISA |
| GDPR | Any org w/ EU data subjects | Article 32 security measures; 72-hr breach notice | EU DPAs (e.g., ICO, CNIL) |
| HIPAA/HITECH | Healthcare | Administrative/Physical/Technical safeguards | HHS OCR |
| SOX | Public companies | ITGC for financial reporting | SEC, PCAOB |
| PCI DSS | Payment card | 12 requirements for CHD protection | Card brands, banks (not government) |
| GLBA | Financial services | Safeguards Rule security program | FTC, banking regulators |
| CCPA/CPRA | CA residents' data | Consumer rights, reasonable security | California AG, CPPA |

---

## 9. Privacy Principles

### OECD Privacy Principles (1980, revised 2013)

The OECD Guidelines on the Protection of Privacy and Transborder Flows of Personal Data established 8 foundational privacy principles that have influenced virtually every privacy framework since.

| Principle | Description |
|-----------|------------|
| **Collection Limitation** | Personal data should be obtained by lawful and fair means; limited to what is necessary; with knowledge/consent of data subject where appropriate |
| **Data Quality** | Personal data should be relevant, accurate, complete, and kept up-to-date as necessary for purpose |
| **Purpose Specification** | Purposes should be specified at time of collection; subsequent use limited to those purposes or compatible ones |
| **Use Limitation** | Data should not be disclosed or used for purposes other than specified (except with consent or legal authority) |
| **Security Safeguards** | Reasonable security safeguards against risks such as loss, unauthorized access, destruction, use, modification, or disclosure |
| **Openness** | Organizations should be transparent about their practices and policies regarding personal data |
| **Individual Participation** | Individuals should have the right to access data about them, challenge it, and have it corrected or erased |
| **Accountability** | Data controllers are accountable for complying with measures that give effect to these principles |

### Fair Information Practice Principles (FIPPs)

Originally formulated in the US Department of HEW (1973) "Records, Computers and the Rights of Citizens" report. Basis for the US Privacy Act (1974) and influential in commercial and government privacy frameworks.

**Eight FIPPs (US government version — OMB A-130):**
1. **Transparency:** Organizations should be transparent about information policies and practices
2. **Individual Participation:** Individuals should have the opportunity to review their records and correct inaccurate information
3. **Purpose Specification:** The purpose for which PII is collected should be specified
4. **Data Minimization:** Only PII that is directly relevant and necessary should be collected
5. **Use Limitation:** PII should be used only as consistent with specified purposes
6. **Data Quality and Integrity:** PII should be accurate, relevant, timely, and complete
7. **Security:** PII should be protected with appropriate operational, administrative, technical, and physical safeguards
8. **Accountability and Auditing:** Organizations should be accountable for compliance and provide ways for violations to be addressed

### EU GDPR Privacy Principles (Article 5)

| GDPR Principle | Description |
|---------------|------------|
| **Lawfulness, fairness and transparency** | Processing must have a legal basis; must be fair; must be transparent to data subjects |
| **Purpose limitation** | Collected for specified, explicit, and legitimate purposes; not further processed in incompatible ways |
| **Data minimisation** | Adequate, relevant, and limited to what is necessary |
| **Accuracy** | Inaccurate data must be erased or rectified without delay |
| **Storage limitation** | Kept in identifiable form no longer than necessary |
| **Integrity and confidentiality** | Processed with appropriate security |
| **Accountability** | Controller responsible for and must be able to demonstrate compliance |

### Privacy-by-Design (PbD) — Ann Cavoukian

Seven foundational principles developed by Ontario Privacy Commissioner Ann Cavoukian; incorporated into GDPR Article 25 as "Data Protection by Design and by Default":

1. Proactive, not reactive; preventive, not remedial
2. Privacy as the default setting
3. Privacy embedded into design (not bolted on)
4. Full functionality — positive-sum, not zero-sum (security AND privacy, not security OR privacy)
5. End-to-end security — full lifecycle protection
6. Visibility and transparency
7. Respect for user privacy — keep it user-centric

### PII, PHI, and Sensitive Categories

**PII (Personally Identifiable Information):**
- NIST definition: "information that can be used to distinguish or trace an individual's identity"
- Direct identifiers: name, SSN, passport number, biometric data
- Indirect identifiers: ZIP code + birthdate + gender (Latanya Sweeney showed 87% of US residents uniquely identified by these three)

**GDPR Special Categories (Article 9) — require explicit consent or other narrow bases:**
- Racial or ethnic origin
- Political opinions
- Religious or philosophical beliefs
- Trade union membership
- Genetic data
- Biometric data (for identification purposes)
- Health data
- Sex life or sexual orientation

**PHI under HIPAA:** 18 HIPAA identifiers that make health information individually identifiable

---

## 10. Business Continuity Planning

### BCP Overview and Lifecycle

Business Continuity Planning (BCP) ensures that critical business functions can continue during and after a significant disruption. It is broader than Disaster Recovery Planning (DRP), which focuses specifically on restoring IT systems.

```
BCP Scope: Entire business (people, processes, partners, facilities)
DRP Scope: IT systems and infrastructure
```

**BCP Lifecycle:**
```
1. Project Initiation and Scope
2. Business Impact Analysis (BIA)
3. Recovery Strategy Development
4. Plan Development
5. Testing and Exercises
6. Maintenance and Update
```

### Business Impact Analysis (BIA)

The BIA is the foundation of the entire BCP. It identifies critical business functions, the impact of their disruption, and the time constraints for recovery.

**BIA process:**
1. **Identify critical business processes** — which processes, if disrupted, would cause significant harm
2. **Identify supporting resources** — people, systems, facilities, vendors, data required for each process
3. **Determine Maximum Tolerable Downtime (MTD)** — maximum time the process can be unavailable before causing unacceptable harm to the organization
4. **Assess impact of disruption** — financial, operational, legal, reputational
5. **Identify interdependencies** — upstream and downstream dependencies between processes and systems

**BIA output:** Ranked list of critical processes with their MTD values; foundation for recovery objective setting

### Recovery Objectives

#### RTO — Recovery Time Objective

**Definition:** The maximum time within which a system or process must be restored after a disruption, to avoid unacceptable consequences.

- Set by the business (based on BIA results)
- Must be ≤ MTD (the system must be restored within the maximum tolerable downtime)
- Drives technical architecture choices (hot site vs. cold site, backup frequency, etc.)

```
Example:
  Order processing system MTD = 4 hours
  RTO = 2 hours (restored within 2 hours to have buffer within MTD)
```

#### RPO — Recovery Point Objective

**Definition:** The maximum amount of data loss an organization can tolerate, measured as the point in time to which data must be recoverable.

- If RPO = 4 hours, backups must occur at least every 4 hours
- Drives backup frequency and replication technology choices

```
Example:
  Financial transactions RPO = 15 minutes
  → Requires near-real-time replication or transaction log shipping

  Internal documents RPO = 24 hours
  → Daily backup is sufficient
```

#### MTTR — Mean Time to Repair/Recover

**Definition:** Average time required to repair a component or system after a failure. Measures the efficiency of the recovery process.

```
MTTR = Total Downtime / Number of Failures
```

#### MTBF — Mean Time Between Failures

**Definition:** Average time a system operates between failures. Measures system reliability.

```
MTBF = Total Uptime / Number of Failures

Availability = MTBF / (MTBF + MTTR)
```

**Example:** A server with MTBF of 10,000 hours and MTTR of 2 hours:
```
Availability = 10,000 / (10,000 + 2) = 99.98%
```

#### RTO, RPO, MTTR, MTBF Relationships

```
Disruption Occurs
       │
       ▼
     RPO ───────────────────────────── Last Good Backup Point
       │                               (How much data we can lose)
       │
       ▼
    Incident Declared
       │
       ▼
    Recovery Begins
       │
       ├─── MTTR ──► System Restored
       │
       └─── RTO = Target for ^^^ (must be < MTD)

MTBF measures gap BETWEEN disruptions (reliability)
```

### Recovery Strategies

**Alternative Site Types:**

| Site Type | Cost | Setup Time | Equipment | Data Currency |
|-----------|------|-----------|-----------|---------------|
| **Hot Site** | Highest | Minutes to hours | Fully configured, operational | Near real-time (replication) |
| **Warm Site** | Medium | Hours to days | Hardware present, software/data needs loading | Periodic (daily/weekly backup) |
| **Cold Site** | Lowest | Days to weeks | Space only; no equipment | Must restore from offsite backup |
| **Mobile Site** | Varies | Hours | Trailer/vehicle with equipment; driven to location | Backup restoration |
| **Cloud DR** | Variable (pay-per-use) | Minutes to hours | Virtualized infrastructure | Snapshot/replication-based |

**Reciprocal Agreement:** Two organizations agree to host each other's operations in a disaster. Low cost, but untested and capacity uncertain — generally not recommended.

**Mutual Aid Agreement:** Similar to reciprocal; common among government agencies

### BCP Testing Types

In increasing order of thoroughness and disruption:

| Test Type | Description | Disruption Level |
|-----------|------------|-----------------|
| **Checklist Review** | Distribute plan; individuals review their sections | None |
| **Structured Walkthrough (Tabletop)** | Team talks through scenario step by step | Minimal |
| **Simulation** | Realistic scenario practice, no actual failover | Low |
| **Parallel Test** | Both primary and alternate sites active simultaneously; DR validates functionality | Medium |
| **Full Interruption Test** | Primary site shut down; operations moved to alternate site | High |

**Best practice:** Tests should proceed from least to most disruptive, building confidence and identifying gaps before attempting higher-risk tests.

**Post-test activities:**
- Document lessons learned
- Update plan based on findings
- Re-test specific areas that failed
- Executive briefing on results

### BCP Key Roles

| Role | Responsibility |
|------|--------------|
| **BCP Coordinator/Manager** | Owns the BCP program; coordinates planning and testing |
| **Executive Sponsor** | Senior leader accountable for BCP; authorizes resources |
| **Business Unit Representatives** | Provide process knowledge; BIA participants; plan implementers |
| **IT/DR Team** | Technical recovery execution |
| **Communications Coordinator** | Internal and external communications during crisis |
| **Damage Assessment Team** | Evaluate impact of disaster; determine recovery path |

---

## 11. Ethics

### (ISC)² Code of Ethics

The (ISC)² Code of Ethics applies to all CISSP holders. Violations can result in revocation of certification.

**Preamble:**
> "Safety of the commonwealth, duty to our principals, and to each other requires that we adhere, and be seen to adhere, to the highest ethical standards of behavior."

**Four Canons (in priority order — higher canons take precedence):**

1. **Protect society, the common good, necessary public trust and confidence, and the infrastructure.**
   - First obligation is to the public and society — even before the employer
   - Must report activities that are a danger to society

2. **Act honorably, honestly, justly, responsibly, and legally.**
   - Tell the truth; keep commitments; refuse to participate in deception or illegal activities

3. **Provide diligent and competent service to principals.**
   - Perform duties with competence; don't accept assignments beyond your ability; don't misrepresent qualifications

4. **Advance and protect the profession.**
   - Support fellow professionals; don't bring shame to the profession; share knowledge ethically

**Key application: When canons conflict:**
- If employer asks you to do something that harms society: Canon 1 (society) takes precedence over Canon 3 (employer)
- If an action is legal but dishonest: Canon 2 (honesty) requires refusing
- Example: A CISSP who discovers their employer is committing fraud has an ethical obligation under Canon 1 to address it, even at risk to their employment

### Computer Ethics Institute — Ten Commandments of Computer Ethics (1992)

While not official (ISC)² material, this framework appears in CISSP study materials:

1. Thou shalt not use a computer to harm other people
2. Thou shalt not interfere with other people's computer work
3. Thou shalt not snoop around in other people's computer files
4. Thou shalt not use a computer to steal
5. Thou shalt not use a computer to bear false witness
6. Thou shalt not copy or use proprietary software for which you have not paid
7. Thou shalt not use other people's computer resources without authorization or proper compensation
8. Thou shalt not appropriate other people's intellectual output
9. Thou shalt think about the social consequences of the program you are writing or the system you are designing
10. Thou shalt always use a computer in ways that ensure consideration and respect for your fellow humans

### Ethical Decision-Making Framework

When facing an ethical dilemma, apply this framework:

1. **Is it legal?** If not, the answer is clear — don't do it.
2. **Does it comply with policy?** If not, either the policy needs updating or the action needs reconsidering.
3. **Is it ethical?** Would you be comfortable if your actions were reported publicly?
4. **Is it consistent with the (ISC)² Code of Ethics?** Apply the canons in order.
5. **What would a prudent security professional do?** Apply the "reasonable professional" standard.

---

## 12. Personnel Security

### Pre-Employment Controls

- **Background checks:** Criminal history, employment verification, education verification, credit check (for financially sensitive positions), reference checks
- **Security clearances:** Government positions may require investigation beyond background checks
- **Non-disclosure agreements (NDAs):** Must be signed before access to sensitive information
- **Employment agreements:** Define responsibilities, acceptable use, ownership of work product

### During Employment Controls

- **Security awareness training:** Annual minimum; role-based training for high-risk positions
- **Separation of duties (SoD):** No single person can control an entire sensitive process end-to-end; reduces fraud and error risk
- **Least privilege:** Access only to what is needed to perform job duties; reviewed regularly
- **Mandatory vacation:** Requires job rotation; can detect fraud (fraudsters often avoid vacations)
- **Job rotation:** Cross-trains employees and makes it harder to sustain ongoing fraud
- **Dual control (two-man rule):** Certain sensitive actions require two authorized individuals present simultaneously
- **Background check refresh:** High-clearance positions may require periodic reinvestigation

### Termination Controls

**Involuntary termination (hostile):**
- Escort from building immediately upon notification
- Disable all access (physical and logical) before or at notification
- Retrieve all equipment, access badges, keys
- Change shared credentials/passwords that the individual knew
- Monitor for suspicious activity immediately after notification

**Voluntary termination (friendly):**
- Exit interview: capture knowledge transfer, collect equipment and credentials
- Transition period with managed access
- Disable access on last day of employment
- Remind of continuing NDA obligations

**Common failure:** Delaying access revocation after termination is one of the most common insider threat vectors. Accounts should be disabled on the employee's last day, not weeks later.

---

## 13. Key Terms Quick Reference

| Term | Definition |
|------|-----------|
| ALE | Annualized Loss Expectancy = ARO × SLE |
| ARO | Annualized Rate of Occurrence (how often per year) |
| ATO | Authorization to Operate (FISMA authorization decision) |
| AV | Asset Value (monetary worth of an asset) |
| BCP | Business Continuity Plan (keeps operations running during disruption) |
| BIA | Business Impact Analysis (identifies critical processes and recovery requirements) |
| CISO | Chief Information Security Officer |
| COSO | Committee of Sponsoring Organizations framework (internal controls) |
| DPO | Data Protection Officer (GDPR required role for some organizations) |
| DRP | Disaster Recovery Plan (focuses on IT system recovery) |
| Due Care | Taking reasonable protective actions |
| Due Diligence | Investigating before making decisions |
| EF | Exposure Factor (% of asset value lost per incident) |
| FIPPs | Fair Information Practice Principles |
| Inherent Risk | Risk before applying any controls |
| MTD | Maximum Tolerable Downtime (BIA output) |
| MTBF | Mean Time Between Failures (reliability metric) |
| MTTR | Mean Time to Repair/Recover (efficiency metric) |
| PHI | Protected Health Information (HIPAA) |
| PII | Personally Identifiable Information |
| Residual Risk | Risk remaining after controls are applied |
| RPO | Recovery Point Objective (maximum acceptable data loss) |
| RTO | Recovery Time Objective (maximum acceptable recovery time) |
| SLE | Single Loss Expectancy = AV × EF |
| Risk Acceptance | Conscious decision to live with a risk as-is |
| Risk Avoidance | Eliminating the activity that creates the risk |
| Risk Mitigation | Implementing controls to reduce risk |
| Risk Transfer | Shifting financial consequences to a third party (insurance, contracts) |

---

*Domain 1 cross-references: Domain 6 (Security Assessment) operationalizes risk assessment; Domain 7 (Security Operations) executes BCP/DRP; All domains implement the policy hierarchy established in Domain 1.*

*Last updated: 2026-03-01 | Reference: CISSP CBK (ISC)², NIST SP 800-30, 800-37, ISO 31000, COSO ERM 2017, COBIT 2019*
