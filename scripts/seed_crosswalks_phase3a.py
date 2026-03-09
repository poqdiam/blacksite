"""
seed_crosswalks_phase3a.py — Phase 3a (8 frameworks)
Functional-equivalence crosswalk: if a control addresses the same security
objective as a NIST 800-53r5 control, it maps — regardless of exact wording.
confidence="high" = direct/official; confidence="medium" = functional equivalence

Frameworks: sox, ccpa, csaccm, glba, ffiec, swiftcsp, pipeda, lgpd

Run: cd /home/graycat/projects/blacksite && .venv/bin/python3 scripts/seed_crosswalks_phase3a.py
"""
import sqlite3, uuid
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "blacksite.db"

FRAMEWORKS = [
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "sox-itgc-2002")),
     "name": "SOX ITGC (Sarbanes-Oxley)", "short_name": "sox",
     "version": "2002/PCAOB", "category": "regulatory", "published_by": "SEC/PCAOB",
     "description": "IT General Controls supporting SOX Section 302/404 internal controls over "
                    "financial reporting. Covers change management, logical access, computer "
                    "operations, and system development.",
     "source_url": "https://pcaobus.org/Standards/Auditing"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "ccpa-cpra-2023")),
     "name": "CCPA/CPRA", "short_name": "ccpa",
     "version": "2023 (CPRA)", "category": "regulatory", "published_by": "California OAG/CPPA",
     "description": "California Consumer Privacy Act as amended by the California Privacy Rights "
                    "Act. Grants consumers rights over personal information and imposes security "
                    "and privacy obligations on covered businesses.",
     "source_url": "https://cppa.ca.gov/regulations/"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "csa-ccm-v4")),
     "name": "CSA Cloud Controls Matrix v4", "short_name": "csaccm",
     "version": "v4.0.10", "category": "industry", "published_by": "CSA",
     "description": "Cloud Security Alliance Cloud Controls Matrix. 197 controls across 17 domains "
                    "for cloud service providers and customers. Basis for CSA STAR certification.",
     "source_url": "https://cloudsecurityalliance.org/research/cloud-controls-matrix/"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "glba-safeguards-2023")),
     "name": "GLBA Safeguards Rule (2023)", "short_name": "glba",
     "version": "16 CFR Part 314 (2023)", "category": "regulatory", "published_by": "FTC",
     "description": "Gramm-Leach-Bliley Act Safeguards Rule as updated in 2023. Requires financial "
                    "institutions to implement a comprehensive information security program with "
                    "specific technical safeguards.",
     "source_url": "https://www.ftc.gov/business-guidance/resources/ftc-safeguards-rule-what-your-business-needs-know"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "ffiec-cat-2015")),
     "name": "FFIEC Cybersecurity Assessment Tool", "short_name": "ffiec",
     "version": "2015", "category": "regulatory", "published_by": "FFIEC",
     "description": "FFIEC CAT helps financial institutions identify cybersecurity risks and determine "
                    "preparedness. Five domains, five maturity levels from Baseline to Innovative.",
     "source_url": "https://www.ffiec.gov/cyberassessmenttool.htm"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "swift-csp-2024")),
     "name": "SWIFT Customer Security Programme (CSP)", "short_name": "swiftcsp",
     "version": "2024", "category": "industry", "published_by": "SWIFT",
     "description": "SWIFT CSP mandatory and advisory security controls for all institutions on the "
                    "SWIFT network. Annual self-attestation required. 32 mandatory + 12 advisory controls.",
     "source_url": "https://www.swift.com/myswift/customer-security-programme-csp"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "pipeda-canada-2000")),
     "name": "PIPEDA (Canada)", "short_name": "pipeda",
     "version": "2000 (amended 2015)", "category": "regulatory", "published_by": "OPC Canada",
     "description": "Personal Information Protection and Electronic Documents Act. Canada's federal "
                    "private-sector privacy law. Ten fair information principles govern collection, "
                    "use, and disclosure of personal information.",
     "source_url": "https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "lgpd-brazil-2020")),
     "name": "LGPD (Brazil)", "short_name": "lgpd",
     "version": "Lei 13.709/2018", "category": "regulatory", "published_by": "ANPD",
     "description": "Lei Geral de Proteção de Dados — Brazil's general data protection law. "
                    "Modeled on GDPR. Governs processing of personal data of individuals in Brazil.",
     "source_url": "https://www.gov.br/cidadania/pt-br/acesso-a-informacao/lgpd"},
]

SOURCE_MAP = {k: "community" for k in ["sox","ccpa","csaccm","glba","ffiec","swiftcsp","pipeda","lgpd"]}

# ── SOX ITGC ─────────────────────────────────────────────────────────────────
# Organized around the four ITGC domains auditors test under PCAOB AS 2201
SOX_CONTROLS = [
    # Change Management
    ("SOX-CM-1","Change Management","Formal change management policy and procedures govern all system changes",
     None,["cm-1","cm-3","sa-10"]),
    ("SOX-CM-2","Change Management","Changes are authorized before implementation (change request and approval)",
     None,["cm-3","cm-5","sa-10"]),
    ("SOX-CM-3","Change Management","Changes are tested in a separate environment before production deployment",
     None,["cm-3","cm-4","sa-11","sa-15"]),
    ("SOX-CM-4","Change Management","Emergency changes follow an expedited but controlled process",
     None,["cm-3","ir-4","cm-5"]),
    ("SOX-CM-5","Change Management","Program-to-production migrations are controlled and restricted",
     None,["cm-5","cm-3","sa-10"]),
    ("SOX-CM-6","Change Management","Changes are logged and records are retained",
     None,["au-3","au-12","cm-3","si-12"]),
    ("SOX-CM-7","Change Management","Developers do not have access to production systems",
     None,["ac-5","ac-6","cm-5"]),
    # Logical Access
    ("SOX-LA-1","Logical Access","Access provisioning follows formal request and approval workflow",
     None,["ac-2","ia-2","ps-4"]),
    ("SOX-LA-2","Logical Access","User access is reviewed periodically and recertified",
     None,["ac-2","ca-7","ia-4"]),
    ("SOX-LA-3","Logical Access","Access is promptly revoked upon termination or transfer",
     None,["ac-2","ps-4","ps-5","ia-4"]),
    ("SOX-LA-4","Logical Access","Privileged/admin access is restricted and separately managed",
     None,["ac-2","ac-6","ia-2"]),
    ("SOX-LA-5","Logical Access","Segregation of duties is enforced for financial system functions",
     None,["ac-5","ac-6","ac-3"]),
    ("SOX-LA-6","Logical Access","Password/authentication controls meet minimum security standards",
     None,["ia-5","ia-2","ac-7"]),
    ("SOX-LA-7","Logical Access","Generic/shared accounts are prohibited or tightly controlled",
     None,["ia-2","ia-4","ac-2"]),
    ("SOX-LA-8","Logical Access","Remote access requires MFA and is logged",
     None,["ia-2","ac-17","au-2"]),
    # Computer Operations
    ("SOX-CO-1","Computer Operations","Job scheduling and batch processing are monitored for failures",
     None,["si-4","au-6","au-5"]),
    ("SOX-CO-2","Computer Operations","Backup and recovery procedures are defined and tested",
     None,["cp-9","cp-10","cp-4"]),
    ("SOX-CO-3","Computer Operations","System availability is monitored and incidents are escalated",
     None,["si-4","ir-4","au-6"]),
    ("SOX-CO-4","Computer Operations","Security events and logs are reviewed on a regular basis",
     None,["au-6","si-4","ca-7"]),
    ("SOX-CO-5","Computer Operations","Data center physical access is restricted to authorized personnel",
     None,["pe-2","pe-3","pe-6"]),
    ("SOX-CO-6","Computer Operations","Disaster recovery plan exists and is tested annually",
     None,["cp-2","cp-4","cp-10"]),
    # System Development
    ("SOX-SD-1","System Development","SDLC methodology requires security requirements in new systems",
     None,["sa-3","sa-4","sa-8"]),
    ("SOX-SD-2","System Development","Systems are tested against requirements before go-live",
     None,["sa-11","ca-2","cm-4"]),
    ("SOX-SD-3","System Development","User acceptance testing (UAT) is completed and documented",
     None,["sa-11","ca-2","sa-3"]),
    ("SOX-SD-4","System Development","Security review is conducted for new and modified applications",
     None,["sa-11","ra-3","ca-2"]),
]

# ── CCPA/CPRA ────────────────────────────────────────────────────────────────
CCPA_CONTROLS = [
    ("1798.100","Consumer Rights","Right to know: consumers can request what personal information is collected",
     None,["pm-20","pm-25","pt-2","ac-3"]),
    ("1798.105","Consumer Rights","Right to delete: consumers can request deletion of personal information",
     None,["mp-6","si-12","pm-25","pt-3"]),
    ("1798.106","Consumer Rights","Right to correct inaccurate personal information",
     None,["pm-25","si-10","pt-2"]),
    ("1798.110","Consumer Rights","Right to know specific pieces of personal information collected",
     None,["pm-20","pm-25","pt-2"]),
    ("1798.115","Consumer Rights","Right to know third parties who received personal information",
     None,["pm-20","pt-2","sa-9"]),
    ("1798.120","Consumer Rights","Right to opt-out of sale or sharing of personal information",
     None,["pm-25","pt-3","pm-20"]),
    ("1798.121","Consumer Rights","Right to limit use of sensitive personal information",
     None,["pm-25","pt-3","ac-3"]),
    ("1798.125","Consumer Rights","Right to non-discrimination for exercising privacy rights",
     None,["pm-20","pm-25"]),
    ("1798.130","Business Obligations","Respond to consumer requests within 45 days",
     None,["pm-20","pm-25","ir-6"]),
    ("1798.135","Business Obligations","Provide two or more designated methods for submitting requests",
     None,["pm-20","pt-2"]),
    ("1798.140","Definitions","Covered business thresholds and definitions of personal information",
     None,["pm-20","ra-2","pm-25"]),
    ("1798.145","Exemptions","Exemptions including employment context and B2B interactions",
     None,["pm-20","ra-2"]),
    ("1798.150","Security","Implement reasonable security to protect personal information",
     None,["sc-28","ac-3","ia-5","si-3","ra-3","pm-9"]),
    ("1798.150(b)","Security","Civil action for unauthorized access due to failure to maintain reasonable security",
     None,["ra-3","pm-9","ir-4","sc-28"]),
    ("CPRA-RegReq-1","Data Minimization","Collect only personal information reasonably necessary for disclosed purpose",
     None,["pm-25","si-12","pt-7","cm-7"]),
    ("CPRA-RegReq-2","Retention","Retain personal information only as long as necessary",
     None,["si-12","mp-6","mp-7","pm-25"]),
    ("CPRA-RegReq-3","Risk Assessment","Conduct risk assessments for high-risk processing activities",
     None,["ra-3","pm-9","pt-5","pl-8"]),
    ("CPRA-RegReq-4","Contractor Agreements","Ensure service providers and contractors comply via contract",
     None,["sa-9","sr-1","sr-3","sr-6"]),
    ("CPRA-RegReq-5","Sensitive PI","Additional protections for sensitive personal information",
     None,["sc-28","ac-3","pm-25","pt-7"]),
    ("CPRA-RegReq-6","Audit","Annual cybersecurity audit for businesses that pose significant risk",
     None,["ca-2","pm-14","ra-3"]),
]

# ── CSA Cloud Controls Matrix v4 ─────────────────────────────────────────────
CSACCM_CONTROLS = [
    # A&A — Audit & Assurance
    ("A&A-01","Audit & Assurance","Establish audit management program for cloud services",
     None,["ca-1","ca-2","pm-14","au-1"]),
    ("A&A-02","Audit & Assurance","Independent audits of cloud environments on defined schedule",
     None,["ca-2","ca-8","au-6"]),
    ("A&A-03","Audit & Assurance","Address audit findings and track remediation",
     None,["ca-5","pm-4","ca-2"]),
    # AIS — Application & Interface Security
    ("AIS-01","Application Security","Define and implement application security policies",
     None,["sa-1","sa-4","sa-8","sa-11"]),
    ("AIS-02","Application Security","Require automated application security testing",
     None,["sa-11","ca-8","ra-5"]),
    ("AIS-03","Application Security","Use automated scanning for open source vulnerabilities",
     None,["sa-11","ra-5","si-2","sr-4"]),
    ("AIS-04","Application Security","Validate application API security",
     None,["sa-11","si-10","sc-8","ac-4"]),
    ("AIS-05","Application Security","Segregate automated build and test environments",
     None,["sa-3","cm-4","sc-3","ac-5"]),
    ("AIS-06","Application Security","Establish secure software design and coding principles",
     None,["sa-8","sa-15","sa-11","cm-6"]),
    ("AIS-07","Application Security","Conduct code reviews for security vulnerabilities",
     None,["sa-11","ca-2"]),
    # BCR — Business Continuity & Resilience
    ("BCR-01","Business Continuity","Establish business continuity management program",
     None,["cp-1","cp-2","pm-11"]),
    ("BCR-02","Business Continuity","Conduct BIA to identify critical assets and recovery priorities",
     None,["cp-2","ra-3","sa-14","pm-11"]),
    ("BCR-03","Business Continuity","Define RTO and RPO for critical services",
     None,["cp-2","cp-7","cp-8","cp-9"]),
    ("BCR-04","Business Continuity","Test disaster recovery plans regularly",
     None,["cp-4","cp-10","ca-2"]),
    ("BCR-05","Business Continuity","Maintain geographically redundant backup sites",
     None,["cp-6","cp-7","cp-9"]),
    ("BCR-06","Business Continuity","Document and maintain recovery procedures",
     None,["cp-2","cp-10","ir-8"]),
    ("BCR-07","Business Continuity","Protect data backup copies from unauthorized access",
     None,["cp-9","mp-4","sc-28"]),
    ("BCR-08","Business Continuity","Test backup restoration procedures",
     None,["cp-4","cp-9","cp-10"]),
    ("BCR-09","Business Continuity","Maintain equipment and software inventory for recovery",
     None,["cm-8","cp-2","sa-14"]),
    ("BCR-10","Business Continuity","Provide customer notification of planned/unplanned outages",
     None,["cp-2","ir-6","pm-15"]),
    ("BCR-11","Business Continuity","Implement redundant network and power infrastructure",
     None,["cp-8","pe-11","sc-5"]),
    # CCC — Change Control & Configuration Management
    ("CCC-01","Change Management","Establish quality change management policy",
     None,["cm-1","cm-3","cm-9"]),
    ("CCC-02","Change Management","Require risk impact analysis before changes",
     None,["cm-4","ra-3","cm-3"]),
    ("CCC-03","Change Management","Restrict change implementation to authorized personnel",
     None,["cm-5","ac-5","ac-6"]),
    ("CCC-04","Change Management","Maintain system baseline configurations",
     None,["cm-2","cm-6","cm-8"]),
    ("CCC-05","Change Management","Log all configuration changes with attribution",
     None,["cm-3","au-3","au-12"]),
    ("CCC-06","Change Management","Deploy changes through automated pipeline with gates",
     None,["sa-10","sa-15","cm-3"]),
    ("CCC-07","Change Management","Conduct post-implementation reviews",
     None,["ca-7","cm-3","pm-4"]),
    # CEK — Cryptography, Encryption & Key Management
    ("CEK-01","Cryptography","Define cryptography, encryption and key management policy",
     None,["sc-1","sc-12","sc-13","ia-7"]),
    ("CEK-02","Cryptography","Encrypt data at rest for all sensitive/regulated data",
     None,["sc-28","mp-4","sc-12"]),
    ("CEK-03","Cryptography","Encrypt data in transit using strong protocols",
     None,["sc-8","sc-23","ia-7","sc-12"]),
    ("CEK-04","Cryptography","Manage cryptographic keys throughout their lifecycle",
     None,["sc-12","sc-28"]),
    ("CEK-05","Cryptography","Use FIPS-validated or equivalent cryptographic modules",
     None,["sc-13","ia-7","sc-12"]),
    ("CEK-06","Cryptography","Implement certificate management program",
     None,["sc-17","sc-12","ia-5"]),
    ("CEK-07","Cryptography","Rotate cryptographic keys on defined schedule",
     None,["sc-12","ia-5"]),
    ("CEK-08","Cryptography","Destroy cryptographic keys when systems are decommissioned",
     None,["sc-12","mp-6","ma-4"]),
    # DSP — Data Security & Privacy
    ("DSP-01","Data Security","Establish data security and privacy policy",
     None,["pm-1","mp-1","pt-1","ra-2"]),
    ("DSP-02","Data Security","Classify data according to sensitivity",
     None,["ra-2","mp-3","ac-16","pm-25"]),
    ("DSP-03","Data Security","Protect sensitive data throughout lifecycle",
     None,["mp-4","sc-28","ac-3","mp-6"]),
    ("DSP-04","Data Security","Define and enforce data retention and disposal schedules",
     None,["si-12","mp-6","mp-7"]),
    ("DSP-05","Data Security","Implement data loss prevention controls",
     None,["sc-28","ac-4","mp-5","si-12"]),
    ("DSP-06","Data Security","Inventory production data to understand location and classification",
     None,["cm-8","ra-2","pm-5","pm-25"]),
    ("DSP-07","Data Security","Implement privacy protections for personal information",
     None,["pt-1","pt-2","pm-20","pm-25"]),
    ("DSP-08","Data Security","Provide data subject access to their personal information",
     None,["pm-20","pm-25","pt-2","ac-3"]),
    ("DSP-09","Data Security","Implement data portability capabilities",
     None,["pm-20","pm-25","mp-5"]),
    ("DSP-10","Data Security","Anonymize or pseudonymize personal data where possible",
     None,["pt-7","sc-28","pm-25","si-12"]),
    # GRC — Governance, Risk & Compliance
    ("GRC-01","Governance","Establish information security governance structure",
     None,["pm-2","pm-10","ca-6","pm-1"]),
    ("GRC-02","Governance","Define, publish, and enforce information security policy",
     None,["pm-1","pl-4","at-2"]),
    ("GRC-03","Governance","Perform enterprise risk assessment annually",
     None,["ra-1","ra-3","pm-9"]),
    ("GRC-04","Governance","Establish risk treatment plan with POA&M",
     None,["ca-5","pm-4","ra-7"]),
    ("GRC-05","Governance","Maintain regulatory compliance monitoring program",
     None,["ca-2","ca-7","pm-14"]),
    ("GRC-06","Governance","Report risk posture to executive leadership",
     None,["pm-9","pm-6","ca-7"]),
    # HRS — Human Resources Security
    ("HRS-01","Human Resources","Implement pre-employment background screening",
     None,["ps-3","ps-2"]),
    ("HRS-02","Human Resources","Require security awareness training upon hire and annually",
     None,["at-2","at-3","pm-13"]),
    ("HRS-03","Human Resources","Define acceptable use policy and require acknowledgment",
     None,["pl-4","at-2","ps-6"]),
    ("HRS-04","Human Resources","Manage user access through HR lifecycle events",
     None,["ac-2","ps-4","ps-5","ia-4"]),
    ("HRS-05","Human Resources","Enforce sanctions for security policy violations",
     None,["ps-8","pl-4"]),
    ("HRS-06","Human Resources","Document and enforce termination procedures",
     None,["ps-4","ac-2","ia-4"]),
    ("HRS-07","Human Resources","Define role-based security responsibilities",
     None,["ps-2","at-3","pm-2"]),
    ("HRS-08","Human Resources","Provide role-specific security training",
     None,["at-3","pm-13","at-2"]),
    # IAM — Identity & Access Management
    ("IAM-01","Identity & Access","Establish identity and access management policy",
     None,["ac-1","ia-1","pm-1"]),
    ("IAM-02","Identity & Access","Enforce unique user IDs; prohibit shared accounts",
     None,["ia-2","ia-4","ac-2"]),
    ("IAM-03","Identity & Access","Require strong authentication for all users",
     None,["ia-2","ia-5","ac-7"]),
    ("IAM-04","Identity & Access","Require MFA for privileged access and remote access",
     None,["ia-2","ac-17","ac-6"]),
    ("IAM-05","Identity & Access","Implement least-privilege access model",
     None,["ac-6","ac-3","ac-5"]),
    ("IAM-06","Identity & Access","Conduct quarterly or more frequent access reviews",
     None,["ac-2","ca-7","ia-4"]),
    ("IAM-07","Identity & Access","Manage service account credentials and rotate regularly",
     None,["ia-5","ia-4","ac-2"]),
    ("IAM-08","Identity & Access","Implement privileged access management (PAM)",
     None,["ac-6","ia-2","ac-2"]),
    ("IAM-09","Identity & Access","Use automated provisioning/deprovisioning via SCIM or similar",
     None,["ac-2","ia-4","ps-4"]),
    ("IAM-10","Identity & Access","Federate identity via SSO for cloud services",
     None,["ia-2","ia-8","ia-4"]),
    ("IAM-11","Identity & Access","Implement session management controls",
     None,["ac-11","ac-12","sc-10"]),
    ("IAM-12","Identity & Access","Log all authentication and authorization events",
     None,["au-2","au-3","au-12"]),
    # IVS — Infrastructure & Virtualization Security
    ("IVS-01","Infrastructure Security","Restrict and monitor hypervisor management access",
     None,["ac-6","ac-2","si-4","au-6"]),
    ("IVS-02","Infrastructure Security","Isolate tenant environments in multi-tenant infrastructure",
     None,["sc-3","sc-7","ac-4"]),
    ("IVS-03","Infrastructure Security","Harden VM and container images per baseline standard",
     None,["cm-6","cm-2","sa-9","cm-7"]),
    ("IVS-04","Infrastructure Security","Implement network segmentation between cloud zones",
     None,["sc-7","ca-3","ac-4"]),
    ("IVS-05","Infrastructure Security","Implement IDS/IPS in cloud network",
     None,["si-4","sc-7","au-6"]),
    ("IVS-06","Infrastructure Security","Define and enforce VM lifecycle management",
     None,["cm-8","cm-3","sa-22"]),
    ("IVS-07","Infrastructure Security","Implement container security policy",
     None,["cm-6","cm-7","sc-3","sa-9"]),
    ("IVS-08","Infrastructure Security","Maintain asset inventory including cloud resources",
     None,["cm-8","pm-5"]),
    # LOG — Logging & Monitoring
    ("LOG-01","Logging","Define logging and monitoring policy",
     None,["au-1","au-2","pm-1"]),
    ("LOG-02","Logging","Generate audit logs for all security-relevant events",
     None,["au-2","au-3","au-12"]),
    ("LOG-03","Logging","Centralize logs in a SIEM or log management platform",
     None,["au-6","si-4","au-9"]),
    ("LOG-04","Logging","Protect log integrity from tampering",
     None,["au-9","si-7","au-3"]),
    ("LOG-05","Logging","Retain logs for defined period meeting regulatory requirements",
     None,["au-11","si-12"]),
    ("LOG-06","Logging","Alert on defined security events in real time",
     None,["si-4","au-6","ir-4","au-5"]),
    ("LOG-07","Logging","Correlate logs across systems to detect attacks",
     None,["au-6","si-4","ir-5"]),
    ("LOG-08","Logging","Review logs on defined schedule; automate where possible",
     None,["au-6","ca-7","si-4"]),
    ("LOG-09","Logging","Synchronize time sources across all systems",
     None,["au-8","sc-45"]),
    # SEF — Security Incident Management
    ("SEF-01","Incident Management","Define incident response policy and procedures",
     None,["ir-1","ir-8","pm-1"]),
    ("SEF-02","Incident Management","Classify and triage security events by severity",
     None,["ir-4","ir-5","au-6"]),
    ("SEF-03","Incident Management","Contain, eradicate, and recover from security incidents",
     None,["ir-4","cp-10","ir-8"]),
    ("SEF-04","Incident Management","Notify affected customers and regulators of incidents",
     None,["ir-6","pm-15","ir-8"]),
    ("SEF-05","Incident Management","Conduct post-incident reviews",
     None,["ir-4","ca-7","pm-4"]),
    ("SEF-06","Incident Management","Test incident response plan annually",
     None,["ir-3","ca-2","cp-4"]),
    ("SEF-07","Incident Management","Preserve forensic evidence during incident investigations",
     None,["au-9","ir-4","au-3"]),
    # STA — Supply Chain Management
    ("STA-01","Supply Chain","Establish supply chain risk management program",
     None,["sr-1","sr-2","sa-9","pm-9"]),
    ("STA-02","Supply Chain","Assess security posture of cloud providers and suppliers",
     None,["sr-6","sa-9","ca-2"]),
    ("STA-03","Supply Chain","Require security clauses in supplier contracts",
     None,["sr-1","sa-9","sr-3"]),
    ("STA-04","Supply Chain","Monitor supplier security compliance continuously",
     None,["sr-6","ca-7","sa-9"]),
    ("STA-05","Supply Chain","Define offboarding process for terminated suppliers",
     None,["sa-9","sr-12","ps-4"]),
    # TVM — Threat & Vulnerability Management
    ("TVM-01","Vulnerability Management","Implement vulnerability scanning program",
     None,["ra-5","ca-7","si-2"]),
    ("TVM-02","Vulnerability Management","Remediate critical/high vulnerabilities within defined SLA",
     None,["si-2","ra-5","pm-4"]),
    ("TVM-03","Vulnerability Management","Conduct penetration testing on defined schedule",
     None,["ca-8","ra-5","ca-2"]),
    ("TVM-04","Vulnerability Management","Subscribe to threat intelligence feeds",
     None,["si-5","pm-16","ra-3"]),
    ("TVM-05","Vulnerability Management","Track and manage software dependencies and SBOM",
     None,["sr-4","sa-12","cm-8"]),
    ("TVM-06","Vulnerability Management","Implement patch management process with SLAs",
     None,["si-2","cm-3","ma-2"]),
    ("TVM-07","Vulnerability Management","Scan container images for vulnerabilities before deployment",
     None,["ra-5","sa-11","cm-7"]),
    # UEM — Universal Endpoint Management
    ("UEM-01","Endpoint Management","Define endpoint security policy for all device types",
     None,["cm-1","cm-6","ac-19"]),
    ("UEM-02","Endpoint Management","Enroll all endpoints in mobile device management (MDM)",
     None,["ac-19","cm-8","cm-6"]),
    ("UEM-03","Endpoint Management","Enable full-disk encryption on all endpoints",
     None,["sc-28","mp-4","ac-19"]),
    ("UEM-04","Endpoint Management","Enforce screen lock and auto-wipe policies",
     None,["ac-11","ac-19","mp-6"]),
    ("UEM-05","Endpoint Management","Restrict installation of unauthorized software",
     None,["cm-11","cm-7","ac-19"]),
    ("UEM-06","Endpoint Management","Deploy endpoint detection and response (EDR) on all devices",
     None,["si-3","si-4","ac-19"]),
    ("UEM-07","Endpoint Management","Apply security patches to endpoints within SLA",
     None,["si-2","cm-3","ac-19"]),
    ("UEM-08","Endpoint Management","Implement BYOD controls and segregation",
     None,["ac-19","ac-20","cm-6"]),
]

# ── GLBA Safeguards Rule (2023) ───────────────────────────────────────────────
GLBA_CONTROLS = [
    ("314.4(a)","Program Governance","Designate a qualified individual responsible for the information security program",
     None,["pm-2","pm-19"]),
    ("314.4(b)","Risk Assessment","Conduct risk assessment identifying reasonably foreseeable internal/external risks",
     None,["ra-1","ra-2","ra-3","pm-9"]),
    ("314.4(b)(1)","Risk Assessment","Risk assessment addresses employee training and management",
     None,["at-2","at-3","ra-3"]),
    ("314.4(b)(2)","Risk Assessment","Risk assessment addresses information systems including network and software design",
     None,["ra-3","sa-8","cm-6","sc-7"]),
    ("314.4(b)(3)","Risk Assessment","Risk assessment addresses detecting and preventing attacks or system failures",
     None,["ra-3","si-4","ir-4","si-3"]),
    ("314.4(c)(1)","Safeguards — Access","Implement access controls including MFA or equivalent",
     None,["ac-2","ac-3","ia-2","ac-6"]),
    ("314.4(c)(2)","Safeguards — Inventory","Know your data: identify and inventory customer information",
     None,["cm-8","ra-2","pm-5","pm-25"]),
    ("314.4(c)(3)","Safeguards — Encryption","Encrypt customer information in transit and at rest",
     None,["sc-8","sc-28","sc-12","ia-7"]),
    ("314.4(c)(4)","Safeguards — Development","Adopt secure development practices for in-house applications",
     None,["sa-3","sa-8","sa-11","sa-15"]),
    ("314.4(c)(5)","Safeguards — Authentication","Implement multi-factor authentication for any individual accessing customer information",
     None,["ia-2","ia-5","ac-17"]),
    ("314.4(c)(6)","Safeguards — Disposal","Dispose of customer information securely within two years or when no longer needed",
     None,["mp-6","mp-7","si-12"]),
    ("314.4(c)(7)","Safeguards — Change Management","Anticipate and evaluate changes to operations before implementation",
     None,["cm-3","cm-4","ra-3"]),
    ("314.4(c)(8)","Safeguards — Monitoring","Monitor and test the effectiveness of key controls and procedures",
     None,["ca-2","ca-7","si-4","au-6"]),
    ("314.4(d)","Training","Train staff to implement the information security program",
     None,["at-2","at-3","pm-13"]),
    ("314.4(e)","Service Providers","Select and monitor service providers that maintain appropriate safeguards",
     None,["sa-9","sr-1","sr-3","sr-6"]),
    ("314.4(f)","Program Evaluation","Evaluate and adjust the program in light of changes and testing results",
     None,["ca-2","ca-7","pm-14","ra-3"]),
    ("314.4(g)","Incident Response","Establish and implement an incident response plan",
     None,["ir-1","ir-4","ir-6","ir-8"]),
    ("314.4(h)","Board Reporting","Report to Board or senior management on information security program",
     None,["pm-2","pm-9","ca-7","pm-6"]),
]

# ── FFIEC CAT ────────────────────────────────────────────────────────────────
FFIEC_CONTROLS = [
    # Domain 1: Cyber Risk Management and Oversight
    ("D1.G.IT.B.1","Cyber Risk Management","Cybersecurity is included in strategic planning",
     None,["pm-9","pm-1","pm-11"]),
    ("D1.G.IT.B.2","Cyber Risk Management","Cybersecurity risks are discussed at board level",
     None,["pm-2","pm-9","pm-10"]),
    ("D1.G.IT.B.3","Cyber Risk Management","CISO or equivalent role is designated",
     None,["pm-2","pm-19"]),
    ("D1.RM.IT.B.1","Risk Management","Cybersecurity risks are included in risk management program",
     None,["pm-9","ra-3","ra-1"]),
    ("D1.RM.IT.B.2","Risk Management","Risk appetite is defined for cybersecurity",
     None,["pm-9","ra-1","ra-2"]),
    ("D1.RM.IT.B.3","Risk Management","Cyber risks are identified and documented",
     None,["ra-3","pm-9","pm-16"]),
    ("D1.RM.IT.B.4","Risk Management","Risks are mitigated and residual risk is accepted",
     None,["ra-7","ca-5","pm-4"]),
    # Domain 2: Threat Intelligence and Collaboration
    ("D2.IS.Is.B.1","Threat Intelligence","Cyber threat intelligence is obtained from reliable sources",
     None,["pm-16","si-5","ra-3"]),
    ("D2.IS.Is.B.2","Threat Intelligence","Threat intelligence is used to monitor for threats",
     None,["si-4","pm-16","ra-3"]),
    ("D2.IS.Is.B.3","Threat Intelligence","Emerging cyber threats are monitored",
     None,["pm-16","si-5","ca-7"]),
    ("D2.IS.Is.E.1","Threat Intelligence","Participation in information sharing forums (e.g., FS-ISAC)",
     None,["pm-15","pm-16","ir-7"]),
    # Domain 3: Cybersecurity Controls
    ("D3.PC.Im.B.1","Preventive Controls","Access controls prevent unauthorized access",
     None,["ac-2","ac-3","ia-2","ac-6"]),
    ("D3.PC.Im.B.2","Preventive Controls","User access is reviewed at least annually",
     None,["ac-2","ca-7","ia-4"]),
    ("D3.PC.Im.B.3","Preventive Controls","MFA is used for critical systems and remote access",
     None,["ia-2","ac-17"]),
    ("D3.PC.Im.B.4","Preventive Controls","Vendor/third-party access is managed",
     None,["sa-9","ac-17","ia-2"]),
    ("D3.PC.Am.B.1","Asset Management","IT assets are inventoried",
     None,["cm-8","pm-5"]),
    ("D3.PC.Am.B.2","Asset Management","Hardware and software assets are managed",
     None,["cm-8","cm-10","cm-11"]),
    ("D3.PC.Se.B.1","Security Operations","Security configurations are established for all systems",
     None,["cm-2","cm-6","cm-7"]),
    ("D3.PC.Se.B.2","Security Operations","Patch management process exists",
     None,["si-2","cm-3","ma-2"]),
    ("D3.PC.Se.B.3","Security Operations","Anti-malware tools are deployed",
     None,["si-3","si-4"]),
    ("D3.PC.Se.B.4","Security Operations","Network segmentation is implemented",
     None,["sc-7","ca-3","ac-4"]),
    ("D3.DC.An.B.1","Detective Controls","Audit logging is enabled for critical systems",
     None,["au-2","au-3","au-12"]),
    ("D3.DC.An.B.2","Detective Controls","Logs are reviewed on regular basis",
     None,["au-6","ca-7","si-4"]),
    ("D3.DC.An.B.3","Detective Controls","Intrusion detection/prevention is implemented",
     None,["si-4","sc-7","au-6"]),
    ("D3.DC.Ev.B.1","Detective Controls","Security events are identified and escalated",
     None,["ir-4","ir-5","au-6"]),
    # Domain 4: External Dependency Management
    ("D4.RM.Rm.B.1","Third-Party Risk","Third parties with access to systems are identified",
     None,["sa-9","sr-1","cm-8"]),
    ("D4.RM.Rm.B.2","Third-Party Risk","Third-party risk is included in risk management",
     None,["sa-9","sr-6","pm-9"]),
    ("D4.RM.Rm.B.3","Third-Party Risk","Contracts include cybersecurity and audit rights",
     None,["sa-9","sr-1","sr-3"]),
    ("D4.RM.Rm.B.4","Third-Party Risk","Third-party performance is monitored",
     None,["sa-9","ca-7","sr-6"]),
    # Domain 5: Cyber Incident Management and Resilience
    ("D5.IR.Im.B.1","Incident Response","Incident response plan is documented",
     None,["ir-1","ir-8"]),
    ("D5.IR.Im.B.2","Incident Response","Incidents are classified and escalated",
     None,["ir-4","ir-5","au-6"]),
    ("D5.IR.Im.B.3","Incident Response","Regulatory notification requirements are documented",
     None,["ir-6","pm-15","ir-8"]),
    ("D5.IR.Im.B.4","Incident Response","Incident response is tested annually",
     None,["ir-3","ca-2","cp-4"]),
    ("D5.IR.Re.B.1","Resilience","Business continuity plan addresses cyber incidents",
     None,["cp-2","ir-4","cp-10"]),
    ("D5.IR.Re.B.2","Resilience","BCP/DR plans are tested",
     None,["cp-4","cp-10","ca-2"]),
    ("D5.IR.Re.B.3","Resilience","Backups are maintained and recovery tested",
     None,["cp-9","cp-10","cp-4"]),
]

# ── SWIFT CSP 2024 ────────────────────────────────────────────────────────────
SWIFT_CONTROLS = [
    # Mandatory controls
    ("1.1","Restrict Internet Access","Ensure SWIFT-related infrastructure is segregated from general IT",
     None,["sc-7","ca-3","ac-4","sc-3"]),
    ("1.2","Operating System Privilege Accounts","Restrict and control OS-level admin accounts",
     None,["ac-6","ia-2","ac-2"]),
    ("1.3A","Virtualization Security","Secure the virtualization platform hosting SWIFT components",
     None,["sc-3","sc-7","cm-6","ac-6"]),
    ("1.3B","Application Security Updates","Keep SWIFT software and OS patched",
     None,["si-2","cm-3","ma-2"]),
    ("1.4","Operator Session Confidentiality and Integrity","Protect operator sessions with encryption and integrity",
     None,["sc-8","sc-23","ia-2"]),
    ("1.5A","Customer Environment Protection","Protect the customer environment from general IT threats",
     None,["sc-7","si-3","cm-7"]),
    ("2.1","Internal Data Flow Security","Authenticate and encrypt SWIFT messaging traffic internally",
     None,["sc-8","ia-3","sc-23"]),
    ("2.2","Security Updates","Install SWIFT and OS security patches within defined timeframes",
     None,["si-2","cm-3"]),
    ("2.3","System Hardening","Minimize attack surface by disabling unnecessary services",
     None,["cm-7","cm-6","sa-9"]),
    ("2.4A","Back-Office Data Flow Security","Secure data flows between SWIFT and back-office systems",
     None,["sc-8","ca-3","ac-4"]),
    ("2.5A","External Transmission Data Protection","Protect external transmissions of SWIFT-related data",
     None,["sc-8","sc-28","mp-5"]),
    ("2.6","Operator Session Confidentiality","Protect RDP/SSH operator sessions to SWIFT systems",
     None,["sc-8","ac-17","ia-2"]),
    ("2.7","Vulnerability Scanning","Perform vulnerability scans of SWIFT environment",
     None,["ra-5","ca-2","si-2"]),
    ("2.8A","Outsourced Critical Activities","Apply CSP requirements to outsourced SWIFT operations",
     None,["sa-9","sr-6","sr-3"]),
    ("2.9","Transaction Business Controls","Implement transaction filtering and screening",
     None,["si-10","au-6","si-4"]),
    ("2.11A","RMA Business Controls","Restrict SWIFT messaging via Relationship Management Application",
     None,["ac-3","ac-6","ia-3"]),
    ("5.1","Logical Access Control","Restrict logical access to SWIFT systems to authorized users",
     None,["ac-2","ac-3","ia-2"]),
    ("5.2","Token Management","Manage hardware tokens for SWIFT authentication",
     None,["ia-5","ia-2","sc-17"]),
    ("5.3A","Privileged Account Management","Control and monitor privileged SWIFT accounts",
     None,["ac-6","ia-2","au-2"]),
    ("5.4","Physical and Logical Password Storage","Protect stored credentials for SWIFT systems",
     None,["ia-5","sc-28","mp-4"]),
    ("6.1","Malware Protection","Deploy and maintain anti-malware on SWIFT infrastructure",
     None,["si-3","si-4","cm-6"]),
    ("6.2","Software Integrity","Verify integrity of SWIFT software",
     None,["si-7","sa-10","cm-14"]),
    ("6.3","Database Integrity","Monitor and protect SWIFT database integrity",
     None,["si-7","au-9","au-3"]),
    ("6.4","Logging and Monitoring","Implement logging for all SWIFT-related activity",
     None,["au-2","au-3","au-6","au-12"]),
    ("6.5A","Intrusion Detection","Implement IDS for SWIFT environment",
     None,["si-4","au-6","ir-5"]),
    ("7.1","Cyber Incident Response Planning","Maintain cyber incident response plan covering SWIFT",
     None,["ir-1","ir-4","ir-8"]),
    ("7.2","Security Training and Awareness","Train SWIFT operators on cybersecurity",
     None,["at-2","at-3"]),
    ("7.3A","Penetration Testing","Conduct annual penetration test of SWIFT environment",
     None,["ca-8","ra-5","ca-2"]),
    ("7.4A","Scenario Risk Assessment","Perform scenario-based risk assessment for SWIFT operations",
     None,["ra-3","pm-9","ca-2"]),
]

# ── PIPEDA ────────────────────────────────────────────────────────────────────
PIPEDA_CONTROLS = [
    ("P1","Accountability","Designate a Privacy Officer accountable for PIPEDA compliance",
     None,["pm-2","pm-20","pm-19"]),
    ("P2","Identifying Purposes","Identify and document the purposes for collecting personal information",
     None,["pm-20","pt-2","pm-25"]),
    ("P3","Consent","Obtain meaningful consent for collection, use, or disclosure",
     None,["pt-2","pm-25","pm-20"]),
    ("P4","Limiting Collection","Collect only personal information necessary for identified purposes",
     None,["pm-25","si-12","cm-7"]),
    ("P5","Limiting Use, Disclosure, Retention","Use and disclose personal information only for purposes it was collected",
     None,["pm-25","si-12","mp-6","ac-3"]),
    ("P6","Accuracy","Ensure personal information is accurate, complete, and up to date",
     None,["si-10","pm-25","si-12"]),
    ("P7","Safeguards","Protect personal information with appropriate security safeguards",
     None,["sc-28","ac-3","ia-5","si-3","ra-3","mp-4"]),
    ("P7-Technical","Safeguards — Technical","Technical safeguards include encryption, firewalls, access controls",
     None,["sc-8","sc-28","ac-2","ia-2","sc-7"]),
    ("P7-Organizational","Safeguards — Organizational","Organizational safeguards include training, policies, access limits",
     None,["at-2","pm-1","ps-3","ac-6"]),
    ("P8","Openness","Make privacy policies and practices readily available",
     None,["pm-20","pt-2","pl-4"]),
    ("P9","Individual Access","Allow individuals to access their personal information on request",
     None,["pm-20","pm-25","pt-2","ac-3"]),
    ("P10","Challenging Compliance","Establish process for individuals to challenge compliance",
     None,["pm-20","pm-25","ir-6"]),
    ("PIPEDA-Breach","Breach Notification","Report significant breaches to OPC and notify affected individuals",
     None,["ir-6","pm-15","ir-8","ir-4"]),
    ("PIPEDA-Records","Breach Records","Maintain records of all privacy breaches for 24 months",
     None,["au-3","si-12","ir-5"]),
]

# ── LGPD ─────────────────────────────────────────────────────────────────────
LGPD_CONTROLS = [
    ("Art.6","Legal Basis","Process personal data only when a legal basis under Art. 7-11 applies",
     None,["pm-25","pt-2","pm-20","ra-2"]),
    ("Art.7","Legal Bases — General","10 legal bases for processing (consent, legitimate interest, etc.)",
     None,["pm-25","pt-2","pm-20"]),
    ("Art.9","Sensitive Data","Additional safeguards for sensitive personal data categories",
     None,["sc-28","ac-3","pm-25","pt-7"]),
    ("Art.11","Sensitive Data Processing","Restrict sensitive data processing to specific legal bases",
     None,["pm-25","pt-7","ac-3","ra-2"]),
    ("Art.17","Data Subject Rights","Honor data subject rights including access, correction, deletion",
     None,["pm-20","pm-25","pt-2","ac-3"]),
    ("Art.18","Data Subject Rights — Specific","Right to anonymization, blocking, or deletion; right to portability",
     None,["pm-25","pt-3","mp-6","si-12"]),
    ("Art.20","Automated Decisions","Right to review of decisions made solely by automated means",
     None,["pm-25","si-10","pt-2"]),
    ("Art.25","Privacy by Design","Implement privacy-by-design and privacy-by-default measures",
     None,["pl-8","sa-8","pm-25","pt-7","cm-7"]),
    ("Art.37","DPO Designation","Designate a Data Protection Officer (DPO)",
     None,["pm-2","pm-20","pm-19"]),
    ("Art.41","Governance","Establish internal privacy governance and compliance program",
     None,["pm-1","pm-2","ca-2","pm-9"]),
    ("Art.46","Security Measures","Adopt security measures to protect personal data",
     None,["sc-28","ac-3","ia-5","ra-3","pm-9","si-3"]),
    ("Art.46-Technical","Security — Technical","Technical measures: encryption, pseudonymization, access control",
     None,["sc-28","sc-8","sc-12","ac-2","ia-2"]),
    ("Art.46-Admin","Security — Administrative","Administrative measures: policies, training, access review",
     None,["pm-1","at-2","ac-2","ca-7"]),
    ("Art.48","Incident Notification","Notify ANPD and data subjects of security incidents in reasonable timeframe",
     None,["ir-6","pm-15","ir-8","ir-4"]),
    ("Art.50","Accountability","Demonstrate compliance; maintain records of processing activities",
     None,["pm-1","pm-14","au-3","ca-2","pm-9"]),
    ("Art.52","International Transfer","Restrict international transfers to adequate countries or approved mechanisms",
     None,["sa-9","sr-6","sc-28","mp-5"]),
]

FRAMEWORK_DATA = {
    "sox":      SOX_CONTROLS,
    "ccpa":     CCPA_CONTROLS,
    "csaccm":   CSACCM_CONTROLS,
    "glba":     GLBA_CONTROLS,
    "ffiec":    FFIEC_CONTROLS,
    "swiftcsp": SWIFT_CONTROLS,
    "pipeda":   PIPEDA_CONTROLS,
    "lgpd":     LGPD_CONTROLS,
}


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    total_fw = total_ctrl = total_xwalk = 0

    for fw in FRAMEWORKS:
        cur.execute(
            "INSERT OR IGNORE INTO compliance_frameworks "
            "(id,name,short_name,version,category,published_by,description,source_url,is_active) "
            "VALUES (?,?,?,?,?,?,?,?,1)",
            (fw["id"], fw["name"], fw["short_name"], fw["version"],
             fw["category"], fw["published_by"], fw["description"], fw["source_url"])
        )
        if cur.rowcount:
            total_fw += 1
        fw_id    = fw["id"]
        sn       = fw["short_name"]
        controls = FRAMEWORK_DATA[sn]

        for ctrl_id, domain, title, level, nist_ids in controls:
            cur.execute(
                "INSERT OR IGNORE INTO framework_controls "
                "(framework_id, control_id, title, domain, level) VALUES (?,?,?,?,?)",
                (fw_id, ctrl_id, title, domain, level)
            )
            if cur.rowcount:
                total_ctrl += 1
            cur.execute("SELECT id FROM framework_controls WHERE framework_id=? AND control_id=?",
                        (fw_id, ctrl_id))
            fc_id = cur.fetchone()[0]

            for nist_id in nist_ids:
                nid = nist_id.lower()
                if '.' in nid:
                    nid = nid.split('.')[0]
                # First NIST ID = high confidence (primary mapping); rest = medium (functional equivalence)
                confidence = "high" if nist_id == nist_ids[0] else "medium"
                cur.execute(
                    "INSERT OR IGNORE INTO control_crosswalks "
                    "(framework_control_id, nist_control_id, mapping_type, confidence, source) "
                    "VALUES (?,?,?,?,?)",
                    (fc_id, nid, "direct", confidence, "community")
                )
                if cur.rowcount:
                    total_xwalk += 1

    conn.commit()
    conn.close()
    print(f"Phase 3a — Seeded: {total_fw} frameworks | {total_ctrl} controls | {total_xwalk} crosswalk mappings")

    conn2 = sqlite3.connect(DB_PATH)
    cur2  = conn2.cursor()
    cur2.execute("""
        SELECT cf.short_name, COUNT(DISTINCT fc.id), COUNT(cx.id)
        FROM compliance_frameworks cf
        JOIN framework_controls fc ON fc.framework_id=cf.id
        JOIN control_crosswalks cx ON cx.framework_control_id=fc.id
        WHERE cf.short_name IN ('sox','ccpa','csaccm','glba','ffiec','swiftcsp','pipeda','lgpd')
        GROUP BY cf.short_name ORDER BY cf.short_name
    """)
    print(f"\n{'framework':<12} {'controls':>9} {'crosswalks':>11}")
    print("-" * 34)
    for r in cur2.fetchall():
        print(f"  {r[0]:<10} {r[1]:>9} {r[2]:>11}")
    conn2.close()


if __name__ == "__main__":
    main()
