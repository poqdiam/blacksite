"""
seed_crosswalks_phase3b.py — Phase 3b (8 frameworks)
Functional-equivalence crosswalk. confidence="medium" for pragmatic mappings.

Frameworks: appi, nerccip, tsapipeline, hitech, cfr11, soc1, tisax, naic

Run: cd /home/graycat/projects/blacksite && .venv/bin/python3 scripts/seed_crosswalks_phase3b.py
"""
import sqlite3, uuid
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "blacksite.db"

FRAMEWORKS = [
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "appi-japan-2022")),
     "name": "APPI (Japan)", "short_name": "appi",
     "version": "2022 Amendment", "category": "regulatory", "published_by": "PPC Japan",
     "description": "Act on Protection of Personal Information. Japan's primary privacy law. "
                    "2022 amendment added breach notification, cross-border transfer rules, "
                    "and pseudonymously processed information provisions.",
     "source_url": "https://www.ppc.go.jp/en/legal/"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "nerc-cip-v7")),
     "name": "NERC CIP v7", "short_name": "nerccip",
     "version": "v7", "category": "regulatory", "published_by": "NERC",
     "description": "North American Electric Reliability Corporation Critical Infrastructure Protection "
                    "standards. Mandatory cybersecurity requirements for the bulk electric system (BES).",
     "source_url": "https://www.nerc.com/pa/Stand/Pages/CIPStandards.aspx"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "tsa-pipeline-sd02d-2022")),
     "name": "TSA Pipeline Security Directive SD-02D", "short_name": "tsapipeline",
     "version": "SD-02D (2022)", "category": "regulatory", "published_by": "TSA/DHS",
     "description": "TSA Security Directives for hazardous liquid and natural gas pipeline operators. "
                    "Requires incident reporting, cybersecurity coordinator, network segmentation, "
                    "access control, and continuous monitoring.",
     "source_url": "https://www.tsa.gov/pipeline-cybersecurity"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "hitech-act-2009")),
     "name": "HITECH Act (2009)", "short_name": "hitech",
     "version": "2009/2021 Omnibus", "category": "regulatory", "published_by": "HHS",
     "description": "Health Information Technology for Economic and Clinical Health Act. Extends HIPAA "
                    "with breach notification requirements, expanded BA liability, and enhanced penalties.",
     "source_url": "https://www.hhs.gov/hipaa/for-professionals/special-topics/hitech-act-enforcement-interim-final-rule/index.html"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "fda-21cfr-part11")),
     "name": "21 CFR Part 11 (FDA Electronic Records)", "short_name": "cfr11",
     "version": "21 CFR Part 11", "category": "regulatory", "published_by": "FDA",
     "description": "FDA regulations governing electronic records and electronic signatures. Applies to "
                    "pharmaceutical, biotech, medical device, and clinical trial organizations.",
     "source_url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "soc1-ssae18-2017")),
     "name": "SOC 1 / SSAE 18", "short_name": "soc1",
     "version": "SSAE 18 (2017)", "category": "industry", "published_by": "AICPA",
     "description": "Service Organization Control Report on controls relevant to user entities' "
                    "internal control over financial reporting (ICFR). ITGC-focused.",
     "source_url": "https://www.aicpa.org/resources/landing/system-and-organization-controls-soc-suite-of-services"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "tisax-vda-isa-6")),
     "name": "TISAX / VDA ISA", "short_name": "tisax",
     "version": "VDA ISA 6.0", "category": "industry", "published_by": "VDA/ENX",
     "description": "Trusted Information Security Assessment Exchange. Mandatory for suppliers to "
                    "German/European automotive OEMs. Based on ISO 27001 with automotive-specific "
                    "extensions for prototype protection and third-party data.",
     "source_url": "https://portal.enx.com/en-US/TISAX/"},
    {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "naic-model-cybersecurity-law-2017")),
     "name": "NAIC Model Cybersecurity Law", "short_name": "naic",
     "version": "2017 (adopted by ~25 states)", "category": "regulatory", "published_by": "NAIC",
     "description": "NAIC Insurance Data Security Model Law. Requires insurance licensees to implement "
                    "an information security program and notify regulators of cybersecurity events.",
     "source_url": "https://content.naic.org/sites/default/files/inline-files/MDL-668.pdf"},
]

# ── APPI (Japan 2022) ─────────────────────────────────────────────────────────
APPI_CONTROLS = [
    ("APPI-15","Purpose Specification","Specify purpose of use of personal information as specifically as possible",
     None,["pm-20","pt-2","pm-25"]),
    ("APPI-16","Restriction on Use","Do not handle personal information beyond specified purpose without consent",
     None,["pm-25","ac-3","si-12"]),
    ("APPI-17","Appropriate Acquisition","Acquire personal information by lawful and fair means",
     None,["pm-25","pt-2","pm-20"]),
    ("APPI-18","Notification at Acquisition","Notify or publicly announce purpose of use when acquiring PI",
     None,["pm-20","pt-2"]),
    ("APPI-20","Security Control Measures","Take necessary and appropriate measures to prevent leakage, loss, or damage",
     None,["sc-28","ac-3","ia-5","ra-3","pm-9","si-3"]),
    ("APPI-20-Tech","Security — Technical","Technical: encryption, access control, monitoring, logging",
     None,["sc-28","sc-8","ac-2","ia-2","au-2","au-6"]),
    ("APPI-20-Org","Security — Organizational","Org: policies, training, incident response, awareness",
     None,["pm-1","at-2","ir-1","ca-7"]),
    ("APPI-21","Supervision of Employees","Supervise employees handling personal information",
     None,["ps-3","at-2","at-3","ps-8"]),
    ("APPI-22","Supervision of Trustees","Supervise third-party processors handling personal data",
     None,["sa-9","sr-6","sr-1","sr-3"]),
    ("APPI-23","Restriction on Third-Party Provision","Restrict disclosure to third parties without consent",
     None,["pm-25","ac-3","mp-5","sa-9"]),
    ("APPI-24","Cross-Border Transfer","Additional restrictions on transfers to foreign third parties",
     None,["sa-9","sr-6","sc-28","mp-5"]),
    ("APPI-27","Retained Personal Data — Disclosure","Disclose retained personal data to data subject on request",
     None,["pm-20","pm-25","pt-2","ac-3"]),
    ("APPI-28","Retained Personal Data — Correction","Correct or add retained personal data on data subject request",
     None,["pm-25","si-10","pt-2"]),
    ("APPI-29","Retained Personal Data — Cessation","Stop using or delete retained personal data on request",
     None,["mp-6","si-12","pm-25","pt-3"]),
    ("APPI-26","Breach Notification","Report personal data breaches to PPC and notify data subjects",
     None,["ir-6","pm-15","ir-8","ir-4"]),
    ("APPI-41","Pseudonymously Processed","Implement safeguards for pseudonymously processed information",
     None,["pt-7","sc-28","pm-25","si-12"]),
    ("APPI-43","Anonymously Processed","Implement safeguards for anonymously processed information",
     None,["pt-7","pm-25","si-12","sc-28"]),
]

# ── NERC CIP v7 ───────────────────────────────────────────────────────────────
NERCCIP_CONTROLS = [
    # CIP-002: BES Cyber System Categorization
    ("CIP-002-5.1a","Asset Identification","Identify and categorize BES Cyber Systems by impact level",
     None,["ra-2","cm-8","pm-11","sa-14"]),
    # CIP-003: Security Management Controls
    ("CIP-003-8-R1","Security Policy","Maintain cybersecurity policies for high and medium impact BES systems",
     None,["pm-1","pl-2","at-2"]),
    ("CIP-003-8-R2","Security Policy — Low","Implement security plan for low impact BES Cyber Systems",
     None,["pm-1","pl-2","cm-6"]),
    ("CIP-003-8-R4","Transient Devices","Protect transient cyber assets and removable media",
     None,["mp-7","mp-4","ac-19","cm-6"]),
    ("CIP-003-8-R5","Vendor Remote Access","Control and monitor vendor remote access",
     None,["ac-17","ia-2","sa-9","au-2"]),
    # CIP-004: Personnel and Training
    ("CIP-004-6-R1","Awareness","Implement security awareness program for personnel with access",
     None,["at-2","pm-13"]),
    ("CIP-004-6-R2","Training","Train personnel with authorized electronic/physical access",
     None,["at-3","at-2"]),
    ("CIP-004-6-R3","Personnel Risk Assessment","Verify identity and conduct 7-year criminal history check",
     None,["ps-3","ps-2"]),
    ("CIP-004-6-R4","Access Management","Authorize and manage logical and physical access",
     None,["ac-2","pe-2","ia-2"]),
    ("CIP-004-6-R5","Access Revocation","Revoke access within 24 hours of termination",
     None,["ps-4","ac-2","ia-4"]),
    # CIP-005: Electronic Security Perimeters
    ("CIP-005-6-R1","Electronic Security Perimeter","Define and protect the Electronic Security Perimeter (ESP)",
     None,["sc-7","ca-3","ac-4"]),
    ("CIP-005-6-R2","Remote Access","Require MFA for all interactive remote access; protect with encryption",
     None,["ia-2","ac-17","sc-8"]),
    ("CIP-005-6-R3","Vendor Remote Access","Control and monitor vendor-initiated interactive remote access",
     None,["ac-17","sa-9","au-2","ia-2"]),
    # CIP-006: Physical Security
    ("CIP-006-6-R1","Physical Security Plan","Implement physical security plan for high/medium impact systems",
     None,["pe-1","pe-2","pe-3","pe-6"]),
    ("CIP-006-6-R2","Visitor Control","Implement visitor control program for Physical Security Perimeter",
     None,["pe-3","pe-8","pe-2"]),
    ("CIP-006-6-R3","Physical Access Controls — Low","Protect low impact systems from unauthorized physical access",
     None,["pe-2","pe-3"]),
    # CIP-007: Systems Security Management
    ("CIP-007-6-R1","Ports and Services","Disable unused physical and logical ports and services",
     None,["cm-7","sc-7","cm-6"]),
    ("CIP-007-6-R2","Security Patches","Evaluate and apply security patches within 35 days of release",
     None,["si-2","cm-3","ma-2"]),
    ("CIP-007-6-R3","Malicious Code Prevention","Deploy malicious code prevention tools",
     None,["si-3","si-4","cm-6"]),
    ("CIP-007-6-R4","Security Event Monitoring","Log security events and alert on defined events",
     None,["au-2","au-3","au-6","au-12","si-4"]),
    ("CIP-007-6-R5","System Access Control","Enforce least privilege; manage shared accounts; authenticate users",
     None,["ac-2","ac-6","ia-2","ia-5"]),
    # CIP-008: Incident Reporting and Response
    ("CIP-008-6-R1","Incident Response Plan","Establish incident response plan for Cyber Security Incidents",
     None,["ir-1","ir-8","ir-4"]),
    ("CIP-008-6-R2","Incident Response Testing","Test incident response plan annually",
     None,["ir-3","ca-2","cp-4"]),
    ("CIP-008-6-R3","Incident Reporting","Report Reportable Cyber Security Incidents to E-ISAC and CISA",
     None,["ir-6","pm-15","ir-8"]),
    # CIP-009: Recovery Plans
    ("CIP-009-6-R1","Recovery Plans","Establish recovery plan for BES Cyber Systems",
     None,["cp-2","cp-10","ir-4","cp-9"]),
    ("CIP-009-6-R2","Recovery Plan Testing","Test recovery plan at minimum annually",
     None,["cp-4","cp-10","ca-2"]),
    ("CIP-009-6-R3","Recovery Plan Updates","Review and update recovery plan after test or actual use",
     None,["cp-2","ir-4","pm-4"]),
    # CIP-010: Configuration Change Management and Vulnerability Management
    ("CIP-010-4-R1","Configuration Change Management","Document and manage configuration changes to BES Cyber Systems",
     None,["cm-3","cm-2","cm-6","au-3"]),
    ("CIP-010-4-R2","Configuration Monitoring","Monitor for unauthorized changes to baseline configurations",
     None,["cm-3","si-7","si-4","au-6"]),
    ("CIP-010-4-R3","Vulnerability Management","Conduct vulnerability assessments at least every 15 months",
     None,["ra-5","ca-2","ca-8"]),
    ("CIP-010-4-R4","Transient Cyber Assets","Manage transient cyber assets and removable media",
     None,["mp-7","mp-4","cm-6","ac-19"]),
    # CIP-011: Information Protection
    ("CIP-011-3-R1","Information Protection Program","Identify BES Cyber System Information and implement access controls",
     None,["mp-4","ac-3","sc-28","ra-2"]),
    ("CIP-011-3-R2","Storage and Transit Protection","Protect stored and transmitted BES Cyber System Information",
     None,["sc-28","sc-8","mp-4","mp-5"]),
    # CIP-013: Supply Chain Risk Management
    ("CIP-013-2-R1","Supply Chain Risk Management Plan","Develop supply chain risk management plan for high/medium impact systems",
     None,["sr-1","sr-2","sa-9","pm-9"]),
    ("CIP-013-2-R2","Implementation","Implement supply chain risk management plan",
     None,["sr-3","sr-6","sa-9","sa-12"]),
    ("CIP-013-2-R3","Plan Review","Review and approve supply chain risk management plan every 15 months",
     None,["sr-1","ca-7","pm-14"]),
    # CIP-014: Physical Security (Transmission)
    ("CIP-014-3-R1","Transmission Station Identification","Identify transmission stations and substations requiring protection",
     None,["ra-2","cm-8","pm-11"]),
    ("CIP-014-3-R5","Physical Security Plan","Develop and implement physical security plan",
     None,["pe-1","pe-2","pe-3","pe-6"]),
]

# ── TSA Pipeline Security Directive SD-02D ────────────────────────────────────
TSAPIPELINE_CONTROLS = [
    ("TSA-1","Incident Reporting","Report cybersecurity incidents to CISA within 12 hours",
     None,["ir-6","pm-15","ir-4"]),
    ("TSA-2","Cybersecurity Coordinator","Designate 24/7 cybersecurity coordinator and alternate",
     None,["pm-2","ir-7","pm-19"]),
    ("TSA-3-1","Network Segmentation","Segment IT and OT networks to prevent lateral movement",
     None,["sc-7","ca-3","ac-4","sc-3"]),
    ("TSA-3-2","Access Control","Restrict access to OT systems; implement least privilege",
     None,["ac-2","ac-6","ia-2","ac-17"]),
    ("TSA-3-3","Continuous Monitoring","Implement continuous monitoring and detection capabilities",
     None,["si-4","au-6","ca-7","ir-5"]),
    ("TSA-3-4","Patch Management","Apply security patches to OT systems within defined timeframes",
     None,["si-2","cm-3","ma-2"]),
    ("TSA-3-5","Credential Management","Change default credentials; enforce strong password policy",
     None,["ia-5","ia-4","cm-6"]),
    ("TSA-3-6","MFA","Implement MFA for remote access to OT systems",
     None,["ia-2","ac-17"]),
    ("TSA-3-7","Email Security","Deploy email filtering and anti-phishing controls",
     None,["si-8","si-3","at-2"]),
    ("TSA-3-8","Endpoint Detection","Deploy EDR or equivalent on OT endpoints where feasible",
     None,["si-3","si-4"]),
    ("TSA-3-9","Incident Response Plan","Develop and test cyber incident response plan for OT environment",
     None,["ir-1","ir-8","ir-3","cp-4"]),
    ("TSA-3-10","Backup and Recovery","Maintain secure backups and test recovery procedures",
     None,["cp-9","cp-10","cp-4"]),
    ("TSA-4","Cybersecurity Assessment","Conduct annual cybersecurity assessment of pipeline systems",
     None,["ca-2","ra-3","ra-5","ca-7"]),
    ("TSA-5","Cybersecurity Plan","Develop and maintain cybersecurity implementation plan",
     None,["pm-1","pl-2","ca-5"]),
]

# ── HITECH Act ────────────────────────────────────────────────────────────────
HITECH_CONTROLS = [
    ("HITECH-13402(a)","Breach Notification — BA","Business associates must notify covered entities of breaches",
     None,["ir-6","sa-9","sr-3"]),
    ("HITECH-13402(b)","Breach Notification — CE","Covered entities notify affected individuals of breaches without unreasonable delay (60 days max)",
     None,["ir-6","ir-8","pm-15"]),
    ("HITECH-13402(e)","Breach Notification — HHS","Notify HHS of breaches; post on website if 500+ individuals",
     None,["ir-6","pm-15","ir-8"]),
    ("HITECH-13402(f)","Breach Definition","Breach = unauthorized acquisition, access, use, or disclosure of unsecured PHI",
     None,["ra-3","ir-4","ir-5"]),
    ("HITECH-13402(h)","Unsecured PHI","PHI not rendered unusable, unreadable, or indecipherable is 'unsecured'",
     None,["sc-28","mp-6","ia-7"]),
    ("HITECH-13404","BA Direct Liability","Business associates directly liable for HIPAA Security Rule compliance",
     None,["sa-9","sr-3","sr-6","ir-1"]),
    ("HITECH-13405(d)","Minimum Necessary","Apply minimum necessary standard to all uses and disclosures",
     None,["pm-25","ac-3","ac-6","si-12"]),
    ("HITECH-13405(e)","Prohibition on Sale","Prohibition on sale of PHI without authorization",
     None,["pm-25","ac-3","mp-5"]),
    ("HITECH-13407","Accounting of Disclosures","Right to accounting of disclosures from EHR for treatment, payment, operations",
     None,["au-3","pm-25","pt-2","si-12"]),
    ("HITECH-13410(d)","Enhanced Penalties","Tiered penalty structure based on culpability and harm",
     None,["ps-8","pm-1","ca-2"]),
    ("HITECH-13411","Audit","HHS must audit covered entities and BAs for compliance",
     None,["ca-2","pm-14","au-6"]),
    ("HITECH-EHR-Security","EHR Access Controls","Certified EHR technology must support unique user identification and audit controls",
     None,["ia-2","au-2","ac-2","au-3"]),
    ("HITECH-13412","Encryption Safe Harbor","Encrypted or destroyed PHI is not 'unsecured'; breach notification not required",
     None,["sc-28","mp-6","ia-7","sc-12"]),
]

# ── 21 CFR Part 11 ────────────────────────────────────────────────────────────
CFR11_CONTROLS = [
    ("11.10(a)","Closed Systems","Validate systems to ensure accuracy, reliability, and performance",
     None,["sa-11","ca-2","cm-4","sa-3"]),
    ("11.10(b)","Closed Systems","Generate accurate and complete copies of records in human-readable form",
     None,["au-3","si-12","mp-4"]),
    ("11.10(c)","Closed Systems","Protect records for their retention period; retrieve throughout retention",
     None,["au-11","mp-4","cp-9","si-12"]),
    ("11.10(d)","Closed Systems","Limit system access to authorized individuals",
     None,["ac-2","ac-3","ia-2","ia-5"]),
    ("11.10(e)","Audit Trail","Use secure, computer-generated, time-stamped audit trails",
     None,["au-2","au-3","au-8","au-9","au-12"]),
    ("11.10(f)","Audit Trail — Operational","Operational system checks to enforce sequencing of events",
     None,["au-3","si-10","cm-3"]),
    ("11.10(g)","Authority Checks","Use authority checks to ensure that only authorized individuals use the system",
     None,["ac-3","ac-6","ia-2"]),
    ("11.10(h)","Device Checks","Use device checks (e.g., use of transaction codes, checksums)",
     None,["si-7","ia-3","au-3"]),
    ("11.10(i)","Personnel Qualifications","Determine personnel education, training, and experience for system use",
     None,["at-3","ps-3","ps-2"]),
    ("11.10(j)(1)","Written Policies","Establish written policies for personnel using electronic records",
     None,["pm-1","pl-4","at-2"]),
    ("11.10(j)(2)","Accountability","Hold individuals accountable and responsible for actions initiated",
     None,["ac-2","ia-2","au-3","ps-8"]),
    ("11.10(k)","Document Controls","Use controls over distribution, access, and use of documentation",
     None,["ac-3","cm-3","mp-4"]),
    ("11.30","Open Systems","Open systems: additional controls including encryption and digital signatures",
     None,["sc-8","sc-28","ia-7","sc-23"]),
    ("11.50","Signature Manifestations","Signed records must display name, date/time, and meaning of signature",
     None,["au-3","ia-2","au-8"]),
    ("11.70","Signature/Record Linking","Electronic signatures must be linked to their electronic records",
     None,["si-7","ia-2","au-3"]),
    ("11.100","General Requirements — Signatures","Electronic signatures are unique to one individual and not reused",
     None,["ia-2","ia-4","ia-5"]),
    ("11.200(a)","Non-Biometric Signatures","Non-biometric signatures use two components (ID + password)",
     None,["ia-2","ia-5","ia-6"]),
    ("11.200(b)","Biometric Signatures","Biometric signatures are designed to ensure they cannot be falsified",
     None,["ia-2","ia-5"]),
    ("11.300","Component Management","Controls for identification codes and passwords",
     None,["ia-4","ia-5","ac-7","ia-11"]),
]

# ── SOC 1 / SSAE 18 ──────────────────────────────────────────────────────────
SOC1_CONTROLS = [
    # ITGC: Logical Access
    ("SOC1-LA-1","Logical Access","User access is provisioned based on documented, approved requests",
     None,["ac-2","ia-2","ps-4"]),
    ("SOC1-LA-2","Logical Access","User access privileges are reviewed at least semiannually",
     None,["ac-2","ca-7","ia-4"]),
    ("SOC1-LA-3","Logical Access","Access is removed promptly upon termination or role change",
     None,["ac-2","ps-4","ps-5"]),
    ("SOC1-LA-4","Logical Access","Privileged access is restricted and monitored",
     None,["ac-6","ia-2","au-6"]),
    ("SOC1-LA-5","Logical Access","Authentication controls enforce password complexity and expiration",
     None,["ia-5","ia-2","ac-7"]),
    ("SOC1-LA-6","Logical Access","Segregation of duties is enforced for financial system processes",
     None,["ac-5","ac-6","ac-3"]),
    ("SOC1-LA-7","Logical Access","Remote access requires MFA and is logged",
     None,["ia-2","ac-17","au-2"]),
    # ITGC: Change Management
    ("SOC1-CM-1","Change Management","Changes follow a formal request, approval, and testing workflow",
     None,["cm-3","cm-4","sa-10"]),
    ("SOC1-CM-2","Change Management","Changes are tested in non-production before deployment",
     None,["cm-4","sa-11","cm-3"]),
    ("SOC1-CM-3","Change Management","Emergency changes follow expedited but documented process",
     None,["cm-3","ir-4","cm-5"]),
    ("SOC1-CM-4","Change Management","Developer access to production is prohibited",
     None,["ac-5","cm-5","ac-6"]),
    ("SOC1-CM-5","Change Management","Change logs are retained and reviewed",
     None,["au-3","au-12","cm-3","au-11"]),
    # ITGC: Computer Operations
    ("SOC1-CO-1","Computer Operations","Scheduled jobs are monitored and failures are investigated",
     None,["si-4","au-6","au-5"]),
    ("SOC1-CO-2","Computer Operations","Backups are performed per schedule and restoration is tested",
     None,["cp-9","cp-10","cp-4"]),
    ("SOC1-CO-3","Computer Operations","Incident response procedures cover financial system disruptions",
     None,["ir-1","ir-4","cp-2"]),
    ("SOC1-CO-4","Computer Operations","Security logs are reviewed regularly",
     None,["au-6","si-4","ca-7"]),
    ("SOC1-CO-5","Computer Operations","Physical access to data center is restricted to authorized personnel",
     None,["pe-2","pe-3","pe-6"]),
    # ITGC: Risk Assessment
    ("SOC1-RA-1","Risk Assessment","IT risks affecting financial reporting are identified and assessed",
     None,["ra-3","pm-9","ra-1"]),
    ("SOC1-RA-2","Risk Assessment","Controls are designed and operating effectively to address IT risks",
     None,["ca-2","ca-7","pm-4"]),
    # Complementary User Entity Controls (CUECs)
    ("SOC1-CUEC-1","User Entity Controls","User entities are responsible for their own access management",
     None,["ac-2","ia-2","ac-6"]),
    ("SOC1-CUEC-2","User Entity Controls","User entities review and follow up on exceptions noted in SOC 1 report",
     None,["ca-5","pm-4","ca-7"]),
]

# ── TISAX / VDA ISA 6.0 ───────────────────────────────────────────────────────
TISAX_CONTROLS = [
    # 1. Information Security Policies
    ("1.1.1","Information Security Policies","Information security policy is established and communicated",
     None,["pm-1","pl-4","at-2"]),
    ("1.1.2","Information Security Policies","Policies are reviewed at planned intervals or after significant changes",
     None,["pm-1","ca-7","pm-14"]),
    # 2. Organization of Information Security
    ("2.1.1","IS Organization","Information security roles and responsibilities are defined",
     None,["pm-2","ps-2","pm-10"]),
    ("2.1.2","IS Organization","Segregation of duties is implemented for conflicting roles",
     None,["ac-5","ac-6","ps-2"]),
    ("2.1.3","IS Organization","Contact with authorities and special interest groups maintained",
     None,["pm-15","ir-7"]),
    ("2.2.1","Mobile Devices","Mobile device policy covers security requirements",
     None,["ac-19","mp-7","cm-6"]),
    # 3. Human Resources Security
    ("3.1.1","HR Security","Background checks performed before employment",
     None,["ps-3","ps-2"]),
    ("3.1.2","HR Security","Security responsibilities included in employment terms",
     None,["ps-6","pl-4","ps-2"]),
    ("3.2.1","HR Security","Awareness training provided to all employees",
     None,["at-2","pm-13"]),
    ("3.2.2","HR Security","Role-specific security training provided",
     None,["at-3","pm-13"]),
    ("3.3.1","HR Security","Responsibilities for termination and return of assets",
     None,["ps-4","ac-2","pe-16"]),
    # 4. Asset Management
    ("4.1.1","Asset Management","Assets are identified and an inventory maintained",
     None,["cm-8","pm-5"]),
    ("4.1.2","Asset Management","Assets have identified owners",
     None,["cm-8","pm-5","ra-2"]),
    ("4.2.1","Asset Classification","Information is classified based on sensitivity",
     None,["ra-2","mp-3","ac-16"]),
    ("4.3.1","Media Handling","Removable media is managed per policy",
     None,["mp-7","mp-4","mp-6"]),
    # 5. Access Control
    ("5.1.1","Access Control","Access control policy established; least privilege enforced",
     None,["ac-1","ac-2","ac-6","ac-3"]),
    ("5.1.2","Access Control","User access is provisioned, reviewed, and revoked formally",
     None,["ac-2","ia-4","ps-4","ca-7"]),
    ("5.2.1","User Access","Unique user IDs for all users; shared accounts prohibited",
     None,["ia-2","ia-4","ac-2"]),
    ("5.2.2","User Access","Authentication controls enforce password policy",
     None,["ia-5","ia-2","ac-7"]),
    ("5.3.1","Privileged Access","Privileged access rights are restricted and monitored",
     None,["ac-6","ia-2","au-6"]),
    ("5.4.1","Remote Access","Remote access is secured and monitored",
     None,["ac-17","ia-2","sc-8","au-2"]),
    # 6. Cryptography
    ("6.1.1","Cryptography","Cryptographic controls policy covers key management and algorithms",
     None,["sc-12","sc-13","ia-7"]),
    ("6.1.2","Cryptography","Sensitive data in transit is encrypted",
     None,["sc-8","sc-12","ia-7"]),
    ("6.1.3","Cryptography","Sensitive data at rest is encrypted where required",
     None,["sc-28","mp-4","sc-12"]),
    # 7. Physical and Environmental Security
    ("7.1.1","Physical Security","Security perimeters protect areas with information assets",
     None,["pe-1","pe-2","pe-3"]),
    ("7.1.2","Physical Security","Physical access is controlled and logged",
     None,["pe-3","pe-6","pe-8"]),
    ("7.2.1","Prototype Protection","Prototype parts, vehicles, and data are physically protected",
     None,["pe-2","pe-3","mp-4","pe-20"]),
    ("7.3.1","Environmental Controls","Environmental threats (fire, flood, power) are mitigated",
     None,["pe-13","pe-14","pe-15","pe-11"]),
    # 8. Operations Security
    ("8.1.1","Operations","Operating procedures are documented and maintained",
     None,["cm-1","pm-1","sa-5"]),
    ("8.1.2","Operations","Capacity management ensures performance requirements are met",
     None,["sc-5","sc-6","cp-2"]),
    ("8.2.1","Malware Protection","Controls against malware are implemented",
     None,["si-3","si-4","si-8"]),
    ("8.3.1","Backup","Backups are taken and tested per backup policy",
     None,["cp-9","cp-10","cp-4"]),
    ("8.4.1","Logging and Monitoring","Events are logged and logs are protected",
     None,["au-2","au-3","au-9","au-12"]),
    ("8.4.2","Logging and Monitoring","Logs are reviewed and anomalies are investigated",
     None,["au-6","si-4","ir-4"]),
    ("8.7.1","Vulnerability Management","Technical vulnerabilities are identified and remediated",
     None,["ra-5","si-2","ca-7"]),
    # 9. Communications Security
    ("9.1.1","Network Security","Networks are managed and controlled to protect information",
     None,["sc-7","ca-3","cm-7"]),
    ("9.1.2","Network Segregation","Networks are segregated based on classification",
     None,["sc-7","ac-4","ca-3"]),
    ("9.2.1","Information Transfer","Policies and controls protect information transfers",
     None,["sc-8","mp-5","ac-4"]),
    # 10. Supplier Relationships
    ("10.1.1","Supplier Security","Information security requirements agreed with suppliers",
     None,["sa-9","sr-1","sr-3"]),
    ("10.1.2","Supplier Security","Supplier security and compliance is monitored",
     None,["sr-6","ca-7","sa-9"]),
    # 11. Incident Management
    ("11.1.1","Incident Management","Responsibilities and procedures for incident management defined",
     None,["ir-1","ir-8","ir-4"]),
    ("11.1.2","Incident Management","Information security events reported promptly",
     None,["ir-6","au-6","ir-5"]),
    ("11.1.3","Incident Management","Incidents assessed and responded to; lessons learned captured",
     None,["ir-4","ir-5","ca-7","pm-4"]),
    # 12. Business Continuity
    ("12.1.1","Business Continuity","Business continuity plans cover information security requirements",
     None,["cp-2","cp-10","ir-4"]),
    ("12.1.2","Business Continuity","BCPs are tested and updated",
     None,["cp-4","ca-2","cp-2"]),
    # 13. Compliance
    ("13.1.1","Compliance","Legal, regulatory, and contractual requirements are identified",
     None,["pm-9","ra-2","pm-1","sa-1"]),
    ("13.2.1","Compliance","Technical compliance is reviewed regularly",
     None,["ca-2","ca-7","ra-5"]),
    # Prototype / Third-Party Data (TISAX-specific)
    ("TP-1","Third-Party Data","Third-party data (customer IP, blueprints) is identified and protected",
     None,["ra-2","mp-4","ac-3","sc-28"]),
    ("TP-2","Third-Party Data","Access to third-party data is restricted to need-to-know",
     None,["ac-3","ac-6","pm-25"]),
]

# ── NAIC Model Cybersecurity Law ──────────────────────────────────────────────
NAIC_CONTROLS = [
    ("Sec4-A","Cybersecurity Program","Develop, implement, and maintain a comprehensive cybersecurity program",
     None,["pm-1","pl-2","ca-2","ca-7"]),
    ("Sec4-B(1)","Cybersecurity Program — Scope","Protect the security and confidentiality of nonpublic information",
     None,["sc-28","ac-3","pm-25","mp-4"]),
    ("Sec4-B(2)","Cybersecurity Program — Threats","Protect against anticipated threats to security of nonpublic information",
     None,["ra-3","pm-9","si-4","ir-4"]),
    ("Sec4-B(3)","Cybersecurity Program — Unauthorized Access","Protect against unauthorized access or use of nonpublic information",
     None,["ac-2","ia-2","sc-28","si-3"]),
    ("Sec4-C(1)","Risk Assessment","Conduct annual risk assessment of nonpublic information and information systems",
     None,["ra-1","ra-2","ra-3","pm-9"]),
    ("Sec4-C(2)","Risk Assessment — Criteria","Risk assessment addresses specific criteria (controls, access, encryption, training, etc.)",
     None,["ra-3","at-2","sc-28","ia-2","ca-7"]),
    ("Sec4-D","Third-Party Risk","Implement due diligence for third-party service providers",
     None,["sa-9","sr-1","sr-3","sr-6"]),
    ("Sec4-D(2)","Third-Party Contracts","Require service providers to implement cybersecurity program via contract",
     None,["sa-9","sr-1","sr-3"]),
    ("Sec4-E","Access Controls","Implement controls including MFA for authorized individuals",
     None,["ac-2","ac-3","ia-2","ac-6"]),
    ("Sec4-F","Encryption","Encrypt nonpublic information held or transmitted",
     None,["sc-8","sc-28","sc-12","ia-7"]),
    ("Sec4-G","Secure Development","Adopt secure development practices and procedures",
     None,["sa-3","sa-8","sa-11","sa-15"]),
    ("Sec4-H","Modification Management","Procedures to monitor and manage changes to systems",
     None,["cm-3","cm-4","ca-7"]),
    ("Sec4-I","Training","Train relevant employees on cybersecurity",
     None,["at-2","at-3","pm-13"]),
    ("Sec4-J","Incident Response","Establish an incident response plan",
     None,["ir-1","ir-4","ir-6","ir-8"]),
    ("Sec4-K","Security Testing","Conduct annual penetration testing and quarterly vulnerability scans",
     None,["ca-8","ra-5","ca-2","ca-7"]),
    ("Sec4-L","Audit Trails","Implement audit trails for detecting and responding to cybersecurity events",
     None,["au-2","au-3","au-6","au-9","au-12"]),
    ("Sec5","Cybersecurity Event Investigation","Investigate cybersecurity events that affect nonpublic information",
     None,["ir-4","ir-5","au-6","ra-3"]),
    ("Sec6-A","Breach Notification — Commissioner","Notify insurance commissioner within 72 hours of cybersecurity event",
     None,["ir-6","pm-15","ir-8"]),
    ("Sec6-B","Breach Notification — Individuals","Notify affected individuals per applicable breach notification laws",
     None,["ir-6","pm-15","ir-8"]),
    ("Sec6-C","Annual Certification","Annually certify compliance with the cybersecurity law",
     None,["pm-14","ca-2","pm-1"]),
    ("Sec6-D","CISO","Designate or designate equivalent executive with cybersecurity responsibility",
     None,["pm-2","pm-19"]),
]

FRAMEWORK_DATA = {
    "appi":        APPI_CONTROLS,
    "nerccip":     NERCCIP_CONTROLS,
    "tsapipeline": TSAPIPELINE_CONTROLS,
    "hitech":      HITECH_CONTROLS,
    "cfr11":       CFR11_CONTROLS,
    "soc1":        SOC1_CONTROLS,
    "tisax":       TISAX_CONTROLS,
    "naic":        NAIC_CONTROLS,
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
    print(f"Phase 3b — Seeded: {total_fw} frameworks | {total_ctrl} controls | {total_xwalk} crosswalk mappings")

    conn2 = sqlite3.connect(DB_PATH)
    cur2  = conn2.cursor()
    cur2.execute("""
        SELECT cf.short_name, COUNT(DISTINCT fc.id), COUNT(cx.id)
        FROM compliance_frameworks cf
        JOIN framework_controls fc ON fc.framework_id=cf.id
        JOIN control_crosswalks cx ON cx.framework_control_id=fc.id
        WHERE cf.short_name IN ('appi','nerccip','tsapipeline','hitech','cfr11','soc1','tisax','naic')
        GROUP BY cf.short_name ORDER BY cf.short_name
    """)
    print(f"\n{'framework':<14} {'controls':>9} {'crosswalks':>11}")
    print("-" * 36)
    for r in cur2.fetchall():
        print(f"  {r[0]:<12} {r[1]:>9} {r[2]:>11}")

    # Grand total
    cur2.execute("""
        SELECT COUNT(DISTINCT cf.id), COUNT(DISTINCT fc.id), COUNT(cx.id)
        FROM compliance_frameworks cf
        JOIN framework_controls fc ON fc.framework_id=cf.id
        JOIN control_crosswalks cx ON cx.framework_control_id=fc.id
    """)
    r = cur2.fetchone()
    print(f"\nGrand total — {r[0]} frameworks | {r[1]} framework controls | {r[2]} crosswalk mappings")
    conn2.close()


if __name__ == "__main__":
    main()
