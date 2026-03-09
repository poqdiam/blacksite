# PCI DSS v4.0 Complete Reference: 12 Requirements and Cardholder Data

**Payment Card Industry Data Security Standard, Version 4.0**
**Effective Date:** March 31, 2022
**v3.2.1 Retirement:** March 31, 2024
**New v4.0 Requirements (Future-Dated):** March 31, 2025
**Standard Body:** PCI Security Standards Council (PCI SSC)
**Website:** pcisecuritystandards.org

---

## Table of Contents

1. [Overview and Scope](#1-overview-and-scope)
2. [Cardholder Data and Account Data Definitions](#2-cardholder-data-and-account-data-definitions)
3. [Cardholder Data Environment (CDE)](#3-cardholder-data-environment-cde)
4. [PCI DSS v4.0 — Six Goals and 12 Requirements Structure](#4-pci-dss-v40--six-goals-and-12-requirements-structure)
5. [Goal 1: Build and Maintain a Secure Network and Systems](#5-goal-1-build-and-maintain-a-secure-network-and-systems)
6. [Goal 2: Protect Account Data](#6-goal-2-protect-account-data)
7. [Goal 3: Maintain a Vulnerability Management Program](#7-goal-3-maintain-a-vulnerability-management-program)
8. [Goal 4: Implement Strong Access Control Measures](#8-goal-4-implement-strong-access-control-measures)
9. [Goal 5: Regularly Monitor and Test Networks](#9-goal-5-regularly-monitor-and-test-networks)
10. [Goal 6: Maintain an Information Security Policy](#10-goal-6-maintain-an-information-security-policy)
11. [PCI DSS v4.0 New Requirements vs v3.2.1](#11-pci-dss-v40-new-requirements-vs-v321)
12. [Validation Methods: SAQ Types](#12-validation-methods-saq-types)
13. [QSA vs ISA vs SAQ Assessments](#13-qsa-vs-isa-vs-saq-assessments)
14. [Penetration Testing Requirements (Requirement 11.4)](#14-penetration-testing-requirements-requirement-114)
15. [Network Segmentation and Scope Reduction](#15-network-segmentation-and-scope-reduction)
16. [Tokenization and P2PE for Descoping](#16-tokenization-and-p2pe-for-descoping)
17. [PCI DSS Overlap with NIST 800-53 and FedRAMP](#17-pci-dss-overlap-with-nist-800-53-and-fedramp)
18. [Quick Reference Tables](#18-quick-reference-tables)

---

## 1. Overview and Scope

### 1.1 What PCI DSS Is

PCI DSS is a contractual security standard developed by the major payment card brands (Visa, Mastercard, American Express, Discover, JCB) through the PCI Security Standards Council (founded 2006). It is not a law — compliance is enforced through contracts between merchants, payment processors, and the card brands.

### 1.2 Who Must Comply

PCI DSS applies to any entity that stores, processes, or transmits cardholder data (CHD) or sensitive authentication data (SAD), or could impact the security of the cardholder data environment. This includes:

| Entity Type | Description |
|---|---|
| Merchants | Businesses accepting payment cards (any size) |
| Service Providers | Companies processing, storing, transmitting CHD/SAD on behalf of others |
| Payment Processors | Entities handling payment transactions for merchants |
| Acquiring Banks | Banks processing card payments for merchants |
| Issuing Banks | Banks that issue cards to cardholders |
| Card Brands | Visa, Mastercard, Amex, Discover, JCB (created the standard) |
| Subcontractors | Any party whose services could affect CDE security |

### 1.3 Compliance Levels

Card brands define merchant and service provider levels based on transaction volume:

**Merchant Levels (Visa/Mastercard):**

| Level | Criteria | Annual Validation Requirement |
|---|---|---|
| Level 1 | >6 million transactions/year; any merchant that has experienced a breach | Annual on-site audit by QSA; quarterly network scan by ASV |
| Level 2 | 1–6 million transactions/year | Annual SAQ; quarterly ASV scan |
| Level 3 | 20,000–1 million e-commerce transactions/year | Annual SAQ; quarterly ASV scan |
| Level 4 | <20,000 e-commerce transactions; all other merchants | Annual SAQ recommended; quarterly ASV scan recommended |

**Service Provider Levels:**

| Level | Visa Criteria | Validation |
|---|---|---|
| Level 1 | >300,000 transactions/year | Annual QSA audit; quarterly ASV scan |
| Level 2 | Up to 300,000 transactions/year | Annual SAQ D SP; quarterly ASV scan |

### 1.4 Enforcement Mechanism

Unlike regulatory frameworks, PCI DSS compliance is enforced through:
- **Contractual penalties:** Card brands can fine acquiring banks; banks pass fines to merchants
- **Increased transaction fees:** Non-compliant entities may face higher per-transaction fees
- **Liability shifts:** Non-compliant entities bear greater liability for fraud losses
- **Revocation of card acceptance:** Ultimately, card brands can prohibit a merchant from accepting cards

---

## 2. Cardholder Data and Account Data Definitions

### 2.1 Account Data

Account data includes both cardholder data and sensitive authentication data:

```
Account Data
  Cardholder Data (CHD)
    Primary Account Number (PAN) — the card number
    Cardholder Name
    Service Code (3 or 4 digit code on magnetic stripe)
    Expiration Date
  Sensitive Authentication Data (SAD)
    Full Track Data (magnetic stripe / equivalent chip data)
    CAV2/CVC2/CVV2/CID (3 or 4 digit security code on card)
    PINs / PIN Blocks
```

### 2.2 Protection Requirements by Data Element

| Data Element | Storage Permitted | Protection Required | Render Unreadable |
|---|---|---|---|
| Primary Account Number (PAN) | Yes | Yes | Yes — must be unreadable in storage |
| Cardholder Name | Yes | Yes | Recommended |
| Service Code | Yes | Yes | Recommended |
| Expiration Date | Yes | Yes | Recommended |
| Full Track Data | No | N/A — cannot store post-authorization | N/A |
| CAV2/CVC2/CVV2/CID | No | N/A — cannot store post-authorization | N/A |
| PIN / PIN Block | No | N/A — cannot store post-authorization | N/A |

**Critical rule:** SAD must NEVER be stored after authorization, even if encrypted. This applies even if the PAN is not stored.

### 2.3 PAN Rendering Unreadable (Requirement 3.5)

Acceptable methods for rendering PAN unreadable in storage:
1. One-way hashes based on strong cryptography (keyed hash of the entire PAN)
2. Truncation (replacing a segment of PAN with X's; storing only first 6 and/or last 4 digits)
3. Index tokens with a securely stored pad
4. Strong cryptography with associated key management processes and procedures

Only the minimum digits necessary should be displayed (first 6 / last 4 is common practice).

---

## 3. Cardholder Data Environment (CDE)

### 3.1 CDE Definition

The CDE is composed of:
- System components that store, process, or transmit CHD and/or SAD
- System components that may not directly handle CHD/SAD but are on the same network segment
- System components that provide security controls for the CDE (firewalls, IDS/IPS)

### 3.2 Connected-To and Security-Impacting Systems

PCI DSS v4.0 introduces clearer scoping language. Systems are in scope if they:
- Store, process, or transmit CHD/SAD (direct scope)
- Are connected to systems that store, process, or transmit CHD/SAD (connected-to scope)
- Could impact the security of in-scope systems (security-impacting scope)

**Examples of connected-to systems:**
- Authentication servers used by CDE systems
- DNS servers resolving CDE hostnames
- Network management systems with access to CDE network segments
- Jump servers used to access CDE

### 3.3 Scope Confirmation (Requirement 12.5.2)

PCI DSS v4.0 explicitly requires:
- Scope confirmed at least once every 12 months and after any significant changes
- Documented confirmation that all system components are properly included or excluded
- Understanding of all account data flows

---

## 4. PCI DSS v4.0 — Six Goals and 12 Requirements Structure

### 4.1 Goal-Requirement Mapping

| Goal | Requirements | Theme |
|---|---|---|
| Build and Maintain a Secure Network and Systems | 1, 2 | Network controls; secure configurations |
| Protect Account Data | 3, 4 | Storage protection; transmission protection |
| Maintain a Vulnerability Management Program | 5, 6 | Malware; secure development |
| Implement Strong Access Control Measures | 7, 8, 9 | Need-to-know; authentication; physical |
| Regularly Monitor and Test Networks | 10, 11 | Logging; testing |
| Maintain an Information Security Policy | 12 | Policy and governance |

### 4.2 PCI DSS v4.0 Approach Options

PCI DSS v4.0 introduces a new **Customized Approach** alongside the traditional **Defined Approach**:

**Defined Approach:** Follow the specific requirements as written (prescriptive). Standard path, familiar from v3.2.1.

**Customized Approach:** For mature organizations. Allows implementation of controls that meet the stated objective of each requirement through means not explicitly prescribed. Requires documented Controls Matrix, targeted risk analysis, independent assessor validation. Only available to Level 1 entities validated by QSA.

---

## 5. Goal 1: Build and Maintain a Secure Network and Systems

### 5.1 Requirement 1 — Install and Maintain Network Security Controls

**Objective:** Protect the CDE from untrusted networks by implementing and maintaining network security controls.

#### 1.1 — Processes and mechanisms for network security controls are defined and understood

- 1.1.1: All security policies and operational procedures for Requirement 1 are documented, kept current, in use, and known to all affected parties
- 1.1.2: Roles and responsibilities for performing activities in Requirement 1 are documented, assigned, and understood

#### 1.2 — Network security controls (NSCs) are configured and maintained

- **1.2.1:** Configuration standards for NSCs must include all settings and address known vulnerabilities
- **1.2.2:** All changes to network connections and NSCs require documentation and authorization
- **1.2.3:** Network diagrams maintained showing all connections between the CDE and other networks (updated when changes occur)
- **1.2.4:** Data flow diagrams maintained showing all account data flows across systems and networks (updated at least once every 12 months)
- **1.2.5:** All services, protocols, and ports allowed must be identified, approved, and have a defined business need
- **1.2.6:** Security features defined and implemented for all services, protocols, and ports in use that are considered insecure
- **1.2.7:** NSC configurations reviewed at least once every six months to ensure they remain relevant and effective
- **1.2.8:** NSC configuration files secured from unauthorized access and kept consistent with active network configurations

#### 1.3 — Network access to and from the CDE is restricted

- **1.3.1:** Inbound traffic to the CDE restricted to that which is necessary
- **1.3.2:** Outbound traffic from the CDE restricted to that which is necessary
- **1.3.3:** NSCs installed between all wireless networks and the CDE; wireless traffic denied or, if business justified, restricted

#### 1.4 — Network connections between trusted and untrusted networks are controlled

- **1.4.1:** NSCs implemented between trusted and untrusted networks
- **1.4.2:** Inbound traffic from untrusted networks to trusted networks restricted to: established session communications; traffic from systems in the DMZ
- **1.4.3:** Anti-spoofing measures implemented to detect and block forged source IP addresses
- **1.4.4:** System components that store CHD shall not be directly accessible from untrusted networks
- **1.4.5:** Disclosure of internal IP addresses and routing information to unauthorized parties restricted

#### 1.5 — Risks to the CDE from computing devices able to connect to both untrusted networks and the CDE are mitigated

- **1.5.1:** Security controls for all computing devices connecting to both untrusted networks and the CDE, including personal devices used to access the CDE

### 5.2 Requirement 2 — Apply Secure Configurations to All System Components

**Objective:** Prevent exploitation of commonly used default credentials and unnecessary services.

#### 2.2 — System components are configured and managed securely

- **2.2.1:** Configuration standards developed, implemented, and maintained; standards address all known security vulnerabilities and are consistent with industry-accepted system hardening standards (CIS, NIST, SANS, etc.)
- **2.2.2:** All vendor default accounts either disabled or renamed; passwords changed to unique values
- **2.2.3:** All vendor default security parameters changed
- **2.2.4:** Only necessary functions, components, scripts, drivers, features, subsystems, file systems, and other components enabled
- **2.2.5:** All insecure services, protocols, or daemons present must be documented, justified, and additional security features implemented
- **2.2.6:** System security parameters configured to prevent misuse
- **2.2.7:** All non-console administrative access encrypted using strong cryptography

#### 2.3 — Wireless environments are configured and managed securely

- **2.3.1:** For wireless environments connected to the CDE or transmitting CHD: change wireless vendor defaults; use strong cryptography for authentication and transmission
- **2.3.2:** For wireless environments connected to the CDE or transmitting CHD: change default wireless encryption keys when devices change or compromise is suspected

---

## 6. Goal 2: Protect Account Data

### 6.1 Requirement 3 — Protect Stored Account Data

**Objective:** Protect stored cardholder data through cryptographic and data minimization controls.

#### 3.2 — Storage of account data is kept to a minimum

- **3.2.1:** Account data storage is kept to a minimum; data retention policies exist; quarterly process to identify and securely delete stored SAD and unnecessary CHD

#### 3.3 — Sensitive authentication data (SAD) is not retained after authorization

- **3.3.1:** SAD is not retained after authorization
- **3.3.2 (new v4.0):** SAD stored prior to completion of authorization is protected using strong cryptography
- **3.3.3 (new v4.0):** Encryption keys/keying material for SAD stored prior to authorization managed separately from operational keys

#### 3.4 — Access to displays of full PAN and ability to copy PAN are restricted

- **3.4.1:** PAN is secured at a minimum by being rendered unreadable anywhere it is stored
- **3.4.2 (new v4.0):** When using remote access technologies, technical controls prevent copy/relocate of PAN for all personnel, except where explicitly authorized for defined business need

#### 3.5 — Primary account number (PAN) is secured wherever it is stored

- **3.5.1:** PAN is secured using any of: strong one-way keyed hash functions of the entire PAN; truncation; index tokens; strong cryptography
- **3.5.1.1 (new v4.0):** Hashes used to render PAN unreadable must be keyed cryptographic hashes, with associated key management
- **3.5.1.2 (new v4.0):** If disk-level or partition-level encryption is used for PAN protection, logical access must be managed separately from OS authentication

#### 3.6 — Cryptographic keys used to protect stored account data are secured

- **3.6.1:** Key management procedures and processes for cryptographic keys include: key generation; key distribution; key storage; key access and use; key retirement/replacement; key destruction; key split knowledge and dual control
- **3.6.1.1:** Secret and private keys used to encrypt/decrypt CHD are minimally allowed access
- **3.6.1.2:** Secret and private keys stored in at least one of: encrypted form; within a secure cryptographic device; at least two full-length key-encrypting keys
- **3.6.1.3:** Access to cleartext cryptographic key-encrypting keys restricted to fewest possible custodians
- **3.6.1.4:** Cryptographic keys protected against disclosure and misuse

#### 3.7 — Key management processes cover all aspects of the key lifecycle

- **3.7.1–3.7.9:** Key generation, distribution, storage, access, retirement, destruction, split knowledge, dual control, annual acknowledgment by custodians

### 6.2 Requirement 4 — Protect Cardholder Data with Strong Cryptography During Transmission Over Open, Public Networks

**Objective:** Encryption of CHD/PAN in transit over open networks.

- **4.2.1:** Strong cryptography used to safeguard PAN during transmission over open public networks
  - Only trusted keys/certificates accepted
  - Certificate of devices that accept connections confirmed
  - Current encryption strength in use — SSLv2, SSLv3, TLS 1.0, TLS 1.1 are prohibited
  - TLS 1.2 minimum; TLS 1.3 recommended
- **4.2.1.1 (new v4.0):** Inventory of trusted keys and certificates used to protect PAN in transit maintained
- **4.2.2:** PAN secured with strong cryptography whenever sent via end-user messaging technologies (email, SMS, chat)

---

## 7. Goal 3: Maintain a Vulnerability Management Program

### 7.1 Requirement 5 — Protect All Systems and Networks from Malicious Software

**Objective:** Deploy and maintain anti-malware on all applicable systems.

- **5.2.1:** Anti-malware solution deployed on all system components except those not at risk from malware (documented risk analysis required for exclusions)
- **5.2.2:** Anti-malware solution detects, removes, blocks all types of malicious software
- **5.2.3:** Systems not at risk from malware are periodically evaluated to confirm exclusion remains appropriate
- **5.2.3.1 (new v4.0):** Frequency of periodic evaluations of non-malware-risk systems defined in targeted risk analysis
- **5.3.1:** Anti-malware solution kept current via automatic updates
- **5.3.2:** Anti-malware solution performs periodic scans AND/OR continuous behavioral analysis
- **5.3.2.1 (new v4.0):** Periodic scans must be performed per targeted risk analysis if behavioral analysis not used
- **5.3.3:** All removable media scanned for malware when inserted
- **5.3.4:** Audit logs for anti-malware solution enabled and retained per Requirement 10
- **5.3.5:** Anti-malware mechanisms cannot be disabled or altered by users unless specifically authorized for defined time period
- **5.4.1 (new future-dated):** Processes and automated mechanisms to detect and protect personnel against phishing attacks

### 7.2 Requirement 6 — Develop and Maintain Secure Systems and Software

**Objective:** Protect systems and applications from known vulnerabilities through secure development and patch management.

#### 6.2 — Bespoke and custom software are developed securely

- **6.2.1:** Bespoke and custom software developed securely including: training for development personnel; SDLC inclusion of security; security design reviews
- **6.2.2:** Software development personnel trained at least once every 12 months on: entity's secure coding guidelines; relevant security threats; secure coding techniques
- **6.2.3:** All bespoke and custom software reviewed prior to production to identify and correct potential vulnerabilities using manual and automated methods
- **6.2.3.1 (new v4.0):** If manual code reviews performed before production: performed by reviewers knowledgeable in secure coding practices; all identified vulnerabilities corrected; other security requirements confirmed
- **6.2.4:** Software engineering techniques address in bespoke and custom software: injection attacks; attacks on authentication and session management; attacks on data and data structures; attacks on cryptography; business logic attacks; access control attacks

#### 6.3 — Security vulnerabilities are identified and addressed

- **6.3.1:** Security vulnerabilities identified, ranked, and addressed using a vulnerability identification process
- **6.3.2:** Inventory of all bespoke and custom software and third-party software components managed to minimize exposure from vulnerabilities
- **6.3.3 (new v4.0):** All system components protected from known vulnerabilities by installing applicable security patches/updates: critical/high patches within 1 month; other patches within 3 months

#### 6.4 — Public-facing web applications are protected against attacks

- **6.4.1:** Public-facing web applications protected against web application attacks using either:
  - Continuous automated technical solution detecting and preventing web-based attacks, OR
  - Periodic web application vulnerability assessment (minimum annually or after changes)
- **6.4.2 (new future-dated):** All public-facing web applications protected by an automated technical solution detecting and preventing web-based attacks continuously (required March 31, 2025)
- **6.4.3 (new v4.0):** All payment page scripts loaded and executed in the consumer's browser are managed: method to confirm that each script is authorized; method to assure integrity of each script; inventory of all scripts with written justification

#### 6.5 — Changes to all system components are managed securely

- **6.5.1–6.5.6:** Test environments separate from production; change procedures; system component assignments review; production data not used in testing; test data removed before production; all system configurations reviewed for security before production

---

## 8. Goal 4: Implement Strong Access Control Measures

### 8.1 Requirement 7 — Restrict Access to System Components and Cardholder Data by Business Need to Know

**Objective:** Limit access to CHD to only those individuals whose job requires such access.

- **7.2.1:** Access control model defined; all access rights granted based on job function and required access; least privilege
- **7.2.2:** Access to system components and data assigned to users based on job classification and function; minimum necessary access
- **7.2.3:** Required privileges approved by authorized personnel
- **7.2.4 (new v4.0):** All user accounts and related access privileges reviewed at least once every 6 months
- **7.2.5 (new v4.0):** All application and system accounts and related access privileges assigned and managed based on least privilege
- **7.2.5.1 (new v4.0):** All access by application and system accounts reviewed periodically per targeted risk analysis
- **7.2.6 (new v4.0):** All user access to query repositories of stored CHD restricted through technical controls
- **7.3.1:** Access control system(s) implemented that restrict access to CDE system components based on need to know
- **7.3.2:** All other access denied by default
- **7.3.3:** Access control system(s) are kept current

### 8.2 Requirement 8 — Identify Users and Authenticate Access to System Components

**Objective:** Ensure appropriate user identification and authentication controls.

#### 8.2 — User identification and related accounts are strictly managed

- **8.2.1:** All user IDs and authentication credentials and related user-identity management are strictly and properly managed throughout the user-access life cycle
- **8.2.2:** Group, shared, or generic accounts used only when necessary on an exceptional basis
- **8.2.3:** Additional requirement for service providers: Each customer's access uniquely identified
- **8.2.4:** Addition/deletion/modification of user IDs, credentials, and other identifier objects managed: additions authorized; deletions/deactivations performed immediately upon termination
- **8.2.5:** Access for terminated users immediately revoked
- **8.2.6:** Inactive user accounts removed or disabled within 90 days
- **8.2.7:** Accounts used by vendors and third parties for remote access: enabled only during use; disabled when not in use; monitored when in use
- **8.2.8:** If a user session has been idle for more than 15 minutes, require re-authentication

#### 8.3 — Strong authentication for users and administrators is established and managed

- **8.3.1:** All user access authenticated via at least one of: something you know (password); something you have (token); something you are (biometric)
- **8.3.2:** Strong cryptography used to render all authentication factors unreadable during transmission and storage on all system components
- **8.3.4:** Invalid authentication attempts limited: locking out user ID after not more than 10 attempts; lockout duration minimum 30 minutes or until administrator re-enables
- **8.3.5:** If passwords/passphrases used as authentication factors: reset upon first use; changed upon any suspicion of compromise
- **8.3.6 (new future-dated):** If passwords/passphrases used as authentication factor: minimum length of at least 12 characters (or, if system does not support 12 characters, a minimum of eight characters) using both numeric and alphabetic characters (required March 31, 2025)
- **8.3.7:** Individuals are not allowed to submit a new password/passphrase that is the same as any of the last four passwords/passphrases used
- **8.3.8:** Authentication policies and procedures documented and communicated to users
- **8.3.9:** If password/passphrase is used as authentication factor for a non-privileged account: change at least once every 90 days, OR assess security posture dynamically and adapt in real time

#### 8.4 — Multi-factor authentication (MFA) is implemented to secure access into the CDE

- **8.4.1:** MFA implemented for all non-console access into the CDE for personnel with administrative access
- **8.4.2 (new v4.0):** MFA implemented for all access into the CDE
- **8.4.3:** MFA implemented for all remote network access originating from outside the entity's network that could access or impact the CDE

#### 8.6 — Use of application and system accounts and associated authentication factors is strictly managed

- **8.6.1 (new v4.0):** If accounts used by systems or applications can be used for interactive login, they are managed per requirements
- **8.6.2 (new v4.0):** Passwords/passphrases for application and system accounts not hardcoded in scripts, code, config files, or other locations
- **8.6.3 (new v4.0):** Passwords/passphrases for application and system accounts protected against misuse

### 8.3 Requirement 9 — Restrict Physical Access to Cardholder Data

**Objective:** Prevent unauthorized physical access to CHD and CDE.

- **9.2.1:** Appropriate facility entry controls implemented to distinguish between onsite personnel and visitors in areas housing sensitive systems
- **9.2.1.1 (new v4.0):** Entry to areas housing CDE requires individual physical access using either: unique badge/token; or MFA biometric/PIN
- **9.2.2:** Physical and/or logical controls implemented to restrict access to publicly accessible network jacks
- **9.2.3:** Physical access to wireless access points, gateways, networking/communications hardware, and telecommunication lines within the facility restricted
- **9.2.4:** Access to consoles in sensitive areas restricted via locking when unattended
- **9.3.1:** Physical access controls: procedures to authorize and manage physical access for all personnel; access promptly revoked upon departure
- **9.3.2:** Procedures implemented for authorizing and managing visitor access
- **9.3.3:** Visitor badges or identification distinguishable from onsite personnel; expire; collected upon departure
- **9.3.4:** Visitor log used to maintain physical audit trail of visitor activity
- **9.4.1:** All media (paper and electronic) with CHD protected
- **9.4.1.1 (new v4.0):** All media with CHD classified in accordance with the sensitivity of the data
- **9.4.1.2 (new v4.0):** All media with CHD inventoried
- **9.4.2:** All media sent outside the facility secured; approved by management
- **9.4.3:** All media with CHD destroyed when no longer needed in a secure manner so the data cannot be reconstructed
- **9.4.4:** Management approves all media destroyed; destruction performed and confirmed
- **9.5.1:** POS devices protected from tampering and unauthorized substitution; includes periodic inspection

---

## 9. Goal 5: Regularly Monitor and Test Networks

### 9.1 Requirement 10 — Log and Monitor All Access to System Components and Cardholder Data

**Objective:** Implement audit trails to detect and minimize the impact of data compromises.

#### 10.2 — Audit logs are implemented to support the detection of anomalies and suspicious activity

- **10.2.1:** Audit logs enabled and active; log entries created for each event including: all individual user access to CHD; all actions by root or administrative privileges; access to and changes to audit trails; invalid logical access attempts; use of identification/authentication mechanisms; initialization/stopping/pausing of audit logs; creation and deletion of system-level objects; failure of security functions
- **10.2.2:** Audit log entries contain sufficient data to reconstruct each event: user identification; type of event; date and time; success or failure indicator; origination; identity/name of affected data/system component/resource

#### 10.3 — Audit logs are protected from destruction and unauthorized modifications

- **10.3.2:** Audit log files protected to prevent modifications by individuals
- **10.3.3:** Audit log files backed up promptly to a centralized log server or media that is difficult to alter
- **10.3.4:** File integrity monitoring or change detection mechanisms used on audit logs

#### 10.4 — Audit logs are reviewed to identify anomalies or suspicious activity

- **10.4.1:** Alerts generated by security controls reviewed at least once per day
- **10.4.1.1 (new future-dated):** Automated mechanisms used to perform audit log reviews (required March 31, 2025)
- **10.4.2:** Logs of all other system components reviewed periodically per entity's targeted risk analysis
- **10.4.3:** Exceptions and anomalies identified during review are addressed

#### 10.5 — Audit log history is retained and available for analysis

- **10.5.1:** Retain audit log history for at least 12 months, with at least the most recent three months available for immediate analysis

#### 10.6 — Time-synchronization mechanisms support consistent time settings across all systems

- **10.6.1:** Internal and external network time protocol (NTP) or similar time synchronization technology configured for all system components

#### 10.7 — Failures of critical security controls are detected, reported, and responded to promptly

- **10.7.1 (for service providers):** Failures of critical security controls detected, alerted, and addressed promptly
- **10.7.2 (new v4.0, for all entities):** Failures of critical security controls detected, alerted, and addressed promptly — critical controls specified

### 9.2 Requirement 11 — Test Security of Systems and Networks Regularly

**Objective:** Identify vulnerabilities through regular testing before they can be exploited.

#### 11.2 — Wireless access points are identified and monitored

- **11.2.1:** Authorized and unauthorized wireless access points managed; testing performed at least once every three months
- **11.2.2:** An inventory of authorized wireless access points maintained

#### 11.3 — External and internal vulnerabilities are regularly identified, prioritized, and addressed

- **11.3.1:** Internal vulnerability scans performed at least once every three months and after significant changes; scan by qualified personnel; vulnerabilities addressed per Requirement 6.3.3 ranking; confirmed clean rescans
- **11.3.1.1 (new v4.0):** All other applicable vulnerabilities managed as defined in targeted risk analysis
- **11.3.1.2 (new future-dated):** Internal vulnerability scans performed via authenticated scanning
- **11.3.1.3 (new v4.0):** Internal vulnerability scans that identify vulnerabilities managed using a risk-based remediation approach
- **11.3.2:** External vulnerability scans performed at least once every three months via PCI SSC-approved ASV (Approved Scanning Vendor); clean scan achieved; rescans after significant changes

#### 11.4 — External and internal penetration testing is regularly performed (see Section 14)

#### 11.5 — Network intrusions and unexpected file changes are detected and responded to

- **11.5.1:** Network intrusion detection and/or intrusion prevention techniques to detect and/or prevent intrusions
- **11.5.1.1 (new future-dated):** Change-and-tamper-detection mechanisms on payment pages; alerts on changes to HTTP headers, page content (required March 31, 2025)
- **11.5.2:** A change-detection mechanism deployed to alert personnel to unauthorized modification of critical files; critical files compared at least weekly

#### 11.6 — Unauthorized changes on payment pages are detected and responded to

- **11.6.1 (new future-dated):** Change and tamper detection mechanism deployed on payment pages in browser to alert on unauthorized modifications (required March 31, 2025)

---

## 10. Goal 6: Maintain an Information Security Policy

### 10.1 Requirement 12 — Support Information Security with Organizational Policies and Programs

**Objective:** Establish and maintain an information security policy addressing all personnel.

- **12.1.1:** Overall information security policy established, published, maintained, and disseminated to all relevant personnel and applicable vendors/business partners
- **12.1.2:** Information security policy reviewed at least once every 12 months and updated when the environment changes
- **12.1.3:** Information security policy clearly defines information security roles and responsibilities for all personnel
- **12.1.4:** Responsibility for information security formally assigned to a CISO or other information security-knowledgeable member of executive management
- **12.2.1:** Acceptable use policies for end-user technologies implemented covering: explicit approval; acceptable uses; list of approved products
- **12.3.1:** Each PCI DSS requirement that provides flexibility must have a targeted risk analysis performed per requirements
- **12.3.2 (new v4.0):** Targeted risk analysis performed for each PCI DSS requirement met with the customized approach
- **12.4.1 (service providers):** Executive management establishes responsibility for the protection of CHD and a PCI DSS compliance program
- **12.4.2 (new v4.0, service providers):** Reviews performed at least once every three months to confirm personnel are following all security policies and operational procedures
- **12.5.1:** Inventory of system components in scope for PCI DSS maintained and kept current
- **12.5.2:** PCI DSS scope confirmed at least once every 12 months and after significant changes
- **12.5.3 (new v4.0, service providers):** PCI DSS scope confirmed every 6 months and after significant changes
- **12.6.1:** Formal security awareness program implemented to make all personnel aware of the entity's information security policy and procedures
- **12.6.2 (new v4.0):** Security awareness program reviewed at least once every 12 months; updated to address threats and vulnerabilities
- **12.6.3:** Personnel acknowledge at least once every 12 months that they have read and understood the security policy
- **12.6.3.1 (new v4.0):** Security awareness training includes awareness of threats and vulnerabilities including phishing and social engineering
- **12.6.3.2 (new v4.0):** Security awareness training includes awareness of acceptable use of end-user technologies
- **12.7.1:** Background checks (criminal, credit, reference) performed prior to hire for personnel in positions with access to CHD
- **12.8.1–12.8.5:** All third-party service providers with access to CHD managed through: list of TPSPs maintained; written agreements; acknowledgment of their responsibility for CHD security; TPSP compliance status monitoring program; documented information about which PCI DSS requirements are managed by each TPSP
- **12.9.1 (service providers):** Written agreement with customers acknowledging responsibility for CHD in TPSP's possession
- **12.10.1:** Incident response plan exists and is ready to be activated in case of system breach; includes at minimum: roles, responsibilities, and communications; incident response procedures; business recovery and continuity procedures; backup processes; analysis of legal requirements for reporting compromises; coverage and responses of all critical system components; reference to or inclusion of incident response procedures from payment brands
- **12.10.2:** Incident response plan reviewed and tested at least once every 12 months
- **12.10.3:** Specific personnel designated to be available 24/7 to respond to suspected or confirmed security incidents
- **12.10.4:** Personnel providing incident response activities receive appropriate and ongoing training
- **12.10.4.1 (new v4.0):** Personnel responsible for responding to suspected and confirmed security incidents receive training at least once every 12 months
- **12.10.5:** Alerts from security monitoring systems included in incident response plan
- **12.10.6 (new v4.0):** Security incident response plan updated and evolved according to lessons learned and to incorporate industry developments
- **12.10.7 (new v4.0):** Incident response procedures maintained and practiced for detection of unexpected PAN in unexpected places

---

## 11. PCI DSS v4.0 New Requirements vs v3.2.1

### 11.1 New Immediate Requirements (Effective March 31, 2024)

These requirements were new in v4.0 and immediately effective upon v3.2.1 retirement:

| Requirement | Description |
|---|---|
| 3.3.2 | SAD stored prior to authorization encrypted |
| 3.5.1.1 | Hashes used to render PAN unreadable must be keyed cryptographic hashes |
| 3.5.1.2 | Disk-level encryption for PAN requires separate logical access management |
| 4.2.1.1 | Inventory of trusted keys and certificates maintained |
| 6.3.3 | All patches: critical/high within 1 month; others within 3 months |
| 6.4.3 | Payment page scripts must be authorized and integrity-assured |
| 7.2.4 | User account access reviewed at least every 6 months |
| 7.2.5 | Application/system account access reviewed per targeted risk analysis |
| 7.2.6 | Access to query CHD repositories restricted by technical controls |
| 8.2.6 | Inactive accounts disabled within 90 days |
| 8.4.2 | MFA required for all access into the CDE |
| 8.6.1–8.6.3 | Application/system account passwords not hardcoded; protected |
| 9.2.1.1 | Entry to CDE requires individual physical access with unique badge/token or MFA |
| 9.4.1.1 | Media with CHD classified per sensitivity |
| 9.4.1.2 | Media with CHD inventoried |
| 10.7.2 | Failures of critical security controls detected and addressed promptly |
| 12.3.1 | Targeted risk analysis for all flexible requirements |
| 12.5.2 | PCI DSS scope confirmed at least once every 12 months |
| 12.6.3.1 | Security awareness training includes phishing awareness |
| 12.10.7 | Incident response for unexpected PAN |

### 11.2 Future-Dated Requirements (Effective March 31, 2025)

| Requirement | Description |
|---|---|
| 5.3.2.1 | Frequency of periodic scans defined in targeted risk analysis |
| 5.4.1 | Automated phishing detection mechanisms |
| 6.4.2 | Automated WAF or equivalent for all public-facing web applications |
| 7.2.5.1 | Application/system account access reviewed per targeted risk analysis |
| 8.3.6 | Minimum password length of 12 characters |
| 10.4.1.1 | Automated mechanisms for audit log review |
| 11.3.1.2 | Internal scans performed via authenticated scanning |
| 11.6.1 | Change/tamper detection on payment pages in browser |
| 12.3.2 | Customized approach requires documented targeted risk analysis |
| 12.4.2 | Service providers: quarterly reviews of personnel compliance |
| 12.10.4.1 | Incident response training at least annually |

### 11.3 Key Themes in v4.0

**Customized Approach:** Entirely new concept allowing mature organizations to design their own controls to meet the stated objectives.

**Targeted Risk Analysis:** Many requirements previously had fixed frequencies — v4.0 allows targeted risk analyses to define appropriate frequencies for some controls.

**Authentication enhancements:** MFA now required for all CDE access (not just remote access); stronger password requirements; system/application account management.

**E-commerce security:** New requirements for payment page script management and browser-side tamper detection specifically address web skimming (Magecart-type attacks).

**Phishing protection:** Explicit requirement to detect and protect against phishing targeting personnel.

---

## 12. Validation Methods: SAQ Types

### 12.1 Overview

Self-Assessment Questionnaires (SAQs) are validation tools for eligible merchants and service providers. There are nine SAQ types corresponding to specific payment acceptance methods.

### 12.2 SAQ Types

| SAQ | Who Uses It | Description | Questions (approx.) |
|---|---|---|---|
| SAQ A | Card-not-present merchants fully outsourcing all CHD functions | All CHD handled by PCI-compliant third-party; no electronic storage; no card present; website redirects or uses iframes | ~20 |
| SAQ A-EP | E-commerce merchants partially outsourcing payment processing | E-commerce only; third party handles CHD; merchant website does not directly receive CHD | ~190 |
| SAQ B | Merchants using imprinters or standalone dial-up terminals | No electronic storage of CHD; card present; no internet connectivity | ~40 |
| SAQ B-IP | Merchants using standalone PTS-approved payment terminals | PTS-approved IP-connected devices only; no electronic storage | ~85 |
| SAQ C | Merchants using payment application systems connected to the Internet | Application connected to internet; CHD not stored | ~160 |
| SAQ C-VT | Merchants who manually enter transactions via virtual terminal | Single payment app on computer connected to internet; no electronic storage | ~70 |
| SAQ D Merchant | Merchants not qualifying for other SAQs | Full assessment for merchants not meeting simpler SAQ criteria | ~250 |
| SAQ D Service Provider | Service providers storing/processing/transmitting CHD | Full requirements for service providers | ~325 |
| SAQ P2PE | Merchants using approved P2PE solution | Hardware payment terminals in validated P2PE solution | ~35 |

### 12.3 SAQ Eligibility Requirements

To use an SAQ, a merchant must:
1. Meet all eligibility criteria for the specific SAQ type
2. Confirm that all requirements stated "in place" are implemented
3. Have no indications that any CHD has been compromised
4. Not be required to undergo an on-site QSA assessment (Level 1 merchants are not SAQ-eligible)

---

## 13. QSA vs ISA vs SAQ Assessments

### 13.1 Qualified Security Assessor (QSA)

**Who:** A company/individual certified by the PCI SSC to perform PCI DSS on-site assessments.

**When required:**
- Level 1 merchants (>6 million transactions)
- Level 1 service providers (>300,000 transactions)
- Any entity choosing to use a QSA for validation

**Output:** Report on Compliance (ROC) + Attestation of Compliance (AOC) signed by QSA.

**Certification:** QSA companies are PCI SSC-approved; individual assessors are QSA-certified with required training and testing.

### 13.2 Internal Security Assessor (ISA)

**Who:** An employee of a merchant or service provider who has completed PCI SSC ISA training and certification.

**When used:**
- Internal PCI compliance programs
- Internal gap assessments and readiness
- Some card brands accept ISA-validated SAQs for Level 2 merchants

**Limitation:** ISA-validated assessments are typically not accepted for Level 1 assessments or ROCs. ISAs cannot perform formal QSA-level assessments for other companies.

### 13.3 Approved Scanning Vendor (ASV)

**Who:** An organization certified by PCI SSC to perform external vulnerability scanning.

**Required for:** External network vulnerability scanning (Requirement 11.3.2) — must be conducted by a PCI SSC-approved ASV.

Internal scans can be performed by internal qualified staff (not required to be ASV).

### 13.4 Assessment Deliverables Comparison

| Assessment Type | Deliverable | Signed By |
|---|---|---|
| QSA On-Site Assessment | Report on Compliance (ROC) + Attestation of Compliance (AOC) | QSA Company and Merchant/SP |
| SAQ Self-Assessment | Completed SAQ + Attestation of Compliance (AOC) | Merchant/SP (and ISA if applicable) |
| External ASV Scan | ASV Scan Report + Compliance Scan Certificate | ASV |

---

## 14. Penetration Testing Requirements (Requirement 11.4)

### 14.1 Penetration Testing Overview

PCI DSS Requirement 11.4 mandates penetration testing to verify that network security controls are working effectively and that all known vulnerabilities have been addressed.

### 14.2 Requirement 11.4 Details

- **11.4.1:** Penetration testing methodology defined, documented, and implemented; includes:
  - Industry-accepted penetration testing approaches (NIST SP 800-115, OWASP, PTES)
  - Coverage for the entire CDE perimeter and critical systems
  - Testing from both inside and outside the network
  - Testing to validate any segmentation and scope-reduction controls
  - Application-layer penetration testing to include at minimum vulnerabilities in Requirement 6.2.4
  - Network-layer penetration tests encompassing all components supporting network functions and operating systems
  - Review and consideration of threats and vulnerabilities experienced in the last 12 months
  - Documented approach to assessing and addressing the risk posed by exploitable vulnerabilities found
  - Retention of penetration testing results and remediation activities for at least 12 months

- **11.4.2:** Internal penetration test performed at least once every 12 months and after any significant infrastructure or application upgrade or change

- **11.4.3:** External penetration test performed at least once every 12 months and after any significant infrastructure or application upgrade or change

- **11.4.4:** Exploitable vulnerabilities and security weaknesses found during penetration testing are corrected; testing to verify corrections is repeated

- **11.4.5:** If network segmentation is used to isolate the CDE: Penetration tests on segmentation controls at least once every 12 months (or every six months for service providers) and after any changes to segmentation controls/methods

- **11.4.6 (new v4.0):** Additional for service providers: Penetration tests on segmentation controls at least once every 6 months and after any changes

- **11.4.7 (new future-dated v4.0):** Additional for multi-tenant service providers: provide external penetration testing to customers for their segmented environment

### 14.3 Who Can Perform Penetration Testing

Unlike ASV scans, penetration testers are not required to be PCI SSC-approved. However:
- Must have organizational independence (cannot test systems they are responsible for)
- Must have qualified expertise in penetration testing
- For service providers: preferred to use a qualified external tester
- For merchants: can be performed by internal qualified personnel if independent

### 14.4 Penetration Testing Scope

**External penetration test covers:**
- External-facing systems in the CDE
- Internet-accessible entry points
- Third-party systems connecting to the CDE
- Segmentation controls from untrusted to CDE

**Internal penetration test covers:**
- Internal network to CDE lateral movement
- Privilege escalation within CDE
- Segmentation between CDE and non-CDE
- Application-level attacks on CHD processing applications

### 14.5 Penetration Testing vs Vulnerability Scanning

| Dimension | Penetration Testing (Req 11.4) | Vulnerability Scanning (Req 11.3) |
|---|---|---|
| Frequency | Annually (or after major changes) | Quarterly (internal and external) |
| Method | Manual + automated; exploits vulnerabilities | Automated scan; identifies potential vulnerabilities |
| Scope | Targeted; simulates attacker | Comprehensive; all identified hosts |
| Output | Detailed findings with exploitability | List of vulnerabilities with CVSS scores |
| Performer | Qualified security professional | Internal staff or ASV |
| Who required | Qualified tester (independent) | ASV (external); qualified staff (internal) |

---

## 15. Network Segmentation and Scope Reduction

### 15.1 Why Segmentation Matters for PCI

Network segmentation is not required by PCI DSS but is strongly recommended as the primary strategy for reducing PCI DSS scope. Without segmentation, the entire network is in scope.

### 15.2 Effective Segmentation

For segmentation to effectively reduce PCI scope, it must:
- Completely isolate (segment) the CDE from all non-CDE systems
- Ensure non-CDE systems cannot connect to CDE systems at all, or are controlled through a firewall with the fewest necessary connections
- Be implemented through firewalls, routers with ACLs, DMZs, VLANs with appropriate controls, or physical separation

### 15.3 Segmentation Controls

| Segmentation Method | Notes |
|---|---|
| Firewall / dedicated appliance | Traditional; most common; requires strict rule management |
| Router ACLs | Can segment; lower assurance than dedicated firewall |
| VLAN | Common; must include associated security controls (no VLAN hopping) |
| Physical separation | Highest assurance; most expensive |
| Air gap | Maximum isolation; no connectivity at all |
| Jump server / bastion host | Controlled access point; jump server itself is in scope |
| Zero-trust network architecture | Emerging approach; each connection authenticated/authorized |

### 15.4 Validating Segmentation

- Penetration test of segmentation controls required at least annually (Req 11.4.5)
- Firewall rule reviews required at least every six months (Req 1.2.7)
- Data flow diagrams must document scope boundaries (Req 1.2.4)
- Scope confirmation must validate segmentation effectiveness (Req 12.5.2)

### 15.5 Connected-To vs Directly Segmented

**Directly in CDE scope:** Systems storing, processing, transmitting CHD/SAD.

**Connected to CDE (also in scope unless segmented):** Systems that have network connectivity to CDE systems.

**Effectively segmented (out of scope):** Systems that cannot communicate with CDE systems, verified through controls and testing.

---

## 16. Tokenization and P2PE for Descoping

### 16.1 Tokenization

**Definition:** Replacement of the PAN with a non-sensitive substitute value (token) that has no exploitable value outside the specific system that generated it.

**How it reduces scope:**
- Systems that only see tokens (not the real PAN) are generally not in scope
- The tokenization system/vault itself is in scope
- Reduces scope for downstream systems, applications, databases, and networks that only need to reference a transaction

**Key considerations:**
- Tokens must be irreversible outside the secure vault
- Vault and detokenization services are fully in scope
- Risk assessment required to confirm token systems are not reversible by attackers
- Format-preserving tokens (same length as PAN) may still be treated as PAN by some assessors

**Tokenization vs Encryption:**
- **Encryption:** PAN encrypted; decryption key exists; technically reversible; all encrypted PAN still in scope
- **Tokenization:** PAN replaced with random value; no mathematical relationship; downstream systems truly cannot recover PAN

### 16.2 Point-to-Point Encryption (P2PE)

**Definition:** Account data is encrypted from the point of interaction (POI terminal) immediately upon card swipe/dip/tap, and is not decrypted until it reaches the secure decryption environment (typically operated by payment processor).

**PCI SSC Validated P2PE Solutions:** PCI SSC maintains a list of validated P2PE solutions. Using a validated P2PE solution significantly reduces merchant scope.

**Scope reduction with validated P2PE:**
- Merchants using PCI SSC-validated P2PE solutions may qualify for SAQ P2PE
- SAQ P2PE has ~35 questions vs ~250 for SAQ D
- Merchant's physical environment (card reader) is in scope, but not the surrounding network/systems
- The P2PE solution provider's environment is in scope (assessed separately)

**P2PE requirements:**
- Hardware POI devices must be PCI-approved
- POI devices must be in tamper-evident packaging from manufacturer
- Solution provider must provide instruction manual
- Merchant must follow solution provider's P2PE instruction manual

### 16.3 Descoping Technologies Summary

| Technology | Scope Reduction | Notes |
|---|---|---|
| Tokenization | High — downstream systems out of scope | Token vault is in scope |
| Validated P2PE | Very High — most merchant environment out of scope | POI device and physical controls in scope |
| Redirect to processor (iFrame) | High — merchant website not in CHD flow | SAQ A may apply |
| Encryption at rest only | Low — encrypted CHD still in scope | Decryption capability keeps systems in scope |
| VLAN segmentation | Moderate — depends on segmentation effectiveness | Requires validation via pen testing |

---

## 17. PCI DSS Overlap with NIST 800-53 and FedRAMP

### 17.1 Framework Comparison

| Dimension | PCI DSS v4.0 | NIST 800-53 Rev 5 | FedRAMP Moderate |
|---|---|---|---|
| Purpose | CHD protection standard | Federal info system security | Cloud services for federal government |
| Authority | PCI SSC (contractual) | NIST (federal guidance) | OMB/GSA/NIST (federal mandate) |
| Required for | Merchants and service providers handling card data | Federal information systems | Cloud services to federal agencies |
| Control depth | Prescriptive + customizable | Very detailed (1,000+ control parameters) | NIST 800-53 with FedRAMP overlays |
| Audit | QSA ROC / SAQ | ATO package | 3PAO assessment; ATO |
| Scope | CDE | System boundary | Cloud service offering |

### 17.2 Control Mapping — PCI DSS to NIST 800-53

| PCI DSS Requirement | NIST 800-53 Control Families |
|---|---|
| Req 1 — Network controls | SC-7 (Boundary Protection); SC-5 (DoS Protection); AC-17 (Remote Access) |
| Req 2 — Secure configurations | CM-6 (Configuration Settings); CM-7 (Least Functionality); SA-22 (Unsupported Software) |
| Req 3 — Stored data protection | SC-28 (Protection at Rest); SC-12 (Key Management); MP-4 (Media Storage) |
| Req 4 — Transmission encryption | SC-8 (Transmission Confidentiality/Integrity); SC-13 (Cryptographic Protection) |
| Req 5 — Malware | SI-3 (Malicious Code Protection); SI-8 (Spam Protection) |
| Req 6 — Secure development | SA-3 (SDLC); SA-11 (Dev Security Testing); SA-15 (Dev Process) |
| Req 7 — Access restriction | AC-2 (Account Management); AC-6 (Least Privilege) |
| Req 8 — Authentication | IA-2 (User Identification/Authentication); IA-5 (Auth Management); AC-7 (Unsuccessful Attempts) |
| Req 9 — Physical access | PE-2 (Physical Access Authorizations); PE-3 (Physical Access Control); PE-6 (Monitoring) |
| Req 10 — Logging | AU-2 (Event Logging); AU-3 (Content of Audit Records); AU-9 (Protection); AU-11 (Retention) |
| Req 11 — Testing | CA-2 (Security Assessments); CA-8 (Penetration Testing); RA-5 (Vulnerability Monitoring) |
| Req 12 — Security policy | PL-1 (Policy); PM-1 (Information Security Program Plan); IR-1 (Incident Response Policy) |

### 17.3 Organizations Requiring Both PCI DSS and FedRAMP

Federal agencies or contractors processing payment card data for government services must comply with both:
- **FedRAMP** for cloud services used by the federal agency
- **PCI DSS** for any cardholder data processed (e.g., online fee payment systems)

**Areas of tension:**
- FedRAMP baseline controls may not fully satisfy PCI DSS requirements (different scopes)
- PCI DSS penetration testing frequency (annual) aligns with FedRAMP annual assessment
- PCI DSS patch timelines (critical: 1 month) are more prescriptive than NIST 800-53 (SI-2, often risk-based)
- FedRAMP continuous monitoring may satisfy some PCI DSS ongoing testing requirements

### 17.4 Shared Evidence Opportunities

Organizations pursuing both PCI DSS and FedRAMP/NIST can leverage shared evidence:
- Risk assessments (RA-3 / PCI Req 12.3)
- Penetration testing reports (CA-8 / PCI Req 11.4)
- Vulnerability scan results (RA-5 / PCI Req 11.3)
- Access reviews (AC-2 / PCI Req 7.2.4)
- Security awareness training (AT-2, AT-3 / PCI Req 12.6)
- Incident response procedures (IR-8 / PCI Req 12.10)
- Configuration management (CM-6 / PCI Req 2.2)

---

## 18. Quick Reference Tables

### 18.1 PCI DSS 12 Requirements Summary

| Req | Goal | Short Description | Key Frequency |
|---|---|---|---|
| 1 | Network Security | Install and maintain network security controls | Rules reviewed every 6 months |
| 2 | Secure Config | Apply secure configurations to all systems | Ongoing; configuration standards maintained |
| 3 | Data Protection | Protect stored account data | Quarterly purge review |
| 4 | Transmission | Protect transmission with strong cryptography | Ongoing; TLS 1.2+ |
| 5 | Malware | Protect against malicious software | Continuous; scans per risk analysis |
| 6 | Secure Dev | Develop and maintain secure systems | Patches: 1 month (critical); 3 months (others) |
| 7 | Access Control | Restrict access by need to know | User access reviews every 6 months |
| 8 | Authentication | Identify users and authenticate access | MFA all CDE access; 90-day password rotation |
| 9 | Physical | Restrict physical access | Visitor log; media inventory |
| 10 | Logging | Log and monitor all access | Daily alert review; 12-month retention |
| 11 | Testing | Test security regularly | Quarterly external ASV; annual pen test |
| 12 | Policy | Maintain information security policy | Annual policy review; annual training |

### 18.2 Data Storage and Protection Summary

| Data Element | Storage Permitted | Render Unreadable | Notes |
|---|---|---|---|
| PAN | Yes | Yes (required) | First 6/last 4 may display; full PAN must be unreadable |
| Cardholder name | Yes | Recommended | Not required to encrypt if PAN absent |
| Expiration date | Yes | Recommended | |
| Service code | Yes | Recommended | |
| Full track data | No | N/A | Never store post-authorization |
| CVV/CVC/CID | No | N/A | Never store |
| PIN/PIN block | No | N/A | Never store |

### 18.3 Testing Frequency Summary

| Test | Frequency | Performer |
|---|---|---|
| External vulnerability scan | At least every 3 months | ASV (PCI SSC-approved) |
| Internal vulnerability scan | At least every 3 months | Qualified internal staff or QSA |
| External penetration test | At least annually | Qualified tester (independent) |
| Internal penetration test | At least annually | Qualified tester (independent) |
| Segmentation penetration test | At least annually (SP: every 6 months) | Qualified tester |
| File integrity monitoring | Weekly | Automated (configured) |
| Wireless access point scan | At least every 3 months | Qualified staff or tool |
| Firewall rule review | At least every 6 months | Qualified staff |
| User access review | At least every 6 months | Management/system owner |
| Scope confirmation | At least annually (SP: every 6 months) | Internal/QSA |

### 18.4 Glossary of PCI DSS Terms

| Term | Definition |
|---|---|
| PAN | Primary Account Number — the payment card number |
| CHD | Cardholder Data — PAN + cardholder name + service code + expiration date |
| SAD | Sensitive Authentication Data — track data, CVV/CVC, PIN — cannot be stored |
| CDE | Cardholder Data Environment — systems storing, processing, transmitting CHD/SAD |
| QSA | Qualified Security Assessor — PCI SSC-certified assessment company |
| ISA | Internal Security Assessor — employee trained and certified by PCI SSC |
| ASV | Approved Scanning Vendor — PCI SSC-approved for external scans |
| ROC | Report on Compliance — detailed QSA assessment report |
| AOC | Attestation of Compliance — formal compliance declaration |
| SAQ | Self-Assessment Questionnaire — merchant/SP self-validation tool |
| P2PE | Point-to-Point Encryption — encryption from POI to decryption environment |
| POI | Point of Interaction — card reader/terminal |
| Tokenization | Replacement of PAN with non-sensitive surrogate value |
| PCI SSC | PCI Security Standards Council — governance body for PCI standards |
| CNP | Card Not Present — transactions where card is not physically present (e-commerce) |
| CP | Card Present — transactions where card is physically present (in-person) |
| TPSP | Third-Party Service Provider — vendor with access to CHD |

---

*Document Version: 1.0*
*Standard Reference: PCI DSS v4.0 (March 2022); PCI SSC SAQ Documentation (2022)*
*v3.2.1 retired March 31, 2024; future-dated v4.0 requirements effective March 31, 2025*
*For authoritative guidance, consult pcisecuritystandards.org and engage a qualified QSA*
