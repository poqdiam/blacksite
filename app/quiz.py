"""
BLACKSITE — information security quiz bank
Questions covering core information security domains.
"""
from __future__ import annotations
from typing import List, Dict, Any

QUESTIONS: List[Dict] = [
    # ── Domain 1: Security & Risk Management ──────────────────────────────────
    {
        "id": 1,
        "domain": "D1",
        "question": "Under the NIST Risk Management Framework (RMF), which step involves assigning a FIPS 199 impact level (Low/Moderate/High) to the information system?",
        "choices": {
            "A": "Select",
            "B": "Categorize",
            "C": "Authorize",
            "D": "Monitor",
        },
        "answer": "B",
        "explanation": "The Categorize step uses FIPS 199 to determine the system's security categorization based on potential impact to confidentiality, integrity, and availability.",
    },
    {
        "id": 2,
        "domain": "D1",
        "question": "Which NIST publication defines the catalog of security and privacy controls for federal information systems and organizations?",
        "choices": {
            "A": "NIST SP 800-37",
            "B": "NIST SP 800-61",
            "C": "NIST SP 800-53",
            "D": "NIST SP 800-171",
        },
        "answer": "C",
        "explanation": "NIST SP 800-53 (currently Rev 5) provides the catalog of security and privacy controls. SP 800-37 is the RMF guide, 800-61 is incident response, 800-171 is for CUI in nonfederal systems.",
    },
    {
        "id": 3,
        "domain": "D1",
        "question": "FIPS 199 defines three security objectives. Which of the following correctly lists all three?",
        "choices": {
            "A": "Authentication, Authorization, Accounting",
            "B": "Confidentiality, Integrity, Availability",
            "C": "Prevention, Detection, Recovery",
            "D": "Risk, Threat, Vulnerability",
        },
        "answer": "B",
        "explanation": "FIPS 199 defines Confidentiality, Integrity, and Availability (CIA triad) as the three security objectives used to categorize information and information systems.",
    },
    {
        "id": 4,
        "domain": "D1",
        "question": "A System Security Plan (SSP) is required by which federal law?",
        "choices": {
            "A": "HIPAA",
            "B": "Sarbanes-Oxley (SOX)",
            "C": "FISMA",
            "D": "GLBA",
        },
        "answer": "C",
        "explanation": "FISMA (Federal Information Security Modernization Act) mandates that federal agencies develop, document, and implement SSPs for their information systems.",
    },
    {
        "id": 5,
        "domain": "D1",
        "question": "What is the primary difference between a threat and a vulnerability in risk management?",
        "choices": {
            "A": "A threat is a weakness; a vulnerability is a potential harm.",
            "B": "A threat is a potential harmful event; a vulnerability is a weakness that can be exploited.",
            "C": "They are interchangeable terms in most frameworks.",
            "D": "A vulnerability is always intentional; a threat is accidental.",
        },
        "answer": "B",
        "explanation": "A threat is an event that could cause harm (e.g., a malicious actor, hurricane). A vulnerability is a weakness that could be exploited to realize that threat.",
    },
    {
        "id": 6,
        "domain": "D1",
        "question": "What does 'least privilege' mean in information security?",
        "choices": {
            "A": "Administrators should have the fewest users reporting to them.",
            "B": "Users and systems should be granted only the minimum permissions necessary to perform their function.",
            "C": "The organization should purchase the least expensive security tools.",
            "D": "Security policies should impose as few restrictions as possible on end users.",
        },
        "answer": "B",
        "explanation": "Least privilege (NIST 800-53r5 AC-6) limits damage from accidents, errors, or unauthorized use by ensuring entities operate with only required access.",
    },
    {
        "id": 7,
        "domain": "D1",
        "question": "In a FedRAMP authorization context, who holds the authority to grant an Authorization to Operate (ATO)?",
        "choices": {
            "A": "System Owner",
            "B": "Information System Security Officer (ISSO)",
            "C": "Authorizing Official (AO)",
            "D": "CISA",
        },
        "answer": "C",
        "explanation": "The Authorizing Official (AO) is a senior official who accepts residual risk on behalf of the organization by granting or denying the ATO.",
    },
    {
        "id": 8,
        "domain": "D1",
        "question": "What is the goal of a Business Impact Analysis (BIA)?",
        "choices": {
            "A": "Identify and rank vulnerabilities in business applications.",
            "B": "Determine the maximum acceptable downtime and recovery priorities for critical business functions.",
            "C": "Document the chain of custody for digital evidence.",
            "D": "Establish acceptable use policies for employees.",
        },
        "answer": "B",
        "explanation": "A BIA identifies which business functions are critical and determines the Maximum Tolerable Downtime (MTD), Recovery Time Objective (RTO), and Recovery Point Objective (RPO).",
    },
    {
        "id": 9,
        "domain": "D1",
        "question": "Defense-in-depth is a security strategy that:",
        "choices": {
            "A": "Relies on a single, highly sophisticated security control to protect the perimeter.",
            "B": "Prioritizes detection over prevention in all scenarios.",
            "C": "Implements multiple, overlapping layers of security controls so that no single failure leads to compromise.",
            "D": "Focuses security resources exclusively on the most critical assets.",
        },
        "answer": "C",
        "explanation": "Defense-in-depth (DiD) ensures that even if one control fails, other layers still protect the system. It's a foundational principle in NIST, DoD, and most security frameworks.",
    },
    {
        "id": 10,
        "domain": "D1",
        "question": "Which concept ensures that no single person can complete a critical or sensitive task alone, requiring two or more people to act together?",
        "choices": {
            "A": "Least privilege",
            "B": "Separation of duties",
            "C": "Job rotation",
            "D": "Need-to-know",
        },
        "answer": "B",
        "explanation": "Separation of duties (NIST AC-5) prevents fraud and error by requiring multiple people to complete sensitive transactions. Job rotation is a related but distinct control.",
    },

    # ── Domain 2: Asset Security ───────────────────────────────────────────────
    {
        "id": 11,
        "domain": "D2",
        "question": "In U.S. government data classification, which label sits immediately below 'Secret'?",
        "choices": {
            "A": "Top Secret",
            "B": "Sensitive But Unclassified (SBU)",
            "C": "Confidential",
            "D": "For Official Use Only (FOUO)",
        },
        "answer": "C",
        "explanation": "U.S. government classification levels from highest to lowest: Top Secret → Secret → Confidential. SBU/FOUO/CUI are unclassified categories, not formal classification levels.",
    },
    {
        "id": 12,
        "domain": "D2",
        "question": "Which of the following best describes 'data at rest'?",
        "choices": {
            "A": "Data currently being processed in CPU registers.",
            "B": "Data transmitted between two systems over the network.",
            "C": "Data stored on a disk, SSD, tape, or other persistent storage medium.",
            "D": "Data that has been archived and is no longer needed.",
        },
        "answer": "C",
        "explanation": "Data at rest refers to inactive data stored on media. Data in transit moves over a network. Data in use is being actively processed. All three states require protection.",
    },
    {
        "id": 13,
        "domain": "D2",
        "question": "Who bears ultimate accountability for classifying and protecting a data asset within an organization?",
        "choices": {
            "A": "Data custodian",
            "B": "Data processor",
            "C": "Data owner",
            "D": "Security administrator",
        },
        "answer": "C",
        "explanation": "The data owner (often a business unit manager) is responsible for classifying data and defining protection requirements. The custodian implements those requirements; the processor handles data on behalf of the controller/owner.",
    },
    {
        "id": 14,
        "domain": "D2",
        "question": "Under GDPR, which right allows individuals to request that their personal data be deleted?",
        "choices": {
            "A": "Right to portability",
            "B": "Right to access",
            "C": "Right to erasure",
            "D": "Right to rectification",
        },
        "answer": "C",
        "explanation": "GDPR Article 17 grants the 'right to erasure' (also called the right to be forgotten), allowing individuals to request deletion of personal data under certain conditions.",
    },

    # ── Domain 3: Security Architecture & Engineering ─────────────────────────
    {
        "id": 15,
        "domain": "D3",
        "question": "Which type of encryption algorithm uses the same key for both encryption and decryption?",
        "choices": {
            "A": "Asymmetric",
            "B": "Hashing",
            "C": "Symmetric",
            "D": "Elliptic Curve",
        },
        "answer": "C",
        "explanation": "Symmetric encryption (e.g., AES, 3DES) uses one shared secret key. Asymmetric encryption (e.g., RSA) uses a public/private key pair.",
    },
    {
        "id": 16,
        "domain": "D3",
        "question": "Kerckhoff's principle states that a cryptosystem should be secure even if:",
        "choices": {
            "A": "The key is publicly known.",
            "B": "Everything about the system, except the key, is public knowledge.",
            "C": "The algorithm uses only open-source components.",
            "D": "The plaintext is structured and predictable.",
        },
        "answer": "B",
        "explanation": "Kerckhoff's principle holds that security should depend only on secrecy of the key, not on secrecy of the algorithm. This is the basis for public standards like AES.",
    },
    {
        "id": 17,
        "domain": "D3",
        "question": "The Bell-LaPadula model's 'simple security property' (no read up) and *-property (no write down) are designed to protect which CIA attribute?",
        "choices": {
            "A": "Integrity",
            "B": "Availability",
            "C": "Confidentiality",
            "D": "Accountability",
        },
        "answer": "C",
        "explanation": "Bell-LaPadula enforces confidentiality: subjects cannot read data at a higher classification level (no read up) and cannot write data to a lower level (no write down), preventing information leakage.",
    },
    {
        "id": 18,
        "domain": "D3",
        "question": "A Trusted Platform Module (TPM) chip is primarily used to:",
        "choices": {
            "A": "Accelerate HTTPS encryption in network appliances.",
            "B": "Provide hardware-based storage of cryptographic keys and attest to platform integrity.",
            "C": "Detect and block malware in real time.",
            "D": "Manage VPN tunnels for remote access.",
        },
        "answer": "B",
        "explanation": "A TPM stores keys, certificates, and measurements in tamper-resistant hardware. It enables secure boot by attesting that the platform hasn't been modified since last measurement.",
    },

    # ── Domain 4: Communication & Network Security ────────────────────────────
    {
        "id": 19,
        "domain": "D4",
        "question": "Which TLS cipher suite feature provides Perfect Forward Secrecy (PFS) by using a fresh key pair for each session?",
        "choices": {
            "A": "RSA key exchange",
            "B": "Ephemeral Diffie-Hellman (DHE or ECDHE)",
            "C": "SHA-256 message authentication",
            "D": "AES-256-GCM bulk encryption",
        },
        "answer": "B",
        "explanation": "PFS is achieved via ephemeral DH key exchange (DHE/ECDHE). Even if the server's long-term private key is later compromised, past session keys cannot be derived, protecting past traffic.",
    },
    {
        "id": 20,
        "domain": "D4",
        "question": "In IPSec, which mode encapsulates the entire original IP packet inside a new IP packet, making it suitable for site-to-site VPNs?",
        "choices": {
            "A": "Transport mode",
            "B": "Aggressive mode",
            "C": "Tunnel mode",
            "D": "Main mode",
        },
        "answer": "C",
        "explanation": "Tunnel mode wraps the entire original packet (header + payload) in a new IP packet, hiding the original source and destination. Transport mode only protects the payload, preserving the original IP header.",
    },
    {
        "id": 21,
        "domain": "D4",
        "question": "A Next-Generation Firewall (NGFW) differs from a traditional stateful firewall primarily because an NGFW can:",
        "choices": {
            "A": "Filter traffic only at Layer 2 (MAC address).",
            "B": "Inspect application-layer content and apply identity-aware policies.",
            "C": "Route traffic without maintaining a connection state table.",
            "D": "Terminate SSL/TLS sessions for backend servers.",
        },
        "answer": "B",
        "explanation": "NGFWs add deep packet inspection (DPI), application identification, user identity awareness, and IPS capabilities on top of traditional stateful packet filtering.",
    },
    {
        "id": 22,
        "domain": "D4",
        "question": "Zero Trust Architecture (ZTA) is based on which core principle?",
        "choices": {
            "A": "Internal network traffic is inherently trusted; only external traffic requires verification.",
            "B": "Never trust, always verify — no implicit trust is granted based on network location.",
            "C": "Physical perimeter security is sufficient to protect internal resources.",
            "D": "Users on corporate VPN bypass multi-factor authentication requirements.",
        },
        "answer": "B",
        "explanation": "ZTA assumes breach and verifies every access request explicitly, regardless of network location. It relies on identity, device health, and context rather than perimeter-based trust.",
    },
    {
        "id": 23,
        "domain": "D4",
        "question": "VLAN hopping via double tagging works because:",
        "choices": {
            "A": "802.1Q tags are encrypted and can be forged.",
            "B": "An attacker on the native VLAN can craft frames with two 802.1Q tags, causing the switch to forward traffic to a target VLAN.",
            "C": "VLAN IDs above 4094 are reserved and bypass access control lists.",
            "D": "Trunk ports strip all VLAN tags before forwarding frames.",
        },
        "answer": "B",
        "explanation": "Double-tagging exploits the fact that switches on a native/untagged VLAN strip the outer tag and forward the inner-tagged frame onto the trunk. Mitigation: never use the native VLAN for user traffic.",
    },

    # ── Domain 5: Identity & Access Management ────────────────────────────────
    {
        "id": 24,
        "domain": "D5",
        "question": "Authentication and authorization are different concepts. Which statement is correct?",
        "choices": {
            "A": "Authentication determines what you can access; authorization verifies who you are.",
            "B": "Authentication verifies identity; authorization determines what actions are permitted.",
            "C": "They are the same concept expressed differently in various frameworks.",
            "D": "Authorization always occurs before authentication in secure systems.",
        },
        "answer": "B",
        "explanation": "AuthN (authentication) = proving identity. AuthZ (authorization) = what you're allowed to do after identity is confirmed. Authentication must precede authorization.",
    },
    {
        "id": 25,
        "domain": "D5",
        "question": "Which access control model grants permissions based on a user's job function within an organization?",
        "choices": {
            "A": "Discretionary Access Control (DAC)",
            "B": "Mandatory Access Control (MAC)",
            "C": "Role-Based Access Control (RBAC)",
            "D": "Rule-Based Access Control",
        },
        "answer": "C",
        "explanation": "RBAC assigns permissions to roles, and users are assigned to roles based on job function. This is the most common enterprise access control model.",
    },
    {
        "id": 26,
        "domain": "D5",
        "question": "In Kerberos authentication, what does the Key Distribution Center (KDC) issue to a client after successful initial authentication?",
        "choices": {
            "A": "A session cookie",
            "B": "A Ticket Granting Ticket (TGT)",
            "C": "A service ticket for the requested resource",
            "D": "A one-time password (OTP)",
        },
        "answer": "B",
        "explanation": "After verifying credentials, the KDC's Authentication Service (AS) issues a TGT. The client uses the TGT to request service tickets from the Ticket Granting Service (TGS) without re-entering credentials.",
    },
    {
        "id": 27,
        "domain": "D5",
        "question": "OAuth 2.0 is primarily designed for:",
        "choices": {
            "A": "Federated identity and single sign-on across enterprise domains.",
            "B": "Delegated authorization — allowing a third-party app to access resources on a user's behalf.",
            "C": "Mutual TLS certificate-based authentication between services.",
            "D": "Replacing passwords with hardware security keys.",
        },
        "answer": "B",
        "explanation": "OAuth 2.0 is an authorization framework allowing apps to obtain limited access to user accounts without sharing passwords. SAML 2.0 is better suited for enterprise SSO/federated identity. OpenID Connect (OIDC) adds authentication on top of OAuth.",
    },
    {
        "id": 28,
        "domain": "D5",
        "question": "A fingerprint scan used for authentication is which type of MFA factor?",
        "choices": {
            "A": "Something you know",
            "B": "Something you have",
            "C": "Something you are",
            "D": "Somewhere you are",
        },
        "answer": "C",
        "explanation": "Biometrics (fingerprint, retina, face) are 'something you are' (inherence factor). 'Something you know' = password/PIN. 'Something you have' = token/smart card/phone. 'Somewhere you are' = geolocation.",
    },

    # ── Domain 6: Security Assessment & Testing ───────────────────────────────
    {
        "id": 29,
        "domain": "D6",
        "question": "Under NIST 800-53r5, continuous monitoring of security controls is addressed by which control family?",
        "choices": {
            "A": "CA — Assessment, Authorization, and Monitoring",
            "B": "RA — Risk Assessment",
            "C": "SI — System and Information Integrity",
            "D": "PM — Program Management",
        },
        "answer": "A",
        "explanation": "CA-7 (Continuous Monitoring) is in the CA family. In Rev 5, the CA family was renamed to 'Assessment, Authorization, and Monitoring' to better reflect its scope.",
    },
    {
        "id": 30,
        "domain": "D6",
        "question": "What distinguishes a vulnerability assessment from a penetration test?",
        "choices": {
            "A": "A penetration test is passive; a vulnerability assessment actively exploits weaknesses.",
            "B": "A vulnerability assessment identifies and ranks weaknesses; a penetration test actively attempts to exploit them to demonstrate impact.",
            "C": "They are the same activity described by different vendors.",
            "D": "Vulnerability assessments are only applicable to web applications.",
        },
        "answer": "B",
        "explanation": "Vulnerability assessments (scanning + analysis) identify what's wrong. Penetration tests go further by attempting exploitation to prove real-world impact and measure actual risk.",
    },
    {
        "id": 31,
        "domain": "D6",
        "question": "A security analyst sees an IDS alert for suspicious traffic, but after investigation finds it was legitimate network activity. This is called a:",
        "choices": {
            "A": "False negative",
            "B": "True positive",
            "C": "True negative",
            "D": "False positive",
        },
        "answer": "D",
        "explanation": "A false positive is an alert triggered by benign activity. A false negative is a real attack that goes undetected — the more dangerous failure mode.",
    },
    {
        "id": 32,
        "domain": "D6",
        "question": "A white-box penetration test provides the tester with:",
        "choices": {
            "A": "No information — the tester simulates an external attacker.",
            "B": "Only the organization name and IP ranges.",
            "C": "Full knowledge: source code, architecture diagrams, credentials, and network details.",
            "D": "Partial knowledge such as IP ranges but no access to source code.",
        },
        "answer": "C",
        "explanation": "White-box (crystal-box) testing gives full access to internals. Black-box simulates an uninformed attacker. Gray-box provides limited knowledge. White-box is most thorough and efficient.",
    },
    {
        "id": 33,
        "domain": "D6",
        "question": "CVSS v3 'Attack Vector' (AV) metric describes:",
        "choices": {
            "A": "Whether authentication is required to exploit the vulnerability.",
            "B": "The context in which exploitation of the vulnerability is possible (Network, Adjacent, Local, Physical).",
            "C": "The number of systems affected by a single exploit.",
            "D": "Whether a changed scope affects components beyond the vulnerable one.",
        },
        "answer": "B",
        "explanation": "AV indicates how remotely accessible the vulnerability is. Network (N) = exploitable remotely; Adjacent (A) = requires adjacent network access; Local (L) = requires local access; Physical (P) = requires physical access.",
    },
    {
        "id": 34,
        "domain": "D6",
        "question": "What is the primary difference between SAST and DAST?",
        "choices": {
            "A": "SAST tests production systems; DAST tests development systems.",
            "B": "SAST analyzes source code without executing it; DAST tests the running application from the outside.",
            "C": "DAST requires source code access; SAST tests the compiled binary.",
            "D": "They are equivalent; the names are vendor-specific branding.",
        },
        "answer": "B",
        "explanation": "Static Application Security Testing (SAST) is white-box analysis of code. Dynamic Application Security Testing (DAST) is black-box testing of a running application. Both are part of a complete AppSec program.",
    },

    # ── Domain 7: Security Operations ─────────────────────────────────────────
    {
        "id": 35,
        "domain": "D7",
        "question": "Under NIST 800-53r5, which control family is abbreviated 'IR'?",
        "choices": {
            "A": "Identity and Risk",
            "B": "Infrastructure Resilience",
            "C": "Incident Response",
            "D": "Integrity Requirements",
        },
        "answer": "C",
        "explanation": "IR = Incident Response. NIST 800-53r5 has 20 control families. Other common ones: AC (Access Control), AU (Audit), SC (System and Communications Protection).",
    },
    {
        "id": 36,
        "domain": "D7",
        "question": "According to NIST SP 800-61, what is the correct sequence of incident response phases?",
        "choices": {
            "A": "Identification → Containment → Eradication → Recovery → Lessons Learned",
            "B": "Preparation → Detection & Analysis → Containment, Eradication & Recovery → Post-Incident Activity",
            "C": "Detection → Triage → Escalation → Resolution → Closure",
            "D": "Prevention → Detection → Reaction → Reporting → Improvement",
        },
        "answer": "B",
        "explanation": "NIST 800-61 defines four phases: (1) Preparation, (2) Detection & Analysis, (3) Containment, Eradication & Recovery, (4) Post-Incident Activity. The SANS model (Preparation, Identification, Containment, Eradication, Recovery, Lessons Learned) is also commonly used.",
    },
    {
        "id": 37,
        "domain": "D7",
        "question": "In digital forensics, 'order of volatility' means:",
        "choices": {
            "A": "Prioritizing the collection of evidence from most volatile (most likely to change or disappear) to least volatile.",
            "B": "Ranking evidence by its legal admissibility.",
            "C": "Documenting the chain of custody from collection to courtroom.",
            "D": "Classifying evidence by its relevance to the investigation.",
        },
        "answer": "A",
        "explanation": "RFC 3227 establishes the order: CPU registers/cache → RAM → swap/paging → running processes → disk → logs/backups. Volatile data (RAM) disappears when power is lost and must be collected first.",
    },
    {
        "id": 38,
        "domain": "D7",
        "question": "A locked server room door is an example of which category of security control?",
        "choices": {
            "A": "Technical",
            "B": "Administrative",
            "C": "Physical",
            "D": "Operational",
        },
        "answer": "C",
        "explanation": "Physical controls protect facilities and hardware. Technical controls use technology (firewalls, encryption). Administrative controls are policies and procedures.",
    },
    {
        "id": 39,
        "domain": "D7",
        "question": "A SOAR platform differs from a SIEM primarily because SOAR:",
        "choices": {
            "A": "Collects and correlates log data from multiple sources.",
            "B": "Automates response workflows and orchestrates actions across security tools.",
            "C": "Performs vulnerability scanning on network endpoints.",
            "D": "Provides long-term storage for audit logs.",
        },
        "answer": "B",
        "explanation": "SIEM = Security Information and Event Management (collect, correlate, alert). SOAR = Security Orchestration, Automation and Response (automate response playbooks, integrate tools, reduce analyst toil).",
    },
    {
        "id": 40,
        "domain": "D7",
        "question": "An organization stores plaintext user passwords in its database. A developer argues this is fine because the database is 'protected by the firewall.' This is a failure of:",
        "choices": {
            "A": "Defense-in-depth — sensitive data should be protected at the data layer regardless of perimeter controls.",
            "B": "Perimeter security — the firewall needs to be upgraded.",
            "C": "Least privilege — users shouldn't be able to set their own passwords.",
            "D": "Availability — plaintext is faster to retrieve, improving uptime.",
        },
        "answer": "A",
        "explanation": "Passwords must be hashed (e.g., bcrypt, Argon2) at rest. Perimeter controls are one layer — not a substitute for protecting data at the storage layer. This also violates SC-28 (Protection of Information at Rest).",
    },

    # ── Domain 8: Software Development Security ───────────────────────────────
    {
        "id": 41,
        "domain": "D8",
        "question": "Under the OWASP Top 10 (2021), which category covers SQL injection and other injection flaws?",
        "choices": {
            "A": "A01: Broken Access Control",
            "B": "A02: Cryptographic Failures",
            "C": "A03: Injection",
            "D": "A07: Identification and Authentication Failures",
        },
        "answer": "C",
        "explanation": "A03:2021 Injection covers SQL, NoSQL, OS, and LDAP injection. SQL injection occurs when untrusted data is sent to an interpreter as part of a command or query. Prevention: parameterized queries, stored procedures, input validation.",
    },
    {
        "id": 42,
        "domain": "D8",
        "question": "In STRIDE threat modeling, what does 'T' (Tampering) represent?",
        "choices": {
            "A": "Unauthorized reading of data.",
            "B": "Maliciously modifying data or code.",
            "C": "Claiming an action was not performed.",
            "D": "Overloading a system to deny service.",
        },
        "answer": "B",
        "explanation": "STRIDE: Spoofing (identity), Tampering (data modification), Repudiation (denying actions), Information Disclosure (data exposure), Denial of Service, Elevation of Privilege. Tampering maps to integrity violations.",
    },
    {
        "id": 43,
        "domain": "D8",
        "question": "Security requirements should be defined during which phase of the Secure Software Development Lifecycle (SSDLC)?",
        "choices": {
            "A": "Testing phase only.",
            "B": "Deployment phase so requirements reflect the production environment.",
            "C": "Requirements/design phase — before coding begins.",
            "D": "Maintenance phase once the system is in production.",
        },
        "answer": "C",
        "explanation": "Security must be 'built in, not bolted on.' Defining requirements during the early phases (requirements and design) is far cheaper than retrofitting security after development. This is the core principle of SSDLC.",
    },
    {
        "id": 44,
        "domain": "D8",
        "question": "A TOCTOU (Time-of-Check to Time-of-Use) vulnerability is an example of:",
        "choices": {
            "A": "An integer overflow in memory management.",
            "B": "A race condition where the state of a resource changes between when it is checked and when it is used.",
            "C": "A cross-site scripting vulnerability in web forms.",
            "D": "A buffer overflow caused by improper bounds checking.",
        },
        "answer": "B",
        "explanation": "TOCTOU is a class of race condition. An attacker manipulates a resource (e.g., a file) between the security check and the privileged operation. Mitigation: atomic operations, locks, re-validation at point of use.",
    },
    {
        "id": 45,
        "domain": "D8",
        "question": "Improper input validation is the root cause of which class of attacks?",
        "choices": {
            "A": "Denial of Service only.",
            "B": "Injection attacks (SQL, command, LDAP), buffer overflows, and XSS.",
            "C": "Man-in-the-middle attacks on TLS sessions.",
            "D": "Brute-force password attacks.",
        },
        "answer": "B",
        "explanation": "Failing to validate and sanitize input enables injection flaws, buffer overflows, cross-site scripting, path traversal, and more. Input validation is one of the most impactful single mitigations in secure coding.",
    },

    # ── Additional cross-domain questions (IDs 46–50) ─────────────────────────
    {
        "id": 46,
        "domain": "D1",
        "question": "Quantitative risk analysis differs from qualitative risk analysis in that quantitative analysis:",
        "choices": {
            "A": "Uses subjective ratings such as High/Medium/Low.",
            "B": "Assigns numerical monetary values to assets, threats, and likelihoods.",
            "C": "Relies solely on expert opinion without data.",
            "D": "Is faster and requires less information to complete.",
        },
        "answer": "B",
        "explanation": "Quantitative analysis uses values like ALE (Annual Loss Expectancy = SLE × ARO). Qualitative uses ratings. Quantitative is more precise but requires more data; qualitative is faster but less objective.",
    },
    {
        "id": 47,
        "domain": "D3",
        "question": "A Hardware Security Module (HSM) provides what primary security advantage over software-based key storage?",
        "choices": {
            "A": "Faster network throughput for encrypted connections.",
            "B": "Tamper-resistant hardware that prevents key extraction even with physical access.",
            "C": "Automatic certificate renewal without administrator intervention.",
            "D": "Compression of encrypted data to reduce storage costs.",
        },
        "answer": "B",
        "explanation": "HSMs are purpose-built hardware that physically destroy or zeroize keys if tampered with. Unlike software keystores, private keys never leave the HSM in plaintext, protecting against OS compromise.",
    },
    {
        "id": 48,
        "domain": "D5",
        "question": "Attribute-Based Access Control (ABAC) makes authorization decisions based on:",
        "choices": {
            "A": "The subject's role within the organization.",
            "B": "The owner of the resource granting access at their discretion.",
            "C": "A combination of subject attributes, object attributes, and environmental conditions.",
            "D": "Security labels and clearance levels assigned by an authority.",
        },
        "answer": "C",
        "explanation": "ABAC evaluates attributes (user department, device compliance, time of day, resource sensitivity) to make fine-grained decisions. RBAC uses roles; DAC uses owner discretion; MAC uses labels/clearances.",
    },
    {
        "id": 49,
        "domain": "D6",
        "question": "In penetration testing, which phase involves using discovered vulnerabilities to gain unauthorized access to systems?",
        "choices": {
            "A": "Reconnaissance",
            "B": "Scanning and enumeration",
            "C": "Exploitation",
            "D": "Reporting",
        },
        "answer": "C",
        "explanation": "Pen test phases: Reconnaissance (passive/active info gathering) → Scanning (enumeration, vulnerability identification) → Exploitation (gaining access) → Post-exploitation (persistence, lateral movement) → Reporting.",
    },
    {
        "id": 50,
        "domain": "D2",
        "question": "Tokenization replaces sensitive data (e.g., a credit card number) with a non-sensitive placeholder. It differs from encryption in that:",
        "choices": {
            "A": "Tokenization is reversible using a key; encryption is one-way.",
            "B": "The token has no mathematical relationship to the original data; there is no key to 'crack.'",
            "C": "Tokenization is only applicable to data in transit, not data at rest.",
            "D": "Encrypted data can be processed without decryption; tokenized data cannot.",
        },
        "answer": "B",
        "explanation": "Tokens are random values stored in a vault that maps them back to originals. Unlike encryption, there is no algorithm or key that transforms the token to the original — the vault is the only lookup mechanism, reducing mathematical attack surface.",
    },
]


def grade_quiz(responses: Dict[int, str]) -> dict:
    """
    Grade a completed full assessment quiz (all questions).

    Args:
        responses: {question_id: selected_answer_letter}

    Returns:
        {score, total, percentage, results: [...]}
    """
    score   = 0
    results = []

    for q in QUESTIONS:
        selected = responses.get(q["id"])
        correct  = q["answer"]
        ok       = (selected == correct)
        if ok:
            score += 1
        results.append({
            "id":          q["id"],
            "question":    q["question"],
            "choices":     q["choices"],
            "selected":    selected,
            "correct":     correct,
            "is_correct":  ok,
            "explanation": q["explanation"],
        })

    return {
        "score":      score,
        "total":      len(QUESTIONS),
        "percentage": round(score / len(QUESTIONS) * 100, 1),
        "results":    results,
    }


def grade_daily_quiz(responses: Dict[int, str], shown_questions: List[Dict]) -> dict:
    """
    Grade a daily quiz attempt against only the questions that were shown.

    Args:
        responses:        {question_id: selected_answer_letter}
        shown_questions:  list of question dicts that were shown to the user

    Returns:
        {score, total, percentage, results: [...]}
    """
    score   = 0
    results = []

    for q in shown_questions:
        selected = responses.get(q["id"])
        correct  = q["answer"]
        ok       = (selected == correct)
        if ok:
            score += 1
        results.append({
            "id":          q["id"],
            "question":    q["question"],
            "choices":     q["choices"],
            "selected":    selected,
            "correct":     correct,
            "is_correct":  ok,
            "explanation": q["explanation"],
        })

    total = len(shown_questions)
    return {
        "score":      score,
        "total":      total,
        "percentage": round(score / total * 100, 1) if total else 0.0,
        "results":    results,
    }
