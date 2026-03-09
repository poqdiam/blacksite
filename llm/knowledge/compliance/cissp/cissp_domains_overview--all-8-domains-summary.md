# CISSP Domains Overview — All 8 Domains Summary

**Certification:** Certified Information Systems Security Professional (CISSP)
**Issuing Body:** (ISC)² — International Information System Security Certification Consortium
**Exam Format:** 125–175 adaptive questions (CAT), 4-hour limit
**Passing Score:** 700 out of 1000 scaled score
**Experience Requirement:** 5 years cumulative paid work in 2+ of the 8 domains
**CBK Version:** Common Body of Knowledge (CBK) — updated periodically; verify current weights with (ISC)²

---

## Domain Weight Summary Table

| # | Domain | CBK Weight |
|---|--------|-----------|
| 1 | Security and Risk Management | 15% |
| 2 | Asset Security | 10% |
| 3 | Security Architecture and Engineering | 13% |
| 4 | Communication and Network Security | 13% |
| 5 | Identity and Access Management (IAM) | 13% |
| 6 | Security Assessment and Testing | 12% |
| 7 | Security Operations | 13% |
| 8 | Software Development Security | 11% |
| | **Total** | **100%** |

---

## How to Use This Document

This overview provides a structured summary of each domain, its core concepts, associated frameworks, key exam topics, and GRC applicability. For deep dives, see the domain-specific reference files in this directory.

---

## Domain 1: Security and Risk Management (15%)

### Overview

The largest single domain by weight. Domain 1 establishes the foundational principles that underpin all other security activities — governance structures, ethical obligations, legal and regulatory compliance, risk management methodology, and business continuity planning. A CISSP candidate who cannot think like a security executive will struggle here.

### Core Concepts

- **CIA Triad:** Confidentiality, Integrity, Availability — the three foundational security properties every control must address
- **Security governance:** The organizational structure, policies, roles, and accountability mechanisms that direct and control security activities
- **Risk management lifecycle:** Identify assets → identify threats and vulnerabilities → assess risk → select controls → monitor and reassess
- **Quantitative risk analysis:** Uses numeric values; ALE = ARO × SLE; SLE = Asset Value × Exposure Factor
- **Qualitative risk analysis:** Uses descriptive scales (low/medium/high); faster but less precise; common in practice
- **Risk treatment options:** Accept (tolerate), Avoid (eliminate), Transfer (insurance, contracts), Mitigate (implement controls)
- **Due care vs. due diligence:** Due care = doing the right thing; due diligence = verifying it was done correctly and is working
- **Business Continuity Planning (BCP):** Ensures critical business functions can continue during and after a disruption; BIA is the foundation
- **Legal and regulatory landscape:** FISMA, GDPR, HIPAA, SOX, GLBA, PCI DSS, CCPA — each imposes different obligations on different industries
- **ISC² Code of Ethics:** Protect society, act honorably, provide competent service, advance the profession

### Key Frameworks and Standards

| Framework | Purpose |
|-----------|---------|
| COSO | Internal control framework; widely used in financial sector |
| COBIT 5 / 2019 | IT governance and management; bridges business goals and IT |
| ISO 38500 | Corporate governance of information technology |
| ISO 31000 | General risk management standard |
| NIST RMF (SP 800-37) | Federal risk management framework; 7-step process |
| NIST SP 800-30 | Risk assessment guidance |
| FAIR | Factor Analysis of Information Risk — quantitative risk model |

### Key Exam Topics

- Policy hierarchy: policy → standard → procedure → guideline
- Types of law: criminal, civil, administrative/regulatory, private
- Intellectual property protections: copyright, patent, trademark, trade secret
- Computer crime laws: CFAA, ECPA, relevant international treaties
- Privacy frameworks: OECD Privacy Principles, FIPPs, GDPR lawful bases
- Security planning: strategic, tactical, operational plans
- Personnel security: hiring, separation of duties, least privilege, termination
- BCP phases: project initiation, BIA, strategy development, plan development, training, maintenance

### GRC Applicability

Domain 1 is the backbone of GRC work. Every governance framework, every risk register, every compliance gap analysis, and every policy document originates from the principles taught in this domain. A GRC practitioner applies Domain 1 when:

- Building or reviewing an information security policy suite
- Conducting a risk assessment or authorizing systems under NIST RMF
- Completing a BIA and developing RTO/RPO targets
- Advising leadership on regulatory obligations (HIPAA, GDPR, FISMA)
- Drafting organizational risk treatment decisions and risk acceptance memos

---

## Domain 2: Asset Security (10%)

### Overview

Asset Security covers the identification, classification, and protection of organizational assets — data, hardware, software, and services — across their full lifecycle. Data classification is the cornerstone: you cannot apply appropriate controls if you do not know what you are protecting and why.

### Core Concepts

- **Asset inventory:** Every security program starts with knowing what you own; assets include hardware, software, data, people, and facilities
- **Data classification:** Assigns sensitivity labels to information to guide handling, storage, transmission, and disposal decisions
- **Data ownership roles:** Data owner (accountable, sets classification), data custodian (implements controls), data processor (acts on instructions), data subject (individual whose data is used)
- **Data states:** Data at rest, data in transit, data in use — each state requires different control types
- **Data lifecycle:** Create → store → use → share → archive → destroy; controls must apply at every stage
- **Retention and disposal:** Legal holds, retention schedules, media sanitization (NIST SP 800-88: clear, purge, destroy)
- **Privacy requirements:** Data minimization, purpose limitation, consent — intersect with classification and lifecycle
- **Scoping and tailoring:** Selecting and adjusting baseline controls to fit the specific data classification and system environment

### Key Frameworks and Standards

| Framework | Purpose |
|-----------|---------|
| NIST SP 800-60 | Data categorization for federal systems (maps data types to FIPS 199 impact levels) |
| FIPS 199 | Federal standards for information categorization (Low/Moderate/High) |
| NIST SP 800-88 | Media sanitization guidelines (clear, purge, destroy) |
| ISO 27001 Annex A.8 | Asset management controls |
| GDPR Articles 5, 25 | Data minimization, purpose limitation, data protection by design |

### Key Exam Topics

- Government vs. commercial classification schemes (Top Secret / Secret / CUI vs. Confidential / Private / Public)
- Data remanence and media sanitization methods
- Scoping, tailoring, and supplementing baseline controls
- Privacy requirements and data subject rights
- Data roles: owner, custodian, steward, processor, controller
- Retention policies and legal hold procedures

### GRC Applicability

- Drafting data classification policies and tagging schemes
- Evaluating media sanitization procedures during audits
- Conducting privacy impact assessments (PIAs)
- Mapping data flows to identify where sensitive data lives and who has access
- Ensuring retention schedules comply with regulatory requirements (HIPAA, GDPR)

---

## Domain 3: Security Architecture and Engineering (13%)

### Overview

Domain 3 is the most technically diverse domain in the CBK. It spans cryptographic theory, secure hardware and software design principles, security models, trusted computing, physical security, and site design. The exam tests whether candidates can evaluate the security properties of complex systems and designs.

### Core Concepts

- **Security models:** Formal mathematical models that define security properties (Bell-LaPadula: no read up / no write down for confidentiality; Biba: no write up / no read down for integrity; Clark-Wilson: well-formed transactions; Brewer-Nash/Chinese Wall: conflict of interest)
- **Cryptography fundamentals:** Symmetric (AES, 3DES, ChaCha20), asymmetric (RSA, ECC, Diffie-Hellman), hashing (SHA-256/512, HMAC), digital signatures
- **PKI:** Certificate authorities (root, intermediate), certificate lifecycle, trust chains, CRL vs. OCSP, key escrow
- **Secure design principles:** Least privilege, defense in depth, fail secure, open design (Kerckhoff's principle), separation of duties, economy of mechanism, complete mediation
- **Trusted Platform Module (TPM):** Hardware root of trust; stores cryptographic keys securely
- **Virtualization and cloud security:** Hypervisor types (Type 1/2), VM escape, cloud shared responsibility model
- **Physical security:** Site selection, perimeter controls, access controls, HVAC, UPS, fire suppression
- **Side-channel attacks:** Timing attacks, power analysis, electromagnetic emanations (TEMPEST)
- **Common architectural vulnerabilities:** Buffer overflows, race conditions, TOCTOU, covert channels

### Key Frameworks and Standards

| Framework | Purpose |
|-----------|---------|
| Common Criteria (ISO 15408) | Evaluation assurance levels (EAL1–EAL7) for products |
| FIPS 140-2/3 | Cryptographic module validation levels (1–4) |
| NIST SP 800-175B | Cryptographic standards and guidelines |
| NIST SP 800-57 | Key management recommendations |
| ISO/IEC 27033 | Network security architecture |

### Key Exam Topics

- Bell-LaPadula, Biba, Clark-Wilson, Brewer-Nash model rules
- Symmetric vs. asymmetric key lengths and use cases
- Hashing: collision resistance, preimage resistance, second preimage resistance
- PKI components: CA, RA, CRL, OCSP, certificate pinning
- Evaluation Assurance Levels (EAL) under Common Criteria
- FIPS 140-2 validation levels and applicability
- Physical controls: mantraps, bollards, CPTED principles
- Cloud deployment models: IaaS, PaaS, SaaS, and responsibility shifts
- Quantum computing threats to current cryptographic algorithms

### GRC Applicability

- Reviewing system security plans (SSPs) for appropriate security architecture
- Evaluating cryptographic controls during security assessments
- Assessing compliance with FIPS 140-2 requirements for federal systems
- Reviewing physical security controls during site audits
- Advising on cloud migration risks and shared responsibility boundaries

---

## Domain 4: Communication and Network Security (13%)

### Overview

Domain 4 covers the full stack of networking — from physical media through application protocols — with an emphasis on identifying insecure configurations, understanding attack vectors, and selecting appropriate protective technologies. The OSI and TCP/IP models serve as the organizing framework.

### Core Concepts

- **OSI model (7 layers):** Physical → Data Link → Network → Transport → Session → Presentation → Application; attacks and controls map to specific layers
- **TCP/IP model (4 layers):** Network Access → Internet → Transport → Application
- **Network protocols:** IPv4/IPv6 addressing, subnetting, routing protocols (BGP, OSPF), DNS, DHCP, ARP
- **Secure protocols:** TLS/SSL (and why SSL/early TLS are deprecated), SSH, SFTP, HTTPS, S/MIME, DNSSEC
- **Firewalls:** Packet filtering, stateful inspection, application layer (proxy), NGFW — know the differences and limitations
- **VPNs:** IPSec (tunnel vs. transport mode, AH vs. ESP), SSL/TLS VPN, split tunneling risks
- **Wireless security:** WEP (broken), WPA/WPA2-Personal, WPA2/WPA3-Enterprise (802.1X + RADIUS), 802.11 attack types
- **Network attacks:** ARP poisoning, DNS poisoning/hijacking, MITM, sniffing, session hijacking, DDoS, BGP hijacking
- **Network segmentation:** VLANs, DMZ architecture, microsegmentation, zero trust network access (ZTNA)
- **Content delivery and proxies:** Forward proxy, reverse proxy, web application firewalls (WAF), load balancers

### Key Frameworks and Standards

| Framework | Purpose |
|-----------|---------|
| IEEE 802.11 (WiFi standards) | Wireless networking and security |
| IEEE 802.1X | Port-based network access control |
| RFC 4301 | IPSec architecture |
| NIST SP 800-77 | IPSec VPN guide |
| NIST SP 800-153 | WLAN security guidelines |
| PCI DSS requirements 1, 6 | Network segmentation and secure transmission |

### Key Exam Topics

- OSI layers, their PDUs, and which protocols operate at each layer
- IPv4 vs. IPv6 differences (addressing, security improvements in IPv6)
- Difference between AH and ESP in IPSec
- TLS handshake process and cipher suite negotiation
- Wireless attack types: evil twin, deauthentication attacks, KRACK
- VLAN hopping attacks and mitigation
- BGP security threats and RPKI
- Network monitoring: NetFlow, packet capture, IDS vs. IPS (signature-based vs. anomaly-based)
- NAT, PAT, and their impact on end-to-end visibility

### GRC Applicability

- Reviewing network architecture diagrams during security assessments
- Evaluating firewall ruleset reviews and segmentation effectiveness
- Assessing compliance with PCI DSS network segmentation requirements
- Reviewing penetration test findings related to network vulnerabilities
- Advising on secure remote access solutions for workforce

---

## Domain 5: Identity and Access Management (IAM) (13%)

### Overview

Domain 5 covers how identities are created, managed, authenticated, and authorized across systems. IAM is increasingly central to zero trust architectures and cloud-first environments. The domain spans authentication protocols, access control models, federation, privileged access management, and the account lifecycle.

### Core Concepts

- **Authentication factors:** Something you know (password, PIN), something you have (token, smart card), something you are (biometrics), somewhere you are (geolocation), something you do (behavioral)
- **MFA:** Combining two or more independent factors; phishing-resistant MFA (FIDO2/passkeys) vs. phishable MFA (SMS OTP, TOTP)
- **Access control models:** DAC (owner-controlled), MAC (label-based, mandatory), RBAC (role-based), ABAC (policy-based with attributes), Rule-based (firewall rules)
- **Authentication protocols:** Kerberos (ticket-based SSO), SAML 2.0 (XML assertions), OAuth 2.0 (authorization delegation), OpenID Connect (identity layer on OAuth), FIDO2/WebAuthn
- **Identity federation:** SSO across trust domains; SAML IdP/SP relationships; OAuth authorization servers
- **Privileged Access Management (PAM):** Just-in-time (JIT) elevation, password vaulting (PASM), session monitoring, PEDM (Privilege Elevation and Delegation Management)
- **Directory services:** LDAP (X.500-based), Active Directory, RADIUS (network authentication), TACACS+ (command-level authorization for network devices)
- **Account lifecycle:** Provisioning, review (access recertification), modification, suspension, deprovisioning
- **Zero Trust:** "Never trust, always verify" — continuous authentication and authorization; no implicit trust from network location

### Key Frameworks and Standards

| Framework | Purpose |
|-----------|---------|
| NIST SP 800-63 | Digital identity guidelines (IAL, AAL, FAL levels) |
| NIST SP 800-207 | Zero Trust Architecture |
| OAuth 2.0 (RFC 6749) | Authorization delegation framework |
| SAML 2.0 | XML-based federated identity standard |
| FIDO2 / WebAuthn | Phishing-resistant authentication standard |
| ISO/IEC 24760 | Identity management framework |

### Key Exam Topics

- Kerberos components: KDC, TGT, TGS, service tickets
- SAML assertion types: authentication, attribute, authorization decision
- Difference between OAuth 2.0 (authorization) and OpenID Connect (authentication)
- Biometric error rates: FAR (False Acceptance Rate) vs. FRR (False Rejection Rate); CER (Crossover Error Rate)
- DAC vs. MAC vs. RBAC: when to use each
- ABAC policy language and policy decision/enforcement points
- RADIUS vs. TACACS+: which supports per-command authorization
- JIT provisioning and time-limited privileged sessions
- Separation of duties and dual control in access management

### GRC Applicability

- Reviewing access control policies and role matrix designs
- Evaluating privileged access management controls during audits
- Assessing identity federation configurations for SSO implementations
- Conducting access recertification campaigns
- Advising on MFA implementation and phishing-resistant authentication

---

## Domain 6: Security Assessment and Testing (12%)

### Overview

Domain 6 covers how security controls are assessed for effectiveness. This includes the full spectrum from vulnerability scanning to red team exercises, compliance audits, log review, and the reporting structures that communicate findings to stakeholders. The domain teaches candidates how to verify that other domains' controls are actually working.

### Core Concepts

- **Security testing types:** Vulnerability assessment (identifies weaknesses), penetration testing (exploits weaknesses to demonstrate impact), red team (adversary simulation), purple team (collaborative red/blue), tabletop exercises
- **Vulnerability scanning:** Authenticated vs. unauthenticated scans, scanner tuning, false positives/negatives, CVSS scoring
- **Penetration testing phases:** Reconnaissance → scanning → exploitation → post-exploitation → reporting; rules of engagement
- **Security audits:** Internal vs. external; operational, compliance (SOC 2, ISO 27001), forensic audits
- **Code review:** Static Application Security Testing (SAST), Dynamic Application Security Testing (DAST), Software Composition Analysis (SCA), manual code review
- **Log review:** What to collect, centralization (SIEM), correlation rules, anomaly detection, retention requirements
- **Synthetic transactions:** Automated tests that simulate user activity to detect failures
- **Test coverage and completeness:** Code coverage metrics, attack surface coverage in pen tests
- **Reporting:** Risk-rated findings, executive summaries, technical details, remediation recommendations, verification testing

### Key Frameworks and Standards

| Framework | Purpose |
|-----------|---------|
| NIST SP 800-115 | Technical guide to information security testing and assessment |
| OWASP Testing Guide | Web application security testing methodology |
| PTES (Penetration Testing Execution Standard) | Pen test methodology standard |
| CVSSv3.1/v4.0 | Common Vulnerability Scoring System |
| CWE/CVE | Common Weakness Enumeration / Common Vulnerabilities and Exposures |
| ISO 19011 | Audit management guidelines |

### Key Exam Topics

- Difference between vulnerability assessment and penetration testing
- CVSSv3 base score components: AV, AC, PR, UI, S, C, I, A
- Types of penetration tests: black box, white box, gray box
- Rules of engagement: scope, authorization, notification requirements
- SOC 1 (financial reporting controls) vs. SOC 2 (security/availability/confidentiality) vs. SOC 3
- Type 1 (design effectiveness) vs. Type 2 (operating effectiveness) reports
- Log management: retention, integrity, centralization, correlation
- Synthetic monitoring and canary deployments
- SAST vs. DAST vs. IAST vs. RASP

### GRC Applicability

- Scoping and managing penetration testing engagements
- Reviewing vulnerability scan results and prioritizing remediation
- Managing audit relationships (auditors, external assessors, certifying bodies)
- Operating security assessment processes under NIST RMF (assess step)
- Reviewing assessment reports and tracking findings through remediation
- Building and maintaining SIEM correlation rules and alert thresholds

---

## Domain 7: Security Operations (13%)

### Overview

Domain 7 is the operational heartbeat of security — the day-to-day activities that detect, respond to, and recover from security events. This domain covers incident response, forensics, physical security operations, SIEM and monitoring, patch management, and disaster recovery. It is heavily tested on process and procedure knowledge.

### Core Concepts

- **Incident response lifecycle:** Preparation → Detection/Identification → Containment → Eradication → Recovery → Post-incident review (lessons learned)
- **Digital forensics:** Chain of custody, order of volatility, forensic acquisition (write blockers, imaging), analysis, presentation
- **Order of volatility (most to least volatile):** CPU registers/cache → RAM → swap/page file → network state → running processes → disk → remote/archival storage
- **SIEM:** Log aggregation, normalization, correlation, alerting, dashboards; tuning to reduce false positives
- **Threat intelligence:** Strategic, tactical, operational, technical; IOCs (Indicators of Compromise), IOAs (Indicators of Attack)
- **Physical security operations:** Guards, CCTV/DVR, locks (mechanical, electronic, biometric), piggybacking/tailgating prevention, visitor management
- **Patch and vulnerability management:** Patch cycle management, emergency patching, patch testing in staging environments
- **Change management:** CAB (Change Advisory Board), change categories (normal, standard, emergency), rollback procedures
- **Disaster recovery:** DR plan development, RTO/RPO targets, recovery strategies (cold/warm/hot site, cloud DR)
- **Business Continuity vs. Disaster Recovery:** BCP = maintaining critical functions; DRP = restoring IT systems after disruption

### Key Frameworks and Standards

| Framework | Purpose |
|-----------|---------|
| NIST SP 800-61 | Computer security incident handling guide |
| NIST SP 800-86 | Integrating forensics into incident response |
| RFC 3227 | Evidence collection and archiving guidelines |
| ITIL 4 | IT service management; includes change and incident management |
| ISO/IEC 27035 | Information security incident management |
| NIST SP 800-34 | Contingency planning guide |

### Key Exam Topics

- IRP phases and activities within each phase
- Evidence handling: chain of custody, write blockers, hash verification (MD5/SHA-1 for integrity)
- Order of volatility and why it matters for forensic collection sequencing
- Mean Time to Detect (MTTD), Mean Time to Respond (MTTR), Mean Time Between Failures (MTBF)
- Hot site vs. warm site vs. cold site vs. mobile site
- RTO (how fast systems must be restored) vs. RPO (how much data loss is acceptable)
- SIEM tuning: reducing false positives while maintaining detection coverage
- Patch management: emergency vs. scheduled patching processes
- Continuity of operations planning (COOP) in federal context
- Anti-malware, endpoint detection and response (EDR), threat hunting

### GRC Applicability

- Reviewing and testing incident response plans (IRP)
- Overseeing security operations center (SOC) metrics and reporting
- Managing DR testing exercises (tabletop, functional, full-scale)
- Conducting post-incident reviews and updating controls based on lessons learned
- Evaluating physical security controls during site assessments
- Ensuring forensic readiness is built into systems and processes
- Reporting security operations metrics to leadership and boards

---

## Domain 8: Software Development Security (11%)

### Overview

Domain 8 covers how to integrate security into the software development lifecycle (SDLC) from requirements through decommission. As organizations increasingly build or buy software, the ability to evaluate security properties of code, architectures, and development processes is essential. DevSecOps is the modern operationalization of this domain.

### Core Concepts

- **SDLC models:** Waterfall, Agile, Scrum, Spiral, RAD — each has different security integration points
- **Secure SDLC:** Security requirements in design phase, threat modeling before coding, security testing in CI/CD pipeline, penetration testing before release
- **Threat modeling:** Identifying threats systematically; STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege); DREAD for risk rating; Attack trees
- **Secure coding practices:** Input validation, output encoding, parameterized queries (SQL injection prevention), proper error handling, secrets management
- **OWASP Top 10:** The most critical web application security risks (injection, broken authentication, IDOR, security misconfiguration, etc.)
- **Static and dynamic analysis:** SAST (code review without execution), DAST (testing running application), IAST (instrumented runtime), RASP (runtime application self-protection)
- **DevSecOps:** Shift-left security; automated security gates in CI/CD pipelines; Infrastructure as Code (IaC) security scanning
- **Software supply chain security:** SBOMs (Software Bill of Materials), dependency scanning, signing artifacts, verifying third-party components
- **Database security:** SQL injection, stored procedures, parameterized queries, database activity monitoring
- **API security:** Authentication (OAuth, API keys), rate limiting, input validation, CORS configuration

### Key Frameworks and Standards

| Framework | Purpose |
|-----------|---------|
| OWASP Top 10 | Most critical web application security risks |
| OWASP SAMM | Software Assurance Maturity Model |
| BSIMM | Building Security In Maturity Model |
| NIST SP 800-218 | Secure Software Development Framework (SSDF) |
| ISO/IEC 27034 | Application security standard |
| SLSA | Supply Chain Levels for Software Artifacts |

### Key Exam Topics

- STRIDE threat modeling categories and mitigations for each
- Difference between SAST, DAST, IAST, RASP
- OWASP Top 10 categories and representative vulnerability examples
- Agile security: security sprints, security user stories, threat modeling in sprint planning
- Database security: parameterized queries vs. stored procedures vs. input validation
- Code signing, artifact signing, and software supply chain integrity
- Secure API design: REST vs. SOAP security considerations
- Software escrow: source code held by third party for continuity
- Change management in software environments: version control, branching strategies, code review gates
- Buffer overflow mechanics and mitigations (ASLR, stack canaries, DEP/NX)

### GRC Applicability

- Reviewing application security policies and SDLC documentation
- Evaluating DevSecOps pipeline security controls during assessments
- Assessing software supply chain risk (third-party libraries, open source components)
- Reviewing penetration test findings for web applications
- Ensuring software development practices comply with NIST SSDF requirements (FISMA/EO 14028)
- Advising development teams on secure coding standards and training requirements
- Evaluating SBOMs and third-party component risk

---

## Cross-Domain Concepts

### The Security Management Triad in Practice

All 8 domains ultimately serve the same three objectives: protect the **confidentiality**, **integrity**, and **availability** of information. When answering exam questions, always evaluate choices through the CIA lens.

### Defense in Depth

No single control is sufficient. CISSP emphasizes layered controls across people, process, and technology — each domain contributes a layer. Domain 1 sets policy; Domain 2 classifies what to protect; Domain 3 designs the architecture; Domain 4 secures the pipes; Domain 5 controls who gets in; Domain 6 verifies controls work; Domain 7 operates and responds; Domain 8 ensures code doesn't introduce new vulnerabilities.

### Risk as the Common Language

Risk management (Domain 1) is the thread connecting all domains. Every control decision in every domain is ultimately a risk decision. The CISSP exam often presents scenarios where you must choose the most appropriate risk treatment given organizational context.

### Governance Accountability Structure

```
Board of Directors / Senior Leadership
    └── CISO / Security Executive
         ├── Security Policy Owner (Domain 1)
         ├── Asset Owners (Domain 2)
         ├── Security Architects (Domain 3)
         ├── Network Security Engineers (Domain 4)
         ├── IAM Team (Domain 5)
         ├── Security Assessment Team (Domain 6)
         ├── SOC / Security Operations (Domain 7)
         └── Application Security / DevSecOps (Domain 8)
```

### Key CISSP Mindset Shifts

| Thinking Like... | Shift To... |
|-----------------|------------|
| A technician (how do I fix this?) | A manager (what is the risk and cost/benefit?) |
| A vendor (my product solves this) | A governance officer (which framework applies?) |
| A hands-on practitioner | A security leader who directs and oversees |
| "Block everything" | "Enable business while managing risk" |

The CISSP exam is notorious for presenting questions where multiple answers are technically correct, but the **most correct** answer reflects the governance and managerial perspective — not the most technically detailed or aggressive response.

---

## Exam Strategy Notes

### Domain-Weighted Study Allocation

If studying for 100 hours total, approximate allocation by weight:

| Domain | Weight | Suggested Hours |
|--------|--------|----------------|
| 1. Security and Risk Management | 15% | 15 hrs |
| 2. Asset Security | 10% | 10 hrs |
| 3. Security Architecture and Engineering | 13% | 13 hrs |
| 4. Communication and Network Security | 13% | 13 hrs |
| 5. Identity and Access Management | 13% | 13 hrs |
| 6. Security Assessment and Testing | 12% | 12 hrs |
| 7. Security Operations | 13% | 13 hrs |
| 8. Software Development Security | 11% | 11 hrs |

### Question-Answering Framework

1. Read the question stem carefully — identify what is **actually** being asked
2. Eliminate answers that are technically wrong
3. Among remaining answers, choose the one that:
   - Addresses the **root cause**, not just symptoms
   - Reflects **governance/management** perspective over technical detail
   - Is the **first** action (before implementing, test; before deploying, assess; before acting, plan)
   - Balances **business enablement** with risk reduction

### High-Yield Topics Across All Domains

- Risk calculations (ALE, SLE, ARO)
- CIA triad applications
- Security governance and policy hierarchy
- Cryptographic algorithm selection and use cases
- Authentication protocols and their security properties
- Incident response phases and the activities within each
- BCP/DRP concepts: RTO, RPO, BIA
- Access control model selection
- Security assessment types and appropriate use cases

---

*Last updated: 2026-03-01 | Source: CISSP CBK (ISC)² official materials, NIST publications, domain-specific reference files*
