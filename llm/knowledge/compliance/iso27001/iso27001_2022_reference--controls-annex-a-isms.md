# ISO/IEC 27001:2022 — Comprehensive Reference
## ISMS, Clause Structure, Annex A Controls, Certification, and Cross-Framework Mappings

**Standard:** ISO/IEC 27001:2022 (supersedes ISO/IEC 27001:2013)
**Full Title:** Information technology — Security techniques — Information security management systems — Requirements
**Companion Standard:** ISO/IEC 27002:2022 (implementation guidance for Annex A controls)
**Published:** October 2022
**Applicable to:** Any organization, any size, any sector

---

## Table of Contents

1. [What Is an ISMS?](#1-what-is-an-isms)
2. [ISO 27001:2022 Structure Overview](#2-iso-270012022-structure-overview)
3. [Clause 4 — Context of the Organization](#3-clause-4--context-of-the-organization)
4. [Clause 5 — Leadership](#4-clause-5--leadership)
5. [Clause 6 — Planning](#5-clause-6--planning)
6. [Clause 7 — Support](#6-clause-7--support)
7. [Clause 8 — Operation](#7-clause-8--operation)
8. [Clause 9 — Performance Evaluation](#8-clause-9--performance-evaluation)
9. [Clause 10 — Improvement](#9-clause-10--improvement)
10. [Annex A — Control Themes and Controls (2022)](#10-annex-a--control-themes-and-controls-2022)
    - [Theme 5: Organizational Controls (37)](#theme-5-organizational-controls-37)
    - [Theme 6: People Controls (8)](#theme-6-people-controls-8)
    - [Theme 7: Physical Controls (14)](#theme-7-physical-controls-14)
    - [Theme 8: Technological Controls (34)](#theme-8-technological-controls-34)
11. [Risk Assessment Methodology](#11-risk-assessment-methodology)
12. [Statement of Applicability (SoA)](#12-statement-of-applicability-soa)
13. [ISO 27001 vs ISO 27002 Relationship](#13-iso-27001-vs-iso-27002-relationship)
14. [Certification Process](#14-certification-process)
15. [ISO 27001 to NIST 800-53 Control Mapping](#15-iso-27001-to-nist-800-53-control-mapping)
16. [ISO 27001 vs FedRAMP vs SOC 2](#16-iso-27001-vs-fedramp-vs-soc-2)
17. [Key Changes: 2013 to 2022 Edition](#17-key-changes-2013-to-2022-edition)

---

## 1. What Is an ISMS?

An **Information Security Management System (ISMS)** is a systematic, risk-based approach to managing an organization's information security. It is not simply a technology framework — it is a management system that includes people, processes, and technology working together under a defined policy and governance structure.

### Core Concept

The ISMS establishes, implements, maintains, and continually improves information security within the context of the organization. It applies the **Plan-Do-Check-Act (PDCA)** cycle:

| Phase | Description |
|-------|-------------|
| **Plan** | Establish ISMS policy, objectives, processes, and procedures relevant to managing risk |
| **Do** | Implement and operate the ISMS |
| **Check** | Monitor and review performance against policy, objectives, and practical experience |
| **Act** | Take corrective and preventive actions, based on results, to achieve continual improvement |

### What the ISMS Protects

The ISMS protects the **confidentiality, integrity, and availability (CIA)** of information — the three pillars of information security:

- **Confidentiality:** Information is not made available or disclosed to unauthorized individuals, entities, or processes.
- **Integrity:** Information assets and processing methods are accurate, complete, and protected from unauthorized modification.
- **Availability:** Information and associated assets are accessible and usable upon demand by an authorized entity.

### Scope of an ISMS

The ISMS scope can encompass:
- An entire organization
- A specific department or business unit
- A single product or service
- A geographic location
- A particular system or process

The scope must be documented and must consider organizational boundaries, interfaces with other organizations, and dependencies on external parties.

### Why Implement an ISMS?

1. **Demonstrate due diligence** in protecting information assets
2. **Meet regulatory and contractual requirements** (GDPR, HIPAA, government contracts)
3. **Reduce risk** of data breaches, cyber incidents, and operational disruption
4. **Build customer and partner trust** via third-party certification
5. **Systematic risk management** rather than reactive security
6. **Competitive differentiation** and entry into procurement processes requiring ISO 27001

---

## 2. ISO 27001:2022 Structure Overview

ISO 27001:2022 follows the **Harmonized Structure (HS)** (formerly called Annex SL / High-Level Structure), which aligns it with other ISO management system standards (ISO 9001, ISO 22301, ISO 14001, etc.) to facilitate integration.

### Full Standard Structure

| Section | Title | Type |
|---------|-------|------|
| 0 | Introduction | Informative |
| 1 | Scope | Normative |
| 2 | Normative References | Normative |
| 3 | Terms and Definitions | Normative |
| 4 | Context of the Organization | **Mandatory** |
| 5 | Leadership | **Mandatory** |
| 6 | Planning | **Mandatory** |
| 7 | Support | **Mandatory** |
| 8 | Operation | **Mandatory** |
| 9 | Performance Evaluation | **Mandatory** |
| 10 | Improvement | **Mandatory** |
| Annex A | Information Security Controls Reference | Normative (selection is risk-driven) |

> **Critical Note:** Clauses 4 through 10 are **mandatory requirements**. Every SHALL statement in these clauses must be addressed for certification. Annex A controls are referenced normatively — organizations must address all 93 controls in their Statement of Applicability, either by implementing them or justifying exclusion.

### Count of Controls: 2013 vs 2022

| Edition | Domains/Themes | Total Controls |
|---------|---------------|----------------|
| ISO 27001:2013 | 14 domains | 114 controls |
| ISO 27001:2022 | 4 themes | 93 controls |

The 2022 edition reduced apparent control count through consolidation and added 11 new controls not present in the 2013 edition.

### 11 New Controls in 2022 (not in 2013)

| Control ID | Title |
|------------|-------|
| 5.7 | Threat intelligence |
| 5.23 | Information security for use of cloud services |
| 5.30 | ICT readiness for business continuity |
| 6.8 | Information security event reporting |
| 7.4 | Physical security monitoring |
| 8.9 | Configuration management |
| 8.10 | Information deletion |
| 8.11 | Data masking |
| 8.12 | Data leakage prevention |
| 8.16 | Monitoring activities |
| 8.23 | Web filtering |
| 8.28 | Secure coding |

---

## 3. Clause 4 — Context of the Organization

### 4.1 Understanding the Organization and Its Context

The organization must determine **external and internal issues** that are relevant to its purpose and that affect its ability to achieve the intended outcomes of its ISMS.

**External issues include:**
- Legal, regulatory, and contractual environment
- Competitive, market, and technology landscape
- Political, economic, social, and environmental factors
- Relationships with and perceptions of external interested parties

**Internal issues include:**
- Governance, organizational structure, roles, and accountabilities
- Policies, objectives, and strategies
- Capabilities (people, knowledge, processes, technology)
- Culture, values, and norms
- Information systems and decision-making processes

**Common tools:** PESTLE analysis (Political, Economic, Social, Technological, Legal, Environmental), SWOT analysis.

### 4.2 Understanding the Needs and Expectations of Interested Parties

The organization must identify:
1. **Interested parties** (stakeholders) relevant to the ISMS
2. The **requirements** of those interested parties that are relevant to information security

**Typical interested parties:**
- Customers and clients
- Regulatory bodies (NIST, FCA, GDPR supervisory authorities)
- Shareholders and investors
- Suppliers and business partners
- Employees
- Industry bodies
- Law enforcement agencies
- The public

**Requirements may include:**
- Contractual security clauses
- Regulatory mandates
- Service level agreements
- Privacy and data protection requirements

### 4.3 Determining the Scope of the ISMS

The organization must determine the **boundaries and applicability** of the ISMS.

When determining scope, the organization must consider:
- External and internal issues (from 4.1)
- Requirements of interested parties (from 4.2)
- Interfaces and dependencies between activities performed by the organization and those performed by other organizations

**The scope must be available as documented information.**

Scope definition is critical for certification — it defines exactly what will be assessed. A narrow scope may be easier to certify but may not provide the level of assurance customers require.

### 4.4 Information Security Management System

The organization must establish, implement, maintain, and continually improve an ISMS in accordance with the requirements of ISO 27001.

This is the foundational requirement that the entire standard supports.

---

## 4. Clause 5 — Leadership

### 5.1 Leadership and Commitment

**Top management** must demonstrate leadership and commitment by:

- Ensuring the information security policy and objectives are established and compatible with the strategic direction
- Ensuring integration of ISMS requirements into the organization's processes
- Ensuring the resources needed for the ISMS are available
- Communicating the importance of effective information security management
- Ensuring the ISMS achieves its intended outcomes
- Directing persons to contribute to ISMS effectiveness
- Promoting continual improvement
- Supporting other relevant management roles in demonstrating their leadership

> **Key principle:** "Top management" means the person or group of people who directs and controls the organization at the highest level. This cannot be delegated entirely to the IT or security department.

### 5.2 Policy

Top management must establish an **information security policy** that:

- Is appropriate to the purpose of the organization
- Includes information security objectives (or provides a framework for setting them)
- Includes a commitment to satisfy applicable information security requirements
- Includes a commitment to continual improvement of the ISMS
- Is available as documented information
- Is communicated within the organization
- Is available to interested parties as appropriate

**Policy content recommendations:**
- Statement of management intent and support
- High-level objectives (CIA preservation)
- Scope reference
- Compliance obligations
- Consequences of violation
- Review cycle

### 5.3 Organizational Roles, Responsibilities, and Authorities

Top management must ensure that responsibilities and authorities for roles relevant to information security are assigned and communicated.

**Mandatory assignments:**
1. A role responsible for ensuring the ISMS conforms to ISO 27001 requirements
2. A role responsible for reporting on ISMS performance to top management

> In practice, this is often the **CISO** or **Information Security Manager**. In smaller organizations it may be the IT Manager or a designated employee. The standard does not require a dedicated headcount — it requires the responsibility to be clearly assigned.

---

## 5. Clause 6 — Planning

### 6.1 Actions to Address Risks and Opportunities

#### 6.1.1 General

The organization must plan for actions to address:
- **Risks** — potential negative impacts on ISMS objectives
- **Opportunities** — potential to enhance information security outcomes

Actions must be proportionate to the potential impact on conformity of products and services.

#### 6.1.2 Information Security Risk Assessment

The organization must define and apply an information security risk assessment process that:

**a) Establishes and maintains information security risk criteria:**
- Risk acceptance criteria
- Criteria for performing information security risk assessments

**b) Ensures repeated risk assessments produce consistent, valid, and comparable results**

**c) Identifies information security risks:**
- Apply the risk assessment process to identify risks associated with the loss of confidentiality, integrity, and availability
- Identify the risk owners

**d) Analyzes the information security risks:**
- Assess the potential consequences if risks were to materialize
- Assess the realistic likelihood of occurrence
- Determine risk levels

**e) Evaluates the information security risks:**
- Compare results of risk analysis with established risk criteria
- Prioritize risks for treatment

**Output:** Documented risk assessment results

#### 6.1.3 Information Security Risk Treatment

The organization must define and apply a risk treatment process to:

**a) Select appropriate risk treatment options:**

| Option | Description |
|--------|-------------|
| **Modify** (mitigate) | Implement controls to reduce likelihood or impact |
| **Retain** (accept) | Consciously accept the risk within risk acceptance criteria |
| **Avoid** | Eliminate the activity or condition that gives rise to the risk |
| **Share** (transfer) | Transfer risk to insurance, outsourcing, or contractual arrangement |

**b) Determine all controls necessary for the risk treatment plan**

**c) Compare controls with Annex A** to verify no necessary controls have been overlooked

**d) Produce a Statement of Applicability (SoA)** that contains:
- Necessary controls
- Justification for their inclusion
- Whether they are implemented or not
- Justification for the exclusion of any Annex A controls

**e) Formulate an information security risk treatment plan**

**f) Obtain risk owner approval of the risk treatment plan and acceptance of residual risks**

**Output:** Documented risk treatment results, Statement of Applicability, risk treatment plan

### 6.2 Information Security Objectives and Planning to Achieve Them

Information security objectives must:
- Be consistent with the information security policy
- Be measurable (if practicable)
- Take into account applicable information security requirements, and results from risk assessment and treatment
- Be communicated
- Be updated as appropriate
- Be available as documented information

**Planning for achieving objectives must include:**
- What will be done
- What resources will be required
- Who will be responsible
- When it will be completed
- How results will be evaluated

### 6.3 Planning of Changes

When the organization determines the need for changes to the ISMS, the changes must be carried out in a **planned manner**.

> This is a 2022 addition. Changes to the ISMS (scope changes, major process changes, significant infrastructure changes) must go through a defined change management process to prevent unintended disruption to the ISMS.

---

## 6. Clause 7 — Support

### 7.1 Resources

The organization must determine and provide the **resources needed** for the establishment, implementation, maintenance, and continual improvement of the ISMS.

Resources include: budget, personnel (trained staff), technology, facilities, time.

### 7.2 Competence

The organization must:
- Determine the necessary competence of persons doing work under its control that affects information security performance
- Ensure those persons are competent on the basis of appropriate education, training, or experience
- Where applicable, take actions to acquire necessary competence and evaluate effectiveness
- Retain appropriate documented information as evidence of competence

**Competence areas may include:**
- Information security risk assessment and treatment
- Security architecture and engineering
- Incident response
- Audit and compliance
- Legal and regulatory knowledge

### 7.3 Awareness

Persons doing work under the organization's control must be aware of:
- The information security policy
- Their contribution to the effectiveness of the ISMS, including benefits of improved performance
- The implications of not conforming to ISMS requirements

**Awareness program elements:**
- Onboarding security training
- Annual security awareness refreshers
- Role-specific training (developers, admins, executives)
- Phishing simulation
- Security newsletters and communications

### 7.4 Communication

The organization must determine the need for internal and external communications relevant to the ISMS, including:
- On what topics to communicate
- When to communicate
- With whom to communicate
- How to communicate

**Internal communications:** Security policy distribution, incident notifications, audit results, management review outputs, awareness campaigns.

**External communications:** Regulatory reporting, incident disclosure to customers, communications with third parties, communications with certification bodies.

### 7.5 Documented Information

#### 7.5.1 General

The ISMS must include:
- Documented information required by ISO 27001
- Documented information determined by the organization as necessary for effectiveness

The extent of documented information depends on the organization's size, type, activities, complexity, and competence of personnel.

#### 7.5.2 Creating and Updating

When creating and updating documented information, the organization must ensure:
- Appropriate identification and description (title, date, author, reference number)
- Appropriate format (language, software version, graphics) and media (paper, electronic)
- Appropriate review and approval for suitability and adequacy

#### 7.5.3 Control of Documented Information

Documented information required by the ISMS must be controlled to ensure:
- It is available and suitable for use, where and when it is needed
- It is adequately protected (confidentiality, improper use, loss of integrity)
- Distribution, access, retrieval, and use are controlled
- Storage and preservation (including legibility) are controlled
- Change control is applied
- Retention and disposition are controlled

**Required documented information under ISO 27001 includes:**
- ISMS scope
- Information security policy
- Risk assessment process
- Risk treatment process
- Risk assessment results
- Risk treatment plan
- Statement of Applicability
- Information security objectives
- Evidence of competence
- Operational planning results
- Results of monitoring and measurement
- Internal audit program and results
- Management review results
- Nature of nonconformities and corrective actions

---

## 7. Clause 8 — Operation

### 8.1 Operational Planning and Control

The organization must plan, implement, control, monitor, and review the processes needed to meet information security requirements, and implement the actions determined in Clause 6, by:
- Establishing criteria for the processes
- Implementing control of processes in accordance with the criteria
- Retaining documented information to the extent necessary to have confidence that the processes have been carried out as planned

The organization must also control planned changes and review unintended changes, taking action as necessary to mitigate adverse effects.

The organization must ensure that externally provided processes, products, or services relevant to the ISMS are controlled.

### 8.2 Information Security Risk Assessment

The organization must perform information security risk assessments at **planned intervals** or when **significant changes** are proposed or occur.

The risk assessment must be performed with consideration for criteria established in 6.1.2.

**Risk assessment triggers:**
- Annual planned review
- Significant change to IT systems or infrastructure
- Significant change to business processes
- New regulatory requirements
- Major security incidents
- Mergers, acquisitions, or significant organizational changes
- Introduction of new technologies or services

**Output:** Retained as documented information.

### 8.3 Information Security Risk Treatment

The organization must implement the information security risk treatment plan.

**Output:** Retain documented information of the results of the information security risk treatment.

---

## 8. Clause 9 — Performance Evaluation

### 9.1 Monitoring, Measurement, Analysis, and Evaluation

The organization must evaluate the performance and effectiveness of the ISMS.

The organization must determine:
- What needs to be monitored and measured (processes, controls, objectives)
- Methods for monitoring, measurement, analysis, and evaluation (ensuring valid results)
- When monitoring and measuring will be performed
- Who will monitor and measure
- When results will be analyzed and evaluated
- Who will analyze and evaluate results

**Output:** Retained as documented information as evidence of results.

**Typical metrics and KPIs:**
- Number and severity of security incidents
- Patch compliance percentage
- Vulnerability scan results and remediation times
- Access review completion rates
- Security awareness training completion rates
- Audit finding closure rates
- ISMS objective achievement status
- Control effectiveness ratings

### 9.2 Internal Audit

#### 9.2.1 General

The organization must conduct internal audits at planned intervals to provide information on whether the ISMS:
- Conforms to the organization's own requirements for its ISMS
- Conforms to the requirements of ISO 27001
- Is effectively implemented and maintained

#### 9.2.2 Internal Audit Programme

The organization must:
- Plan, establish, implement, and maintain an audit program(me) including frequency, methods, responsibilities, planning requirements, and reporting
- Define audit criteria and scope for each audit
- Select auditors and conduct audits to ensure objectivity and impartiality of the audit process
- Ensure results are reported to relevant management
- Retain documented information as evidence of the audit programme and results

**Internal audit requirements:**
- Auditors must not audit their own work (objectivity requirement)
- Can be internal staff with appropriate training or external consultants
- Must cover all applicable ISMS requirements over the audit cycle
- Findings must be tracked and remediated

### 9.3 Management Review

#### 9.3.1 General

Top management must review the organization's ISMS at planned intervals to ensure its continuing suitability, adequacy, and effectiveness.

#### 9.3.2 Management Review Inputs

Management review must include consideration of:
- Status of actions from previous management reviews
- Changes in external and internal issues relevant to the ISMS
- Changes in needs and expectations of interested parties
- Feedback on information security performance, including trends in:
  - Nonconformities and corrective actions
  - Monitoring and measurement results
  - Audit results
  - Fulfilment of information security objectives
- Feedback from interested parties
- Results of risk assessment and status of risk treatment plan
- Opportunities for continual improvement

#### 9.3.3 Management Review Results

Outputs of the management review must include decisions related to:
- Opportunities for continual improvement
- Any need for changes to the ISMS

**Output:** Retained as documented information as evidence of management review results.

---

## 9. Clause 10 — Improvement

### 10.1 Continual Improvement

The organization must continually improve the suitability, adequacy, and effectiveness of the ISMS.

Continual improvement can be driven by:
- Internal audit findings
- Corrective actions
- Management review outputs
- Changes in risk landscape
- New threats and vulnerabilities
- Lessons learned from incidents
- Benchmarking against industry standards

### 10.2 Nonconformity and Corrective Action

When a nonconformity occurs, the organization must:

**a) React to the nonconformity:**
- Take action to control and correct it
- Deal with the consequences

**b) Evaluate the need for action to eliminate the causes:**
- Review the nonconformity
- Determine the causes of the nonconformity
- Determine if similar nonconformities exist, or could potentially occur

**c) Implement any action needed**

**d) Review the effectiveness of any corrective action taken**

**e) Make changes to the ISMS if necessary**

**Output:** Documented information as evidence of:
- The nature of the nonconformities and any subsequent actions taken
- Results of any corrective action

**Nonconformity types:**
- **Major nonconformity:** Systematic failure or complete absence of a required element — will prevent certification
- **Minor nonconformity:** Isolated failure or partial implementation — must be corrected within agreed timeframe
- **Observation/opportunity for improvement:** Not a formal nonconformity but auditor recommendation

---

## 10. Annex A — Control Themes and Controls (2022)

The 2022 edition reorganizes controls into **4 themes** (replacing 14 domains from the 2013 edition). There are **93 controls** total.

Each control is tagged with five attributes:
1. **Control type:** Preventive / Detective / Corrective
2. **Information security properties:** Confidentiality / Integrity / Availability
3. **Cybersecurity concepts:** Identify / Protect / Detect / Respond / Recover
4. **Operational capabilities:** Governance, Asset management, etc.
5. **Security domains:** Governance and Ecosystem / Protection / Defence / Resilience

---

### Theme 5: Organizational Controls (37)

| Control ID | Control Title | Description Summary |
|------------|---------------|---------------------|
| 5.1 | Policies for information security | Define, approve, publish, communicate, and regularly review an information security policy and topic-specific policies |
| 5.2 | Information security roles and responsibilities | Define and allocate information security responsibilities per the organization's information security policy |
| 5.3 | Segregation of duties | Conflicting duties and areas of responsibility shall be segregated to reduce opportunities for unauthorized or unintentional modification or misuse of assets |
| 5.4 | Management responsibilities | Management shall require all personnel to apply information security in accordance with established policies, topic-specific policies, and procedures |
| 5.5 | Contact with authorities | The organization shall establish and maintain contact with relevant authorities (law enforcement, regulatory bodies) |
| 5.6 | Contact with special interest groups | Maintain contact with special interest groups (ISACs, security forums, professional associations) for security intelligence |
| 5.7 | Threat intelligence | **NEW in 2022.** Collect and analyze information about information security threats to produce threat intelligence |
| 5.8 | Information security in project management | Information security shall be integrated into project management across all types of projects |
| 5.9 | Inventory of information and other associated assets | Develop and maintain an inventory of information and other associated assets, including owners |
| 5.10 | Acceptable use of information and other associated assets | Rules for acceptable use and procedures for handling information and assets |
| 5.11 | Return of assets | Personnel and other interested parties shall return organizational assets upon change or termination of employment |
| 5.12 | Classification of information | Classify information according to its need for protection based on confidentiality requirements |
| 5.13 | Labelling of information | Develop and implement appropriate information labelling procedures in accordance with the information classification scheme |
| 5.14 | Information transfer | Define and implement transfer rules, procedures, or agreements for all types of transfer |
| 5.15 | Access control | Define and implement rules for physical and logical access to information and assets based on business and information security requirements |
| 5.16 | Identity management | Manage the full life cycle of identities — creation, maintenance, and removal |
| 5.17 | Authentication information | Manage the allocation and management of authentication information through a formal management process |
| 5.18 | Access rights | Provision, review, modify, and remove access rights according to the topic-specific policy on access control |
| 5.19 | Information security in supplier relationships | Define and implement processes and procedures to manage information security risks associated with the use of supplier products or services |
| 5.20 | Addressing information security within supplier agreements | Establish relevant information security requirements with each supplier based on the type of supplier relationship |
| 5.21 | Managing information security in the ICT supply chain | Define and implement processes and procedures to manage information security risks associated with the ICT supply chain |
| 5.22 | Monitoring, review, and change management of supplier services | Regularly monitor, review, evaluate, and manage changes to supplier information security practices and service delivery |
| 5.23 | Information security for use of cloud services | **NEW in 2022.** Establish and manage information security for cloud service acquisition, use, management, and exit |
| 5.24 | Information security incident management planning and preparation | Plan and prepare for managing information security incidents by defining processes, roles, and responsibilities |
| 5.25 | Assessment and decision on information security events | Assess events and decide if they are to be classified as information security incidents |
| 5.26 | Response to information security incidents | Respond to information security incidents in accordance with documented procedures |
| 5.27 | Learning from information security incidents | Apply knowledge gained from analyzing and resolving information security incidents to reduce likelihood or impact of future incidents |
| 5.28 | Collection of evidence | Establish and implement procedures for identification, collection, acquisition, and preservation of evidence related to information security events |
| 5.29 | Information security during disruption | Plan how to maintain information security during disruption |
| 5.30 | ICT readiness for business continuity | **NEW in 2022.** Plan, implement, maintain, and test ICT readiness based on business continuity objectives and ICT continuity requirements |
| 5.31 | Legal, statutory, regulatory, and contractual requirements | Identify, document, and keep up to date all relevant legal, statutory, regulatory, and contractual requirements and the organization's approach to meeting these |
| 5.32 | Intellectual property rights | Implement appropriate procedures to protect intellectual property rights |
| 5.33 | Protection of records | Protect records from loss, destruction, falsification, unauthorized access, and unauthorized release |
| 5.34 | Privacy and protection of PII | Identify and meet requirements regarding the preservation of privacy and protection of PII |
| 5.35 | Independent review of information security | Review the organization's approach to managing information security and its implementation (including people, processes, and technologies) independently at planned intervals or when significant changes occur |
| 5.36 | Compliance with policies, rules, and standards for information security | Regularly review compliance with the organization's information security policy, topic-specific policies, rules, and standards |
| 5.37 | Documented operating procedures | Document operating procedures for information processing facilities and make them available to personnel who need them |

---

### Theme 6: People Controls (8)

| Control ID | Control Title | Description Summary |
|------------|---------------|---------------------|
| 6.1 | Screening | Background verification checks on all candidates for employment shall be carried out prior to joining the organization, in accordance with applicable laws, regulations, and ethical standards |
| 6.2 | Terms and conditions of employment | Employment contractual agreements shall state the personnel's and organization's responsibilities for information security |
| 6.3 | Information security awareness, education, and training | Personnel and relevant interested parties shall receive appropriate awareness education and training and regular updates in the organization's information security policy, topic-specific policies, and procedures |
| 6.4 | Disciplinary process | A disciplinary process shall be formalized and communicated to take actions against personnel and other relevant interested parties who have committed information security policy violations |
| 6.5 | Responsibilities after termination or change of employment | Information security responsibilities and duties that remain valid after termination or change of employment shall be defined, enforced, and communicated to relevant personnel and other interested parties |
| 6.6 | Confidentiality or non-disclosure agreements | Confidentiality or non-disclosure agreements reflecting the organization's needs for protection of information shall be identified, documented, regularly reviewed, and signed by personnel and other relevant interested parties |
| 6.7 | Remote working | Security measures shall be implemented when personnel are working remotely to protect information accessed, processed, or stored outside the organization's premises |
| 6.8 | Information security event reporting | **NEW in 2022.** The organization shall provide a mechanism for personnel to report observed or suspected information security events through appropriate channels in a timely manner |

---

### Theme 7: Physical Controls (14)

| Control ID | Control Title | Description Summary |
|------------|---------------|---------------------|
| 7.1 | Physical security perimeters | Define and use security perimeters to protect areas that contain information and other associated assets |
| 7.2 | Physical entry | Secure areas shall be protected by appropriate entry controls and access points to ensure only authorized personnel are allowed access |
| 7.3 | Securing offices, rooms, and facilities | Physical security for offices, rooms, and facilities shall be designed and implemented |
| 7.4 | Physical security monitoring | **NEW in 2022.** Premises shall be continuously monitored for unauthorized physical access |
| 7.5 | Protecting against physical and environmental threats | Design and implement protection against physical and environmental threats such as natural disasters and other intentional or unintentional physical threats |
| 7.6 | Working in secure areas | Security measures for working in secure areas shall be designed and implemented |
| 7.7 | Clear desk and clear screen | Clear desk rules for papers and removable storage media and clear screen rules for information processing facilities shall be defined and appropriately enforced |
| 7.8 | Equipment siting and protection | Equipment shall be sited securely and protected from environmental and physical threats |
| 7.9 | Security of assets off-premises | Off-site assets shall be protected, taking into account the different risks of working outside the organization's premises |
| 7.10 | Storage media | Storage media shall be managed through their life cycle of acquisition, use, transportation, and disposal in accordance with the organization's classification scheme and handling requirements |
| 7.11 | Supporting utilities | Information processing facilities shall be protected from power failures and other disruptions caused by failures in supporting utilities |
| 7.12 | Cabling security | Cables carrying power, data, or supporting information services shall be protected from interception, interference, or damage |
| 7.13 | Equipment maintenance | Equipment shall be maintained correctly to ensure availability, integrity, and confidentiality of information |
| 7.14 | Secure disposal or re-use of equipment | Items of equipment containing storage media shall be verified to ensure that any sensitive data and licensed software has been removed or securely overwritten prior to disposal or re-use |

---

### Theme 8: Technological Controls (34)

| Control ID | Control Title | Description Summary |
|------------|---------------|---------------------|
| 8.1 | User endpoint devices | Information stored on, processed by, or accessible via user endpoint devices shall be protected |
| 8.2 | Privileged access rights | The allocation and use of privileged access rights shall be restricted and managed |
| 8.3 | Information access restriction | Access to information and other associated assets shall be restricted in accordance with the established topic-specific policy on access control |
| 8.4 | Access to source code | Read and write access to source code, development tools, and software libraries shall be appropriately managed |
| 8.5 | Secure authentication | Secure authentication technologies and procedures shall be implemented based on information access restrictions and the topic-specific policy on access control |
| 8.6 | Capacity management | The use of resources shall be monitored and adjusted in line with current and expected capacity requirements |
| 8.7 | Protection against malware | Protection against malware shall be implemented and supported by appropriate user awareness |
| 8.8 | Management of technical vulnerabilities | Information about technical vulnerabilities of information systems in use shall be obtained in a timely fashion, the organization's exposure to such vulnerabilities evaluated, and appropriate measures taken |
| 8.9 | Configuration management | **NEW in 2022.** Configurations, including security configurations, of hardware, software, services, and networks shall be established, documented, implemented, monitored, and reviewed |
| 8.10 | Information deletion | **NEW in 2022.** Information stored in information systems, devices, or in any other storage media shall be deleted when no longer required |
| 8.11 | Data masking | **NEW in 2022.** Data masking shall be used in accordance with the organization's topic-specific policy on access control and other related topic-specific policies and business requirements |
| 8.12 | Data leakage prevention | **NEW in 2022.** Data leakage prevention measures shall be applied to systems, networks, and any other devices that process, store, or transmit sensitive information |
| 8.13 | Information backup | Backup copies of information, software, and systems shall be maintained and regularly tested in accordance with the agreed topic-specific policy on backup |
| 8.14 | Redundancy of information processing facilities | Information processing facilities shall be implemented with sufficient redundancy to meet availability requirements |
| 8.15 | Logging | Logs that record activities, exceptions, faults, and other relevant events shall be produced, stored, protected, and analyzed |
| 8.16 | Monitoring activities | **NEW in 2022.** Networks, systems, and applications shall be monitored for anomalous behavior and appropriate actions taken to evaluate potential information security incidents |
| 8.17 | Clock synchronization | The clocks of information processing systems used by the organization shall be synchronized to approved time sources |
| 8.18 | Use of privileged utility programs | The use of utility programs that might be capable of overriding system and application controls shall be restricted and tightly controlled |
| 8.19 | Installation of software on operational systems | Procedures and measures shall be implemented to securely manage software installation on operational systems |
| 8.20 | Networks security | Networks and network devices shall be secured, managed, and controlled to protect information in systems and applications |
| 8.21 | Security of network services | Security mechanisms, service levels, and service requirements of network services shall be identified, implemented, and monitored |
| 8.22 | Segregation of networks | Groups of information services, users, and information systems shall be segregated in the organization's networks |
| 8.23 | Web filtering | **NEW in 2022.** Access to external websites shall be managed to reduce exposure to malicious content |
| 8.24 | Use of cryptography | Rules for the effective use of cryptography, including cryptographic key management, shall be defined and implemented |
| 8.25 | Secure development life cycle | Rules for the secure development of software and systems shall be established and applied |
| 8.26 | Application security requirements | Information security requirements shall be identified, specified, and approved when developing or acquiring applications |
| 8.27 | Secure system architecture and engineering principles | Principles for engineering secure systems shall be established, documented, maintained, and applied to any information system development or integration activities |
| 8.28 | Secure coding | **NEW in 2022.** Secure coding principles shall be applied to software development |
| 8.29 | Security testing in development and acceptance | Security testing processes shall be defined and implemented in the development life cycle |
| 8.30 | Outsourced development | The organization shall direct, monitor, and review the activities related to outsourced system development |
| 8.31 | Separation of development, test, and production environments | Development, testing, and production environments shall be separated and secured |
| 8.32 | Change management | Changes to information processing facilities and information systems shall be subject to change management procedures |
| 8.33 | Test information | Test information shall be appropriately selected, protected, and managed |
| 8.34 | Protection of information systems during audit testing | Audit tests and other assurance activities involving assessment of operational systems shall be planned and agreed between the tester and appropriate management |

---

## 11. Risk Assessment Methodology

### ISO 31000 Alignment

ISO 27001 aligns with **ISO 31000:2018 (Risk Management — Guidelines)** for its risk management approach. The risk assessment process must be systematic, analytical, and structured.

### Risk Assessment Approaches

ISO 27001 does not mandate a specific risk assessment methodology. Common approaches include:

| Methodology | Description |
|-------------|-------------|
| **Asset-based** | Identify assets → threats → vulnerabilities → calculate risk |
| **Scenario-based** | Define threat scenarios → assess likelihood and impact |
| **Process-based** | Map processes → identify where information is used → assess risks to processes |
| **Qualitative** | Risk rated High/Medium/Low using descriptive scales |
| **Semi-quantitative** | Numerical scales (1-5) for likelihood and impact; risk = L × I |
| **Quantitative** | Financial/probabilistic estimates (ALE = ARO × SLE); resource-intensive |

### Mandatory Elements of the Risk Assessment

Regardless of methodology chosen, the process MUST:

1. **Define risk criteria:**
   - Risk acceptance threshold (e.g., risks rated "Medium" or above require treatment)
   - Likelihood scale definition
   - Impact scale definition (consider CIA impact levels)

2. **Identify risks:**
   - Assets in scope (from asset inventory)
   - Threats to those assets
   - Vulnerabilities that could be exploited
   - Existing controls (current state)
   - Risk owners (accountable persons)

3. **Analyze risks:**
   - Likelihood of occurrence (considering existing controls)
   - Consequence/impact if risk materializes
   - Determine current risk level

4. **Evaluate risks:**
   - Compare to risk acceptance criteria
   - Produce prioritized list of risks for treatment

### Risk Treatment Options

| Treatment Option | ISO 27001 Term | Practical Meaning |
|-----------------|---------------|-------------------|
| Mitigate | Modify | Implement controls from Annex A or elsewhere |
| Accept | Retain | Document acceptance, obtain management sign-off |
| Avoid | Avoid | Cease the activity creating the risk |
| Transfer | Share | Insurance, outsourcing, contractual arrangements |

### Risk Register Requirements

The risk register is a key artifact. It should capture:

- Risk ID
- Risk description
- Asset(s) affected
- Threat and vulnerability
- Risk owner
- Inherent risk level (before controls)
- Existing controls
- Residual risk level (after existing controls)
- Treatment decision
- Planned additional controls
- Target risk level
- Treatment timeline
- Residual risk after treatment
- Risk acceptance (if retained)

---

## 12. Statement of Applicability (SoA)

The **Statement of Applicability (SoA)** is a key ISMS document and a **mandatory certification artifact**. It bridges the gap between the risk assessment/treatment process and the Annex A controls.

### Required Content of the SoA

For each of the 93 Annex A controls, the SoA must state:

1. **Whether the control is applicable or not applicable**
2. **Justification for inclusion** (which risk(s) or requirement(s) necessitate the control)
3. **Whether the control is currently implemented**
4. **Justification for exclusion** (if a control is deemed not applicable)

### Structure of the SoA

| Column | Description |
|--------|-------------|
| Control ID | e.g., 5.7, 8.2 |
| Control Title | e.g., Threat intelligence |
| Applicable (Y/N) | Is this control included in scope? |
| Justification for Inclusion | Risk reference, legal requirement, contractual obligation, or best practice |
| Implementation Status | Implemented / Partially Implemented / Planned / Not Implemented |
| Justification for Exclusion | If N/A: explain why (no asset of that type, risk does not apply, etc.) |

### Common Exclusion Justifications

- "7.14 Secure disposal — Not applicable: organization operates entirely in cloud; no physical hardware to dispose"
- "8.4 Access to source code — Not applicable: organization does not develop software"
- "8.33 Test information — Not applicable: no development environment maintained"

> **Caution:** Exclusions must be defensible. Auditors will challenge weak exclusion justifications. Excluding a control does not eliminate the underlying risk — it means the organization accepts it or addresses it another way.

### SoA as a Living Document

The SoA must be:
- Reviewed at least annually or when significant changes occur
- Updated to reflect changes in scope, risk assessment results, or control implementation status
- Version controlled
- Available to the certification body

---

## 13. ISO 27001 vs ISO 27002 Relationship

| Attribute | ISO 27001 | ISO 27002 |
|-----------|-----------|-----------|
| **Purpose** | Requirements for ISMS (auditable) | Guidance for implementing controls |
| **Nature** | Normative (SHALL statements) | Informative (guidance, SHOULD/MAY) |
| **Certification** | Organizations are certified against this | Cannot be certified against 27002 |
| **Annex A** | Lists 93 controls with brief descriptions | Provides detailed implementation guidance for same 93 controls |
| **Use** | Defines what you must do | Explains how to do it |
| **Audience** | Management, auditors, certification bodies | Security practitioners, implementers |

### How They Work Together

1. **ISO 27001 Clause 6.1.3** requires organizations to compare their controls against Annex A and produce a Statement of Applicability
2. **Annex A** provides a reference list of 93 controls with brief control names and purposes
3. **ISO 27002** provides the detailed "how to" guidance for each of those same 93 controls, including:
   - Purpose of the control
   - Implementation guidance
   - Other information (supplementary context)

**Example:** Annex A 8.8 says "Manage technical vulnerabilities" in one sentence. ISO 27002 8.8 provides 2+ pages covering vulnerability scanning, patch management processes, timelines, emergency patching, risk acceptance when patches cannot be applied, etc.

### Other Standards in the ISO 27000 Family

| Standard | Title |
|----------|-------|
| ISO 27000 | Overview and vocabulary |
| ISO 27001 | ISMS requirements |
| ISO 27002 | Information security controls (implementation guide) |
| ISO 27003 | ISMS implementation guidance |
| ISO 27004 | Information security management measurement |
| ISO 27005 | Information security risk management |
| ISO 27006 | Requirements for certification bodies |
| ISO 27007 | Guidelines for ISMS auditing |
| ISO 27017 | Cloud security controls (extension of 27002 for cloud) |
| ISO 27018 | Protecting PII in public clouds |
| ISO 27701 | Privacy Information Management System (PIMS) — extends 27001/27002 for GDPR |

---

## 14. Certification Process

ISO 27001 certification is conducted by accredited **Certification Bodies (CBs)**, also known as Registrars. In the US, accreditation is typically through **ANAB** (ANSI National Accreditation Board) or **IAS**. Globally, accreditation bodies include **UKAS** (UK), **DAkkS** (Germany), **RvA** (Netherlands).

### Pre-Certification Requirements

Before engaging a certification body, the organization should:

1. Define and document ISMS scope
2. Complete risk assessment and treatment
3. Produce Statement of Applicability
4. Implement required controls
5. Operate the ISMS for a minimum period (typically 3+ months to show evidence of operation)
6. Conduct at least one internal audit cycle
7. Conduct at least one management review

### Stage 1 Audit (Documentation Review)

**Purpose:** Assess ISMS readiness and review documentation

**Activities:**
- Review of ISMS documentation (policies, procedures, risk assessment, SoA, etc.)
- Review of scope to confirm it is adequately defined
- Confirm understanding of ISMS and how it operates
- Identify areas of concern to focus Stage 2 audit

**Outputs:**
- Stage 1 audit report
- List of issues to be addressed before Stage 2 (non-conformities, areas to clarify)
- Confirmation of readiness to proceed to Stage 2 (or recommendation to delay)

**Duration:** Typically 1-3 days on-site or remote

**Timing:** Stage 2 must follow Stage 1, typically within 6 months

### Stage 2 Audit (Certification Audit)

**Purpose:** Determine whether the ISMS is effectively implemented and operated

**Activities:**
- Interview key personnel across all ISMS roles
- Review evidence of ISMS operation (logs, records, meeting minutes, training records)
- Test control effectiveness through sampling and observation
- Verify all applicable Annex A controls are addressed
- Confirm risk assessment and treatment are appropriate and complete
- Assess all clauses 4-10 against evidence

**Findings classification:**
| Finding Type | Definition | Impact on Certification |
|-------------|------------|------------------------|
| **Major nonconformity** | Systematic failure or complete absence of a requirement | Certification cannot be granted until resolved |
| **Minor nonconformity** | Isolated or partial failure of a requirement | Must be corrected within agreed timeframe (typically 3 months) |
| **Observation / OFI** | Not a conformity issue; suggested improvement | No formal requirement to act |

**Duration:** Depends on organization size. ISMS certification audits are sized in "man-days" using ISO/IEC 27006 tables based on employee count.

**Example audit day estimates (Stage 2):**
| Employees | Approximate Stage 2 Days |
|-----------|--------------------------|
| 1-10 | 2-3 days |
| 11-25 | 3-4 days |
| 26-100 | 4-5 days |
| 101-250 | 5-6 days |
| 251-500 | 6-8 days |

### Certification Award

Upon successful completion of Stage 2 (with all major nonconformities resolved):
- Certificate issued for **3-year validity**
- Certificate lists: organization name, scope, standard version, issue date, expiry date

### Surveillance Audits

- **Year 1 surveillance:** Within 12 months of initial certification
- **Year 2 surveillance:** Within 12 months of Year 1 surveillance
- Surveillance audits are shorter than the initial certification audit
- Auditors verify continued compliance and address any changes

### Recertification Audit

- At the end of the 3-year cycle
- Full re-audit (similar to initial certification)
- If passed: certificate renewed for another 3 years

### Transition from ISO 27001:2013 to ISO 27001:2022

Organizations certified to the 2013 edition had until **October 31, 2025** to transition to the 2022 edition. All certificates issued against the 2013 edition expired by that date.

---

## 15. ISO 27001 to NIST 800-53 Control Mapping

The following table maps key ISO 27001:2022 Annex A controls to their closest NIST SP 800-53 Rev 5 control family equivalents. This mapping is approximate — direct one-to-one correspondence does not exist in all cases.

| ISO 27001:2022 Control | ISO Control Title | NIST 800-53 Control(s) | NIST Control Family |
|------------------------|-------------------|------------------------|---------------------|
| 5.1 | Policies for information security | PL-1, PM-1 | Planning, Program Management |
| 5.2 | Information security roles and responsibilities | PM-2, AC-5, PS-7 | Program Mgmt, Access Control, Personnel |
| 5.3 | Segregation of duties | AC-5 | Access Control |
| 5.7 | Threat intelligence | SI-5, PM-16 | System & Info Integrity, Program Mgmt |
| 5.9 | Inventory of information and other associated assets | CM-8 | Configuration Management |
| 5.12 | Classification of information | RA-2 | Risk Assessment |
| 5.15 | Access control | AC-1, AC-2, AC-3 | Access Control |
| 5.16 | Identity management | IA-1, IA-2, IA-4 | Identification & Authentication |
| 5.17 | Authentication information | IA-5 | Identification & Authentication |
| 5.24 | Information security incident management planning | IR-1, IR-4, IR-8 | Incident Response |
| 5.26 | Response to information security incidents | IR-4, IR-5, IR-6 | Incident Response |
| 5.29 | Information security during disruption | CP-1, CP-2 | Contingency Planning |
| 5.30 | ICT readiness for business continuity | CP-6, CP-7, CP-9 | Contingency Planning |
| 5.31 | Legal, statutory, regulatory, and contractual requirements | PM-9, SA-2 | Program Mgmt, System & Services Acq |
| 6.1 | Screening | PS-3 | Personnel Security |
| 6.3 | Information security awareness, education, and training | AT-2, AT-3 | Awareness & Training |
| 6.4 | Disciplinary process | PS-8 | Personnel Security |
| 6.7 | Remote working | AC-17 | Access Control |
| 7.1 | Physical security perimeters | PE-3 | Physical & Environmental Protection |
| 7.2 | Physical entry | PE-2, PE-3 | Physical & Environmental Protection |
| 7.4 | Physical security monitoring | PE-6 | Physical & Environmental Protection |
| 7.10 | Storage media | MP-1 through MP-8 | Media Protection |
| 7.14 | Secure disposal or re-use of equipment | MP-6 | Media Protection |
| 8.2 | Privileged access rights | AC-6 | Access Control |
| 8.5 | Secure authentication | IA-2, IA-8 | Identification & Authentication |
| 8.7 | Protection against malware | SI-3 | System & Info Integrity |
| 8.8 | Management of technical vulnerabilities | RA-5, SI-2 | Risk Assessment, System & Info Integrity |
| 8.9 | Configuration management | CM-2, CM-3, CM-6 | Configuration Management |
| 8.12 | Data leakage prevention | SI-12, AC-23 | System & Info Integrity, Access Control |
| 8.13 | Information backup | CP-9 | Contingency Planning |
| 8.15 | Logging | AU-2, AU-3, AU-12 | Audit & Accountability |
| 8.16 | Monitoring activities | SI-4, AU-6 | System & Info Integrity, Audit & Accountability |
| 8.20 | Networks security | SC-7, SC-8 | System & Comm Protection |
| 8.22 | Segregation of networks | SC-7, AC-4 | System & Comm Protection, Access Control |
| 8.24 | Use of cryptography | SC-12, SC-13, SC-28 | System & Comm Protection |
| 8.25 | Secure development life cycle | SA-3, SA-8, SA-11 | System & Services Acquisition |
| 8.28 | Secure coding | SA-11, SA-15 | System & Services Acquisition |

### Mapping Limitations

- ISO 27001 controls are broader and more principle-based; NIST 800-53 controls are more prescriptive
- NIST 800-53 has ~1,000 control parameters across ~20 families; ISO 27001 has 93 controls across 4 themes
- Some NIST controls (e.g., SA-9, PM-30) have no direct ISO 27001 equivalent
- Some ISO 27001 controls (e.g., 5.7 Threat Intelligence) map to multiple NIST controls across families
- Organizations should use official crosswalk tools (NIST SP 800-53B, NIST Cybersecurity Framework) for authoritative mappings

---

## 16. ISO 27001 vs FedRAMP vs SOC 2

### Comparison Table

| Attribute | ISO 27001:2022 | FedRAMP | SOC 2 Type II |
|-----------|---------------|---------|---------------|
| **Origin** | International (ISO/IEC) | US Federal Government (GSA/OMB) | AICPA (US accounting body) |
| **Applicability** | Any organization globally | Cloud service providers serving US federal agencies | Service organizations (typically cloud/SaaS) |
| **Mandatory for** | Often contractual; sometimes regulatory | Mandatory to sell cloud services to US federal government | Not legally mandatory; customer-driven |
| **Control framework** | 93 controls across 4 themes | NIST 800-53 (Low: 127, Moderate: 323, High: 421 controls) | Trust Service Criteria (CC, Availability, Confidentiality, Privacy, Processing Integrity) |
| **Assessment body** | Accredited Certification Body (CB) | 3PAO (Third Party Assessment Organization) | Licensed CPA firm |
| **Output** | Certificate | Authority to Operate (ATO) or P-ATO | SOC 2 Report (Type I: design, Type II: operating effectiveness) |
| **Validity** | 3 years (with annual surveillance) | Continuous monitoring; annual reviews | Point-in-time (Type I) or period (Type II — typically 12 months) |
| **Scope definition** | Organization-defined, must be documented | Cloud service boundary defined by CSP | Service boundary defined by service organization |
| **Risk assessment** | Required, organization chooses methodology | Required, aligned to FISMA/NIST 800-37 | Not explicitly required but implicit in control design |
| **Continuous monitoring** | Not explicitly required (annual surveillance) | Required — monthly vulnerability scans, annual penetration test | Not explicitly required (Type II covers a period) |
| **Public disclosure** | Certificate is public; details are not | Authorization package partially public on FedRAMP Marketplace | Report is confidential; shared under NDA |
| **Cloud-specific controls** | 5.23 (cloud services) — single control | Entire framework designed for cloud | Cloud-relevant but not cloud-specific |
| **Cost to achieve** | Lower (weeks to months preparation) | High (hundreds of thousands to millions) | Moderate ($50K-$500K depending on scope) |

### When to Pursue Which Framework

| Situation | Recommended Framework(s) |
|-----------|--------------------------|
| Selling to US federal agencies | FedRAMP (mandatory) |
| Selling to enterprise customers globally | ISO 27001 (widely recognized internationally) |
| Selling SaaS to US enterprise customers | SOC 2 Type II (most commonly requested) |
| Selling to EU customers under GDPR | ISO 27001 + ISO 27701 (privacy extension) |
| DoD contract requiring CUI handling | CMMC Level 2 or 3 |
| Healthcare customers | HIPAA (required) + SOC 2 or ISO 27001 (complementary) |
| Maximum assurance for federal cloud | FedRAMP High |
| Startup, limited budget, international reach | ISO 27001 (start here) |

### Mutual Recognition and Overlap

- **FedRAMP + ISO 27001:** FedRAMP agencies may give partial credit for ISO 27001 certifications, but FedRAMP authorization is still required. Some controls overlap but FedRAMP is far more prescriptive.
- **SOC 2 + ISO 27001:** Many organizations pursue both. SOC 2 satisfies US enterprise customers; ISO 27001 satisfies international and procurement requirements. Audit activities can be partially combined.
- **ISO 27001 + GDPR:** ISO 27001 implementation supports GDPR compliance but does not replace it. ISO 27701 adds a privacy layer on top of ISO 27001 specifically addressing GDPR requirements.
- **FedRAMP + SOC 2:** FedRAMP authorization generally satisfies SOC 2 security requirements for a cloud service. Some CSPs maintain both for commercial and federal market coverage.

---

## 17. Key Changes: 2013 to 2022 Edition

### Structural Changes

| Area | 2013 Edition | 2022 Edition |
|------|-------------|-------------|
| Annex A domains/themes | 14 domains | 4 themes |
| Total controls | 114 | 93 |
| New controls | N/A | 11 new |
| Merged controls | N/A | 24 pairs/groups merged |
| Renamed controls | N/A | Many updated titles |

### Clause-Level Changes

1. **Clause 4.2:** Added requirement to determine which requirements of interested parties will be addressed through the ISMS
2. **Clause 6.1.3(c):** Added requirement to compare controls with Annex A AND also with other reference frameworks (not just Annex A)
3. **Clause 6.3 (new):** Planning of changes — formal change management for ISMS
4. **Clause 8.1:** Expanded to reference criteria for processes
5. **Clause 9.3:** Split into 9.3.1, 9.3.2, 9.3.3 for clarity

### Control Attribute Tags (New in 2022)

Each control now includes five attribute tags making it easier to filter controls by:
- **Control type:** Preventive, Detective, Corrective
- **Information security properties:** Confidentiality, Integrity, Availability
- **Cybersecurity concepts:** Identify, Protect, Detect, Respond, Recover (aligns with NIST CSF)
- **Operational capabilities:** Governance, Asset management, Information protection, Human resource security, Physical security, System and network security, Application security, Secure configuration, Identity and access management, Threat and vulnerability management, Continuity, Supplier relationships security, Legal and compliance, Information security event management, Information security assurance
- **Security domains:** Governance and Ecosystem, Protection, Defence, Resilience

### Major Practical Implications of the 2022 Changes

1. **Cloud services (5.23):** Organizations must now explicitly address cloud security in their ISMS — previously implicit
2. **Threat intelligence (5.7):** Requires organizations to establish a formal threat intelligence program or subscription
3. **Configuration management (8.9):** Formalizes configuration baselines and deviation management
4. **Secure coding (8.28):** Requires secure development practices — significant for software companies
5. **Data leakage prevention (8.12):** DLP programs now explicitly required for applicable organizations
6. **Physical security monitoring (7.4):** CCTV and physical monitoring now explicitly required

---

## Summary Reference Card

| Topic | Key Points |
|-------|------------|
| **Mandatory clauses** | 4, 5, 6, 7, 8, 9, 10 |
| **Total Annex A controls** | 93 (4 themes) |
| **Organizational controls** | Theme 5: 37 controls |
| **People controls** | Theme 6: 8 controls |
| **Physical controls** | Theme 7: 14 controls |
| **Technological controls** | Theme 8: 34 controls |
| **New controls in 2022** | 11 new controls |
| **Certificate validity** | 3 years |
| **Surveillance audits** | Year 1 and Year 2 |
| **Risk treatment options** | Modify, Retain, Avoid, Share |
| **SoA requirement** | All 93 controls must be addressed |
| **PDCA phases** | Plan, Do, Check, Act |
| **Companion standard** | ISO 27002:2022 (implementation guidance) |

---

*Document Version: 1.0 | Framework Version: ISO/IEC 27001:2022 | Intended Use: LLM GRC Knowledge Base*
*This document is a reference summary. For certification purposes, always consult the full normative text of ISO/IEC 27001:2022 and ISO/IEC 27002:2022 directly.*
