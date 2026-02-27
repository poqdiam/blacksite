#!/usr/bin/env python3
"""
BLACKSITE — Test Data Seed Script
==================================

[SEED] Convention
-----------------
Every record inserted by this script has a "[SEED]" prefix in its primary
name field (system name, candidate name, etc.).  This makes it trivial to:

  1. Identify seed data at a glance in any UI or SQL query.
  2. Remove ALL seed data with a single command:
       python scripts/seed_test_data.py --clean

The script never touches records whose name field does NOT start with "[SEED]",
so production data is never affected.

Usage
-----
  python scripts/seed_test_data.py            # populate DB with fake data
  python scripts/seed_test_data.py --clean    # delete ALL [SEED] records
  python scripts/seed_test_data.py --status   # count existing [SEED] records
"""

import argparse
import os
import random
import sqlite3
import sys
import uuid
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "blacksite.db")

# ---------------------------------------------------------------------------
# Employees (from config.yaml)
# ---------------------------------------------------------------------------
EMPLOYEES = [
    {"username": "alice.chen",      "name": "Alice Chen"},
    {"username": "marcus.okafor",   "name": "Marcus Okafor"},
    {"username": "priya.sharma",    "name": "Priya Sharma"},
    {"username": "derek.holloway",  "name": "Derek Holloway"},
    {"username": "samira.nazari",   "name": "Samira Nazari"},
    {"username": "james.trent",     "name": "James Trent"},
    {"username": "lucia.reyes",     "name": "Lucia Reyes"},
    {"username": "ben.ashworth",    "name": "Ben Ashworth"},
    {"username": "kwame.asante",    "name": "Kwame Asante"},
    {"username": "nadia.volkov",    "name": "Nadia Volkov"},
]

# ---------------------------------------------------------------------------
# Control families and titles
# ---------------------------------------------------------------------------
CONTROL_FAMILIES = {
    "AC": "Access Control",
    "AT": "Awareness and Training",
    "AU": "Audit and Accountability",
    "CA": "Assessment, Authorization, and Monitoring",
    "CM": "Configuration Management",
    "CP": "Contingency Planning",
    "IA": "Identification and Authentication",
    "IR": "Incident Response",
    "MA": "Maintenance",
    "MP": "Media Protection",
    "PE": "Physical and Environmental Protection",
    "PL": "Planning",
    "PM": "Program Management",
    "PS": "Personnel Security",
    "RA": "Risk Assessment",
    "SA": "System and Services Acquisition",
    "SC": "System and Communications Protection",
    "SI": "System and Information Integrity",
    "SR": "Supply Chain Risk Management",
}

CONTROL_TITLES = {
    "AC": [
        "Access Control Policy and Procedures",
        "Account Management",
        "Access Enforcement",
        "Information Flow Enforcement",
        "Separation of Duties",
        "Least Privilege",
        "Unsuccessful Logon Attempts",
        "System Use Notification",
        "Concurrent Session Control",
        "Session Lock",
    ],
    "AT": [
        "Awareness and Training Policy and Procedures",
        "Literacy Training and Awareness",
        "Role-Based Training",
        "Training Records",
        "Contacts with Security Groups and Associations",
        "Security and Privacy Training",
        "Insider Threat Awareness",
        "Social Engineering Awareness",
        "Phishing Simulations",
        "Privileged User Training",
    ],
    "AU": [
        "Audit and Accountability Policy and Procedures",
        "Event Logging",
        "Content of Audit Records",
        "Audit Log Storage Capacity",
        "Response to Audit Logging Process Failures",
        "Audit Record Review, Analysis, and Reporting",
        "Audit Record Reduction and Report Generation",
        "Time Stamps",
        "Protection of Audit Information",
        "Audit Record Retention",
    ],
    "CA": [
        "Policy and Procedures",
        "Control Assessments",
        "Information Exchange",
        "Plan of Action and Milestones",
        "Information System Connections",
        "Authorization",
        "Continuous Monitoring",
        "Penetration Testing",
        "Internal System Connections",
        "Security and Privacy Assessment Reports",
    ],
    "CM": [
        "Configuration Management Policy and Procedures",
        "Baseline Configuration",
        "Configuration Change Control",
        "Security Impact Analysis",
        "Access Restrictions for Change",
        "Configuration Settings",
        "Least Functionality",
        "Information System Component Inventory",
        "Configuration Management Plan",
        "Software Usage Restrictions",
    ],
    "CP": [
        "Contingency Planning Policy and Procedures",
        "Contingency Plan",
        "Contingency Plan Training",
        "Contingency Plan Testing",
        "Alternate Storage Site",
        "Alternate Processing Site",
        "Telecommunications Services",
        "Information System Backup",
        "Information System Recovery and Reconstitution",
        "Failover Capability",
    ],
    "IA": [
        "Identification and Authentication Policy and Procedures",
        "Identification and Authentication (Organizational Users)",
        "Device Identification and Authentication",
        "Identifier Management",
        "Authenticator Management",
        "Authenticator Feedback",
        "Cryptographic Module Authentication",
        "Identification and Authentication (Non-Organizational Users)",
        "Service Identification and Authentication",
        "Adaptive Authentication",
    ],
    "IR": [
        "Incident Response Policy and Procedures",
        "Incident Response Training",
        "Incident Response Testing",
        "Incident Handling",
        "Incident Monitoring",
        "Incident Reporting",
        "Incident Response Assistance",
        "Incident Response Plan",
        "Information Spillage Response",
        "Integrated Information Security Analysis Team",
    ],
    "MA": [
        "System Maintenance Policy and Procedures",
        "Controlled Maintenance",
        "Maintenance Tools",
        "Nonlocal Maintenance",
        "Maintenance Personnel",
        "Timely Maintenance",
        "Field Maintenance",
        "Preventive Maintenance",
        "Predictive Maintenance",
        "Maintenance Reviews and Reports",
    ],
    "MP": [
        "Media Protection Policy and Procedures",
        "Media Access",
        "Media Marking",
        "Media Storage",
        "Media Transport",
        "Media Sanitization",
        "Media Use",
        "Media Downgrading",
        "Cryptographic Protection",
        "Media Distribution",
    ],
    "PE": [
        "Physical and Environmental Protection Policy and Procedures",
        "Physical Access Authorizations",
        "Physical Access Control",
        "Access Control for Transmission",
        "Access Control for Output Devices",
        "Monitoring Physical Access",
        "Visitor Access Records",
        "Power Equipment and Cabling",
        "Emergency Shutoff",
        "Emergency Power",
    ],
    "PL": [
        "Planning Policy and Procedures",
        "System Security and Privacy Plan",
        "System Security and Privacy Plan Update",
        "Rules of Behavior",
        "Privacy Impact Assessment",
        "Security and Privacy Architectures",
        "Concept of Operations",
        "Central Management",
        "Technology Refresh Plan",
        "Baseline Selection",
    ],
    "PM": [
        "Information Security Program Plan",
        "Senior Agency Information Security Officer",
        "Information Security Resources",
        "Plan of Action and Milestones Process",
        "Information System Inventory",
        "Information Security Measures of Performance",
        "Enterprise Architecture",
        "Critical Infrastructure Plan",
        "Risk Management Strategy",
        "Authorization Process",
    ],
    "PS": [
        "Personnel Security Policy and Procedures",
        "Position Risk Designation",
        "Personnel Screening",
        "Personnel Termination",
        "Personnel Transfer",
        "Access Agreements",
        "External Personnel Security",
        "Personnel Sanctions",
        "Position Descriptions",
        "Personnel Actions",
    ],
    "RA": [
        "Risk Assessment Policy and Procedures",
        "Security Categorization",
        "Risk Assessment",
        "Risk Assessment Update",
        "Vulnerability Monitoring and Scanning",
        "Technical Surveillance Countermeasures Survey",
        "Insider Threat Program",
        "Privacy Risk Assessment",
        "Supply Chain Risk Assessment",
        "Criticality Analysis",
    ],
    "SA": [
        "System and Services Acquisition Policy and Procedures",
        "Allocation of Resources",
        "System Development Life Cycle",
        "Acquisition Process",
        "Information System Documentation",
        "Security and Privacy Engineering Principles",
        "External System Services",
        "Developer Configuration Management",
        "Developer Testing and Evaluation",
        "Developer Security Architecture and Design",
    ],
    "SC": [
        "System and Communications Protection Policy and Procedures",
        "Separation of System and User Functionality",
        "Security Function Isolation",
        "Information in Shared System Resources",
        "Denial-of-Service Protection",
        "Boundary Protection",
        "Transmission Confidentiality and Integrity",
        "Network Disconnect",
        "Cryptographic Key Establishment and Management",
        "Cryptographic Protection",
    ],
    "SI": [
        "System and Information Integrity Policy and Procedures",
        "Flaw Remediation",
        "Malicious Code Protection",
        "Information System Monitoring",
        "Security Alerts, Advisories, and Directives",
        "Security Function Verification",
        "Software, Firmware, and Information Integrity",
        "Spam Protection",
        "Information Input Validation",
        "Error Handling",
    ],
    "SR": [
        "Supply Chain Risk Management Policy and Procedures",
        "Supply Chain Risk Management Plan",
        "Supply Chain Controls and Processes",
        "Provenance",
        "Acquisition Strategies, Tools, and Methods",
        "Supply Chain Risk Management Awareness",
        "Inspection of Systems or Components",
        "Notification Agreements",
        "Tamper Resistance and Detection",
        "Validate as Genuine and Not Altered",
    ],
}

# Build the full control list: [(control_id, family_abbr, title), ...]
ALL_CONTROLS = []
for fam, titles in CONTROL_TITLES.items():
    for i, title in enumerate(titles, start=1):
        ALL_CONTROLS.append((f"{fam.lower()}-{i}", fam, title))

# ---------------------------------------------------------------------------
# System names (100)
# ---------------------------------------------------------------------------
SYSTEM_NAMES = [
    "Financial Reporting System",
    "HR Identity Management Platform",
    "Network Operations Center",
    "Incident Response Platform",
    "Cloud Storage Gateway",
    "Endpoint Detection and Response",
    "Security Information and Event Management",
    "Enterprise Resource Planning",
    "Vulnerability Management System",
    "Identity and Access Management",
    "Customer Relationship Management",
    "Supply Chain Management Portal",
    "Patch Management Infrastructure",
    "Data Loss Prevention Platform",
    "Privileged Access Management",
    "Multi-Factor Authentication Service",
    "Audit Log Aggregation System",
    "Configuration Management Database",
    "Change Management Platform",
    "Asset Inventory System",
    "Email Security Gateway",
    "Web Application Firewall",
    "Intrusion Detection System",
    "Network Access Control",
    "Data Warehouse Platform",
    "Business Continuity Management System",
    "Disaster Recovery Orchestration",
    "Backup and Recovery Infrastructure",
    "Container Orchestration Platform",
    "DevSecOps Pipeline",
    "Code Repository and CI/CD System",
    "API Gateway",
    "Zero Trust Network Access",
    "Cloud Workload Protection Platform",
    "Security Orchestration Automation and Response",
    "Threat Intelligence Platform",
    "Insider Threat Detection System",
    "User Behavior Analytics",
    "Digital Forensics Platform",
    "Malware Analysis Sandbox",
    "Penetration Testing Infrastructure",
    "Red Team Operations Platform",
    "Physical Access Control System",
    "Video Surveillance Management",
    "Building Management System",
    "Industrial Control System Monitor",
    "SCADA Integration Gateway",
    "Operational Technology Security Monitor",
    "Mobile Device Management",
    "Unified Endpoint Management",
    "Fleet Management System",
    "Logistics Coordination Platform",
    "Procurement Management System",
    "Contract Management Database",
    "Legal Case Management Platform",
    "Document Management System",
    "Records Management System",
    "Freedom of Information Act Portal",
    "Privacy Impact Assessment Tool",
    "Risk Registry Platform",
    "Policy Management System",
    "Compliance Tracking Dashboard",
    "GRC Automation Platform",
    "Audit Finding Management System",
    "Internal Control Assessment Tool",
    "Budget Execution System",
    "Grants Management Platform",
    "Travel Authorization System",
    "Payroll Processing System",
    "Benefits Administration Platform",
    "Training Management System",
    "Learning Management System",
    "Performance Management Portal",
    "Workforce Planning System",
    "Succession Planning Platform",
    "Onboarding and Offboarding System",
    "Badge and Credentialing System",
    "Security Clearance Tracking Platform",
    "Background Investigation Portal",
    "Secure Communications Platform",
    "Collaboration and Messaging System",
    "Video Conferencing Infrastructure",
    "Enterprise Content Management",
    "Knowledge Management Portal",
    "Geospatial Information System",
    "Data Analytics Platform",
    "Machine Learning Operations Platform",
    "AI Model Registry",
    "Data Governance Platform",
    "Master Data Management System",
    "Enterprise Service Bus",
    "Integration Middleware Platform",
    "Federated Identity Broker",
    "Certificate Authority Infrastructure",
    "Public Key Infrastructure",
    "Secrets Management Vault",
    "Cloud Security Posture Management",
    "Software Composition Analysis Platform",
    "Static Application Security Testing",
    "Dynamic Application Security Testing",
]

# System type pool
SYSTEM_TYPES = ["major_application", "general_support_system", "minor_application"]
ENVIRONMENTS = ["on_prem", "cloud", "hybrid", "saas", "paas", "iaas"]
IMPACT_LEVELS = ["Low", "Moderate", "High"]
AUTH_STATUSES = ["authorized", "in_progress", "expired", "not_authorized"]
AUTH_STATUS_WEIGHTS = [0.40, 0.30, 0.15, 0.15]

# Owner first/last names pool
OWNER_FIRSTS = [
    "James", "Patricia", "Robert", "Linda", "Michael", "Barbara",
    "William", "Elizabeth", "David", "Jennifer", "Richard", "Maria",
    "Joseph", "Susan", "Thomas", "Margaret", "Charles", "Dorothy",
    "Christopher", "Lisa", "Daniel", "Nancy", "Matthew", "Karen",
    "Anthony", "Betty", "Mark", "Helen", "Donald", "Sandra",
]
OWNER_LASTS = [
    "Harrington", "Blackwell", "Okafor", "Patel", "Nakamura", "Rodriguez",
    "Chen", "Williams", "Johnson", "Martinez", "Nguyen", "Anderson",
    "Thompson", "Garcia", "Davis", "Wilson", "Taylor", "Moore",
    "Jackson", "Lee", "Harris", "Clark", "Lewis", "Robinson",
    "Walker", "Hall", "Young", "King", "Wright", "Scott",
]

# Realistic description templates for systems
SYSTEM_DESC_TEMPLATES = [
    "Provides {function} capabilities for the organization, supporting {users} users across {count} business units. Processes {data_type} data classified at the {impact} impact level.",
    "Enterprise platform managing {function} workflows and {data_type} data for {count} operational divisions. Interfaces with {ext} external systems via encrypted API channels.",
    "Mission-critical system responsible for {function} across the enterprise. Hosts {data_type} records for {users} authorized personnel with role-based access controls.",
    "Centralized {function} solution deployed in a {env} environment. Aggregates {data_type} data from {count} field offices and provides unified reporting to leadership.",
    "Supports {function} operations for the program office. Processes sensitive {data_type} information and integrates with {ext} downstream systems for automated reporting.",
]

FUNCTIONS = [
    "financial management", "identity governance", "security monitoring",
    "configuration management", "incident response", "risk assessment",
    "audit logging", "supply chain tracking", "workforce management",
    "data analytics", "vulnerability management", "policy enforcement",
    "access control", "records management", "endpoint protection",
]
DATA_TYPES = [
    "personally identifiable information (PII)", "financial", "personnel",
    "operational", "controlled unclassified information (CUI)", "audit",
    "configuration", "threat intelligence", "compliance", "contractual",
]
EXT_SYSTEMS = [
    "FISMA reporting", "OMB MAX", "FEMA logistics", "GSA procurement",
    "Treasury financial", "OPM personnel", "DHS threat intel",
    "CISA advisories", "NSA cryptographic services",
]

# Control narrative templates by status
NARRATIVE_TEMPLATES = {
    "implemented": [
        "The organization has fully implemented {ctrl_title} in accordance with NIST SP 800-53 Rev 5 requirements. Policy documents are current, reviewed annually, and distributed to all personnel with system access. Automated enforcement mechanisms are in place and tested quarterly. Evidence of implementation is maintained in the system security plan and verified during annual assessments.",
        "Access controls for {ctrl_title} are operationally active across all system components. The responsible role ({role}) conducts monthly reviews of control effectiveness, documents findings, and escalates anomalies to the ISSO within 24 hours. Control inheritance is documented for shared services. Audit logs capture all relevant events and are reviewed weekly by the security team.",
        "Implementation of {ctrl_title} is complete and verified through automated compliance scanning and quarterly manual reviews. Configuration baselines are maintained in the CMDB, deviations are flagged within 4 hours, and remediation is tracked via the POA&M process. The control has been operational since system authorization with zero exceptions noted in the last assessment cycle.",
        "This control is fully operational and tested. The {role} maintains procedure documentation updated within 30 days of any organizational change. Technical safeguards are enforced at the system boundary and verified through continuous monitoring feeds integrated with the enterprise SIEM. No open findings related to this control area.",
    ],
    "in_progress": [
        "Implementation of {ctrl_title} is currently underway. Phase 1 (policy development) is complete; technical configuration is 60% complete with an expected completion date per the project milestone plan. The {role} is coordinating with IT operations to deploy remaining components. Known gaps are documented in the active POA&M and tracked bi-weekly.",
        "Partial implementation exists for {ctrl_title}. Legacy subsystems running on end-of-life platforms have not yet been migrated to the new control framework. A remediation timeline has been established with interim compensating controls in place. Target full implementation is Q3 of the current fiscal year pending budget approval.",
        "Control implementation is in progress following a recent system upgrade. The {role} has drafted updated procedures that are pending final approval from the authorizing official. Automated enforcement is deployed on 7 of 12 system components; remaining components are scheduled for configuration during the next maintenance window.",
        "Policy and procedure components of {ctrl_title} are implemented; technical enforcement is 45% complete. A vendor-supplied patch addressing the remaining capability gap is in test validation. The interim period compensating control (manual review and approval workflow) has been active since the last authorization cycle.",
    ],
    "not_started": [
        "Implementation of {ctrl_title} has not yet been initiated. This control was identified during the recent security categorization review as applicable to the system. The {role} has been assigned responsibility for developing the implementation plan. A milestone entry has been added to the project tracker with an initial target start date in the next fiscal quarter.",
        "This control area has not been addressed. It was flagged during the annual review as a gap requiring remediation. Resource constraints and competing priorities have delayed initiation. A POA&M item has been created and the system owner has been notified. Compensating controls are under evaluation pending formal risk acceptance.",
        "No implementation exists for {ctrl_title}. This control was newly identified as applicable following a significant change to the system boundary. The ISSO is coordinating with the system owner to establish a remediation roadmap. Interim risk acceptance documentation is pending review by the authorizing official.",
    ],
    "not_applicable": [
        "This control is not applicable to the system. The system does not process, store, or transmit information types that trigger this control requirement. Applicability determination was made by the {role} during the security categorization review and documented in the system security plan. Rationale is consistent with NIST SP 800-53 Rev 5 guidance.",
        "{ctrl_title} is designated not applicable for this system based on its operational environment and data classification. The system operates in an air-gapped enclave with no external network connectivity, eliminating the risk scenario this control addresses. N/A determination reviewed and approved during the authorization process.",
        "Control not applicable. The system is a read-only data repository with no user authentication required beyond network perimeter controls. The responsible {role} confirmed N/A designation with supporting documentation in the SSP appendix. This determination is reviewed annually or upon significant system change.",
    ],
    "inherited": [
        "{ctrl_title} is fully inherited from the enterprise General Support System (GSS). The parent system provides this capability as a common control, eliminating the need for system-specific implementation. Inheritance documentation is maintained in the system security plan, referencing the parent system's authorization package and control implementation statement.",
        "This control is inherited from the cloud service provider (CSP) under a FedRAMP-authorized infrastructure. The CSP's implementation satisfies requirements at the system level. Residual responsibilities for the system owner are documented and limited to configuring tenant-specific parameters per CSP guidance.",
        "Control inherited from the enterprise identity management platform operated by the central IT organization. The {role} has reviewed the inherited control documentation and confirmed it meets the requirements applicable to this system. Annual review of the inheritance relationship is conducted as part of the continuous monitoring program.",
    ],
}

# POAM weakness names and descriptions
WEAKNESS_NAMES = [
    ("Privileged Account Review Not Performed", "ac-6"),
    ("Multi-Factor Authentication Not Enforced", "ia-2"),
    ("Audit Log Review Gap", "au-6"),
    ("Patch Management Lag > 30 Days", "si-2"),
    ("Incomplete System Security Plan", "pl-2"),
    ("Configuration Baseline Not Documented", "cm-2"),
    ("Contingency Plan Not Tested", "cp-4"),
    ("Personnel Screening Records Incomplete", "ps-3"),
    ("Vulnerability Scan Overdue", "ra-5"),
    ("Incident Response Procedures Not Updated", "ir-8"),
    ("Media Sanitization Not Documented", "mp-6"),
    ("Remote Access Session Timeout Not Configured", "ac-12"),
    ("Supply Chain Risk Assessment Not Completed", "sr-3"),
    ("Encryption at Rest Not Implemented", "sc-28"),
    ("Security Awareness Training Overdue", "at-2"),
    ("Boundary Protection Controls Incomplete", "sc-7"),
    ("Software Composition Analysis Not Performed", "sa-11"),
    ("Contractor Access Agreement Expired", "ps-6"),
    ("Data Backup Testing Not Verified", "cp-9"),
    ("Certificate Expiry Not Monitored", "sc-17"),
    ("Least Privilege Review Overdue", "ac-6"),
    ("Log Retention Below Minimum Requirement", "au-11"),
    ("Unauthorized Software Detected", "cm-7"),
    ("Insider Threat Controls Not Implemented", "ps-8"),
    ("Privacy Impact Assessment Outdated", "ra-8"),
]

REMEDIATION_PLANS = [
    "Implement automated tooling to enforce control requirement. Assign remediation ownership to system administrator. Schedule completion within 90 days with bi-weekly progress reviews.",
    "Update policy documentation and conduct technical implementation sprint. Validate via configuration scan and submit evidence to ISSO for review. Target closure in next quarterly review cycle.",
    "Procure and deploy enterprise solution to address identified gap. Engage vendor for implementation support. Pilot on non-production environment before production rollout.",
    "Conduct manual review and apply interim compensating controls. Develop standard operating procedure for ongoing compliance. Full technical remediation scheduled for next maintenance window.",
    "Escalate to system owner and program manager for resource allocation. Interim risk acceptance documentation submitted pending board approval. Full remediation tied to FY budget cycle.",
]

DETECTION_SOURCES = ["assessment", "scan", "audit", "pentest", "self_report"]
SEVERITIES = ["Critical", "High", "Moderate", "Low", "Informational"]
SEVERITY_WEIGHTS = [0.05, 0.20, 0.45, 0.25, 0.05]
POAM_STATUSES = ["open", "in_progress", "closed", "risk_accepted", "false_positive"]
POAM_STATUS_WEIGHTS = [0.35, 0.35, 0.15, 0.10, 0.05]

RESPONSIBLE_PARTIES = [
    "Information System Owner", "ISSO", "System Administrator",
    "Network Operations", "Security Operations Center",
    "IT Operations", "Compliance Team", "Program Office",
    "Cloud Operations", "Identity Management Team",
]

# Risk data
RISK_NAMES = [
    ("Unauthorized Access to Sensitive Data", "human"),
    ("Ransomware Attack on Production Systems", "human"),
    ("Insider Threat Data Exfiltration", "human"),
    ("Supply Chain Compromise", "human"),
    ("Phishing-Induced Credential Theft", "human"),
    ("Unpatched Critical Vulnerability Exploitation", "technical"),
    ("Misconfigured Cloud Storage Exposure", "technical"),
    ("Legacy System End-of-Life Risk", "technical"),
    ("Database Injection Attack", "human"),
    ("Denial of Service Against Critical Services", "human"),
    ("Power Failure Causing Data Loss", "environmental"),
    ("Natural Disaster Disrupting Operations", "environmental"),
    ("Third-Party Vendor Breach", "human"),
    ("Weak Authentication Bypass", "technical"),
    ("Data Leakage via Unsanctioned Shadow IT", "human"),
    ("Certificate Expiry Causing Service Outage", "technical"),
    ("Social Engineering Attack on Privileged Users", "human"),
    ("Backup Failure Leading to Unrecoverable Data", "technical"),
    ("Zero-Day Vulnerability in Critical Component", "technical"),
    ("Physical Theft of Portable Media", "human"),
]

THREAT_EVENTS = [
    "Spear phishing campaign targeting system administrators",
    "Exploitation of known CVE in unpatched component",
    "Brute-force attack against authentication service",
    "Man-in-the-middle interception of API communications",
    "SQL injection against web-facing application layer",
    "Physical intrusion into server room",
    "Malicious code insertion via compromised software update",
    "Credential stuffing using leaked password databases",
    "Lateral movement following initial access compromise",
    "Data exfiltration via encrypted covert channel",
]

VULNERABILITIES = [
    "Insufficient patch management processes allow vulnerabilities to persist beyond acceptable remediation windows.",
    "Lack of multi-factor authentication on privileged accounts increases susceptibility to credential-based attacks.",
    "Inadequate network segmentation permits lateral movement between system tiers.",
    "Weak logging and monitoring posture reduces detection capability for advanced persistent threats.",
    "End-of-life software components no longer receive vendor security updates.",
    "Overly permissive access control configurations violate least privilege principles.",
    "Absence of data-at-rest encryption exposes sensitive records to physical media theft.",
    "Incomplete backup testing creates uncertainty around recovery time and recovery point objectives.",
    "Third-party integrations lack contractual security requirements and periodic assessments.",
    "Insufficient security awareness training increases susceptibility to social engineering.",
]

TREATMENT_PLANS = [
    "Deploy technical controls to eliminate or reduce attack surface. Implement continuous monitoring to detect residual risk. Review effectiveness quarterly.",
    "Transfer risk through cyber insurance policy and contractual liability clauses with third-party service providers.",
    "Accept residual risk with documented rationale approved by authorizing official. Review acceptance annually.",
    "Avoid risk by decommissioning vulnerable component and migrating functionality to hardened successor system.",
    "Implement compensating controls including enhanced monitoring, additional authentication factors, and network access restrictions.",
]

TREATMENTS = ["Accept", "Mitigate", "Transfer", "Avoid"]
TREATMENT_WEIGHTS = [0.10, 0.65, 0.15, 0.10]

ROLES = [
    "Information System Security Officer (ISSO)",
    "System Administrator",
    "Database Administrator",
    "Network Engineer",
    "Security Analyst",
    "System Owner",
    "Privacy Officer",
    "Configuration Manager",
    "Incident Response Team Lead",
    "Compliance Manager",
]

# Candidate fake names
CANDIDATE_FIRST = [
    "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn",
    "Skyler", "Reese", "Cameron", "Drew", "Alexis", "Blake", "Kendall",
    "Parker", "Finley", "Rowan", "Sage", "Dakota", "River",
]
CANDIDATE_LAST = [
    "Montgomery", "Blackwood", "Fitzgerald", "Osei", "Nakashima",
    "Vasquez", "Petrov", "Obasi", "Lindqvist", "Brennan",
    "Hashimoto", "Delacroix", "Okonkwo", "Kowalski", "Ramirez",
    "Bergstrom", "Mwangi", "Volkov", "Chatterjee", "Oduya",
]

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def new_uuid() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def future_date(min_days: int = 30, max_days: int = 365) -> str:
    delta = timedelta(days=random.randint(min_days, max_days))
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%d")


def past_date(min_days: int = 30, max_days: int = 730) -> str:
    delta = timedelta(days=random.randint(min_days, max_days))
    return (datetime.now(timezone.utc) - delta).strftime("%Y-%m-%d")


def varied_due_date() -> str:
    """Mix of overdue, near-future, and far-future dates."""
    roll = random.random()
    if roll < 0.25:
        return past_date(10, 180)        # overdue
    elif roll < 0.55:
        return future_date(1, 60)        # upcoming / urgent
    else:
        return future_date(61, 365)      # planned / far future


def weighted_choice(choices, weights):
    return random.choices(choices, weights=weights, k=1)[0]


def build_narrative(status: str, ctrl_title: str, role: str) -> str:
    templates = NARRATIVE_TEMPLATES[status]
    tmpl = random.choice(templates)
    return tmpl.format(ctrl_title=ctrl_title, role=role)


def build_system_description(sys_name: str, impact: str) -> str:
    tmpl = random.choice(SYSTEM_DESC_TEMPLATES)
    return tmpl.format(
        function=random.choice(FUNCTIONS),
        users=random.randint(50, 5000),
        count=random.randint(2, 20),
        data_type=random.choice(DATA_TYPES),
        impact=impact,
        env=random.choice(["cloud", "hybrid", "on-premises"]),
        ext=random.choice(EXT_SYSTEMS),
    )


def compute_risk_level(score: int) -> str:
    if score >= 20:
        return "Critical"
    elif score >= 12:
        return "High"
    elif score >= 6:
        return "Moderate"
    else:
        return "Low"


def print_progress(label: str, current: int, total: int, end: str = "\r"):
    bar_len = 30
    filled = int(bar_len * current / total) if total else bar_len
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"  {label} [{bar}] {current}/{total}", end=end, flush=True)


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

def seed_systems(cur) -> list:
    """Insert 100 [SEED] systems. Returns list of system IDs."""
    print("Creating systems...")
    system_ids = []
    for i, raw_name in enumerate(SYSTEM_NAMES, start=1):
        sid = new_uuid()
        name = f"[SEED] {raw_name}"
        abbr = "".join(w[0] for w in raw_name.split() if w)[:6].upper()
        sys_type = random.choice(SYSTEM_TYPES)
        env = random.choice(ENVIRONMENTS)
        conf = random.choice(IMPACT_LEVELS)
        integ = random.choice(IMPACT_LEVELS)
        avail = random.choice(IMPACT_LEVELS)
        overall = max([conf, integ, avail], key=lambda x: ["Low", "Moderate", "High"].index(x))
        auth_status = weighted_choice(AUTH_STATUSES, AUTH_STATUS_WEIGHTS)

        # Auth dates
        if auth_status == "authorized":
            auth_date = past_date(30, 365)
            auth_expiry = future_date(30, 730)
        elif auth_status == "expired":
            auth_date = past_date(365, 1460)
            auth_expiry = past_date(10, 365)
        else:
            auth_date = None
            auth_expiry = None

        owner_first = random.choice(OWNER_FIRSTS)
        owner_last = random.choice(OWNER_LASTS)
        owner_name = f"{owner_first} {owner_last}"
        owner_email = f"{owner_first.lower()}.{owner_last.lower()}@agency.gov"

        description = build_system_description(name, overall)
        purpose = f"The system supports {random.choice(FUNCTIONS)} mission functions and is operated under the authority of the program office in accordance with applicable federal information security requirements."
        boundary = f"The authorization boundary includes all hardware, software, and interconnections documented in the system inventory. External connections are limited to {random.randint(1, 5)} authorized interfaces with documented interconnection security agreements (ISAs)."

        cur.execute(
            """
            INSERT INTO systems
              (id, name, abbreviation, system_type, environment,
               owner_name, owner_email, description, purpose, boundary,
               confidentiality_impact, integrity_impact, availability_impact, overall_impact,
               auth_status, auth_date, auth_expiry, created_at, updated_at, created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                sid, name, abbr, sys_type, env,
                owner_name, owner_email, description, purpose, boundary,
                conf, integ, avail, overall,
                auth_status, auth_date, auth_expiry,
                now_iso(), now_iso(), "seed-script",
            ),
        )
        system_ids.append(sid)
        print_progress("systems", i, len(SYSTEM_NAMES))
    print()  # newline after progress
    return system_ids


def seed_system_controls(cur, system_ids: list):
    """Insert ~150 controls per system sampled from ALL_CONTROLS."""
    print("Creating system_controls...")
    status_choices = ["implemented", "in_progress", "not_started", "not_applicable", "inherited"]
    status_weights = [0.40, 0.25, 0.20, 0.10, 0.05]
    impl_types = ["system", "hybrid", "inherited"]

    total_systems = len(system_ids)
    for idx, sid in enumerate(system_ids, start=1):
        sample = random.sample(ALL_CONTROLS, min(150, len(ALL_CONTROLS)))
        for ctrl_id, family, title in sample:
            status = weighted_choice(status_choices, status_weights)
            impl_type = "inherited" if status == "inherited" else random.choice(impl_types[:2])
            role = random.choice(ROLES)
            narrative = build_narrative(status, title, role) if status != "not_started" else None
            inherited_from = None
            inherited_narrative = None
            if status == "inherited" and len(system_ids) > 1:
                inherited_from = random.choice([s for s in system_ids if s != sid])
                inherited_narrative = f"Control implementation provided by the parent system. Inheriting system configures tenant parameters per parent system guidance documented in the shared SSP appendix."

            ts = now_iso()
            cur.execute(
                """
                INSERT OR IGNORE INTO system_controls
                  (system_id, control_id, control_family, control_title,
                   status, implementation_type, narrative, responsible_role,
                   inherited_from, inherited_narrative,
                   last_updated_by, last_updated_at, created_at, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    sid, ctrl_id, family, title,
                    status, impl_type, narrative, role,
                    inherited_from, inherited_narrative,
                    "seed-script", ts, ts, "seed-script",
                ),
            )
        print_progress("system_controls", idx, total_systems)
    print()


def seed_poam_items(cur, system_ids: list):
    """Insert 5-15 POA&M items per system."""
    print("Creating poam_items...")
    total = len(system_ids)
    for idx, sid in enumerate(system_ids, start=1):
        count = random.randint(5, 15)
        used_weaknesses = random.sample(WEAKNESS_NAMES, min(count, len(WEAKNESS_NAMES)))
        for w_name, ctrl_id in used_weaknesses:
            severity = weighted_choice(SEVERITIES, SEVERITY_WEIGHTS)
            status = weighted_choice(POAM_STATUSES, POAM_STATUS_WEIGHTS)
            completion_date = None
            if status == "closed":
                completion_date = past_date(10, 180)

            cur.execute(
                """
                INSERT INTO poam_items
                  (id, system_id, control_id, weakness_name, weakness_description,
                   detection_source, severity, responsible_party, resources_required,
                   scheduled_completion, status, remediation_plan, completion_date,
                   comments, created_at, updated_at, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_uuid(), sid, ctrl_id,
                    f"[SEED] {w_name}",
                    f"During a recent {random.choice(DETECTION_SOURCES)} activity, the security team identified that {w_name.lower()} for this system. This weakness increases the likelihood of unauthorized access or data exposure and requires timely remediation in accordance with the POA&M process.",
                    random.choice(DETECTION_SOURCES),
                    severity,
                    random.choice(RESPONSIBLE_PARTIES),
                    f"Estimated {random.choice(['4 hours', '8 hours', '2 days', '1 week', '1 FTE-month'])} of engineering effort and potential software licensing costs.",
                    varied_due_date(),
                    status,
                    random.choice(REMEDIATION_PLANS),
                    completion_date,
                    f"Identified via {random.choice(DETECTION_SOURCES)}. Assigned to {random.choice(RESPONSIBLE_PARTIES)} for remediation tracking." if random.random() > 0.4 else None,
                    now_iso(), now_iso(), "seed-script",
                ),
            )
        print_progress("poam_items", idx, total)
    print()


def seed_risks(cur, system_ids: list):
    """Insert 3-8 risks per system."""
    print("Creating risks...")
    total = len(system_ids)
    for idx, sid in enumerate(system_ids, start=1):
        count = random.randint(3, 8)
        used_risks = random.sample(RISK_NAMES, min(count, len(RISK_NAMES)))
        for r_name, threat_src in used_risks:
            likelihood = random.randint(1, 5)
            impact = random.randint(1, 5)
            risk_score = likelihood * impact
            risk_level = compute_risk_level(risk_score)
            treatment = weighted_choice(TREATMENTS, TREATMENT_WEIGHTS)
            residual_likelihood = max(1, likelihood - random.randint(1, 2))
            residual_impact = max(1, impact - random.randint(0, 1))
            residual_score = residual_likelihood * residual_impact
            residual_level = compute_risk_level(residual_score)
            status = random.choices(["open", "closed", "accepted"], weights=[0.60, 0.20, 0.20])[0]

            cur.execute(
                """
                INSERT INTO risks
                  (id, system_id, risk_name, risk_description,
                   threat_source, threat_event, vulnerability,
                   likelihood, impact, risk_score, risk_level,
                   treatment, treatment_plan,
                   residual_likelihood, residual_impact, residual_score, residual_level,
                   owner, status, review_date, created_at, updated_at, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_uuid(), sid,
                    f"[SEED] {r_name}",
                    f"This risk represents the potential for {r_name.lower()} affecting system confidentiality, integrity, or availability. The threat source is {threat_src} in nature. Materialization of this risk could result in {random.choice(['operational disruption', 'data breach', 'regulatory non-compliance', 'reputational damage', 'financial loss'])} and may trigger mandatory breach reporting obligations.",
                    threat_src,
                    random.choice(THREAT_EVENTS),
                    random.choice(VULNERABILITIES),
                    likelihood, impact, risk_score, risk_level,
                    treatment,
                    random.choice(TREATMENT_PLANS),
                    residual_likelihood, residual_impact, residual_score, residual_level,
                    random.choice(RESPONSIBLE_PARTIES),
                    status,
                    future_date(30, 365),
                    now_iso(), now_iso(), "seed-script",
                ),
            )
        print_progress("risks", idx, total)
    print()


def seed_submissions(cur, system_ids: list):
    """Insert 0-2 submissions per system."""
    print("Creating submissions...")
    sub_types = ["initial", "reauthorization", "significant_change", "annual_review"]
    sub_statuses = ["draft", "submitted", "under_review", "authorized", "denied", "withdrawn"]
    sub_status_weights = [0.15, 0.20, 0.20, 0.30, 0.10, 0.05]

    total = len(system_ids)
    for idx, sid in enumerate(system_ids, start=1):
        count = random.choices([0, 1, 2], weights=[0.30, 0.50, 0.20])[0]
        for _ in range(count):
            status = weighted_choice(sub_statuses, sub_status_weights)
            submitted_at = None
            reviewer = None
            reviewed_at = None
            decision = None
            decision_date = None
            ato_expiry = None

            if status not in ("draft",):
                submitted_at = datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))
                submitted_at = submitted_at.isoformat()

            if status in ("authorized", "denied"):
                reviewer = f"{random.choice(OWNER_FIRSTS)} {random.choice(OWNER_LASTS)}"
                reviewed_at = (
                    datetime.now(timezone.utc) - timedelta(days=random.randint(5, 60))
                ).isoformat()
                decision = "authorized" if status == "authorized" else "denied"
                decision_date = past_date(5, 60)
                if decision == "authorized":
                    ato_expiry = future_date(365, 1095)

            ctrl_total = random.randint(100, 190)
            ctrl_impl = int(ctrl_total * random.uniform(0.55, 0.95))
            ctrl_na = int(ctrl_total * random.uniform(0.05, 0.15))
            ctrl_gap = ctrl_total - ctrl_impl - ctrl_na

            cur.execute(
                """
                INSERT INTO submissions
                  (id, system_id, submission_type, status, package_notes,
                   submitted_by, submitted_at, reviewer, reviewed_at,
                   decision, decision_date, ato_expiry,
                   controls_total, controls_impl, controls_na, controls_gap,
                   created_at, updated_at, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_uuid(), sid,
                    random.choice(sub_types),
                    status,
                    f"[SEED] Authorization package submitted for {random.choice(['annual review', 'initial authorization', 'reauthorization following significant change', 'continuous monitoring review'])}. Package includes SSP, SAR, POA&M, and supporting artifacts.",
                    random.choice([e["username"] for e in EMPLOYEES]),
                    submitted_at,
                    reviewer, reviewed_at,
                    decision, decision_date, ato_expiry,
                    ctrl_total, ctrl_impl, ctrl_na, max(0, ctrl_gap),
                    now_iso(), now_iso(), "seed-script",
                ),
            )
        print_progress("submissions", idx, total)
    print()


def seed_candidates(cur) -> list:
    """Insert 20 [SEED] candidates. Returns list of (id, name) tuples."""
    print("Creating candidates...")
    assert len(CANDIDATE_FIRST) == 20 and len(CANDIDATE_LAST) == 20
    candidate_records = []
    for i, (first, last) in enumerate(zip(CANDIDATE_FIRST, CANDIDATE_LAST), start=1):
        cid = new_uuid()
        name = f"[SEED] {first} {last}"
        email = f"{first.lower()}.{last.lower()}@example.com"
        cur.execute(
            "INSERT INTO candidates (id, name, email, created_at) VALUES (?,?,?,?)",
            (cid, name, email, now_iso()),
        )
        candidate_records.append((cid, name))
        print_progress("candidates", i, 20)
    print()
    return candidate_records


def seed_assessments(cur, candidate_records: list, system_ids: list) -> list:
    """Insert 1-3 assessments per candidate. Returns list of assessment IDs."""
    print("Creating assessments...")
    assessment_ids = []
    total = len(candidate_records)
    for idx, (cid, cname) in enumerate(candidate_records, start=1):
        count = random.randint(1, 3)
        for j in range(count):
            aid = new_uuid()
            ssp_score = round(random.uniform(40.0, 98.0), 1)
            quiz_score = round(random.uniform(50.0, 100.0), 1)
            combined = round(0.70 * ssp_score + 0.30 * quiz_score, 1)
            is_allstar = combined >= 80 and quiz_score >= 80
            ctrl_found = random.randint(60, 150)
            ctrl_complete = int(ctrl_found * random.uniform(0.50, 0.85))
            ctrl_partial = int(ctrl_found * random.uniform(0.05, 0.20))
            ctrl_insuff = int(ctrl_found * random.uniform(0.02, 0.10))
            ctrl_not_found = ctrl_found - ctrl_complete - ctrl_partial - ctrl_insuff

            filename = f"[SEED]_SSP_{cname.replace('[SEED] ', '').replace(' ', '_')}_{j+1}.pdf"
            sys_id = random.choice(system_ids) if random.random() > 0.3 else None

            cur.execute(
                """
                INSERT INTO assessments
                  (id, candidate_id, system_id, filename, file_path, uploaded_at, submitted_by,
                   status, total_controls_found, controls_complete, controls_partial,
                   controls_insufficient, controls_not_found, ssp_score, quiz_score,
                   combined_score, is_allstar, email_sent, error_message)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    aid, cid, sys_id,
                    filename,
                    f"uploads/{filename}",
                    (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))).isoformat(),
                    random.choice([e["username"] for e in EMPLOYEES]),
                    "complete",
                    ctrl_found, ctrl_complete, ctrl_partial,
                    ctrl_insuff, max(0, ctrl_not_found),
                    ssp_score, quiz_score, combined,
                    is_allstar,
                    random.random() > 0.3,
                    None,
                ),
            )
            assessment_ids.append(aid)
        print_progress("assessments", idx, total)
    print()
    return assessment_ids


def seed_system_assignments(cur, system_ids: list):
    """Assign each system to 1-2 employees."""
    print("Creating system_assignments...")
    total = len(system_ids)
    for idx, sid in enumerate(system_ids, start=1):
        assignees = random.sample(EMPLOYEES, random.randint(1, 2))
        for emp in assignees:
            cur.execute(
                """
                INSERT INTO system_assignments
                  (system_id, remote_user, assigned_by, assigned_at, note)
                VALUES (?,?,?,?,?)
                """,
                (
                    sid,
                    emp["username"],
                    "seed-script",
                    now_iso(),
                    f"Assigned during initial system catalog population. Primary point of contact: {emp['name']}.",
                ),
            )
        print_progress("system_assignments", idx, total)
    print()


def seed_daily_quiz_activity(cur):
    """Insert 14 days of quiz history for each employee."""
    print("Creating daily_quiz_activity...")
    today = datetime.now(timezone.utc).date()
    total = len(EMPLOYEES)
    for idx, emp in enumerate(EMPLOYEES, start=1):
        for day_offset in range(14):
            quiz_date = (today - timedelta(days=day_offset)).isoformat()
            # Employees miss some days (30% skip rate)
            if random.random() < 0.30:
                continue
            score = random.randint(40, 100)
            passed = score >= 75
            completed_at = datetime.combine(
                today - timedelta(days=day_offset),
                datetime.min.time(),
                tzinfo=timezone.utc,
            ) + timedelta(hours=random.randint(8, 17), minutes=random.randint(0, 59))

            cur.execute(
                """
                INSERT OR IGNORE INTO daily_quiz_activity
                  (remote_user, quiz_date, score, passed, completed_at)
                VALUES (?,?,?,?,?)
                """,
                (emp["username"], quiz_date, score, passed, completed_at.isoformat()),
            )
        print_progress("daily_quiz_activity", idx, total)
    print()


# ---------------------------------------------------------------------------
# Main seed / clean / status operations
# ---------------------------------------------------------------------------

def do_seed(db_path: str):
    random.seed(42)   # reproducible run
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")

    try:
        print(f"\nSeeding BLACKSITE database: {db_path}\n")
        system_ids = seed_systems(cur)
        con.commit()

        seed_system_controls(cur, system_ids)
        con.commit()

        seed_poam_items(cur, system_ids)
        con.commit()

        seed_risks(cur, system_ids)
        con.commit()

        seed_submissions(cur, system_ids)
        con.commit()

        candidate_records = seed_candidates(cur)
        con.commit()

        seed_assessments(cur, candidate_records, system_ids)
        con.commit()

        seed_system_assignments(cur, system_ids)
        con.commit()

        seed_daily_quiz_activity(cur)
        con.commit()

        # Summary
        print("\nSeed complete. Record counts:")
        for table, col in [
            ("systems",               "name"),
            ("system_controls",       "control_id"),
            ("poam_items",            "weakness_name"),
            ("risks",                 "risk_name"),
            ("submissions",           "package_notes"),
            ("candidates",            "name"),
            ("assessments",           "filename"),
            ("system_assignments",    "remote_user"),
            ("daily_quiz_activity",   "remote_user"),
        ]:
            if table in ("system_assignments", "daily_quiz_activity"):
                # These join to seeded tables — count via system_assignments→systems or dqa all
                if table == "system_assignments":
                    cur.execute(
                        "SELECT COUNT(*) FROM system_assignments sa JOIN systems s ON sa.system_id=s.id WHERE s.name LIKE '[SEED]%'"
                    )
                else:
                    cur.execute(
                        "SELECT COUNT(*) FROM daily_quiz_activity WHERE remote_user IN ({})".format(
                            ",".join("?" * len(EMPLOYEES))
                        ),
                        [e["username"] for e in EMPLOYEES],
                    )
            elif table == "system_controls":
                cur.execute(
                    "SELECT COUNT(*) FROM system_controls sc JOIN systems s ON sc.system_id=s.id WHERE s.name LIKE '[SEED]%'"
                )
            elif table == "submissions":
                cur.execute(
                    "SELECT COUNT(*) FROM submissions sub JOIN systems s ON sub.system_id=s.id WHERE s.name LIKE '[SEED]%'"
                )
            else:
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} LIKE '[SEED]%'")
            (n,) = cur.fetchone()
            print(f"  {table:<26} {n:>6} records")

        db_size = os.path.getsize(db_path)
        print(f"\nDatabase size: {db_size / (1024*1024):.2f} MB ({db_path})")

    except Exception as exc:
        con.rollback()
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise
    finally:
        con.close()


def do_clean(db_path: str):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys=OFF")   # disable FK checks for bulk delete

    print(f"\nCleaning [SEED] records from: {db_path}\n")

    # Order matters: delete dependents first
    try:
        # Gather seeded system IDs
        cur.execute("SELECT id FROM systems WHERE name LIKE '[SEED]%'")
        seeded_sys_ids = [row[0] for row in cur.fetchall()]

        # Gather seeded candidate IDs
        cur.execute("SELECT id FROM candidates WHERE name LIKE '[SEED]%'")
        seeded_cand_ids = [row[0] for row in cur.fetchall()]

        # Gather seeded assessment IDs (from seeded candidates)
        seeded_assess_ids = []
        if seeded_cand_ids:
            ph = ",".join("?" * len(seeded_cand_ids))
            cur.execute(f"SELECT id FROM assessments WHERE candidate_id IN ({ph})", seeded_cand_ids)
            seeded_assess_ids = [row[0] for row in cur.fetchall()]

        # Also grab assessments linked to seeded systems
        if seeded_sys_ids:
            ph = ",".join("?" * len(seeded_sys_ids))
            cur.execute(f"SELECT id FROM assessments WHERE system_id IN ({ph}) AND filename LIKE '[SEED]%'", seeded_sys_ids)
            extra = [row[0] for row in cur.fetchall()]
            seeded_assess_ids = list(set(seeded_assess_ids + extra))

        totals = {}

        # control_results linked to seeded assessments
        if seeded_assess_ids:
            ph = ",".join("?" * len(seeded_assess_ids))
            cur.execute(f"DELETE FROM control_results WHERE assessment_id IN ({ph})", seeded_assess_ids)
            totals["control_results"] = cur.rowcount
            cur.execute(f"DELETE FROM quiz_responses WHERE assessment_id IN ({ph})", seeded_assess_ids)
            totals["quiz_responses"] = cur.rowcount
            cur.execute(f"DELETE FROM control_edits WHERE assessment_id IN ({ph})", seeded_assess_ids)
            totals["control_edits"] = cur.rowcount

        # assessments
        if seeded_assess_ids:
            ph = ",".join("?" * len(seeded_assess_ids))
            cur.execute(f"DELETE FROM assessments WHERE id IN ({ph})", seeded_assess_ids)
            totals["assessments"] = cur.rowcount

        # candidates
        if seeded_cand_ids:
            ph = ",".join("?" * len(seeded_cand_ids))
            cur.execute(f"DELETE FROM candidates WHERE id IN ({ph})", seeded_cand_ids)
            totals["candidates"] = cur.rowcount

        # system-linked tables
        if seeded_sys_ids:
            ph = ",".join("?" * len(seeded_sys_ids))
            cur.execute(f"DELETE FROM system_controls WHERE system_id IN ({ph})", seeded_sys_ids)
            totals["system_controls"] = cur.rowcount
            cur.execute(f"DELETE FROM poam_items WHERE system_id IN ({ph})", seeded_sys_ids)
            totals["poam_items"] = cur.rowcount
            cur.execute(f"DELETE FROM risks WHERE system_id IN ({ph})", seeded_sys_ids)
            totals["risks"] = cur.rowcount
            cur.execute(f"DELETE FROM submissions WHERE system_id IN ({ph})", seeded_sys_ids)
            totals["submissions"] = cur.rowcount
            cur.execute(f"DELETE FROM system_assignments WHERE system_id IN ({ph})", seeded_sys_ids)
            totals["system_assignments"] = cur.rowcount

        # daily_quiz_activity seeded employees (only rows inserted by seed)
        cur.execute(
            "DELETE FROM daily_quiz_activity WHERE remote_user IN ({}) AND id IN (SELECT id FROM daily_quiz_activity WHERE remote_user IN ({}))".format(
                ",".join("?" * len(EMPLOYEES)),
                ",".join("?" * len(EMPLOYEES)),
            ),
            [e["username"] for e in EMPLOYEES] * 2,
        )
        totals["daily_quiz_activity"] = cur.rowcount

        # systems last
        if seeded_sys_ids:
            ph = ",".join("?" * len(seeded_sys_ids))
            cur.execute(f"DELETE FROM systems WHERE id IN ({ph})", seeded_sys_ids)
            totals["systems"] = cur.rowcount

        con.commit()
        print("Deleted records:")
        for table, n in totals.items():
            print(f"  {table:<26} {n:>6} rows removed")
        print("\nClean complete.")

    except Exception as exc:
        con.rollback()
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise
    finally:
        cur.execute("PRAGMA foreign_keys=ON")
        con.close()


def do_status(db_path: str):
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    print(f"\n[SEED] record counts in: {db_path}\n")

    checks = [
        ("systems",         "SELECT COUNT(*) FROM systems WHERE name LIKE '[SEED]%'", None),
        ("system_controls", "SELECT COUNT(*) FROM system_controls sc JOIN systems s ON sc.system_id=s.id WHERE s.name LIKE '[SEED]%'", None),
        ("poam_items",      "SELECT COUNT(*) FROM poam_items WHERE weakness_name LIKE '[SEED]%'", None),
        ("risks",           "SELECT COUNT(*) FROM risks WHERE risk_name LIKE '[SEED]%'", None),
        ("submissions",     "SELECT COUNT(*) FROM submissions sub JOIN systems s ON sub.system_id=s.id WHERE s.name LIKE '[SEED]%'", None),
        ("candidates",      "SELECT COUNT(*) FROM candidates WHERE name LIKE '[SEED]%'", None),
        ("assessments",     "SELECT COUNT(*) FROM assessments WHERE filename LIKE '[SEED]%'", None),
        ("system_assignments",
         "SELECT COUNT(*) FROM system_assignments sa JOIN systems s ON sa.system_id=s.id WHERE s.name LIKE '[SEED]%'",
         None),
        ("daily_quiz_activity",
         "SELECT COUNT(*) FROM daily_quiz_activity WHERE remote_user IN ({})".format(
             ",".join("?" * len(EMPLOYEES))
         ),
         [e["username"] for e in EMPLOYEES]),
    ]

    total_seeded = 0
    for label, sql, params in checks:
        cur.execute(sql, params or [])
        (n,) = cur.fetchone()
        total_seeded += n
        status_icon = "+" if n > 0 else " "
        print(f"  [{status_icon}] {label:<26} {n:>6} records")

    print(f"\n  Total seed records: {total_seeded}")

    db_size = os.path.getsize(db_path)
    print(f"  Database size:      {db_size / (1024*1024):.2f} MB")
    con.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="BLACKSITE seed script — populate or clean [SEED] test data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove ALL [SEED] records from the database.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Report how many [SEED] records currently exist.",
    )
    parser.add_argument(
        "--db",
        default=DB_PATH,
        help=f"Path to SQLite database (default: {DB_PATH})",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"ERROR: Database not found at {args.db}", file=sys.stderr)
        print("Run the BLACKSITE app at least once to initialize the database.", file=sys.stderr)
        sys.exit(1)

    if args.clean:
        do_clean(args.db)
    elif args.status:
        do_status(args.db)
    else:
        do_seed(args.db)


if __name__ == "__main__":
    main()
