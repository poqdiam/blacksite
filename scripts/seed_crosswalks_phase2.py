"""
seed_crosswalks_phase2.py
Adds 11 additional compliance frameworks with NIST SP 800-53r5 crosswalk data.

Frameworks:
  ssdf        — NIST SSDF v1.1 (SP 800-218)
  soc2        — SOC 2 Trust Services Criteria (AICPA 2017)
  pcidss      — PCI DSS 4.0
  nydfs500    — NYDFS 23 NYCRR Part 500 (2023 amendment)
  basel3      — Basel III Operational Risk / BCBS 239
  hipaa       — HIPAA Security Rule (45 CFR Part 164)
  fdamdcyber  — FDA Cybersecurity in Medical Devices (2023)
  fedramp     — FedRAMP Moderate Baseline (Rev 5)
  isa62443    — ISA/IEC 62443-3-3 (2013)
  fisma       — FISMA 2014
  gdpr        — GDPR (EU) 2016/679

Run: cd /home/graycat/projects/blacksite && .venv/bin/python3 scripts/seed_crosswalks_phase2.py
"""
import sqlite3, uuid
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "blacksite.db"

# ─────────────────────────────────────────────────────────────────────────────
# Framework metadata
# ─────────────────────────────────────────────────────────────────────────────
FRAMEWORKS = [
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "nist-ssdf-1.1")),
        "name":        "NIST SSDF v1.1",
        "short_name":  "ssdf",
        "version":     "1.1",
        "category":    "federal",
        "published_by":"NIST",
        "description": "Secure Software Development Framework (SP 800-218). Core practices for "
                       "integrating security into the software development lifecycle (SDLC).",
        "source_url":  "https://csrc.nist.gov/pubs/sp/800/218/final",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "aicpa-soc2-2017")),
        "name":        "SOC 2 (Trust Services Criteria)",
        "short_name":  "soc2",
        "version":     "2017",
        "category":    "industry",
        "published_by":"AICPA",
        "description": "AICPA Trust Services Criteria covering Security, Availability, Processing "
                       "Integrity, Confidentiality, and Privacy. Common for cloud service audits.",
        "source_url":  "https://www.aicpa.org/resources/article/aicpa-trust-services-criteria",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "pci-dss-4.0")),
        "name":        "PCI DSS 4.0",
        "short_name":  "pcidss",
        "version":     "4.0",
        "category":    "industry",
        "published_by":"PCI SSC",
        "description": "Payment Card Industry Data Security Standard v4.0. 12 requirements for "
                       "protecting cardholder data. Introduces customized approach.",
        "source_url":  "https://www.pcisecuritystandards.org/document_library/",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "nydfs-23-nycrr-500")),
        "name":        "NYDFS 23 NYCRR Part 500",
        "short_name":  "nydfs500",
        "version":     "2023 Amendment",
        "category":    "regulatory",
        "published_by":"NYDFS",
        "description": "New York State DFS cybersecurity regulation for covered entities. 2023 "
                       "amendment added enhanced requirements and expanded scope.",
        "source_url":  "https://www.dfs.ny.gov/industry_guidance/cybersecurity",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "bcbs-239-operational-risk")),
        "name":        "Basel III Operational Risk (BCBS 239)",
        "short_name":  "basel3",
        "version":     "2013/2019",
        "category":    "regulatory",
        "published_by":"BIS/BCBS",
        "description": "BIS principles for risk data aggregation, reporting, and operational "
                       "resilience for systemically important banks (G-SIBs and D-SIBs).",
        "source_url":  "https://www.bis.org/bcbs/publ/d239.htm",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "hipaa-security-rule-2003")),
        "name":        "HIPAA Security Rule",
        "short_name":  "hipaa",
        "version":     "45 CFR Part 164",
        "category":    "regulatory",
        "published_by":"HHS",
        "description": "Administrative, physical, and technical safeguards for electronic protected "
                       "health information (ePHI). Applies to covered entities and business associates.",
        "source_url":  "https://www.hhs.gov/hipaa/for-professionals/security/index.html",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "fda-cybersecurity-medical-devices-2023")),
        "name":        "FDA Cybersecurity — Medical Devices (2023)",
        "short_name":  "fdamdcyber",
        "version":     "2023",
        "category":    "regulatory",
        "published_by":"FDA",
        "description": "FDA final guidance on cybersecurity in medical devices: Quality System "
                       "Considerations and Content of Premarket Submissions (Sep 2023).",
        "source_url":  "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/"
                       "cybersecurity-medical-devices-quality-system-considerations-and-content-premarket-submissions",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "fedramp-moderate-rev5")),
        "name":        "FedRAMP Moderate Baseline",
        "short_name":  "fedramp",
        "version":     "Rev 5",
        "category":    "federal",
        "published_by":"GSA",
        "description": "Federal Risk and Authorization Management Program Moderate baseline (FIPS 199 "
                       "Moderate). Built on NIST SP 800-53r5 with FedRAMP-specific parameters.",
        "source_url":  "https://www.fedramp.gov/documents-templates/",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "isa-iec-62443-3-3-2013")),
        "name":        "ISA/IEC 62443-3-3",
        "short_name":  "isa62443",
        "version":     "2013",
        "category":    "industry",
        "published_by":"ISA/IEC",
        "description": "Security for industrial automation and control systems (IACS). Part 3-3 "
                       "system security requirements (SR) and security levels for OT environments.",
        "source_url":  "https://www.isa.org/standards-and-publications/isa-standards/"
                       "isa-iec-62443-series-of-standards",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "fisma-2014")),
        "name":        "FISMA 2014",
        "short_name":  "fisma",
        "version":     "2014",
        "category":    "federal",
        "published_by":"OMB/NIST",
        "description": "Federal Information Security Modernization Act. Requires federal agencies to "
                       "maintain information security programs aligned to NIST standards.",
        "source_url":  "https://csrc.nist.gov/topics/laws-and-regulations/laws/fisma",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "gdpr-2016-679")),
        "name":        "GDPR (EU) 2016/679",
        "short_name":  "gdpr",
        "version":     "2018",
        "category":    "regulatory",
        "published_by":"EU Parliament",
        "description": "General Data Protection Regulation governing personal data protection and "
                       "privacy in the EU. Articles 25 and 32 address technical/organizational measures.",
        "source_url":  "https://gdpr.eu/",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Source map (for control_crosswalks.source field)
# ─────────────────────────────────────────────────────────────────────────────
SOURCE_MAP = {
    "ssdf":       "nist_official",
    "soc2":       "community",
    "pcidss":     "community",
    "nydfs500":   "community",
    "basel3":     "community",
    "hipaa":      "nist_official",   # NIST 800-66r2 provides HIPAA → 800-53 crosswalk
    "fdamdcyber": "community",
    "fedramp":    "nist_official",
    "isa62443":   "community",
    "fisma":      "nist_official",
    "gdpr":       "community",
}

# ─────────────────────────────────────────────────────────────────────────────
# NIST SSDF v1.1 → NIST SP 800-53r5
# Source: NIST SP 800-218 Appendix B; NIST SSDF to SP 800-53r5 crosswalk
# Format: (ctrl_id, domain, title, level, [nist_800_53_ids])
# ─────────────────────────────────────────────────────────────────────────────
SSDF_CONTROLS = [
    # ── PO: Prepare the Organization ──────────────────────────────────────────
    ("PO.1.1", "Prepare the Organization",
     "Define security requirements for software development and establish policies",
     None, ["pm-1","pm-4","sa-1","sa-2","sa-3","sa-4","pl-8"]),
    ("PO.1.2", "Prepare the Organization",
     "Identify roles and responsibilities for software security",
     None, ["pm-2","pm-29","sa-1","sa-3","at-3"]),
    ("PO.1.3", "Prepare the Organization",
     "Communicate roles and responsibilities for software security throughout the org",
     None, ["pm-2","at-2","at-3"]),
    ("PO.2.1", "Prepare the Organization",
     "Implement criteria for secure coding into development policies",
     None, ["sa-1","sa-11","sa-15","cm-2"]),
    ("PO.2.2", "Prepare the Organization",
     "Implement secure coding standards and guidelines",
     None, ["sa-11","sa-15"]),
    ("PO.3.1", "Prepare the Organization",
     "Use well-secured software development environments",
     None, ["sa-3","sa-4","sa-8","cm-2","cm-6","cm-7"]),
    ("PO.3.2", "Prepare the Organization",
     "Provide secure development environment to developers",
     None, ["sa-3","sa-4","cm-6","sc-28"]),
    ("PO.3.3", "Prepare the Organization",
     "Configure tools to generate logs and other data for analysis",
     None, ["au-2","au-3","au-12","sa-15"]),
    ("PO.4.1", "Prepare the Organization",
     "Define and use criteria to determine whether code has unacceptable security vulnerabilities",
     None, ["sa-11","sa-15","ra-3","ra-5"]),
    ("PO.4.2", "Prepare the Organization",
     "Implement processes to receive vulnerability reports from external sources",
     None, ["si-5","ra-5","ir-6"]),
    ("PO.5.1", "Prepare the Organization",
     "Establish and maintain supporting processes for secure software development",
     None, ["sa-3","sa-8","pm-7","pl-8"]),
    ("PO.5.2", "Prepare the Organization",
     "Secure and harden development infrastructure",
     None, ["cm-2","cm-6","cm-7","sc-7","si-3","si-4"]),
    # ── PS: Protect the Software ──────────────────────────────────────────────
    ("PS.1.1", "Protect Software",
     "Maintain integrity of code throughout the SDLC",
     None, ["sa-10","sa-12","cm-3","cm-14","si-7"]),
    ("PS.2.1", "Protect Software",
     "Verify third-party software complies with security requirements",
     None, ["sa-4","sa-9","sa-12","sa-14","sr-3","sr-4","sr-6"]),
    ("PS.2.2", "Protect Software",
     "Assess the security of acquired software before use",
     None, ["sa-4","sa-9","sa-11","ra-3","sr-5","sr-6"]),
    ("PS.3.1", "Protect Software",
     "Archive and protect each software release",
     None, ["cm-3","sa-10","cp-9","mp-4","si-7"]),
    ("PS.3.2", "Protect Software",
     "Provide integrity verification mechanisms for released software",
     None, ["si-7","sa-10","cm-14"]),
    # ── PW: Produce Well-Secured Software ────────────────────────────────────
    ("PW.1.1", "Produce Well-Secured Software",
     "Use a consistent secure design process",
     None, ["sa-8","sa-15","pl-8","sr-2"]),
    ("PW.1.2", "Produce Well-Secured Software",
     "Design software to meet security and resiliency requirements",
     None, ["sa-8","sa-15","cp-2","sc-5","sc-7"]),
    ("PW.2.1", "Produce Well-Secured Software",
     "Follow all security requirements for development environment",
     None, ["sa-3","sa-4","sa-8","cm-6"]),
    ("PW.4.1", "Produce Well-Secured Software",
     "Use up-to-date and trusted third-party components",
     None, ["sa-12","sr-3","sr-4","sr-5","si-2"]),
    ("PW.4.2", "Produce Well-Secured Software",
     "Create and maintain a software bill of materials (SBOM)",
     None, ["sa-12","sr-3","sr-4","cm-8"]),
    ("PW.5.1", "Produce Well-Secured Software",
     "Eliminate or mitigate all security vulnerabilities before product release",
     None, ["sa-11","ra-3","ra-5","si-2"]),
    ("PW.6.1", "Produce Well-Secured Software",
     "Test executable code to identify vulnerabilities and verify remediation",
     None, ["sa-11","ca-2","ca-8","ra-5"]),
    ("PW.6.2", "Produce Well-Secured Software",
     "Configure the compilation/build process to improve executable security",
     None, ["sa-15","cm-6","cm-7"]),
    ("PW.7.1", "Produce Well-Secured Software",
     "Establish and follow coding practices that address security",
     None, ["sa-11","sa-15","cm-6"]),
    ("PW.7.2", "Produce Well-Secured Software",
     "Review code for security vulnerabilities using manual or automated methods",
     None, ["sa-11","ca-2","ca-7"]),
    ("PW.8.1", "Produce Well-Secured Software",
     "Perform security testing on software prior to release",
     None, ["sa-11","ca-2","ca-8","ra-5"]),
    ("PW.8.2", "Produce Well-Secured Software",
     "Conduct penetration testing on software prior to release",
     None, ["ca-8","sa-11","ra-5"]),
    ("PW.9.1", "Produce Well-Secured Software",
     "Configure default settings to be secure",
     None, ["cm-6","cm-7","sa-4","sa-8"]),
    ("PW.9.2", "Produce Well-Secured Software",
     "Evaluate security of software before adopting default settings",
     None, ["cm-6","sa-4","ra-3"]),
    # ── RV: Respond to Vulnerabilities ───────────────────────────────────────
    ("RV.1.1", "Respond to Vulnerabilities",
     "Establish and maintain a process for receiving vulnerability reports",
     None, ["si-5","ir-6","ra-5"]),
    ("RV.1.2", "Respond to Vulnerabilities",
     "Review reported vulnerabilities and investigate root causes",
     None, ["ra-3","ra-5","si-5","ca-7"]),
    ("RV.1.3", "Respond to Vulnerabilities",
     "Establish and follow processes for remediating vulnerabilities",
     None, ["si-2","ra-5","ca-7","pm-4"]),
    ("RV.2.1", "Respond to Vulnerabilities",
     "Analyze discovered vulnerabilities to understand risk",
     None, ["ra-3","ra-5","si-5"]),
    ("RV.2.2", "Respond to Vulnerabilities",
     "Develop and execute a plan to remediate vulnerabilities",
     None, ["si-2","ra-5","pm-4","ca-7"]),
    ("RV.3.1", "Respond to Vulnerabilities",
     "Analyze vulnerabilities to identify root causes",
     None, ["ca-7","ra-3","pm-4"]),
    ("RV.3.2", "Respond to Vulnerabilities",
     "Review software for similar vulnerabilities to remediated ones",
     None, ["sa-11","ca-7","si-2"]),
    ("RV.3.3", "Respond to Vulnerabilities",
     "Evaluate applicability of vulnerability reports from other sources",
     None, ["si-5","ra-5","ca-7"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# SOC 2 Trust Services Criteria → NIST SP 800-53r5
# Source: AICPA TSC 2017 + NIST 800-53r5 community crosswalk
# ─────────────────────────────────────────────────────────────────────────────
SOC2_CONTROLS = [
    # ── CC1: Control Environment ──────────────────────────────────────────────
    ("CC1.1", "Control Environment", "Commitment to integrity and ethical values",
     None, ["pm-1","at-2","pm-19"]),
    ("CC1.2", "Control Environment", "Board independence and oversight of internal controls",
     None, ["pm-2","pm-9","ca-5"]),
    ("CC1.3", "Control Environment", "Organizational structure, reporting lines, and authority",
     None, ["pm-2","pm-10","ps-2"]),
    ("CC1.4", "Control Environment", "Commitment to attract and retain competent personnel",
     None, ["ps-1","ps-2","ps-3","at-2","at-3"]),
    ("CC1.5", "Control Environment", "Accountability for internal control responsibilities",
     None, ["pm-2","pm-10","au-6","ca-7"]),
    # ── CC2: Communication ────────────────────────────────────────────────────
    ("CC2.1", "Communication", "Communicate relevant information internally to support control functions",
     None, ["pm-15","at-2","at-3","pl-4"]),
    ("CC2.2", "Communication", "Communicate with external parties about matters affecting controls",
     None, ["pm-15","sa-9","sr-1"]),
    ("CC2.3", "Communication", "Provide separate communication channels for reporting concerns",
     None, ["ir-6","pm-19","at-2"]),
    # ── CC3: Risk Assessment ──────────────────────────────────────────────────
    ("CC3.1", "Risk Assessment", "Specify objectives clearly to identify and assess associated risks",
     None, ["pm-9","ra-1","ra-2"]),
    ("CC3.2", "Risk Assessment", "Identify and analyze risks to the achievement of objectives",
     None, ["ra-3","pm-9","pm-16"]),
    ("CC3.3", "Risk Assessment", "Assess fraud risk",
     None, ["ra-3","pm-9","si-12"]),
    ("CC3.4", "Risk Assessment", "Identify and assess changes that could significantly impact controls",
     None, ["cm-3","ra-3","pm-9","ca-7"]),
    # ── CC4: Monitoring ───────────────────────────────────────────────────────
    ("CC4.1", "Monitoring", "Evaluate controls to ascertain effectiveness",
     None, ["ca-2","ca-7","au-6","pm-14"]),
    ("CC4.2", "Monitoring", "Evaluate and communicate deficiencies in a timely manner",
     None, ["ca-5","ca-7","ir-4","pm-14"]),
    # ── CC5: Control Activities ───────────────────────────────────────────────
    ("CC5.1", "Control Activities", "Select and develop control activities that mitigate risks",
     None, ["pm-9","pm-4","ca-2","sa-4"]),
    ("CC5.2", "Control Activities", "Select and develop general technology controls",
     None, ["cm-2","cm-6","cm-7","sa-8","sc-7"]),
    ("CC5.3", "Control Activities", "Deploy control activities through policies that specify expected behavior",
     None, ["pm-1","pl-4","at-2"]),
    # ── CC6: Logical and Physical Access ─────────────────────────────────────
    ("CC6.1", "Logical and Physical Access", "Implement logical access security measures",
     None, ["ac-1","ac-2","ac-3","ac-5","ac-6","ac-7","ia-1","ia-2","ia-5"]),
    ("CC6.2", "Logical and Physical Access", "Manage user provisioning and deprovisioning",
     None, ["ac-2","ia-2","ps-4","ps-5"]),
    ("CC6.3", "Logical and Physical Access", "Manage role-based access and least privilege",
     None, ["ac-2","ac-3","ac-5","ac-6","ac-16"]),
    ("CC6.4", "Logical and Physical Access", "Restrict physical access to sensitive assets",
     None, ["pe-1","pe-2","pe-3","pe-6","pe-8"]),
    ("CC6.5", "Logical and Physical Access", "Dispose of assets responsibly",
     None, ["mp-6","mp-7","pe-16"]),
    ("CC6.6", "Logical and Physical Access", "Manage logical access for external users and services",
     None, ["ac-17","ac-20","ia-3","sa-9","sc-7"]),
    ("CC6.7", "Logical and Physical Access", "Restrict data transmission to authorized parties",
     None, ["ac-4","sc-7","sc-8","sc-28","mp-4"]),
    ("CC6.8", "Logical and Physical Access", "Prevent unauthorized use of accounts and credentials",
     None, ["ac-7","ia-2","ia-5","ia-11","si-3"]),
    # ── CC7: System Operations ────────────────────────────────────────────────
    ("CC7.1", "System Operations", "Detect and monitor for configuration changes",
     None, ["cm-3","cm-8","si-7","au-2","au-12"]),
    ("CC7.2", "System Operations", "Monitor system components for anomalies",
     None, ["si-4","au-6","ir-5","ra-5"]),
    ("CC7.3", "System Operations", "Evaluate security events to determine if they constitute incidents",
     None, ["ir-4","ir-5","au-6","si-4"]),
    ("CC7.4", "System Operations", "Respond to identified security incidents",
     None, ["ir-1","ir-4","ir-5","ir-6","ir-8"]),
    ("CC7.5", "System Operations", "Restore the affected environment after incident",
     None, ["ir-4","cp-10","cp-12","si-13"]),
    # ── CC8: Change Management ────────────────────────────────────────────────
    ("CC8.1", "Change Management", "Authorize, design, develop, test, and deploy changes",
     None, ["cm-3","cm-4","cm-5","sa-10","sa-15"]),
    # ── CC9: Risk Mitigation ──────────────────────────────────────────────────
    ("CC9.1", "Risk Mitigation", "Identify and select risk mitigation strategies",
     None, ["ra-3","pm-9","pm-16","ca-5"]),
    ("CC9.2", "Risk Mitigation", "Assess and manage vendor and business partner risk",
     None, ["sa-9","sr-1","sr-3","sr-6","pm-9"]),
    # ── A1: Availability ─────────────────────────────────────────────────────
    ("A1.1", "Availability", "Maintain sufficient capacity to meet availability commitments",
     None, ["cp-2","cp-8","sc-5","sc-6","pe-11"]),
    ("A1.2", "Availability", "Restore systems to meet availability commitments after disruption",
     None, ["cp-2","cp-10","cp-9","ir-4","si-13"]),
    ("A1.3", "Availability", "Test recovery procedures to meet availability commitments",
     None, ["cp-4","cp-10","ca-2"]),
    # ── C1: Confidentiality ───────────────────────────────────────────────────
    ("C1.1", "Confidentiality", "Identify and maintain confidential information per policy",
     None, ["mp-4","sc-28","ac-16","ra-2"]),
    ("C1.2", "Confidentiality", "Dispose of confidential information per policy",
     None, ["mp-6","mp-7","sc-28","si-12"]),
    # ── PI1: Processing Integrity ─────────────────────────────────────────────
    ("PI1.1", "Processing Integrity", "Obtain information to initiate transactions",
     None, ["si-10","si-12","au-3"]),
    ("PI1.2", "Processing Integrity", "Implement controls to prevent errors during processing",
     None, ["si-10","au-3","cm-3"]),
    ("PI1.3", "Processing Integrity", "Store and maintain inputs, items being processed, and outputs",
     None, ["au-3","si-12","mp-4","cp-9"]),
    ("PI1.4", "Processing Integrity", "Address errors or omissions during processing",
     None, ["si-10","ir-4","au-6"]),
    ("PI1.5", "Processing Integrity", "Deliver outputs completely and accurately",
     None, ["si-10","si-12","sc-8"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# PCI DSS 4.0 → NIST SP 800-53r5
# Source: PCI SSC v4.0 (March 2022); NIST 800-53r5 community crosswalk
# ─────────────────────────────────────────────────────────────────────────────
PCIDSS_CONTROLS = [
    # ── Req 1: Network Security Controls ─────────────────────────────────────
    ("1.1", "Network Security Controls", "Processes and mechanisms for network security are defined",
     None, ["sc-7","ca-3","pl-2"]),
    ("1.2", "Network Security Controls", "Network security controls (NSCs) are configured and maintained",
     None, ["sc-7","cm-6","cm-7","ca-3"]),
    ("1.3", "Network Security Controls", "Network access to/from cardholder data environment is restricted",
     None, ["sc-7","ac-4","ac-17","ca-3"]),
    ("1.4", "Network Security Controls", "Network connections between trusted and untrusted networks controlled",
     None, ["sc-7","ca-3","ac-4","cm-7"]),
    ("1.5", "Network Security Controls", "Risks from computing devices on untrusted networks are mitigated",
     None, ["sc-7","ac-17","ac-20","ia-3"]),
    # ── Req 2: Secure Configurations ─────────────────────────────────────────
    ("2.1", "Secure Configurations", "Processes for managing secure configurations are defined",
     None, ["cm-1","cm-2","cm-6","sa-4"]),
    ("2.2", "Secure Configurations", "System components are configured and managed securely",
     None, ["cm-6","cm-7","sa-4","sa-9"]),
    ("2.3", "Secure Configurations", "Wireless environments are configured and managed securely",
     None, ["cm-6","sc-40","ia-3"]),
    # ── Req 3: Protect Stored Account Data ───────────────────────────────────
    ("3.1", "Protect Stored Account Data", "Processes for protecting stored account data are defined",
     None, ["sc-28","mp-4","ra-2"]),
    ("3.2", "Protect Stored Account Data", "Storage of account data is kept to a minimum",
     None, ["mp-6","si-12","sc-28"]),
    ("3.3", "Protect Stored Account Data", "Sensitive authentication data (SAD) is not retained",
     None, ["sc-28","mp-6","mp-7"]),
    ("3.4", "Protect Stored Account Data", "Access to stored account data is controlled",
     None, ["ac-3","ac-6","mp-4","sc-28"]),
    ("3.5", "Protect Stored Account Data", "Primary account number (PAN) is secured wherever stored",
     None, ["sc-28","mp-4","ac-3"]),
    ("3.6", "Protect Stored Account Data", "Cryptographic keys are secured",
     None, ["sc-12","sc-28","mp-4"]),
    ("3.7", "Protect Stored Account Data", "Cryptographic key management policies are implemented",
     None, ["sc-12","sc-28","sa-4"]),
    # ── Req 4: Protect Cardholder Data in Transit ─────────────────────────────
    ("4.1", "Protect Data in Transit", "Processes for protecting cardholder data in transit defined",
     None, ["sc-8","sc-28","ia-1"]),
    ("4.2", "Protect Data in Transit", "PAN is protected during transmission over open networks",
     None, ["sc-8","sc-23","ia-3"]),
    # ── Req 5: Protect Against Malicious Software ────────────────────────────
    ("5.1", "Protect Against Malware", "Processes for protecting against malware are defined",
     None, ["si-3","si-8","pm-1"]),
    ("5.2", "Protect Against Malware", "Malware is prevented and detected",
     None, ["si-3","si-4","si-8"]),
    ("5.3", "Protect Against Malware", "Anti-malware mechanisms are active and maintained",
     None, ["si-3","cm-6","si-2"]),
    ("5.4", "Protect Against Malware", "Anti-phishing mechanisms protect users",
     None, ["si-3","si-8","at-2"]),
    # ── Req 6: Develop and Maintain Secure Systems ────────────────────────────
    ("6.1", "Develop Secure Systems", "Processes for developing and maintaining secure systems defined",
     None, ["sa-3","sa-4","sa-8","sa-15"]),
    ("6.2", "Develop Secure Systems", "Bespoke and custom software are developed securely",
     None, ["sa-11","sa-15","cm-6"]),
    ("6.3", "Develop Secure Systems", "Security vulnerabilities are identified and addressed",
     None, ["ra-5","si-2","si-5","sa-11"]),
    ("6.4", "Develop Secure Systems", "Public-facing web applications are protected",
     None, ["si-10","sc-7","sc-23","sa-11"]),
    ("6.5", "Develop Secure Systems", "Changes are managed and documented",
     None, ["cm-3","cm-4","cm-5","sa-10"]),
    # ── Req 7: Restrict Access by Business Need ───────────────────────────────
    ("7.1", "Restrict Access", "Processes for restricting access to system components defined",
     None, ["ac-1","ac-2","ac-3","pm-1"]),
    ("7.2", "Restrict Access", "Access to system components is appropriately defined and assigned",
     None, ["ac-2","ac-3","ac-5","ac-6","ac-16"]),
    ("7.3", "Restrict Access", "Access is managed via an access control system",
     None, ["ac-2","ac-3","ia-2","ac-16"]),
    # ── Req 8: Identify Users and Authenticate ───────────────────────────────
    ("8.1", "Identify and Authenticate", "Processes for identifying and authenticating users defined",
     None, ["ia-1","ia-2","ia-5","pm-1"]),
    ("8.2", "Identify and Authenticate", "All users are assigned a unique ID",
     None, ["ia-2","ac-2","ia-5"]),
    ("8.3", "Identify and Authenticate", "User authentication is managed",
     None, ["ia-5","ia-2","ia-11","ac-7"]),
    ("8.4", "Identify and Authenticate", "Multi-factor authentication is implemented",
     None, ["ia-2","ia-2.1","ia-2.2"]),
    ("8.5", "Identify and Authenticate", "Multi-factor authentication systems are not susceptible to replay attacks",
     None, ["ia-2","ia-8","sc-23"]),
    ("8.6", "Identify and Authenticate", "System/app accounts and related auth mechanisms are managed",
     None, ["ia-2","ia-5","ac-2","cm-6"]),
    # ── Req 9: Restrict Physical Access ──────────────────────────────────────
    ("9.1", "Restrict Physical Access", "Processes for restricting physical access defined",
     None, ["pe-1","pe-2","pe-3"]),
    ("9.2", "Restrict Physical Access", "Physical access controls manage entry into facilities",
     None, ["pe-2","pe-3","pe-6"]),
    ("9.3", "Restrict Physical Access", "Physical access for personnel is authorized and managed",
     None, ["pe-2","pe-3","ps-4","ps-5"]),
    ("9.4", "Restrict Physical Access", "Physical access to cardholder data areas restricted",
     None, ["pe-2","pe-3","pe-6","pe-8"]),
    ("9.5", "Restrict Physical Access", "Point of interaction devices are protected",
     None, ["pe-3","cm-8","pe-20"]),
    # ── Req 10: Log and Monitor All Access ───────────────────────────────────
    ("10.1", "Log and Monitor Access", "Logging and monitoring processes defined",
     None, ["au-1","au-2","au-12","pm-1"]),
    ("10.2", "Log and Monitor Access", "Audit logs capture all individual access to system components",
     None, ["au-2","au-3","au-12"]),
    ("10.3", "Log and Monitor Access", "Audit logs are protected from destruction and unauthorized modifications",
     None, ["au-9","au-3","si-7"]),
    ("10.4", "Log and Monitor Access", "Audit logs are reviewed to identify anomalies",
     None, ["au-6","si-4","ir-5"]),
    ("10.5", "Log and Monitor Access", "Audit log history is retained",
     None, ["au-11","au-3","si-12"]),
    ("10.6", "Log and Monitor Access", "Time synchronization mechanisms support consistent audit logs",
     None, ["au-8","sc-45"]),
    ("10.7", "Log and Monitor Access", "Failures of critical security controls are detected and responded to",
     None, ["si-4","ir-4","au-6"]),
    # ── Req 11: Test Security ─────────────────────────────────────────────────
    ("11.1", "Test Security", "Processes for testing security of systems and networks defined",
     None, ["ca-2","ca-8","ra-5","pm-1"]),
    ("11.2", "Test Security", "Wireless access points are managed",
     None, ["ca-7","sc-40","cm-8"]),
    ("11.3", "Test Security", "External and internal vulnerabilities are regularly identified and addressed",
     None, ["ra-5","ca-2","ca-8","si-2"]),
    ("11.4", "Test Security", "External and internal penetration testing is performed",
     None, ["ca-8","ra-5","si-6"]),
    ("11.5", "Test Security", "Network intrusions and unexpected file changes are detected and responded to",
     None, ["si-4","si-7","ir-4"]),
    ("11.6", "Test Security", "Unauthorized changes on payment pages are detected and responded to",
     None, ["si-4","si-7","ca-7"]),
    # ── Req 12: Security Policy ───────────────────────────────────────────────
    ("12.1", "Security Policy", "Comprehensive information security policy exists",
     None, ["pm-1","pl-4","at-2"]),
    ("12.2", "Security Policy", "Acceptable use policies are implemented",
     None, ["pl-4","at-2","ac-8"]),
    ("12.3", "Security Policy", "Risks to the CDE are formally identified, evaluated, and managed",
     None, ["ra-3","pm-9","ca-5"]),
    ("12.4", "Security Policy", "PCI DSS compliance is managed",
     None, ["ca-2","ca-7","pm-14"]),
    ("12.5", "Security Policy", "PCI DSS scope is documented and validated",
     None, ["pm-9","ca-2","cm-8","ra-2"]),
    ("12.6", "Security Policy", "Security awareness education is ongoing",
     None, ["at-2","at-3","pm-13"]),
    ("12.7", "Security Policy", "Personnel are screened prior to hire",
     None, ["ps-3","ps-2"]),
    ("12.8", "Security Policy", "Third-party service provider risk is managed",
     None, ["sa-9","sr-1","sr-3","sr-6"]),
    ("12.9", "Security Policy", "TPSPs acknowledge their responsibilities for security",
     None, ["sa-9","sr-1","sr-6"]),
    ("12.10", "Security Policy", "Suspected or confirmed security incidents are responded to immediately",
     None, ["ir-1","ir-4","ir-6","ir-8"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# NYDFS 23 NYCRR Part 500 → NIST SP 800-53r5
# Source: NYDFS Part 500 (2023 amendment); NIST community crosswalk
# ─────────────────────────────────────────────────────────────────────────────
NYDFS500_CONTROLS = [
    ("500.02", "Cybersecurity Program", "Establish and maintain a cybersecurity program",
     None, ["pm-1","pl-2","ca-2","ca-7"]),
    ("500.03", "Cybersecurity Policy", "Implement cybersecurity policies based on risk assessment",
     None, ["pm-1","pl-2","ra-2","ra-3"]),
    ("500.04", "CISO", "Designate a qualified CISO responsible for cybersecurity program",
     None, ["pm-2","pm-19"]),
    ("500.05", "Penetration Testing", "Annual penetration testing and vulnerability assessments",
     None, ["ca-8","ra-5","ca-2","si-2"]),
    ("500.06", "Audit Trail", "Maintain audit trail systems sufficient to detect and respond to incidents",
     None, ["au-2","au-3","au-6","au-9","au-11","au-12"]),
    ("500.07", "Access Privileges", "Implement access privilege and MFA policies",
     None, ["ac-2","ac-3","ac-5","ac-6","ia-2","ia-5"]),
    ("500.08", "Application Security", "Implement written application security procedures",
     None, ["sa-4","sa-11","sa-15","cm-6"]),
    ("500.09", "Risk Assessment", "Conduct periodic risk assessments",
     None, ["ra-1","ra-2","ra-3","ra-5","pm-9"]),
    ("500.10", "Cybersecurity Personnel", "Employ qualified cybersecurity personnel",
     None, ["at-3","pm-2","ps-3","pm-13"]),
    ("500.11", "Third Party Service Providers", "Manage security of third-party vendors",
     None, ["sa-9","sr-1","sr-3","sr-6","pm-9"]),
    ("500.12", "Multi-Factor Authentication", "Implement MFA for access to internal systems",
     None, ["ia-2","ia-2.1","ia-2.2","ia-2.6"]),
    ("500.13", "Limitations on Data Retention", "Data retention limits and secure disposal",
     None, ["si-12","mp-6","mp-7","sc-28"]),
    ("500.14", "Training and Monitoring", "Security awareness and training program",
     None, ["at-2","at-3","pm-13","au-6"]),
    ("500.15", "Encryption of Nonpublic Information", "Encrypt nonpublic information in transit and at rest",
     None, ["sc-8","sc-28","sc-12","ia-7"]),
    ("500.16", "Incident Response Plan", "Establish and maintain a written incident response plan",
     None, ["ir-1","ir-4","ir-6","ir-8","cp-2"]),
    ("500.17", "Notices to Superintendent", "Notify NYDFS of material cybersecurity events within 72 hours",
     None, ["ir-6","pm-15","ir-7"]),
    ("500.18", "Confidentiality", "Certify compliance annually",
     None, ["pm-14","ca-2","pm-1"]),
    ("500.19", "Exemptions", "Reduced requirements for smaller entities",
     None, ["pm-1","ra-3"]),
    ("500.20", "Enforcement", "Enforcement provisions",
     None, ["pm-1","ca-2"]),
    ("500.21", "Effective Date", "Transitional requirements and timelines",
     None, ["pm-1"]),
    ("500.22", "Endpoint Detection and Response", "Implement EDR and security event alerting",
     None, ["si-3","si-4","au-6","ir-4"]),
    ("500.23", "Backup and Recovery", "Maintain secure isolated backups and test recovery",
     None, ["cp-9","cp-10","cp-4","si-12"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# Basel III Operational Risk (BCBS 239) → NIST SP 800-53r5
# Source: BCBS 239 (2013), BCBS operational resilience (2021), community crosswalk
# ─────────────────────────────────────────────────────────────────────────────
BASEL3_CONTROLS = [
    ("BCBS-P1", "Governance", "Board and senior management oversight of risk data aggregation",
     None, ["pm-2","pm-9","pm-10","ca-7"]),
    ("BCBS-P2", "Data Architecture", "Maintain strong data architecture and IT infrastructure",
     None, ["cm-2","cm-6","pm-7","pl-8","sa-8"]),
    ("BCBS-P3", "Accuracy and Integrity", "Ensure accuracy and integrity of aggregated risk data",
     None, ["si-7","au-3","si-10","cm-3"]),
    ("BCBS-P4", "Completeness", "Capture and aggregate all material risk data",
     None, ["au-3","si-12","cm-8","pm-11"]),
    ("BCBS-P5", "Timeliness", "Generate accurate risk data reports in a timely manner",
     None, ["au-6","pm-6","si-4"]),
    ("BCBS-P6", "Adaptability", "Generate risk data to meet ad-hoc reporting requests",
     None, ["pm-6","pm-11","cp-2"]),
    ("BCBS-P7", "Accuracy (reporting)", "Risk management reports reflect aggregated data accurately",
     None, ["au-3","si-10","au-6"]),
    ("BCBS-P8", "Comprehensiveness", "Reports cover all material risk areas",
     None, ["pm-9","pm-11","ra-3"]),
    ("BCBS-P9", "Clarity and Usefulness", "Reports communicate information clearly",
     None, ["pm-6","au-6","pm-9"]),
    ("BCBS-P10", "Frequency", "Reports are produced at appropriate frequency",
     None, ["au-6","pm-6","ca-7"]),
    ("BCBS-P11", "Distribution", "Reports distributed to appropriate recipients",
     None, ["pm-10","ac-16","mp-4"]),
    ("BCBS-RES1", "Operational Resilience", "Map critical operations and dependencies",
     None, ["cp-2","pm-11","sa-14","pl-8"]),
    ("BCBS-RES2", "Operational Resilience", "Define operational resilience tolerances",
     None, ["cp-2","pm-9","ra-3","si-13"]),
    ("BCBS-RES3", "Operational Resilience", "Test ability to operate within resilience tolerances",
     None, ["cp-4","ca-2","ca-7","si-13"]),
    ("BCBS-RES4", "Operational Resilience", "Maintain a recovery and continuity plan for critical operations",
     None, ["cp-2","cp-9","cp-10","ir-4"]),
    ("BCBS-TRM1", "Technology Risk", "Manage technology risk including cyber risk",
     None, ["ra-3","pm-9","si-4","ca-7"]),
    ("BCBS-TRM2", "Technology Risk", "Establish sound cybersecurity practices",
     None, ["pm-1","sc-7","ia-2","ac-2","si-3"]),
    ("BCBS-TRM3", "Technology Risk", "Manage third-party and outsourcing technology risk",
     None, ["sa-9","sr-1","sr-3","sr-6"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# HIPAA Security Rule → NIST SP 800-53r5
# Source: NIST SP 800-66r2 (HIPAA Security Rule Guide) — official HHS/NIST crosswalk
# ─────────────────────────────────────────────────────────────────────────────
HIPAA_CONTROLS = [
    # ── Administrative Safeguards (164.308) ───────────────────────────────────
    ("164.308(a)(1)(i)", "Administrative Safeguards",
     "Risk analysis — conduct accurate/thorough risk assessment of ePHI",
     None, ["ra-3","ra-2","ra-5","pm-9"]),
    ("164.308(a)(1)(ii)(B)", "Administrative Safeguards",
     "Risk management — implement security measures to reduce identified risks",
     None, ["pm-4","ca-5","ra-3","si-2"]),
    ("164.308(a)(1)(ii)(C)", "Administrative Safeguards",
     "Sanction policy — apply appropriate sanctions for workforce violations",
     None, ["ps-8","pm-9","pl-4"]),
    ("164.308(a)(1)(ii)(D)", "Administrative Safeguards",
     "Information system activity review — review activity logs",
     None, ["au-6","ca-7","si-4"]),
    ("164.308(a)(2)", "Administrative Safeguards",
     "Assigned security responsibility — designate security official",
     None, ["pm-2","pm-19"]),
    ("164.308(a)(3)(i)", "Administrative Safeguards",
     "Authorization/supervision of workforce access to ePHI",
     None, ["ps-2","ac-2","ia-2"]),
    ("164.308(a)(3)(ii)(A)", "Administrative Safeguards",
     "Workforce clearance procedure",
     None, ["ps-3","ps-2","ac-2"]),
    ("164.308(a)(3)(ii)(B)", "Administrative Safeguards",
     "Termination procedures — revoke access upon workforce termination",
     None, ["ps-4","ps-5","ac-2"]),
    ("164.308(a)(4)(i)", "Administrative Safeguards",
     "Information access management — policies for authorizing access",
     None, ["ac-1","ac-2","ac-3","ac-16"]),
    ("164.308(a)(4)(ii)(A)", "Administrative Safeguards",
     "Isolating healthcare clearinghouse function",
     None, ["sc-3","ac-3","ca-3"]),
    ("164.308(a)(4)(ii)(B)", "Administrative Safeguards",
     "Access authorization — establish policies for granting access",
     None, ["ac-2","ac-3","ia-5"]),
    ("164.308(a)(4)(ii)(C)", "Administrative Safeguards",
     "Access establishment and modification — routine access reviews",
     None, ["ac-2","ia-5","ac-6"]),
    ("164.308(a)(5)(i)", "Administrative Safeguards",
     "Security awareness and training program",
     None, ["at-2","at-3","pm-13"]),
    ("164.308(a)(5)(ii)(A)", "Administrative Safeguards",
     "Security reminders",
     None, ["at-2","pl-4"]),
    ("164.308(a)(5)(ii)(B)", "Administrative Safeguards",
     "Protection from malicious software",
     None, ["si-3","si-4","si-8"]),
    ("164.308(a)(5)(ii)(C)", "Administrative Safeguards",
     "Log-in monitoring",
     None, ["ac-7","au-6","ia-2"]),
    ("164.308(a)(5)(ii)(D)", "Administrative Safeguards",
     "Password management",
     None, ["ia-5","ia-11","ac-7"]),
    ("164.308(a)(6)(i)", "Administrative Safeguards",
     "Security incident procedures — identify and respond to suspected incidents",
     None, ["ir-1","ir-4","ir-6"]),
    ("164.308(a)(6)(ii)", "Administrative Safeguards",
     "Response and reporting — mitigate effects of incidents",
     None, ["ir-4","ir-5","ir-6","ir-8"]),
    ("164.308(a)(7)(i)", "Administrative Safeguards",
     "Contingency plan — establish policies to respond to emergencies",
     None, ["cp-1","cp-2","cp-9","cp-10"]),
    ("164.308(a)(7)(ii)(A)", "Administrative Safeguards",
     "Data backup plan",
     None, ["cp-9","cp-6","mp-4"]),
    ("164.308(a)(7)(ii)(B)", "Administrative Safeguards",
     "Disaster recovery plan",
     None, ["cp-2","cp-10","ir-4"]),
    ("164.308(a)(7)(ii)(C)", "Administrative Safeguards",
     "Emergency mode operation plan",
     None, ["cp-2","cp-10","cp-12"]),
    ("164.308(a)(7)(ii)(D)", "Administrative Safeguards",
     "Testing and revision procedures — test contingency plans",
     None, ["cp-4","ca-2"]),
    ("164.308(a)(7)(ii)(E)", "Administrative Safeguards",
     "Applications and data criticality analysis",
     None, ["cp-2","ra-3","sa-14"]),
    ("164.308(a)(8)", "Administrative Safeguards",
     "Evaluation — perform periodic technical and nontechnical evaluation",
     None, ["ca-2","ca-7","pm-14"]),
    ("164.308(b)(1)", "Administrative Safeguards",
     "Business associate contracts — obtain satisfactory assurances",
     None, ["sa-9","sr-1","sr-3"]),
    # ── Physical Safeguards (164.310) ─────────────────────────────────────────
    ("164.310(a)(1)", "Physical Safeguards",
     "Facility access controls — limit physical access to ePHI systems",
     None, ["pe-1","pe-2","pe-3","pe-6"]),
    ("164.310(a)(2)(i)", "Physical Safeguards",
     "Contingency operations — procedures for physical access during emergencies",
     None, ["cp-2","pe-2","pe-10"]),
    ("164.310(a)(2)(ii)", "Physical Safeguards",
     "Facility security plan — safeguard facility and equipment",
     None, ["pe-1","pe-2","pe-3"]),
    ("164.310(a)(2)(iii)", "Physical Safeguards",
     "Access control and validation — validate personnel access",
     None, ["pe-2","pe-3","ia-2","ps-4"]),
    ("164.310(a)(2)(iv)", "Physical Safeguards",
     "Maintenance records — document repairs and modifications to physical components",
     None, ["ma-2","pe-3","cm-3"]),
    ("164.310(b)", "Physical Safeguards",
     "Workstation use — specify proper workstation functions",
     None, ["ac-8","cm-6","cm-7"]),
    ("164.310(c)", "Physical Safeguards",
     "Workstation security — implement safeguards for workstations",
     None, ["pe-3","ac-19","cm-6"]),
    ("164.310(d)(1)", "Physical Safeguards",
     "Device and media controls — policies for hardware/electronic media",
     None, ["mp-1","mp-4","mp-6","mp-7","pe-16"]),
    # ── Technical Safeguards (164.312) ────────────────────────────────────────
    ("164.312(a)(1)", "Technical Safeguards",
     "Access control — unique user identification and emergency access procedure",
     None, ["ac-1","ac-2","ac-3","ia-2","ia-5"]),
    ("164.312(a)(2)(i)", "Technical Safeguards",
     "Unique user identification",
     None, ["ia-2","ac-2"]),
    ("164.312(a)(2)(ii)", "Technical Safeguards",
     "Emergency access procedure",
     None, ["ia-2","cp-2","pe-2"]),
    ("164.312(a)(2)(iii)", "Technical Safeguards",
     "Automatic logoff",
     None, ["ac-11","ac-12"]),
    ("164.312(a)(2)(iv)", "Technical Safeguards",
     "Encryption and decryption of ePHI",
     None, ["sc-28","sc-12","ia-7"]),
    ("164.312(b)", "Technical Safeguards",
     "Audit controls — hardware, software, and procedural mechanisms for audit",
     None, ["au-2","au-3","au-6","au-9","au-12"]),
    ("164.312(c)(1)", "Technical Safeguards",
     "Integrity — protect ePHI from improper alteration or destruction",
     None, ["si-7","au-3","sc-28"]),
    ("164.312(c)(2)", "Technical Safeguards",
     "Authentication mechanism to corroborate ePHI has not been altered",
     None, ["si-7","ia-3","sc-8"]),
    ("164.312(d)", "Technical Safeguards",
     "Person or entity authentication — verify person accessing ePHI is who they claim",
     None, ["ia-2","ia-3","ia-5","ia-8"]),
    ("164.312(e)(1)", "Technical Safeguards",
     "Transmission security — guard against unauthorized access during transmission",
     None, ["sc-8","sc-23","ia-7"]),
    ("164.312(e)(2)(i)", "Technical Safeguards",
     "Integrity controls for ePHI in transit",
     None, ["sc-8","si-7"]),
    ("164.312(e)(2)(ii)", "Technical Safeguards",
     "Encryption for ePHI in transit",
     None, ["sc-8","sc-12","ia-7"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# FDA Cybersecurity in Medical Devices (2023) → NIST SP 800-53r5
# Source: FDA Final Guidance Sep 2023; NIST 800-53r5 community crosswalk
# ─────────────────────────────────────────────────────────────────────────────
FDAMDCYBER_CONTROLS = [
    ("FDA-DG-1", "Device Design and Architecture",
     "Incorporate cybersecurity requirements into device design",
     None, ["sa-3","sa-4","sa-8","pl-8","sr-2"]),
    ("FDA-DG-2", "Device Design and Architecture",
     "Perform threat modeling as part of device design",
     None, ["ra-3","sa-11","pm-28","pl-8"]),
    ("FDA-DG-3", "Device Design and Architecture",
     "Apply security by design principles (least functionality, defense in depth)",
     None, ["cm-7","sa-8","sc-3","sc-7","sc-29"]),
    ("FDA-DG-4", "Device Design and Architecture",
     "Define authentication and authorization controls for device access",
     None, ["ia-2","ia-3","ia-5","ac-1","ac-2","ac-3"]),
    ("FDA-DG-5", "Device Design and Architecture",
     "Implement cryptographic controls for data protection",
     None, ["sc-8","sc-12","sc-28","ia-7"]),
    ("FDA-DG-6", "Device Design and Architecture",
     "Secure device communication interfaces and network connections",
     None, ["sc-7","sc-23","ca-3","ac-4"]),
    ("FDA-SBOM-1", "Software Bill of Materials",
     "Develop and maintain a Software Bill of Materials (SBOM) for the device",
     None, ["sr-4","sa-12","cm-8","sr-3"]),
    ("FDA-SBOM-2", "Software Bill of Materials",
     "Include all software components, versions, and licensing in SBOM",
     None, ["cm-8","sr-4","sa-12"]),
    ("FDA-VM-1", "Vulnerability Management",
     "Establish a coordinated vulnerability disclosure policy",
     None, ["si-5","ra-5","ir-6","pm-15"]),
    ("FDA-VM-2", "Vulnerability Management",
     "Implement timely patching and software update mechanisms",
     None, ["si-2","cm-3","sa-10","sa-11"]),
    ("FDA-VM-3", "Vulnerability Management",
     "Monitor for known and newly discovered vulnerabilities throughout device lifecycle",
     None, ["ra-5","si-5","ca-7","si-2"]),
    ("FDA-QS-1", "Quality System",
     "Establish device cybersecurity controls within Quality System (QS) procedures",
     None, ["sa-3","sa-4","pm-1","cm-3"]),
    ("FDA-QS-2", "Quality System",
     "Include cybersecurity risk management in design controls",
     None, ["ra-3","sa-11","ca-2","pm-9"]),
    ("FDA-QS-3", "Quality System",
     "Document cybersecurity testing and verification results",
     None, ["sa-11","ca-2","ca-8","au-3"]),
    ("FDA-MON-1", "Monitoring",
     "Implement device security monitoring and anomaly detection capabilities",
     None, ["si-4","au-2","au-6","ir-5"]),
    ("FDA-MON-2", "Monitoring",
     "Capture and protect device security logs",
     None, ["au-2","au-3","au-9","au-12"]),
    ("FDA-IR-1", "Incident Response",
     "Develop and maintain an incident response plan for cybersecurity events",
     None, ["ir-1","ir-4","ir-6","ir-8"]),
    ("FDA-IR-2", "Incident Response",
     "Report cybersecurity incidents to FDA and customers per applicable requirements",
     None, ["ir-6","pm-15","si-5"]),
    ("FDA-LIFE-1", "Lifecycle Security",
     "Define end-of-life security support policy for devices",
     None, ["sa-3","sa-22","cm-8","pm-30"]),
    ("FDA-LIFE-2", "Lifecycle Security",
     "Provide continued security updates throughout supported device lifecycle",
     None, ["si-2","cm-3","sa-10","sa-22"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# FedRAMP Moderate Baseline → NIST SP 800-53r5
# FedRAMP controls ARE NIST 800-53 controls; framework control IDs use FedRAMP
# naming convention. Crosswalk is 1:1 to corresponding NIST 800-53r5 control.
# Source: GSA FedRAMP Moderate Baseline (Rev 5, 2023)
# ─────────────────────────────────────────────────────────────────────────────
FEDRAMP_CONTROLS = [
    # ── Access Control (AC) ───────────────────────────────────────────────────
    ("FR-AC-1",  "Access Control", "Access Control Policy and Procedures", None, ["ac-1"]),
    ("FR-AC-2",  "Access Control", "Account Management", None, ["ac-2"]),
    ("FR-AC-3",  "Access Control", "Access Enforcement", None, ["ac-3"]),
    ("FR-AC-4",  "Access Control", "Information Flow Enforcement", None, ["ac-4"]),
    ("FR-AC-5",  "Access Control", "Separation of Duties", None, ["ac-5"]),
    ("FR-AC-6",  "Access Control", "Least Privilege", None, ["ac-6"]),
    ("FR-AC-7",  "Access Control", "Unsuccessful Logon Attempts", None, ["ac-7"]),
    ("FR-AC-8",  "Access Control", "System Use Notification", None, ["ac-8"]),
    ("FR-AC-11", "Access Control", "Session Lock", None, ["ac-11"]),
    ("FR-AC-12", "Access Control", "Session Termination", None, ["ac-12"]),
    ("FR-AC-14", "Access Control", "Permitted Actions without Identification or Authentication", None, ["ac-14"]),
    ("FR-AC-17", "Access Control", "Remote Access", None, ["ac-17"]),
    ("FR-AC-18", "Access Control", "Wireless Access", None, ["ac-18"]),
    ("FR-AC-19", "Access Control", "Access Control for Mobile Devices", None, ["ac-19"]),
    ("FR-AC-20", "Access Control", "Use of External Systems", None, ["ac-20"]),
    ("FR-AC-21", "Access Control", "Information Sharing", None, ["ac-21"]),
    ("FR-AC-22", "Access Control", "Publicly Accessible Content", None, ["ac-22"]),
    # ── Awareness and Training (AT) ───────────────────────────────────────────
    ("FR-AT-1", "Awareness and Training", "Awareness and Training Policy and Procedures", None, ["at-1"]),
    ("FR-AT-2", "Awareness and Training", "Literacy Training and Awareness", None, ["at-2"]),
    ("FR-AT-3", "Awareness and Training", "Role-Based Training", None, ["at-3"]),
    ("FR-AT-4", "Awareness and Training", "Training Records", None, ["at-4"]),
    # ── Audit and Accountability (AU) ─────────────────────────────────────────
    ("FR-AU-1",  "Audit and Accountability", "Audit and Accountability Policy and Procedures", None, ["au-1"]),
    ("FR-AU-2",  "Audit and Accountability", "Event Logging", None, ["au-2"]),
    ("FR-AU-3",  "Audit and Accountability", "Content of Audit Records", None, ["au-3"]),
    ("FR-AU-4",  "Audit and Accountability", "Audit Log Storage Capacity", None, ["au-4"]),
    ("FR-AU-5",  "Audit and Accountability", "Response to Audit Logging Process Failures", None, ["au-5"]),
    ("FR-AU-6",  "Audit and Accountability", "Audit Record Review, Analysis, and Reporting", None, ["au-6"]),
    ("FR-AU-8",  "Audit and Accountability", "Time Stamps", None, ["au-8"]),
    ("FR-AU-9",  "Audit and Accountability", "Protection of Audit Information", None, ["au-9"]),
    ("FR-AU-11", "Audit and Accountability", "Audit Record Retention", None, ["au-11"]),
    ("FR-AU-12", "Audit and Accountability", "Audit Record Generation", None, ["au-12"]),
    # ── Assessment, Authorization, Monitoring (CA) ────────────────────────────
    ("FR-CA-1", "Assessment, Authorization, Monitoring", "Policy and Procedures", None, ["ca-1"]),
    ("FR-CA-2", "Assessment, Authorization, Monitoring", "Control Assessments", None, ["ca-2"]),
    ("FR-CA-3", "Assessment, Authorization, Monitoring", "Information Exchange", None, ["ca-3"]),
    ("FR-CA-5", "Assessment, Authorization, Monitoring", "Plan of Action and Milestones", None, ["ca-5"]),
    ("FR-CA-6", "Assessment, Authorization, Monitoring", "Authorization", None, ["ca-6"]),
    ("FR-CA-7", "Assessment, Authorization, Monitoring", "Continuous Monitoring", None, ["ca-7"]),
    ("FR-CA-8", "Assessment, Authorization, Monitoring", "Penetration Testing", None, ["ca-8"]),
    ("FR-CA-9", "Assessment, Authorization, Monitoring", "Internal System Connections", None, ["ca-9"]),
    # ── Configuration Management (CM) ─────────────────────────────────────────
    ("FR-CM-1",  "Configuration Management", "Configuration Management Policy and Procedures", None, ["cm-1"]),
    ("FR-CM-2",  "Configuration Management", "Baseline Configuration", None, ["cm-2"]),
    ("FR-CM-3",  "Configuration Management", "Configuration Change Control", None, ["cm-3"]),
    ("FR-CM-4",  "Configuration Management", "Impact Analyses", None, ["cm-4"]),
    ("FR-CM-5",  "Configuration Management", "Access Restrictions for Change", None, ["cm-5"]),
    ("FR-CM-6",  "Configuration Management", "Configuration Settings", None, ["cm-6"]),
    ("FR-CM-7",  "Configuration Management", "Least Functionality", None, ["cm-7"]),
    ("FR-CM-8",  "Configuration Management", "System Component Inventory", None, ["cm-8"]),
    ("FR-CM-9",  "Configuration Management", "Configuration Management Plan", None, ["cm-9"]),
    ("FR-CM-10", "Configuration Management", "Software Usage Restrictions", None, ["cm-10"]),
    ("FR-CM-11", "Configuration Management", "User-Installed Software", None, ["cm-11"]),
    # ── Contingency Planning (CP) ─────────────────────────────────────────────
    ("FR-CP-1",  "Contingency Planning", "Contingency Planning Policy and Procedures", None, ["cp-1"]),
    ("FR-CP-2",  "Contingency Planning", "Contingency Plan", None, ["cp-2"]),
    ("FR-CP-3",  "Contingency Planning", "Contingency Training", None, ["cp-3"]),
    ("FR-CP-4",  "Contingency Planning", "Contingency Plan Testing", None, ["cp-4"]),
    ("FR-CP-6",  "Contingency Planning", "Alternate Storage Site", None, ["cp-6"]),
    ("FR-CP-7",  "Contingency Planning", "Alternate Processing Site", None, ["cp-7"]),
    ("FR-CP-8",  "Contingency Planning", "Telecommunications Services", None, ["cp-8"]),
    ("FR-CP-9",  "Contingency Planning", "System Backup", None, ["cp-9"]),
    ("FR-CP-10", "Contingency Planning", "System Recovery and Reconstitution", None, ["cp-10"]),
    # ── Identification and Authentication (IA) ────────────────────────────────
    ("FR-IA-1",  "Identification and Authentication", "Policy and Procedures", None, ["ia-1"]),
    ("FR-IA-2",  "Identification and Authentication", "Identification and Authentication (Org Users)", None, ["ia-2"]),
    ("FR-IA-3",  "Identification and Authentication", "Device Identification and Authentication", None, ["ia-3"]),
    ("FR-IA-4",  "Identification and Authentication", "Identifier Management", None, ["ia-4"]),
    ("FR-IA-5",  "Identification and Authentication", "Authenticator Management", None, ["ia-5"]),
    ("FR-IA-6",  "Identification and Authentication", "Authentication Feedback", None, ["ia-6"]),
    ("FR-IA-7",  "Identification and Authentication", "Cryptographic Module Authentication", None, ["ia-7"]),
    ("FR-IA-8",  "Identification and Authentication", "Identification and Authentication (Non-Org Users)", None, ["ia-8"]),
    ("FR-IA-11", "Identification and Authentication", "Re-Authentication", None, ["ia-11"]),
    ("FR-IA-12", "Identification and Authentication", "Identity Proofing", None, ["ia-12"]),
    # ── Incident Response (IR) ────────────────────────────────────────────────
    ("FR-IR-1", "Incident Response", "Incident Response Policy and Procedures", None, ["ir-1"]),
    ("FR-IR-2", "Incident Response", "Incident Response Training", None, ["ir-2"]),
    ("FR-IR-3", "Incident Response", "Incident Response Testing", None, ["ir-3"]),
    ("FR-IR-4", "Incident Response", "Incident Handling", None, ["ir-4"]),
    ("FR-IR-5", "Incident Response", "Incident Monitoring", None, ["ir-5"]),
    ("FR-IR-6", "Incident Response", "Incident Reporting", None, ["ir-6"]),
    ("FR-IR-7", "Incident Response", "Incident Response Assistance", None, ["ir-7"]),
    ("FR-IR-8", "Incident Response", "Incident Response Plan", None, ["ir-8"]),
    # ── Maintenance (MA) ──────────────────────────────────────────────────────
    ("FR-MA-1", "Maintenance", "System Maintenance Policy and Procedures", None, ["ma-1"]),
    ("FR-MA-2", "Maintenance", "Controlled Maintenance", None, ["ma-2"]),
    ("FR-MA-3", "Maintenance", "Maintenance Tools", None, ["ma-3"]),
    ("FR-MA-4", "Maintenance", "Nonlocal Maintenance", None, ["ma-4"]),
    ("FR-MA-5", "Maintenance", "Maintenance Personnel", None, ["ma-5"]),
    ("FR-MA-6", "Maintenance", "Timely Maintenance", None, ["ma-6"]),
    # ── Media Protection (MP) ─────────────────────────────────────────────────
    ("FR-MP-1", "Media Protection", "Media Protection Policy and Procedures", None, ["mp-1"]),
    ("FR-MP-2", "Media Protection", "Media Access", None, ["mp-2"]),
    ("FR-MP-3", "Media Protection", "Media Marking", None, ["mp-3"]),
    ("FR-MP-4", "Media Protection", "Media Storage", None, ["mp-4"]),
    ("FR-MP-5", "Media Protection", "Media Transport", None, ["mp-5"]),
    ("FR-MP-6", "Media Protection", "Media Sanitization", None, ["mp-6"]),
    ("FR-MP-7", "Media Protection", "Media Use", None, ["mp-7"]),
    # ── Physical and Environmental Protection (PE) ────────────────────────────
    ("FR-PE-1",  "Physical Protection", "Physical and Environmental Protection Policy", None, ["pe-1"]),
    ("FR-PE-2",  "Physical Protection", "Physical Access Authorizations", None, ["pe-2"]),
    ("FR-PE-3",  "Physical Protection", "Physical Access Control", None, ["pe-3"]),
    ("FR-PE-6",  "Physical Protection", "Monitoring Physical Access", None, ["pe-6"]),
    ("FR-PE-8",  "Physical Protection", "Visitor Access Records", None, ["pe-8"]),
    ("FR-PE-9",  "Physical Protection", "Power Equipment and Cabling", None, ["pe-9"]),
    ("FR-PE-10", "Physical Protection", "Emergency Shutoff", None, ["pe-10"]),
    ("FR-PE-11", "Physical Protection", "Emergency Power", None, ["pe-11"]),
    ("FR-PE-12", "Physical Protection", "Emergency Lighting", None, ["pe-12"]),
    ("FR-PE-13", "Physical Protection", "Fire Protection", None, ["pe-13"]),
    ("FR-PE-14", "Physical Protection", "Environmental Controls", None, ["pe-14"]),
    ("FR-PE-15", "Physical Protection", "Water Damage Protection", None, ["pe-15"]),
    ("FR-PE-16", "Physical Protection", "Delivery and Removal", None, ["pe-16"]),
    ("FR-PE-17", "Physical Protection", "Alternate Work Site", None, ["pe-17"]),
    # ── Planning (PL) ─────────────────────────────────────────────────────────
    ("FR-PL-1", "Planning", "Planning Policy and Procedures", None, ["pl-1"]),
    ("FR-PL-2", "Planning", "System Security and Privacy Plans", None, ["pl-2"]),
    ("FR-PL-4", "Planning", "Rules of Behavior", None, ["pl-4"]),
    ("FR-PL-8", "Planning", "Security and Privacy Architectures", None, ["pl-8"]),
    ("FR-PL-10","Planning", "Baseline Selection", None, ["pl-10"]),
    ("FR-PL-11","Planning", "Baseline Tailoring", None, ["pl-11"]),
    # ── Program Management (PM) ───────────────────────────────────────────────
    ("FR-PM-1",  "Program Management", "Information Security Program Plan", None, ["pm-1"]),
    ("FR-PM-2",  "Program Management", "Information Security Program Leadership Roles", None, ["pm-2"]),
    ("FR-PM-3",  "Program Management", "Information Security and Privacy Resources", None, ["pm-3"]),
    ("FR-PM-4",  "Program Management", "Plan of Action and Milestones Process", None, ["pm-4"]),
    ("FR-PM-5",  "Program Management", "System Inventory", None, ["pm-5"]),
    ("FR-PM-6",  "Program Management", "Measures of Performance", None, ["pm-6"]),
    ("FR-PM-9",  "Program Management", "Risk Management Strategy", None, ["pm-9"]),
    ("FR-PM-10", "Program Management", "Authorization Process", None, ["pm-10"]),
    ("FR-PM-11", "Program Management", "Mission and Business Process Definition", None, ["pm-11"]),
    ("FR-PM-14", "Program Management", "Testing, Training, and Monitoring", None, ["pm-14"]),
    ("FR-PM-15", "Program Management", "Security and Privacy Groups and Associations", None, ["pm-15"]),
    ("FR-PM-16", "Program Management", "Threat Awareness Program", None, ["pm-16"]),
    # ── Personnel Security (PS) ───────────────────────────────────────────────
    ("FR-PS-1", "Personnel Security", "Personnel Security Policy and Procedures", None, ["ps-1"]),
    ("FR-PS-2", "Personnel Security", "Position Risk Designation", None, ["ps-2"]),
    ("FR-PS-3", "Personnel Security", "Personnel Screening", None, ["ps-3"]),
    ("FR-PS-4", "Personnel Security", "Personnel Termination", None, ["ps-4"]),
    ("FR-PS-5", "Personnel Security", "Personnel Transfer", None, ["ps-5"]),
    ("FR-PS-6", "Personnel Security", "Access Agreements", None, ["ps-6"]),
    ("FR-PS-7", "Personnel Security", "External Personnel Security", None, ["ps-7"]),
    ("FR-PS-8", "Personnel Security", "Personnel Sanctions", None, ["ps-8"]),
    ("FR-PS-9", "Personnel Security", "Position Descriptions", None, ["ps-9"]),
    # ── Risk Assessment (RA) ──────────────────────────────────────────────────
    ("FR-RA-1", "Risk Assessment", "Risk Assessment Policy and Procedures", None, ["ra-1"]),
    ("FR-RA-2", "Risk Assessment", "Security Categorization", None, ["ra-2"]),
    ("FR-RA-3", "Risk Assessment", "Risk Assessment", None, ["ra-3"]),
    ("FR-RA-5", "Risk Assessment", "Vulnerability Monitoring and Scanning", None, ["ra-5"]),
    ("FR-RA-7", "Risk Assessment", "Risk Response", None, ["ra-7"]),
    ("FR-RA-9", "Risk Assessment", "Criticality Analysis", None, ["ra-9"]),
    # ── System and Services Acquisition (SA) ─────────────────────────────────
    ("FR-SA-1",  "System Acquisition", "Policy and Procedures", None, ["sa-1"]),
    ("FR-SA-2",  "System Acquisition", "Allocation of Resources", None, ["sa-2"]),
    ("FR-SA-3",  "System Acquisition", "System Development Life Cycle", None, ["sa-3"]),
    ("FR-SA-4",  "System Acquisition", "Acquisition Process", None, ["sa-4"]),
    ("FR-SA-5",  "System Acquisition", "System Documentation", None, ["sa-5"]),
    ("FR-SA-8",  "System Acquisition", "Security and Privacy Engineering Principles", None, ["sa-8"]),
    ("FR-SA-9",  "System Acquisition", "External System Services", None, ["sa-9"]),
    ("FR-SA-10", "System Acquisition", "Developer Configuration Management", None, ["sa-10"]),
    ("FR-SA-11", "System Acquisition", "Developer Testing and Evaluation", None, ["sa-11"]),
    ("FR-SA-15", "System Acquisition", "Development Process, Standards, and Tools", None, ["sa-15"]),
    ("FR-SA-16", "System Acquisition", "Developer-Provided Training", None, ["sa-16"]),
    ("FR-SA-17", "System Acquisition", "Developer Security and Privacy Architecture and Design", None, ["sa-17"]),
    ("FR-SA-22", "System Acquisition", "Unsupported System Components", None, ["sa-22"]),
    # ── System and Communications Protection (SC) ─────────────────────────────
    ("FR-SC-1",  "System and Communications Protection", "Policy and Procedures", None, ["sc-1"]),
    ("FR-SC-5",  "System and Communications Protection", "Denial of Service Protection", None, ["sc-5"]),
    ("FR-SC-7",  "System and Communications Protection", "Boundary Protection", None, ["sc-7"]),
    ("FR-SC-8",  "System and Communications Protection", "Transmission Confidentiality and Integrity", None, ["sc-8"]),
    ("FR-SC-10", "System and Communications Protection", "Network Disconnect", None, ["sc-10"]),
    ("FR-SC-12", "System and Communications Protection", "Cryptographic Key Establishment and Management", None, ["sc-12"]),
    ("FR-SC-13", "System and Communications Protection", "Cryptographic Protection", None, ["sc-13"]),
    ("FR-SC-15", "System and Communications Protection", "Collaborative Computing Devices and Applications", None, ["sc-15"]),
    ("FR-SC-17", "System and Communications Protection", "Public Key Infrastructure Certificates", None, ["sc-17"]),
    ("FR-SC-18", "System and Communications Protection", "Mobile Code", None, ["sc-18"]),
    ("FR-SC-19", "System and Communications Protection", "Voice over IP Technologies", None, ["sc-19"]),
    ("FR-SC-20", "System and Communications Protection", "Secure Name/Address Resolution Service (Auth Source)", None, ["sc-20"]),
    ("FR-SC-21", "System and Communications Protection", "Secure Name/Address Resolution Service (Recursive)", None, ["sc-21"]),
    ("FR-SC-22", "System and Communications Protection", "Architecture and Provisioning for DNS", None, ["sc-22"]),
    ("FR-SC-23", "System and Communications Protection", "Session Authenticity", None, ["sc-23"]),
    ("FR-SC-28", "System and Communications Protection", "Protection of Information at Rest", None, ["sc-28"]),
    ("FR-SC-39", "System and Communications Protection", "Process Isolation", None, ["sc-39"]),
    # ── System and Information Integrity (SI) ─────────────────────────────────
    ("FR-SI-1",  "System and Information Integrity", "Policy and Procedures", None, ["si-1"]),
    ("FR-SI-2",  "System and Information Integrity", "Flaw Remediation", None, ["si-2"]),
    ("FR-SI-3",  "System and Information Integrity", "Malicious Code Protection", None, ["si-3"]),
    ("FR-SI-4",  "System and Information Integrity", "System Monitoring", None, ["si-4"]),
    ("FR-SI-5",  "System and Information Integrity", "Security Alerts, Advisories, and Directives", None, ["si-5"]),
    ("FR-SI-6",  "System and Information Integrity", "Security and Privacy Function Verification", None, ["si-6"]),
    ("FR-SI-7",  "System and Information Integrity", "Software, Firmware, and Information Integrity", None, ["si-7"]),
    ("FR-SI-8",  "System and Information Integrity", "Spam Protection", None, ["si-8"]),
    ("FR-SI-10", "System and Information Integrity", "Information Input Validation", None, ["si-10"]),
    ("FR-SI-12", "System and Information Integrity", "Information Management and Retention", None, ["si-12"]),
    # ── Supply Chain Risk Management (SR) ─────────────────────────────────────
    ("FR-SR-1",  "Supply Chain Risk Management", "Policy and Procedures", None, ["sr-1"]),
    ("FR-SR-2",  "Supply Chain Risk Management", "Supply Chain Risk Management Plan", None, ["sr-2"]),
    ("FR-SR-3",  "Supply Chain Risk Management", "Supply Chain Controls and Processes", None, ["sr-3"]),
    ("FR-SR-5",  "Supply Chain Risk Management", "Acquisition Strategies, Tools, and Methods", None, ["sr-5"]),
    ("FR-SR-6",  "Supply Chain Risk Management", "Supplier Assessments and Reviews", None, ["sr-6"]),
    ("FR-SR-8",  "Supply Chain Risk Management", "Notification Agreements", None, ["sr-8"]),
    ("FR-SR-10", "Supply Chain Risk Management", "Inspection of Systems or Components", None, ["sr-10"]),
    ("FR-SR-11", "Supply Chain Risk Management", "Component Authenticity", None, ["sr-11"]),
    ("FR-SR-12", "Supply Chain Risk Management", "Component Disposal", None, ["sr-12"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# ISA/IEC 62443-3-3 → NIST SP 800-53r5
# Source: ISA-62443-3-3 (2013); DHS ICS-CERT community crosswalk
# Security Requirements (SR) with foundational requirements (FR)
# ─────────────────────────────────────────────────────────────────────────────
ISA62443_CONTROLS = [
    # ── SR 1: Identification and Authentication Control ───────────────────────
    ("SR 1.1",  "Identification and Authentication", "Human user identification and authentication",
     None, ["ia-2","ia-5","ia-8","ac-14"]),
    ("SR 1.2",  "Identification and Authentication", "Software process and device identification and authentication",
     None, ["ia-3","ia-5","sc-3"]),
    ("SR 1.3",  "Identification and Authentication", "Account management",
     None, ["ac-2","ia-4","ps-4"]),
    ("SR 1.4",  "Identification and Authentication", "Identifier management",
     None, ["ia-4","ac-2"]),
    ("SR 1.5",  "Identification and Authentication", "Authenticator management",
     None, ["ia-5","ia-4"]),
    ("SR 1.6",  "Identification and Authentication", "Wireless access management",
     None, ["ac-18","ia-3","sc-40"]),
    ("SR 1.7",  "Identification and Authentication", "Strength of password-based authentication",
     None, ["ia-5","ia-11"]),
    ("SR 1.8",  "Identification and Authentication", "Public key infrastructure (PKI) certificates",
     None, ["sc-17","ia-5","ia-7"]),
    ("SR 1.9",  "Identification and Authentication", "Strength of public key authentication",
     None, ["ia-5","ia-7","sc-12"]),
    ("SR 1.10", "Identification and Authentication", "Authenticator feedback",
     None, ["ia-6"]),
    ("SR 1.11", "Identification and Authentication", "Unsuccessful login attempts",
     None, ["ac-7","ia-2"]),
    ("SR 1.12", "Identification and Authentication", "System use notification",
     None, ["ac-8"]),
    ("SR 1.13", "Identification and Authentication", "Access via untrusted networks",
     None, ["ac-17","sc-7","ia-2"]),
    # ── SR 2: Use Control ─────────────────────────────────────────────────────
    ("SR 2.1",  "Use Control", "Authorization enforcement",
     None, ["ac-3","ac-6","ac-16"]),
    ("SR 2.2",  "Use Control", "Wireless use control",
     None, ["ac-18","sc-40"]),
    ("SR 2.3",  "Use Control", "Use control for portable and mobile devices",
     None, ["ac-19","mp-7","cm-6"]),
    ("SR 2.4",  "Use Control", "Mobile code",
     None, ["sc-18","cm-6"]),
    ("SR 2.5",  "Use Control", "Session lock",
     None, ["ac-11","ac-12"]),
    ("SR 2.6",  "Use Control", "Remote session termination",
     None, ["ac-17","ac-12","sc-10"]),
    ("SR 2.7",  "Use Control", "Concurrent session control",
     None, ["ac-10","ac-2"]),
    ("SR 2.8",  "Use Control", "Auditable events",
     None, ["au-2","au-3","au-12"]),
    ("SR 2.9",  "Use Control", "Audit storage capacity",
     None, ["au-4","au-5"]),
    ("SR 2.10", "Use Control", "Response to audit processing failures",
     None, ["au-5","ir-4"]),
    ("SR 2.11", "Use Control", "Timestamps",
     None, ["au-8","sc-45"]),
    ("SR 2.12", "Use Control", "Non-repudiation",
     None, ["au-10","ia-2"]),
    # ── SR 3: System Integrity ────────────────────────────────────────────────
    ("SR 3.1",  "System Integrity", "Communication integrity",
     None, ["sc-8","si-7","sc-23"]),
    ("SR 3.2",  "System Integrity", "Malicious code protection",
     None, ["si-3","si-4","si-8"]),
    ("SR 3.3",  "System Integrity", "Security functionality verification",
     None, ["si-6","ca-7","ca-2"]),
    ("SR 3.4",  "System Integrity", "Software and information integrity",
     None, ["si-7","sa-10","cm-14"]),
    ("SR 3.5",  "System Integrity", "Input validation",
     None, ["si-10","sc-7"]),
    ("SR 3.6",  "System Integrity", "Deterministic output",
     None, ["si-10","cp-12"]),
    ("SR 3.7",  "System Integrity", "Error handling",
     None, ["si-11","ir-4"]),
    ("SR 3.8",  "System Integrity", "Session integrity",
     None, ["sc-23","ia-2","ac-17"]),
    ("SR 3.9",  "System Integrity", "Protection of audit information",
     None, ["au-9","si-7"]),
    # ── SR 4: Data Confidentiality ────────────────────────────────────────────
    ("SR 4.1",  "Data Confidentiality", "Information confidentiality",
     None, ["sc-28","sc-8","mp-4","ac-4"]),
    ("SR 4.2",  "Data Confidentiality", "Information persistence",
     None, ["mp-6","sc-28","si-12"]),
    ("SR 4.3",  "Data Confidentiality", "Use of cryptography",
     None, ["sc-13","sc-12","ia-7"]),
    # ── SR 5: Restricted Data Flow ────────────────────────────────────────────
    ("SR 5.1",  "Restricted Data Flow", "Network segmentation",
     None, ["sc-7","ca-3","ac-4","sc-3"]),
    ("SR 5.2",  "Restricted Data Flow", "Zone boundary protection",
     None, ["sc-7","ca-3","ac-4"]),
    ("SR 5.3",  "Restricted Data Flow", "General purpose person-to-person communication restrictions",
     None, ["sc-7","ac-4","cm-7"]),
    ("SR 5.4",  "Restricted Data Flow", "Application partitioning",
     None, ["sc-3","sc-7","ac-4"]),
    # ── SR 6: Timely Response to Events ──────────────────────────────────────
    ("SR 6.1",  "Timely Response to Events", "Audit log accessibility",
     None, ["au-6","au-9","ir-5"]),
    ("SR 6.2",  "Timely Response to Events", "Continuous monitoring",
     None, ["ca-7","si-4","au-6"]),
    # ── SR 7: Resource Availability ───────────────────────────────────────────
    ("SR 7.1",  "Resource Availability", "Denial of service protection",
     None, ["sc-5","sc-6","cp-2"]),
    ("SR 7.2",  "Resource Availability", "Resource management",
     None, ["sc-5","sc-6","sa-8"]),
    ("SR 7.3",  "Resource Availability", "Control system backup",
     None, ["cp-9","cp-6","cp-2"]),
    ("SR 7.4",  "Resource Availability", "Control system recovery and reconstitution",
     None, ["cp-10","cp-2","ir-4"]),
    ("SR 7.5",  "Resource Availability", "Emergency power",
     None, ["pe-11","cp-8","cp-2"]),
    ("SR 7.6",  "Resource Availability", "Network and security configuration settings",
     None, ["cm-6","cm-2","sc-7"]),
    ("SR 7.7",  "Resource Availability", "Least functionality",
     None, ["cm-7","sa-9","sc-3"]),
    ("SR 7.8",  "Resource Availability", "Control system component inventory",
     None, ["cm-8","pm-5","sa-14"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# FISMA 2014 → NIST SP 800-53r5
# FISMA provisions map to NIST control families (1:1 or family-level)
# Source: FISMA 2014; OMB A-130; NIST SP 800-53r5 directly implements FISMA
# ─────────────────────────────────────────────────────────────────────────────
FISMA_CONTROLS = [
    ("FISMA-3544(b)(1)", "Information Security Program", "Periodic risk assessments",
     None, ["ra-1","ra-2","ra-3","ra-5","pm-9"]),
    ("FISMA-3544(b)(2)", "Information Security Program", "Risk-based policies and procedures",
     None, ["pm-1","pl-2","pl-4","pm-9"]),
    ("FISMA-3544(b)(3)", "Information Security Program", "Security plans for agency information systems",
     None, ["pl-2","pl-7","pm-1","ca-6"]),
    ("FISMA-3544(b)(4)", "Information Security Program", "Security awareness training",
     None, ["at-1","at-2","at-3","at-4"]),
    ("FISMA-3544(b)(5)", "Information Security Program", "Periodic testing and evaluation of security controls",
     None, ["ca-2","ca-7","ca-8","pm-14"]),
    ("FISMA-3544(b)(6)", "Information Security Program", "Process for remediating deficiencies (POA&M)",
     None, ["ca-5","pm-4","si-2","ra-7"]),
    ("FISMA-3544(b)(7)", "Information Security Program", "Procedures for detecting, reporting, and responding to incidents",
     None, ["ir-1","ir-4","ir-5","ir-6","ir-8"]),
    ("FISMA-3544(b)(8)", "Information Security Program", "Plans and procedures for continuity of operations",
     None, ["cp-1","cp-2","cp-9","cp-10"]),
    ("FISMA-3544(c)(1)", "System Inventory", "Maintain inventory of agency information systems",
     None, ["pm-5","cm-8","pm-11"]),
    ("FISMA-3544(c)(2)", "System Inventory", "Identify interfaces between agency systems and external systems",
     None, ["ca-3","pm-5","cm-8"]),
    ("FISMA-3545",       "Inspector General Evaluation", "Independent evaluation of agency security program",
     None, ["ca-2","pm-14","ca-7"]),
    ("FISMA-3546",       "Agency Reporting", "Annual reporting to OMB on security program effectiveness",
     None, ["pm-6","pm-14","ca-7"]),
    ("FISMA-AC",         "Access Control Family", "Access control as required by NIST standards",
     None, ["ac-1","ac-2","ac-3","ac-5","ac-6","ac-17"]),
    ("FISMA-AT",         "Awareness and Training Family", "Security awareness and training as required",
     None, ["at-1","at-2","at-3","at-4"]),
    ("FISMA-AU",         "Audit Family", "Audit and accountability as required",
     None, ["au-1","au-2","au-6","au-9","au-11","au-12"]),
    ("FISMA-CA",         "Assessment Family", "Security assessment and authorization as required",
     None, ["ca-1","ca-2","ca-5","ca-6","ca-7"]),
    ("FISMA-CM",         "Configuration Management Family", "Configuration management as required",
     None, ["cm-1","cm-2","cm-6","cm-7","cm-8"]),
    ("FISMA-CP",         "Contingency Planning Family", "Contingency planning as required",
     None, ["cp-1","cp-2","cp-4","cp-9","cp-10"]),
    ("FISMA-IA",         "Identification and Authentication Family", "Identification and authentication as required",
     None, ["ia-1","ia-2","ia-4","ia-5","ia-8"]),
    ("FISMA-IR",         "Incident Response Family", "Incident response as required",
     None, ["ir-1","ir-4","ir-6","ir-8"]),
    ("FISMA-MA",         "Maintenance Family", "System maintenance as required",
     None, ["ma-1","ma-2","ma-4","ma-5"]),
    ("FISMA-MP",         "Media Protection Family", "Media protection as required",
     None, ["mp-1","mp-4","mp-6","mp-7"]),
    ("FISMA-PE",         "Physical Protection Family", "Physical and environmental protection as required",
     None, ["pe-1","pe-2","pe-3","pe-6"]),
    ("FISMA-PL",         "Planning Family", "Planning as required",
     None, ["pl-1","pl-2","pl-4","pl-8"]),
    ("FISMA-PM",         "Program Management Family", "Program management as required",
     None, ["pm-1","pm-2","pm-9","pm-10","pm-14"]),
    ("FISMA-PS",         "Personnel Security Family", "Personnel security as required",
     None, ["ps-1","ps-2","ps-3","ps-4","ps-6"]),
    ("FISMA-RA",         "Risk Assessment Family", "Risk assessment as required",
     None, ["ra-1","ra-2","ra-3","ra-5"]),
    ("FISMA-SA",         "System Acquisition Family", "System and services acquisition as required",
     None, ["sa-1","sa-3","sa-4","sa-9","sa-11"]),
    ("FISMA-SC",         "System Communications Family", "System and communications protection as required",
     None, ["sc-1","sc-7","sc-8","sc-12","sc-28"]),
    ("FISMA-SI",         "System Integrity Family", "System and information integrity as required",
     None, ["si-1","si-2","si-3","si-4","si-7"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# GDPR (EU) 2016/679 → NIST SP 800-53r5
# Source: ENISA GDPR → 800-53 mapping; EC29 WP guidelines; community crosswalk
# ─────────────────────────────────────────────────────────────────────────────
GDPR_CONTROLS = [
    # ── Article 5: Principles ─────────────────────────────────────────────────
    ("Art.5(1)(a)", "Data Processing Principles", "Lawfulness, fairness, and transparency",
     None, ["pm-1","pl-4","at-2","pm-9"]),
    ("Art.5(1)(b)", "Data Processing Principles", "Purpose limitation",
     None, ["pm-9","si-12","mp-6","ra-2"]),
    ("Art.5(1)(c)", "Data Processing Principles", "Data minimisation",
     None, ["si-12","mp-6","mp-7","ra-2","pm-25"]),
    ("Art.5(1)(d)", "Data Processing Principles", "Accuracy",
     None, ["si-10","si-12","pm-25"]),
    ("Art.5(1)(e)", "Data Processing Principles", "Storage limitation",
     None, ["si-12","mp-6","mp-7"]),
    ("Art.5(1)(f)", "Data Processing Principles", "Integrity and confidentiality",
     None, ["sc-28","sc-8","ia-5","si-7","ac-3","mp-4"]),
    ("Art.5(2)",    "Data Processing Principles", "Accountability — demonstrate compliance",
     None, ["pm-1","pm-14","au-3","ca-2"]),
    # ── Article 13/14: Transparency ──────────────────────────────────────────
    ("Art.13-14", "Transparency", "Provide privacy notices to data subjects",
     None, ["pm-20","pt-2","pl-4"]),
    # ── Article 15-22: Data Subject Rights ────────────────────────────────────
    ("Art.15-16", "Data Subject Rights", "Right of access and rectification",
     None, ["pm-20","pm-25","pt-2","ac-3"]),
    ("Art.17",    "Data Subject Rights", "Right to erasure ('right to be forgotten')",
     None, ["mp-6","si-12","pm-25","pt-3"]),
    ("Art.18",    "Data Subject Rights", "Right to restriction of processing",
     None, ["pm-25","mp-4","ac-3"]),
    ("Art.20",    "Data Subject Rights", "Right to data portability",
     None, ["pm-20","pm-25","mp-5"]),
    ("Art.21",    "Data Subject Rights", "Right to object",
     None, ["pm-25","pm-20","pt-3"]),
    # ── Article 24: Controller Responsibilities ────────────────────────────────
    ("Art.24", "Controller Responsibilities", "Implement appropriate technical/organizational measures",
     None, ["pm-1","pm-9","ca-2","pl-2","ra-3"]),
    # ── Article 25: Privacy by Design and Default ──────────────────────────────
    ("Art.25(1)", "Privacy by Design", "Data protection by design — implement from inception",
     None, ["pl-8","sa-8","pm-9","pm-25","pt-7"]),
    ("Art.25(2)", "Privacy by Design", "Data protection by default — process minimum personal data",
     None, ["cm-7","ac-3","pm-25","pt-7","si-12"]),
    # ── Article 28: Processor Requirements ────────────────────────────────────
    ("Art.28", "Processor Requirements", "Data processing agreements with processors",
     None, ["sa-9","sr-1","sr-3","sr-6"]),
    ("Art.28(3)", "Processor Requirements", "Processor contractual security obligations",
     None, ["sa-9","sr-6","pm-9"]),
    # ── Article 30: Records of Processing ────────────────────────────────────
    ("Art.30", "Processing Records", "Maintain records of processing activities",
     None, ["au-3","pm-5","si-12","pm-11"]),
    # ── Article 32: Security of Processing ────────────────────────────────────
    ("Art.32(1)(a)", "Security of Processing", "Pseudonymisation and encryption of personal data",
     None, ["sc-28","sc-12","mp-4","ia-7","pt-7"]),
    ("Art.32(1)(b)", "Security of Processing", "Confidentiality, integrity, availability, and resilience",
     None, ["sc-28","sc-8","cp-2","si-7","ac-3","ia-2"]),
    ("Art.32(1)(c)", "Security of Processing", "Restore availability/access to personal data after incident",
     None, ["cp-9","cp-10","ir-4","cp-2"]),
    ("Art.32(1)(d)", "Security of Processing", "Regular testing and evaluation of security measures",
     None, ["ca-2","ca-7","ca-8","ra-5","pm-14"]),
    ("Art.32(2)",    "Security of Processing", "Risk-appropriate security measures",
     None, ["ra-3","pm-9","ca-5","si-2"]),
    ("Art.32(4)",    "Security of Processing", "Processors act only on controller instructions",
     None, ["sa-9","sr-6","ac-3"]),
    # ── Article 33: Breach Notification to Authority ──────────────────────────
    ("Art.33", "Breach Notification", "Notify supervisory authority within 72 hours of personal data breach",
     None, ["ir-6","ir-8","pm-15","ir-4"]),
    # ── Article 34: Communication to Data Subjects ───────────────────────────
    ("Art.34", "Breach Notification", "Communicate personal data breach to data subjects",
     None, ["ir-6","pm-15","ir-8"]),
    # ── Article 35: Data Protection Impact Assessment ─────────────────────────
    ("Art.35", "Data Protection Impact Assessment", "Conduct DPIA for high-risk processing",
     None, ["ra-3","pl-8","pm-9","pm-25","pt-5"]),
    # ── Article 37-39: Data Protection Officer ───────────────────────────────
    ("Art.37-39", "Data Protection Officer", "Designate and tasks of DPO",
     None, ["pm-2","pm-20","at-3"]),
    # ── Article 44-49: International Transfers ────────────────────────────────
    ("Art.44-49", "International Transfers", "Transfers of personal data to third countries",
     None, ["sa-9","sr-6","sc-28","mp-5"]),
    # ── Article 83: Administrative Fines ─────────────────────────────────────
    ("Art.83", "Enforcement", "Conditions for imposing administrative fines",
     None, ["pm-1","ca-2","ca-7"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# Master lookup
# ─────────────────────────────────────────────────────────────────────────────
FRAMEWORK_DATA = {
    "ssdf":       SSDF_CONTROLS,
    "soc2":       SOC2_CONTROLS,
    "pcidss":     PCIDSS_CONTROLS,
    "nydfs500":   NYDFS500_CONTROLS,
    "basel3":     BASEL3_CONTROLS,
    "hipaa":      HIPAA_CONTROLS,
    "fdamdcyber": FDAMDCYBER_CONTROLS,
    "fedramp":    FEDRAMP_CONTROLS,
    "isa62443":   ISA62443_CONTROLS,
    "fisma":      FISMA_CONTROLS,
    "gdpr":       GDPR_CONTROLS,
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
        fw_id = fw["id"]
        sn    = fw["short_name"]
        src   = SOURCE_MAP[sn]
        controls = FRAMEWORK_DATA[sn]

        for row in controls:
            ctrl_id, domain, title, level, nist_ids = row
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
                # Collapse enhancements to base control (e.g. "ia-2.1" → "ia-2")
                if '.' in nid:
                    nid = nid.split('.')[0]
                cur.execute(
                    "INSERT OR IGNORE INTO control_crosswalks "
                    "(framework_control_id, nist_control_id, mapping_type, confidence, source) "
                    "VALUES (?,?,?,?,?)",
                    (fc_id, nid, "direct", "high", src)
                )
                if cur.rowcount:
                    total_xwalk += 1

    conn.commit()
    conn.close()

    print(f"Seeded: {total_fw} frameworks  |  {total_ctrl} framework controls  |  {total_xwalk} crosswalk mappings")

    # ── Verification summary ──────────────────────────────────────────────────
    conn2 = sqlite3.connect(DB_PATH)
    cur2  = conn2.cursor()
    cur2.execute("SELECT short_name, name FROM compliance_frameworks ORDER BY category, short_name")
    print("\nAll frameworks in DB:")
    for r in cur2.fetchall():
        print(f"  {r[0]:<14}  {r[1]}")
    cur2.execute("""
        SELECT cf.short_name, COUNT(DISTINCT fc.id) as controls, COUNT(cx.id) as mappings
        FROM compliance_frameworks cf
        JOIN framework_controls fc ON fc.framework_id = cf.id
        JOIN control_crosswalks cx ON cx.framework_control_id = fc.id
        GROUP BY cf.short_name ORDER BY cf.short_name
    """)
    print(f"\n{'framework':<14} {'controls':>9} {'crosswalks':>11}")
    print("-" * 36)
    for r in cur2.fetchall():
        print(f"  {r[0]:<12} {r[1]:>9} {r[2]:>11}")
    conn2.close()


if __name__ == "__main__":
    main()
