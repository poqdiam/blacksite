# NIST SP 800-37 Rev 2 — Risk Management Framework (RMF)
## Complete Process Reference for GRC Practitioners

Source: NIST Special Publication 800-37 Revision 2 (December 2018)
"Risk Management Framework for Information Systems and Organizations: A System Life Cycle Approach for Security and Privacy"

---

## RMF Overview

The RMF provides a disciplined, structured, and flexible process for managing security and privacy risk. It integrates security and privacy into the system development life cycle (SDLC) and is mandatory for federal information systems under FISMA.

**Key Outputs**: Authorization to Operate (ATO) or Denial of Authorization to Operate (DATO)
**Governing Authority**: NIST, OMB, CISA
**Applies To**: Federal agencies, contractors processing federal data, FedRAMP cloud providers

---

## RMF Steps

### STEP 0 — PREPARE (Added in Rev 2)

**Purpose**: Carry out essential activities at the organization and system level to help prepare the organization to manage security and privacy risks using the RMF.

**Organization-Level Tasks**:
- P-1: Risk management roles assigned (CIO, SAISO, AO, ISSO, ISSM)
- P-2: Risk management strategy established (risk tolerance, assumptions, constraints)
- P-3: Risk assessment (organization level)
- P-4: Organizationally tailored control baselines and cybersecurity framework profiles established
- P-5: Common controls identified
- P-6: Mission/business focus understood
- P-7: Information types identified
- P-8: Stakeholder needs and requirements identified
- P-9: Enterprise architecture established
- P-10: Requirements allocation decisions made
- P-11: Supply chain risk management strategy established
- P-12: Authorization boundary defined (if applicable)
- P-13: Information life cycle identified
- P-14: Risk assessment (system level) — preliminary
- P-15: Requirements defined
- P-16: Enterprise architecture placement and allocation

**System-Level Tasks**:
- P-14 to P-19 define the system in context of the enterprise architecture

**Key Artifacts Produced**:
- Risk management strategy document
- Organizational risk tolerance statement
- Authorized software/hardware list (if applicable)
- Mission/business process list
- Supply chain risk management plan

---

### STEP 1 — CATEGORIZE

**Purpose**: Categorize the system and the information processed, stored, and transmitted based on an impact analysis.

**Tasks**:
- C-1: Document system characteristics (name, purpose, architecture, data types)
- C-2: Describe information types (NIST SP 800-60 Vol I & II for federal systems)
- C-3: Determine security impact values (Confidentiality, Integrity, Availability)
- C-4: Determine overall system impact level (HIGH water mark rule)

**FIPS 199 Impact Levels**:
- **LOW**: Adverse effect would be limited
- **MODERATE**: Adverse effect would be serious
- **HIGH**: Adverse effect would be severe or catastrophic

**Impact Determination (FIPS 199)**:
| Objective | LOW | MODERATE | HIGH |
|-----------|-----|----------|------|
| Confidentiality | Limited | Serious | Severe/Catastrophic |
| Integrity | Limited | Serious | Severe/Catastrophic |
| Availability | Limited | Serious | Severe/Catastrophic |

**Overall System Security Category**:
`SC_system = {(confidentiality, impact), (integrity, impact), (availability, impact)}`
Final impact = HIGH watermark of C, I, A values

**Key Artifacts Produced**:
- System Security Plan (SSP) — Initial
- FIPS 199 categorization worksheet
- NIST SP 800-60 information type mapping

**Common Mistakes**:
- Not considering the aggregation effect (low sensitivity data that in bulk becomes high)
- Using nominal impact instead of worst-case
- Not involving the System Owner and AO in categorization decisions

---

### STEP 2 — SELECT

**Purpose**: Select, tailor, and document the controls to protect the system based on risk assessment.

**Tasks**:
- S-1: Select security control baseline (Low/Moderate/High from NIST SP 800-53)
- S-2: Apply organization-defined parameters (ODPs) — fill in specific values for controls requiring them
- S-3: Tailor control baselines (additions, removals with justification)
- S-4: Designate controls as system-specific, hybrid, or common/inherited
- S-5: Assign responsibility for each control (System Owner, AO, ISSO, common control provider)
- S-6: Update SSP with selected controls
- S-7: Develop continuous monitoring strategy

**Control Baseline Numbers (approximate, NIST 800-53 Rev 5)**:
- Low baseline: ~128 controls
- Moderate baseline: ~323 controls
- High baseline: ~421 controls

**Tailoring Actions**:
- **Additions**: Add controls from 800-53 catalog not in baseline (compensating/supplemental)
- **Removals (Scoping)**: Remove controls not applicable based on technology/environment
- **Parameter Assignment**: Fill in organization-specific values (e.g., minimum password length)
- **Compensating Controls**: Alternative approaches when baseline control cannot be implemented

**Control Designations**:
- **Common (Inherited)**: Provided by another system/organization; ISSO inherits and documents
- **Hybrid**: Partially common, partially system-specific
- **System-Specific**: Fully implemented by the system under assessment

**Key Artifacts Produced**:
- Control selection worksheet (SSP Appendix)
- Tailoring rationale document
- Continuous monitoring strategy (initial)
- Updated SSP with control table

---

### STEP 3 — IMPLEMENT

**Purpose**: Implement the selected controls and document the implementation.

**Tasks**:
- I-1: Implement controls per SSP (in code, config, policy, procedure)
- I-2: Document how controls are implemented in the SSP (Implementation Statement)
- I-3: Review and approve control implementation

**Implementation Types**:
- **Technical**: Firewall rules, encryption, access control lists, audit logs
- **Operational**: Procedures, training, physical security, backup procedures
- **Management**: Risk assessments, security planning, authorization processes

**SSP Control Implementation Narrative Quality Criteria**:
Each control narrative should answer:
1. What is done to satisfy the control?
2. Who does it?
3. Where is it done (system components)?
4. When/how often?
5. How is it verified?

**Common Gaps**:
- Narratives that restate the control requirement rather than describe the implementation
- Missing specifics about system components (e.g., "we use encryption" vs "AES-256 for data at rest on RDS")
- No documentation of inherited controls from cloud providers

**Key Artifacts Produced**:
- SSP with completed control implementation narratives
- Supporting evidence (screenshots, config files, logs)
- Configuration baselines (STIG checklists, CIS benchmarks)

---

### STEP 4 — ASSESS

**Purpose**: Assess the controls to determine if they are implemented correctly, operating as intended, and producing the desired outcome.

**Tasks**:
- A-1: Select assessor (independent: SCA, 3PAO for FedRAMP; internal for low-impact)
- A-2: Develop Security Assessment Plan (SAP)
- A-3: Assess controls using SAP procedures
- A-4: Prepare Security Assessment Report (SAR)
- A-5: Conduct initial remediation of findings (optional before authorization)

**Assessment Methods (NIST SP 800-53A)**:
- **Examine**: Review documentation, architecture diagrams, policies, procedures
- **Interview**: Question personnel (ISSO, system admin, end users)
- **Test**: Automated scanning, manual testing, penetration testing

**Finding Severity**:
- **High**: Critical vulnerability, control completely unmet, high risk of exploit
- **Moderate**: Significant weakness, control partially met, moderate risk
- **Low**: Minor deficiency, control mostly met, low risk
- **Informational**: Best practice recommendation, no control gap

**SAR Structure**:
1. Executive Summary
2. Assessment Methodology
3. System Description
4. Control Assessment Results (pass/fail/other than satisfied/not applicable)
5. Findings and Recommendations
6. Attachments (evidence, tool outputs)

**Key Artifacts Produced**:
- Security Assessment Plan (SAP)
- Security Assessment Report (SAR)
- Raw assessment evidence (scan reports, interview notes, test results)
- Finding tracker / draft POA&M

---

### STEP 5 — AUTHORIZE

**Purpose**: Authorize the system to operate based on a determination that the risk to operations, assets, and individuals from operating the system is acceptable.

**Tasks**:
- AU-1: Prepare authorization package (SSP, SAR, POA&M, Executive Summary)
- AU-2: Adjudicate risk findings (AO reviews, risk acceptances)
- AU-3: Determine risk acceptability
- AU-4: Issue authorization decision

**Authorization Decision Types**:
- **ATO (Authorization to Operate)**: Risk accepted; system may operate
  - Typically 3 years for federal systems, 1 year for FedRAMP provisional
- **ATO with Conditions**: Operates with specific restrictions; POA&Ms must be closed by date
- **DATO (Denial of Authorization to Operate)**: Risk not accepted; system must not operate
- **Common Control Authorization**: AO authorizes inherited controls once for use by many systems

**Authorization Package Contents**:
1. System Security Plan (SSP) — complete, current
2. Security Assessment Report (SAR) — from independent assessor
3. POA&M — all open findings with milestones
4. Executive Summary — risk summary for AO
5. Interconnection Security Agreements (ISAs) if applicable
6. Penetration test results (High-impact systems)
7. Privacy Impact Assessment (PIA) if PII/PHI processed

**POA&M Management**:
- All "Other Than Satisfied" (OTS) findings must appear in POA&M
- Each item: unique ID, control ID, finding description, risk level, milestone, responsible party
- AO-accepted risks documented separately (Risk Acceptance letter)

**Authorization Term**:
- ATO is not permanent — it requires ongoing monitoring
- Must be reauthorized when: system changes significantly, conditions of ATO violated, scheduled reauthorization

**Key Artifacts Produced**:
- ATO Letter (signed by AO)
- Authorization Package
- Risk Acceptance Letters (for accepted risks)
- Updated POA&M

---

### STEP 6 — MONITOR

**Purpose**: Continuously monitor the security posture of the system to ensure controls remain effective over time.

**Tasks**:
- M-1: Monitor control effectiveness (ongoing testing and review)
- M-2: Assess selected controls per continuous monitoring strategy
- M-3: Respond to risk (new vulnerabilities, incidents, configuration changes)
- M-4: Report security status to AO and organization
- M-5: Update SSP, SAR, POA&M as system changes
- M-6: Review authorization to operate (trigger-based or scheduled)
- M-7: Dispose of system if decommissioned

**Continuous Monitoring Activities**:
- **Vulnerability Scanning**: Monthly (NIST/FedRAMP minimum)
- **Patch Management**: Apply critical patches within 30 days (high), 90 days (moderate)
- **Log Review**: Daily automated, weekly manual spot-check
- **Configuration Drift**: Compare against approved baseline
- **Account Review**: Quarterly access recertification
- **Incident Monitoring**: 24/7 (SIEM alerts)
- **POA&M Reviews**: Monthly progress checks with ISSO

**Significant Change Definition** (triggers re-assessment or re-authorization):
- Change in impact level
- New system interconnections
- New data types or information types
- Major architectural changes (new components, new cloud services)
- Change in operating environment (new data center, new cloud region)
- Change in threat landscape (new attack vector targeting the system)

**Reporting Cadence** (FedRAMP):
- Monthly: Vulnerability scan results, POA&M updates
- Quarterly: Control testing results, significant change notifications
- Annually: Full annual assessment (selected controls)
- As-needed: Incident reports, significant change requests

**Key Artifacts Produced**:
- Ongoing assessment results
- Updated POA&M (monthly)
- Incident reports
- Significant change request forms
- Annual security review report

---

## Key RMF Roles

| Role | Abbreviation | Responsibilities |
|------|-------------|-----------------|
| Authorizing Official | AO | Makes risk acceptance decision; signs ATO |
| AO Designated Representative | AODR | Assists AO; reviews packages on AO's behalf |
| Chief Information Officer | CIO | Oversees agency IT; designates ISSOs |
| Senior Agency Information Security Officer | SAISO / CISO | Manages agency security program |
| Information System Security Officer | ISSO | Day-to-day security operations for a system |
| Information System Security Manager | ISSM | Oversees multiple ISSOs; manages portfolio |
| System Owner | SO | Accountable for the system; funds security activities |
| Common Control Provider | CCP | Provides inherited controls used by multiple systems |
| Security Control Assessor | SCA | Performs independent assessment (Step 4) |
| Privacy Officer | PO / CPO | Manages privacy program; PIA oversight |

---

## RMF in BLACKSITE Context

BLACKSITE implements the full RMF lifecycle. Key mappings:
- **Categorize**: System record `impact_level`, `fips_category`, `is_eis`
- **Select**: Control table `system_controls` with `status`, `implementation_status`
- **Implement**: SSP narratives in `ssp_entries`, `controls` with implementation notes
- **Assess**: `AtoDocument` type=SAR, assessment findings
- **Authorize**: `AtoDocument` type=ATO_LETTER, `ato_date`, `ato_expiry`, AO signature
- **Monitor**: `PoamItem` table, `DailyLogbook`, continuous monitoring plan in docs
- **POA&M**: Full POA&M engine with ID format `ABVR-YYYYMM-NNNNACNN`

---

## References

- NIST SP 800-37 Rev 2: https://doi.org/10.6028/NIST.SP.800-37r2
- NIST SP 800-53 Rev 5: https://doi.org/10.6028/NIST.SP.800-53r5
- NIST SP 800-53A Rev 5: https://doi.org/10.6028/NIST.SP.800-53Ar5
- FIPS 199: https://doi.org/10.6028/NIST.FIPS.199
- FIPS 200: https://doi.org/10.6028/NIST.FIPS.200
