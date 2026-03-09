"""
seed_crosswalks.py — Phase 30
Populates compliance_frameworks, framework_controls, and control_crosswalks
using official NIST-published mappings and CIS/community mappings.

Frameworks seeded:
  - NIST CSF 2.0        (csf2)        — NIST official crosswalk to 800-53r5
  - NIST SP 800-171r3   (sp800171)    — Derived directly from 800-53r5 (Appendix D)
  - CMMC 2.0            (cmmc2)       — DoD 32 CFR Part 170 mappings
  - ISO/IEC 27001:2022  (iso27001)    — NIST official crosswalk
  - CIS Controls v8.1   (cis8)        — CIS official 800-53r5 mappings

Run: cd /home/graycat/projects/blacksite && .venv/bin/python3 scripts/seed_crosswalks.py
"""
import sqlite3, uuid, sys, os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "blacksite.db"

# ─────────────────────────────────────────────────────────────────────────────
# Framework metadata
# ─────────────────────────────────────────────────────────────────────────────
FRAMEWORKS = [
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "nist-csf-2.0")),
        "name":        "NIST Cybersecurity Framework 2.0",
        "short_name":  "csf2",
        "version":     "2.0",
        "category":    "federal",
        "published_by":"NIST",
        "description": "Voluntary framework for improving critical infrastructure cybersecurity. "
                       "CSF 2.0 adds a new GOVERN function and expands supply chain guidance.",
        "source_url":  "https://csrc.nist.gov/pubs/cswp/29/final",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "nist-sp800-171r3")),
        "name":        "NIST SP 800-171 Rev 3",
        "short_name":  "sp800171",
        "version":     "Rev 3",
        "category":    "federal",
        "published_by":"NIST",
        "description": "Protecting Controlled Unclassified Information (CUI) in Nonfederal Systems. "
                       "Required for DoD contractors under DFARS 252.204-7012.",
        "source_url":  "https://csrc.nist.gov/pubs/sp/800/171/r3/final",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "cmmc-2.0")),
        "name":        "CMMC 2.0",
        "short_name":  "cmmc2",
        "version":     "2.0",
        "category":    "federal",
        "published_by":"DoD",
        "description": "Cybersecurity Maturity Model Certification — DoD contractor requirement "
                       "for handling FCI and CUI. Three levels: Foundational (L1), Advanced (L2), Expert (L3).",
        "source_url":  "https://www.acq.osd.mil/cmmc/",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "iso-27001-2022")),
        "name":        "ISO/IEC 27001:2022",
        "short_name":  "iso27001",
        "version":     "2022",
        "category":    "industry",
        "published_by":"ISO/IEC",
        "description": "International standard for Information Security Management Systems (ISMS). "
                       "Annex A provides 93 controls across 4 themes.",
        "source_url":  "https://www.iso.org/standard/82875.html",
    },
    {
        "id":          str(uuid.uuid5(uuid.NAMESPACE_DNS, "cis-controls-v8.1")),
        "name":        "CIS Controls v8.1",
        "short_name":  "cis8",
        "version":     "v8.1",
        "category":    "industry",
        "published_by":"CIS",
        "description": "18 prioritized safeguards for cyber defense. Organized into Implementation "
                       "Groups (IG1/IG2/IG3) for resource-based adoption.",
        "source_url":  "https://www.cisecurity.org/controls/v8",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# NIST CSF 2.0 → NIST 800-53r5 crosswalk
# Source: NIST SP 800-53r5 Crosswalk (csrc.nist.gov/projects/olir)
# Six functions: GOVERN(GV), IDENTIFY(ID), PROTECT(PR), DETECT(DE), RESPOND(RS), RECOVER(RC)
# ─────────────────────────────────────────────────────────────────────────────
CSF2_CONTROLS = [
    # ── GOVERN ──────────────────────────────────────────────────────────────
    ("GV.OC-01", "GOVERN", "Organizational mission and objectives are established", None,
     ["pm-1","pm-2","pm-3","pm-28","ra-9"]),
    ("GV.OC-02", "GOVERN", "Internal and external stakeholder needs are understood", None,
     ["pm-2","pm-19"]),
    ("GV.OC-03", "GOVERN", "Legal, regulatory, and contractual requirements are understood", None,
     ["pm-9","sa-9","sr-1"]),
    ("GV.OC-04", "GOVERN", "Critical objectives and dependencies are identified and communicated", None,
     ["pm-1","pm-11","pm-30","cp-2"]),
    ("GV.OC-05", "GOVERN", "Outcomes, capabilities, and services that the org depends on are understood", None,
     ["pm-11","sa-12","sr-2"]),
    ("GV.RM-01", "GOVERN", "Risk management objectives are established and agreed to", None,
     ["pm-9","ra-1","ra-2"]),
    ("GV.RM-02", "GOVERN", "Risk appetite and risk tolerance statements are established", None,
     ["pm-9","ra-1"]),
    ("GV.RM-03", "GOVERN", "Organizational risk management practices are established", None,
     ["pm-9","ra-1","ra-3"]),
    ("GV.RM-04", "GOVERN", "Strategic direction on risk management is established and communicated", None,
     ["pm-2","pm-9"]),
    ("GV.RM-05", "GOVERN", "Lines of communication across org re: risk are established", None,
     ["pm-2","pm-19"]),
    ("GV.RM-06", "GOVERN", "A standardized approach for expressing cybersecurity risk is established", None,
     ["ra-1","ra-3","ra-7"]),
    ("GV.RM-07", "GOVERN", "Strategic opportunities are characterized in terms of cybersecurity risk", None,
     ["pm-9","ra-3"]),
    ("GV.RR-01", "GOVERN", "Organizational leadership is responsible and accountable for cybersecurity risk", None,
     ["pm-2","pm-3"]),
    ("GV.RR-02", "GOVERN", "Roles, responsibilities, and authorities are established", None,
     ["pm-2","ac-5","ac-6"]),
    ("GV.RR-03", "GOVERN", "Adequate resources are allocated to a cybersecurity program", None,
     ["pm-3"]),
    ("GV.RR-04", "GOVERN", "Cybersecurity is included in human resources practices", None,
     ["ps-1","ps-2","ps-3","ps-4","ps-5","ps-6","ps-7","ps-8"]),
    ("GV.PO-01", "GOVERN", "Cybersecurity policy is established based on org mission", None,
     ["pm-1","ac-1","at-1","au-1","ca-1","cm-1","cp-1","ia-1","ir-1","ma-1","mp-1","pe-1","pl-1","pm-1","ps-1","ra-1","sa-1","sc-1","si-1","sr-1"]),
    ("GV.PO-02", "GOVERN", "Cybersecurity roles and responsibilities are coordinated with third parties", None,
     ["sa-9","sr-1","sr-2"]),
    ("GV.SC-01", "GOVERN", "A cybersecurity supply chain risk management program is established", None,
     ["pm-30","sr-1","sr-2"]),
    ("GV.SC-02", "GOVERN", "Cybersecurity roles and responsibilities for suppliers are established", None,
     ["sa-9","sr-1","sr-5"]),
    ("GV.SC-03", "GOVERN", "Suppliers are prioritized by criticality", None,
     ["ra-9","sr-2","sr-3"]),
    ("GV.SC-04", "GOVERN", "Suppliers are known and prioritized by criticality", None,
     ["sa-9","sr-2","sr-3"]),
    ("GV.SC-05", "GOVERN", "Requirements for addressing risks in the supply chain are established", None,
     ["sa-4","sa-9","sr-1","sr-5"]),
    ("GV.SC-06", "GOVERN", "Planning and due diligence are performed in suppliers/partners selection", None,
     ["sr-3","sr-5"]),
    ("GV.SC-07", "GOVERN", "Risks posed by suppliers are understood, recorded, prioritized, responded to", None,
     ["ra-3","sr-6"]),
    ("GV.SC-08", "GOVERN", "Relevant suppliers are included in incident planning", None,
     ["cp-2","ir-4","sa-9"]),
    ("GV.SC-09", "GOVERN", "Supply chain security practices are integrated into program and budgets", None,
     ["pm-30","sr-1"]),
    ("GV.SC-10", "GOVERN", "Cybersecurity supply chain risk management plans include provisions for incidents", None,
     ["ir-4","sa-9","sr-8"]),
    ("GV.OV-01", "GOVERN", "Cybersecurity risk results are used to inform and improve org mission", None,
     ["pm-9","ra-3","ra-7"]),
    ("GV.OV-02", "GOVERN", "The cybersecurity risk management strategy is reviewed and adjusted", None,
     ["pm-9","ra-3"]),
    ("GV.OV-03", "GOVERN", "Organizational cybersecurity risk management performance is evaluated", None,
     ["pm-9","ca-7"]),
    # ── IDENTIFY ─────────────────────────────────────────────────────────────
    ("ID.AM-01", "IDENTIFY", "Inventories of hardware managed by the org are maintained", None,
     ["cm-8"]),
    ("ID.AM-02", "IDENTIFY", "Inventories of software, services, and systems are maintained", None,
     ["cm-8","pm-5"]),
    ("ID.AM-03", "IDENTIFY", "Representations of organizational communication and data flows are maintained", None,
     ["pl-8","sa-17"]),
    ("ID.AM-04", "IDENTIFY", "Inventories of services provided by suppliers are maintained", None,
     ["sa-9"]),
    ("ID.AM-05", "IDENTIFY", "Assets are prioritized based on classification, criticality, and business value", None,
     ["ra-2","ra-9","cm-8","pm-5"]),
    ("ID.AM-07", "IDENTIFY", "Inventories of data and corresponding metadata for designated data types are maintained", None,
     ["cm-8","pm-5","ra-2"]),
    ("ID.AM-08", "IDENTIFY", "Systems, hardware, software, services, and data are managed throughout their life cycles", None,
     ["cm-8","sa-2","sa-3","si-12"]),
    ("ID.RA-01", "IDENTIFY", "Vulnerabilities in assets are identified, validated, and recorded", None,
     ["ra-3","ra-5","ca-2"]),
    ("ID.RA-02", "IDENTIFY", "Cyber threat intelligence is received from information sharing forums", None,
     ["pm-15","pm-16","si-5"]),
    ("ID.RA-03", "IDENTIFY", "Internal and external threats to the org are identified and recorded", None,
     ["ra-3","pm-12","pm-16"]),
    ("ID.RA-04", "IDENTIFY", "Potential impacts and likelihoods of threats are identified and recorded", None,
     ["ra-3","ra-5"]),
    ("ID.RA-05", "IDENTIFY", "Threats, vulnerabilities, likelihoods, and impacts are prioritized", None,
     ["ra-3","ra-5"]),
    ("ID.RA-06", "IDENTIFY", "Risk responses are chosen, prioritized, planned, tracked, and communicated", None,
     ["ra-3","ra-7","pm-4"]),
    ("ID.RA-07", "IDENTIFY", "Changes and exceptions are managed, assessed for risk impact", None,
     ["cm-3","ra-3"]),
    ("ID.RA-08", "IDENTIFY", "Processes for receiving, analyzing, and responding to vulnerability disclosures", None,
     ["ra-5","si-5"]),
    ("ID.RA-09", "IDENTIFY", "The authenticity and integrity of hardware and software are assessed", None,
     ["sr-4","sr-9","sr-11"]),
    ("ID.RA-10", "IDENTIFY", "Critical suppliers are assessed prior to acquisition", None,
     ["sr-3","sr-5","sr-6"]),
    ("ID.IM-01", "IDENTIFY", "Improvements are identified from evaluations, assessments, and exercises", None,
     ["ca-2","ca-7","pm-14"]),
    ("ID.IM-02", "IDENTIFY", "Improvements are identified from security tests and exercises", None,
     ["ca-2","ca-8","pm-14"]),
    ("ID.IM-03", "IDENTIFY", "Improvements are identified from executive review of cybersecurity posture", None,
     ["pm-9","ca-7"]),
    ("ID.IM-04", "IDENTIFY", "Incident response plans and other cybersecurity plans that affect operations are established", None,
     ["ir-8","cp-2","pm-8"]),
    # ── PROTECT ──────────────────────────────────────────────────────────────
    ("PR.AA-01", "PROTECT", "Identities and credentials for authorized users are managed", None,
     ["ia-1","ia-2","ia-4","ia-5"]),
    ("PR.AA-02", "PROTECT", "Identities are proofed and bound to credentials based on context", None,
     ["ia-3","ia-4","ia-5","ia-12"]),
    ("PR.AA-03", "PROTECT", "Users, services, and hardware are authenticated", None,
     ["ia-2","ia-3","ia-5","ia-8"]),
    ("PR.AA-04", "PROTECT", "Identity assertions are protected, conveyed, and verified", None,
     ["ia-5","ia-8","sc-8"]),
    ("PR.AA-05", "PROTECT", "Access permissions, entitlements, and authorizations are defined", None,
     ["ac-1","ac-2","ac-3","ac-5","ac-6"]),
    ("PR.AA-06", "PROTECT", "Physical access to assets is managed, monitored, and enforced", None,
     ["pe-2","pe-3","pe-4","pe-5","pe-6"]),
    ("PR.AT-01", "PROTECT", "Personnel are provided with awareness and training", None,
     ["at-1","at-2","at-3"]),
    ("PR.AT-02", "PROTECT", "Individuals with elevated privileges understand roles and responsibilities", None,
     ["at-3","ps-7"]),
    ("PR.DS-01", "PROTECT", "The confidentiality, integrity, and availability of data at rest is protected", None,
     ["mp-2","mp-4","mp-5","sc-28","si-12"]),
    ("PR.DS-02", "PROTECT", "The confidentiality, integrity, and availability of data in transit is protected", None,
     ["sc-8","sc-28"]),
    ("PR.DS-10", "PROTECT", "The confidentiality, integrity, and availability of data in use is protected", None,
     ["sc-4","sc-39"]),
    ("PR.DS-11", "PROTECT", "Backups of data are created, protected, maintained, and tested", None,
     ["cp-9","cp-10"]),
    ("PR.IR-01", "PROTECT", "Networks and environments are protected from unauthorized logical access", None,
     ["ac-4","sc-7","sc-20","sc-21","sc-22"]),
    ("PR.IR-02", "PROTECT", "The organization's technology assets are protected from environmental threats", None,
     ["pe-9","pe-10","pe-11","pe-12","pe-13","pe-14","pe-15"]),
    ("PR.IR-03", "PROTECT", "Mechanisms are implemented to achieve resilience in normal and adverse situations", None,
     ["cp-6","cp-7","sc-5","sc-6"]),
    ("PR.IR-04", "PROTECT", "Adequate resource capacity to ensure availability is maintained", None,
     ["cp-2","sc-5"]),
    ("PR.PS-01", "PROTECT", "Configuration management practices are established and applied", None,
     ["cm-1","cm-2","cm-6","cm-7","cm-9"]),
    ("PR.PS-02", "PROTECT", "Software is maintained, replaced, and removed commensurate with risk", None,
     ["cm-10","cm-11","si-2","si-7"]),
    ("PR.PS-03", "PROTECT", "Hardware is maintained, replaced, and removed commensurate with risk", None,
     ["ma-2","ma-3","ma-4","ma-6"]),
    ("PR.PS-04", "PROTECT", "Log records are generated and made available for continuous monitoring", None,
     ["au-2","au-3","au-6","au-7","au-12"]),
    ("PR.PS-05", "PROTECT", "Installation and execution of unauthorized software are prevented", None,
     ["cm-7","cm-10","cm-11","si-7"]),
    ("PR.PS-06", "PROTECT", "Secure software development practices are integrated", None,
     ["sa-3","sa-8","sa-11","sa-15","sr-4"]),
    # ── DETECT ───────────────────────────────────────────────────────────────
    ("DE.CM-01", "DETECT", "Networks and network services are monitored to find adverse events", None,
     ["au-6","ca-7","si-3","si-4"]),
    ("DE.CM-02", "DETECT", "The physical environment is monitored to find adverse events", None,
     ["pe-6"]),
    ("DE.CM-03", "DETECT", "Personnel activity and technology usage are monitored", None,
     ["ac-17","au-6","au-13","si-4"]),
    ("DE.CM-06", "DETECT", "External service provider activities and services are monitored", None,
     ["ca-7","sa-9"]),
    ("DE.CM-09", "DETECT", "Computing hardware and software, runtime environments are monitored", None,
     ["au-6","ca-7","cm-3","si-4","si-7"]),
    ("DE.AE-02", "DETECT", "Potentially adverse events are analyzed to better understand associated activities", None,
     ["au-6","ir-4","si-4"]),
    ("DE.AE-03", "DETECT", "Information is correlated from multiple sources", None,
     ["au-6","ir-4","si-4"]),
    ("DE.AE-04", "DETECT", "The estimated impact and scope of adverse events are understood", None,
     ["ir-4","ra-3","si-4"]),
    ("DE.AE-06", "DETECT", "Information on adverse events is provided to authorized staff", None,
     ["au-6","ir-4","si-4"]),
    ("DE.AE-07", "DETECT", "Cyber threat intelligence and other contextual information are integrated", None,
     ["pm-16","ra-3","si-4","si-5"]),
    ("DE.AE-08", "DETECT", "Incidents are declared when adverse events meet defined criteria", None,
     ["ir-4","ir-5","ir-6"]),
    # ── RESPOND ──────────────────────────────────────────────────────────────
    ("RS.MA-01", "RESPOND", "The incident response plan is executed in coordination with relevant third parties", None,
     ["ir-4","ir-8"]),
    ("RS.MA-02", "RESPOND", "Incident reports are triaged and validated", None,
     ["ir-4","ir-5","ir-6"]),
    ("RS.MA-03", "RESPOND", "Incidents are categorized and prioritized", None,
     ["ir-4","ir-5"]),
    ("RS.MA-04", "RESPOND", "Incidents are escalated or elevated as needed", None,
     ["ir-4","ir-6"]),
    ("RS.MA-05", "RESPOND", "The criteria for initiating incident recovery are applied", None,
     ["ir-4","cp-10"]),
    ("RS.AN-03", "RESPOND", "Analysis is performed to establish what has taken place during an incident", None,
     ["ir-4","au-6"]),
    ("RS.AN-06", "RESPOND", "Actions performed during an investigation are recorded", None,
     ["ir-4","au-12"]),
    ("RS.AN-07", "RESPOND", "Cause of an incident is determined", None,
     ["ir-4"]),
    ("RS.AN-08", "RESPOND", "Incidents are categorized consistent with response plans", None,
     ["ir-4","ir-5"]),
    ("RS.CO-02", "RESPOND", "Internal and external stakeholders are notified of incidents", None,
     ["ir-6","ir-7"]),
    ("RS.CO-03", "RESPOND", "Information is shared with designated internal and external stakeholders", None,
     ["ir-6","pm-15"]),
    ("RS.MI-01", "RESPOND", "Incidents are contained", None,
     ["ir-4"]),
    ("RS.MI-02", "RESPOND", "Incidents are eradicated", None,
     ["ir-4","si-3"]),
    # ── RECOVER ──────────────────────────────────────────────────────────────
    ("RC.RP-01", "RECOVER", "The recovery portion of the incident response plan is executed", None,
     ["cp-10","ir-4"]),
    ("RC.RP-02", "RECOVER", "Recovery actions are selected, scoped, prioritized, and performed", None,
     ["cp-10","ir-4"]),
    ("RC.RP-03", "RECOVER", "The integrity of backups and other restoration assets is verified", None,
     ["cp-9","cp-10"]),
    ("RC.RP-04", "RECOVER", "Critical missions and business functions are provided from alternate sites", None,
     ["cp-7","cp-10"]),
    ("RC.RP-05", "RECOVER", "The integrity of restored assets is verified, systems and services restored", None,
     ["cp-10","si-7"]),
    ("RC.RP-06", "RECOVER", "The end of incident recovery is declared based on criteria", None,
     ["cp-10","ir-4"]),
    ("RC.CO-03", "RECOVER", "Recovery activities and progress are communicated to stakeholders", None,
     ["cp-2","ir-4"]),
    ("RC.CO-04", "RECOVER", "Public updates on incidents and recovery are shared using approved methods", None,
     ["ir-7"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# NIST SP 800-171r3 → 800-53r5 crosswalk
# Source: NIST SP 800-171r3 Appendix D (direct derivation from 800-53r5)
# Requirements organized by 17 families
# ─────────────────────────────────────────────────────────────────────────────
SP800171_CONTROLS = [
    # 3.1 Access Control
    ("3.1.1",  "Access Control", "Limit system access to authorized users", "L1",  ["ac-2","ac-3","ac-17"]),
    ("3.1.2",  "Access Control", "Limit system access to types of transactions authorized users permitted to execute", "L1", ["ac-3"]),
    ("3.1.3",  "Access Control", "Control the flow of CUI in accordance with approved authorizations", "L2", ["ac-4","ac-4.21"]),
    ("3.1.4",  "Access Control", "Separate the duties of individuals to reduce risk of malevolent activity", "L2", ["ac-5"]),
    ("3.1.5",  "Access Control", "Employ the principle of least privilege", "L2", ["ac-6"]),
    ("3.1.6",  "Access Control", "Use non-privileged accounts when accessing non-security functions", "L2", ["ac-6.2"]),
    ("3.1.7",  "Access Control", "Prevent non-privileged users from executing privileged functions", "L2", ["ac-6.10"]),
    ("3.1.8",  "Access Control", "Limit unsuccessful login attempts", "L2", ["ac-7"]),
    ("3.1.9",  "Access Control", "Provide privacy and security notices", "L2", ["ac-8"]),
    ("3.1.10", "Access Control", "Use session lock with pattern-hiding displays", "L2", ["ac-11","ac-11.1"]),
    ("3.1.11", "Access Control", "Terminate sessions after defined conditions", "L2", ["ac-12"]),
    ("3.1.12", "Access Control", "Monitor and control remote access sessions", "L2", ["ac-17"]),
    ("3.1.13", "Access Control", "Employ cryptographic mechanisms for remote access", "L2", ["ac-17.2"]),
    ("3.1.14", "Access Control", "Route remote access via managed access control points", "L2", ["ac-17.3"]),
    ("3.1.15", "Access Control", "Authorize remote execution of privileged commands via remote access", "L2", ["ac-17.4"]),
    ("3.1.16", "Access Control", "Authorize wireless access prior to allowing connections", "L2", ["ac-18"]),
    ("3.1.17", "Access Control", "Protect wireless access using authentication and encryption", "L2", ["ac-18.1"]),
    ("3.1.18", "Access Control", "Control connection of mobile devices", "L2", ["ac-19"]),
    ("3.1.19", "Access Control", "Encrypt CUI on mobile devices and mobile computing platforms", "L2", ["ac-19.5"]),
    ("3.1.20", "Access Control", "Verify and control connections to external systems", "L2", ["ac-20"]),
    ("3.1.21", "Access Control", "Limit use of portable storage devices on external systems", "L2", ["ac-20.2"]),
    ("3.1.22", "Access Control", "Control CUI posted or processed on publicly accessible systems", "L2", ["ac-22"]),
    # 3.2 Awareness and Training
    ("3.2.1",  "Awareness & Training", "Ensure personnel are aware of security risks", "L1", ["at-2"]),
    ("3.2.2",  "Awareness & Training", "Ensure personnel are trained on security responsibilities", "L2", ["at-3"]),
    ("3.2.3",  "Awareness & Training", "Provide security awareness training on recognizing threats", "L2", ["at-2.2"]),
    # 3.3 Audit and Accountability
    ("3.3.1",  "Audit & Accountability", "Create and retain logs of user activity", "L2", ["au-2","au-3","au-12"]),
    ("3.3.2",  "Audit & Accountability", "Ensure individual user actions can be traced to users", "L2", ["au-2","au-3","au-12","ia-2"]),
    ("3.3.3",  "Audit & Accountability", "Review and update logged events", "L2", ["au-2.3"]),
    ("3.3.4",  "Audit & Accountability", "Alert in event of audit logging process failure", "L2", ["au-5"]),
    ("3.3.5",  "Audit & Accountability", "Correlate audit record review, analysis, and reporting processes", "L2", ["au-6"]),
    ("3.3.6",  "Audit & Accountability", "Provide audit record reduction and report generation", "L2", ["au-7"]),
    ("3.3.7",  "Audit & Accountability", "Provide system capability that compares and synchronizes clocks", "L2", ["au-8"]),
    ("3.3.8",  "Audit & Accountability", "Protect audit information and tools from unauthorized access", "L2", ["au-9"]),
    ("3.3.9",  "Audit & Accountability", "Limit management of audit logging to subset of privileged users", "L2", ["au-9.4"]),
    # 3.4 Configuration Management
    ("3.4.1",  "Configuration Management", "Establish baseline configs and inventories of systems", "L1", ["cm-2","cm-8"]),
    ("3.4.2",  "Configuration Management", "Establish security configuration settings", "L1", ["cm-6","cm-7"]),
    ("3.4.3",  "Configuration Management", "Track, review, approve, and log changes to systems", "L2", ["cm-3"]),
    ("3.4.4",  "Configuration Management", "Analyze security impact of changes prior to implementation", "L2", ["cm-4"]),
    ("3.4.5",  "Configuration Management", "Define, document, approve, and enforce physical/logical access restrictions", "L2", ["cm-5"]),
    ("3.4.6",  "Configuration Management", "Employ principle of least functionality", "L2", ["cm-7"]),
    ("3.4.7",  "Configuration Management", "Restrict, disable, or prevent the use of nonessential programs", "L2", ["cm-7.2"]),
    ("3.4.8",  "Configuration Management", "Apply deny-by-exception policy to prevent use of unauthorized software", "L2", ["cm-7.5"]),
    ("3.4.9",  "Configuration Management", "Control and monitor user-installed software", "L2", ["cm-11"]),
    # 3.5 Identification and Authentication
    ("3.5.1",  "Identification & Authentication", "Identify system users, processes, and devices", "L1", ["ia-2","ia-3","ia-4","ia-5"]),
    ("3.5.2",  "Identification & Authentication", "Authenticate identities before allowing access", "L1", ["ia-2","ia-5"]),
    ("3.5.3",  "Identification & Authentication", "Use multi-factor authentication for local and network access", "L2", ["ia-2.1","ia-2.2"]),
    ("3.5.4",  "Identification & Authentication", "Employ replay-resistant authentication mechanisms", "L2", ["ia-2.8"]),
    ("3.5.5",  "Identification & Authentication", "Employ identifier management", "L2", ["ia-4"]),
    ("3.5.6",  "Identification & Authentication", "Disable identifiers after defined period of inactivity", "L2", ["ia-4.4"]),
    ("3.5.7",  "Identification & Authentication", "Enforce minimum password complexity and change requirements", "L2", ["ia-5.1"]),
    ("3.5.8",  "Identification & Authentication", "Prohibit password reuse for specified generations", "L2", ["ia-5.1"]),
    ("3.5.9",  "Identification & Authentication", "Allow temporary password use with immediate change requirement", "L2", ["ia-5"]),
    ("3.5.10", "Identification & Authentication", "Store and transmit only cryptographically protected passwords", "L2", ["ia-5.1"]),
    ("3.5.11", "Identification & Authentication", "Obscure feedback of authentication information", "L2", ["ia-6"]),
    # 3.6 Incident Response
    ("3.6.1",  "Incident Response", "Establish operational incident-handling capability", "L1", ["ir-2","ir-4","ir-5","ir-6","ir-7"]),
    ("3.6.2",  "Incident Response", "Track, document, and report incidents to appropriate officials", "L1", ["ir-5","ir-6"]),
    ("3.6.3",  "Incident Response", "Test incident response capability", "L2", ["ir-3","ir-3.2"]),
    # 3.7 Maintenance
    ("3.7.1",  "Maintenance", "Perform maintenance on systems", "L2", ["ma-2"]),
    ("3.7.2",  "Maintenance", "Provide controls on tools, techniques, mechanisms, and personnel for maintenance", "L2", ["ma-3","ma-3.1","ma-3.2"]),
    ("3.7.3",  "Maintenance", "Ensure equipment removed for maintenance is sanitized", "L2", ["ma-2.2"]),
    ("3.7.4",  "Maintenance", "Check media containing diagnostic programs for malicious code", "L2", ["ma-3.2"]),
    ("3.7.5",  "Maintenance", "Require MFA for remote maintenance sessions", "L2", ["ma-4.6"]),
    ("3.7.6",  "Maintenance", "Supervise maintenance activities of personnel without required access", "L2", ["ma-5"]),
    # 3.8 Media Protection
    ("3.8.1",  "Media Protection", "Protect system media containing CUI", "L1", ["mp-2"]),
    ("3.8.2",  "Media Protection", "Limit access to CUI on system media", "L1", ["mp-2"]),
    ("3.8.3",  "Media Protection", "Sanitize or destroy system media before disposal", "L1", ["mp-6"]),
    ("3.8.4",  "Media Protection", "Mark media with necessary CUI markings and distribution limitations", "L2", ["mp-3"]),
    ("3.8.5",  "Media Protection", "Control access to media containing CUI", "L2", ["mp-4"]),
    ("3.8.6",  "Media Protection", "Implement cryptographic mechanisms to protect CUI during transport", "L2", ["mp-5.4"]),
    ("3.8.7",  "Media Protection", "Control the use of removable media", "L2", ["mp-7"]),
    ("3.8.8",  "Media Protection", "Prohibit the use of portable storage devices when unknown ownership", "L2", ["mp-7.1"]),
    ("3.8.9",  "Media Protection", "Protect backups of CUI at storage locations", "L2", ["cp-9.3"]),
    # 3.9 Personnel Security
    ("3.9.1",  "Personnel Security", "Screen individuals prior to authorizing access", "L1", ["ps-3"]),
    ("3.9.2",  "Personnel Security", "Ensure CUI is protected during and after personnel actions", "L1", ["ps-4","ps-5"]),
    # 3.10 Physical Protection
    ("3.10.1", "Physical Protection", "Limit physical access to systems to authorized individuals", "L1", ["pe-2","pe-3"]),
    ("3.10.2", "Physical Protection", "Protect and monitor the physical facility and support infrastructure", "L2", ["pe-6","pe-13","pe-14","pe-15"]),
    ("3.10.3", "Physical Protection", "Escort visitors and monitor visitor activity", "L2", ["pe-2","pe-3"]),
    ("3.10.4", "Physical Protection", "Maintain audit logs of physical access", "L2", ["pe-8"]),
    ("3.10.5", "Physical Protection", "Control and manage physical access devices", "L2", ["pe-3"]),
    ("3.10.6", "Physical Protection", "Enforce safeguarding measures for CUI at alternate work sites", "L2", ["pe-17"]),
    # 3.11 Risk Assessment
    ("3.11.1", "Risk Assessment", "Periodically assess risk to systems", "L2", ["ra-3"]),
    ("3.11.2", "Risk Assessment", "Scan for vulnerabilities periodically and when new vulnerabilities are identified", "L2", ["ra-5"]),
    ("3.11.3", "Risk Assessment", "Remediate vulnerabilities in accordance with risk assessments", "L2", ["ra-5","si-2"]),
    # 3.12 Security Assessment
    ("3.12.1", "Security Assessment", "Periodically assess the security controls to determine effectiveness", "L2", ["ca-2"]),
    ("3.12.2", "Security Assessment", "Develop and implement plans of action to correct deficiencies", "L2", ["ca-5"]),
    ("3.12.3", "Security Assessment", "Monitor controls on an ongoing basis", "L2", ["ca-7"]),
    ("3.12.4", "Security Assessment", "Develop, document, and periodically update system security plans", "L2", ["pl-2"]),
    # 3.13 System and Communications Protection
    ("3.13.1", "System & Communications", "Monitor, control, and protect communications at external boundaries", "L1", ["sc-7"]),
    ("3.13.2", "System & Communications", "Employ architectural designs and implementation techniques for security", "L2", ["sc-2","sc-3"]),
    ("3.13.3", "System & Communications", "Separate user functionality from system management functionality", "L2", ["sc-2"]),
    ("3.13.4", "System & Communications", "Prevent unauthorized and unintended information transfer", "L2", ["sc-4"]),
    ("3.13.5", "System & Communications", "Implement subnetworks for publicly accessible system components", "L1", ["sc-7.5"]),
    ("3.13.6", "System & Communications", "Deny network communications traffic by default", "L2", ["sc-7.5","cm-7"]),
    ("3.13.7", "System & Communications", "Prevent remote devices from simultaneously connecting to local and other networks", "L2", ["sc-7.7"]),
    ("3.13.8", "System & Communications", "Implement cryptographic mechanisms to prevent unauthorized disclosure of CUI", "L2", ["sc-8","sc-8.1"]),
    ("3.13.9", "System & Communications", "Terminate network connections after defined period of inactivity", "L2", ["sc-10"]),
    ("3.13.10","System & Communications", "Establish and manage cryptographic keys", "L2", ["sc-12"]),
    ("3.13.11","System & Communications", "Employ FIPS-validated cryptography when protecting CUI", "L2", ["sc-13"]),
    ("3.13.12","System & Communications", "Prohibit remote activation of collaborative computing devices", "L2", ["sc-15"]),
    ("3.13.13","System & Communications", "Control and monitor the use of mobile code", "L2", ["sc-18"]),
    ("3.13.14","System & Communications", "Control and monitor the use of VoIP technologies", "L2", ["sc-19"]),
    ("3.13.15","System & Communications", "Protect the authenticity of communications sessions", "L2", ["sc-23"]),
    ("3.13.16","System & Communications", "Protect CUI at rest", "L2", ["sc-28"]),
    # 3.14 System and Information Integrity
    ("3.14.1", "System & Info Integrity", "Identify, report, and correct system flaws", "L1", ["si-2"]),
    ("3.14.2", "System & Info Integrity", "Provide protection from malicious code", "L1", ["si-3"]),
    ("3.14.3", "System & Info Integrity", "Monitor system security alerts and advisories", "L1", ["si-5"]),
    ("3.14.4", "System & Info Integrity", "Update malicious code protection mechanisms", "L2", ["si-3.2"]),
    ("3.14.5", "System & Info Integrity", "Perform periodic scans and real-time scans of files", "L2", ["si-3.1","si-3.2"]),
    ("3.14.6", "System & Info Integrity", "Monitor systems to detect attacks and indicators of potential attacks", "L2", ["si-4"]),
    ("3.14.7", "System & Info Integrity", "Identify unauthorized use of systems", "L2", ["si-4"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# CMMC 2.0 → NIST 800-53r5 crosswalk
# Level 1: 17 practices (FCI protection, FAR 52.204-21 basic safeguarding)
# Level 2: 110 practices (= all 800-171r3 requirements)
# Level 3: 24 additional practices from 800-172 (advanced)
# For CMMC, we map L1 practices directly; L2 practices reference 800-171 (already mapped)
# ─────────────────────────────────────────────────────────────────────────────
CMMC2_CONTROLS = [
    # Level 1 — Foundational (17 practices, FAR basic safeguarding)
    ("AC.L1-3.1.1",  "Access Control", "Authorized Access Control", "L1",  ["ac-2","ac-3","ac-17"]),
    ("AC.L1-3.1.2",  "Access Control", "Transaction & Function Control", "L1", ["ac-3"]),
    ("IA.L1-3.5.1",  "Identification & Authentication", "Identification", "L1", ["ia-2","ia-4","ia-5"]),
    ("IA.L1-3.5.2",  "Identification & Authentication", "Authentication", "L1", ["ia-2","ia-5"]),
    ("MP.L1-3.8.3",  "Media Protection", "Media Disposal", "L1", ["mp-6"]),
    ("PE.L1-3.10.1", "Physical Protection", "Limit Physical Access", "L1", ["pe-2","pe-3"]),
    ("PE.L1-3.10.3", "Physical Protection", "Escort Visitors", "L1", ["pe-2","pe-3"]),
    ("PE.L1-3.10.4", "Physical Protection", "Physical Access Logs", "L1", ["pe-8"]),
    ("PE.L1-3.10.5", "Physical Protection", "Manage Physical Access Devices", "L1", ["pe-3"]),
    ("SC.L1-3.13.1", "System & Comms Protection", "Boundary Protection", "L1", ["sc-7"]),
    ("SC.L1-3.13.5", "System & Comms Protection", "Public-Access System Separation", "L1", ["sc-7.5"]),
    ("SI.L1-3.14.1", "System & Info Integrity", "Flaw Remediation", "L1", ["si-2"]),
    ("SI.L1-3.14.2", "System & Info Integrity", "Malicious Code Protection", "L1", ["si-3"]),
    ("SI.L1-3.14.3", "System & Info Integrity", "Security Alerts", "L1", ["si-5"]),
    ("SI.L1-3.14.4", "System & Info Integrity", "Update Malicious Code Protection", "L1", ["si-3.2"]),
    ("SI.L1-3.14.5", "System & Info Integrity", "System & File Scanning", "L1", ["si-3.1","si-3.2"]),
    ("PS.L1-3.9.2",  "Personnel Security", "Personnel Actions", "L1", ["ps-4","ps-5"]),
    # Level 2 — Advanced (110 practices = 800-171r3)
    # Rather than duplicate, we map L2 controls to their 800-53 equivalents directly
    ("AC.L2-3.1.3",  "Access Control", "Control CUI Flow", "L2",  ["ac-4","ac-4.21"]),
    ("AC.L2-3.1.4",  "Access Control", "Separation of Duties", "L2", ["ac-5"]),
    ("AC.L2-3.1.5",  "Access Control", "Least Privilege", "L2", ["ac-6"]),
    ("AC.L2-3.1.6",  "Access Control", "Non-Privileged Account Use", "L2", ["ac-6.2"]),
    ("AC.L2-3.1.7",  "Access Control", "Privileged Functions", "L2", ["ac-6.10"]),
    ("AC.L2-3.1.8",  "Access Control", "Unsuccessful Logon Attempts", "L2", ["ac-7"]),
    ("AC.L2-3.1.9",  "Access Control", "Privacy and Security Notices", "L2", ["ac-8"]),
    ("AC.L2-3.1.10", "Access Control", "Session Lock", "L2", ["ac-11","ac-11.1"]),
    ("AC.L2-3.1.11", "Access Control", "Session Termination", "L2", ["ac-12"]),
    ("AC.L2-3.1.12", "Access Control", "Remote Access Control", "L2", ["ac-17"]),
    ("AC.L2-3.1.13", "Access Control", "Remote Access Confidentiality", "L2", ["ac-17.2"]),
    ("AC.L2-3.1.14", "Access Control", "Remote Access Routing", "L2", ["ac-17.3"]),
    ("AC.L2-3.1.15", "Access Control", "Privileged Remote Access", "L2", ["ac-17.4"]),
    ("AC.L2-3.1.16", "Access Control", "Wireless Access Authorization", "L2", ["ac-18"]),
    ("AC.L2-3.1.17", "Access Control", "Wireless Access Protection", "L2", ["ac-18.1"]),
    ("AC.L2-3.1.18", "Access Control", "Mobile Device Connection", "L2", ["ac-19"]),
    ("AC.L2-3.1.19", "Access Control", "Encryption of CUI on Mobile", "L2", ["ac-19.5"]),
    ("AC.L2-3.1.20", "Access Control", "External Connections", "L2", ["ac-20"]),
    ("AC.L2-3.1.21", "Access Control", "Portable Storage Use", "L2", ["ac-20.2"]),
    ("AC.L2-3.1.22", "Access Control", "Publicly Accessible Content", "L2", ["ac-22"]),
    ("IA.L2-3.5.3",  "Identification & Authentication", "Multi-Factor Authentication", "L2", ["ia-2.1","ia-2.2"]),
    ("IA.L2-3.5.4",  "Identification & Authentication", "Replay-Resistant Auth", "L2", ["ia-2.8"]),
    ("IA.L2-3.5.5",  "Identification & Authentication", "Identifier Management", "L2", ["ia-4"]),
    ("IA.L2-3.5.6",  "Identification & Authentication", "Identifier Deactivation", "L2", ["ia-4.4"]),
    ("IA.L2-3.5.7",  "Identification & Authentication", "Password Complexity", "L2", ["ia-5.1"]),
    ("IA.L2-3.5.8",  "Identification & Authentication", "Password Reuse", "L2", ["ia-5.1"]),
    ("IA.L2-3.5.9",  "Identification & Authentication", "Temporary Passwords", "L2", ["ia-5"]),
    ("IA.L2-3.5.10", "Identification & Authentication", "Cryptographic Password Protection", "L2", ["ia-5.1"]),
    ("IA.L2-3.5.11", "Identification & Authentication", "Obscure Authentication Feedback", "L2", ["ia-6"]),
    ("AU.L2-3.3.1",  "Audit & Accountability", "System Auditing", "L2", ["au-2","au-3","au-12"]),
    ("AU.L2-3.3.2",  "Audit & Accountability", "User Accountability", "L2", ["au-2","au-3","au-12","ia-2"]),
    ("AU.L2-3.3.3",  "Audit & Accountability", "Review/Update Log Events", "L2", ["au-2.3"]),
    ("AU.L2-3.3.4",  "Audit & Accountability", "Audit Failure Alerting", "L2", ["au-5"]),
    ("AU.L2-3.3.5",  "Audit & Accountability", "Audit Correlation", "L2", ["au-6"]),
    ("AU.L2-3.3.6",  "Audit & Accountability", "Audit Reduction/Reporting", "L2", ["au-7"]),
    ("AU.L2-3.3.7",  "Audit & Accountability", "Clock Synchronization", "L2", ["au-8"]),
    ("AU.L2-3.3.8",  "Audit & Accountability", "Audit Protection", "L2", ["au-9"]),
    ("AU.L2-3.3.9",  "Audit & Accountability", "Audit Management", "L2", ["au-9.4"]),
    ("CM.L2-3.4.1",  "Configuration Management", "System Baselining", "L2", ["cm-2","cm-8"]),
    ("CM.L2-3.4.2",  "Configuration Management", "Security Config Settings", "L2", ["cm-6","cm-7"]),
    ("CM.L2-3.4.3",  "Configuration Management", "System Change Management", "L2", ["cm-3"]),
    ("CM.L2-3.4.4",  "Configuration Management", "Security Impact Analysis", "L2", ["cm-4"]),
    ("CM.L2-3.4.5",  "Configuration Management", "Access Restrictions for Change", "L2", ["cm-5"]),
    ("CM.L2-3.4.6",  "Configuration Management", "Least Functionality", "L2", ["cm-7"]),
    ("CM.L2-3.4.7",  "Configuration Management", "Nonessential Functionality", "L2", ["cm-7.2"]),
    ("CM.L2-3.4.8",  "Configuration Management", "Application Execution Policy", "L2", ["cm-7.5"]),
    ("CM.L2-3.4.9",  "Configuration Management", "User-Installed Software", "L2", ["cm-11"]),
    ("IR.L2-3.6.1",  "Incident Response", "Incident Handling", "L2", ["ir-2","ir-4","ir-5","ir-6","ir-7"]),
    ("IR.L2-3.6.2",  "Incident Response", "Incident Reporting", "L2", ["ir-5","ir-6"]),
    ("IR.L2-3.6.3",  "Incident Response", "Incident Response Testing", "L2", ["ir-3","ir-3.2"]),
    ("MA.L2-3.7.1",  "Maintenance", "Perform Maintenance", "L2", ["ma-2"]),
    ("MA.L2-3.7.2",  "Maintenance", "Controlled Maintenance", "L2", ["ma-3","ma-3.1","ma-3.2"]),
    ("MA.L2-3.7.3",  "Maintenance", "Equipment Sanitization", "L2", ["ma-2.2"]),
    ("MA.L2-3.7.4",  "Maintenance", "Media Inspection", "L2", ["ma-3.2"]),
    ("MA.L2-3.7.5",  "Maintenance", "Multifactor Authentication for Remote Maintenance", "L2", ["ma-4.6"]),
    ("MA.L2-3.7.6",  "Maintenance", "Maintenance Personnel", "L2", ["ma-5"]),
    ("MP.L2-3.8.1",  "Media Protection", "Media Protection", "L2", ["mp-2"]),
    ("MP.L2-3.8.2",  "Media Protection", "Media Access", "L2", ["mp-2"]),
    ("MP.L2-3.8.4",  "Media Protection", "Media Marking", "L2", ["mp-3"]),
    ("MP.L2-3.8.5",  "Media Protection", "Media Accountability", "L2", ["mp-4"]),
    ("MP.L2-3.8.6",  "Media Protection", "Portable Storage Encryption", "L2", ["mp-5.4"]),
    ("MP.L2-3.8.7",  "Media Protection", "Removable Media", "L2", ["mp-7"]),
    ("MP.L2-3.8.8",  "Media Protection", "Shared Media", "L2", ["mp-7.1"]),
    ("MP.L2-3.8.9",  "Media Protection", "Protect Backups", "L2", ["cp-9.3"]),
    ("PS.L2-3.9.1",  "Personnel Security", "Screen Individuals", "L2", ["ps-3"]),
    ("PE.L2-3.10.2", "Physical Protection", "Monitor Facility and Infrastructure", "L2", ["pe-6","pe-13","pe-14","pe-15"]),
    ("PE.L2-3.10.6", "Physical Protection", "Alternate Work Site", "L2", ["pe-17"]),
    ("RA.L2-3.11.1", "Risk Assessment", "Risk Assessments", "L2", ["ra-3"]),
    ("RA.L2-3.11.2", "Risk Assessment", "Vulnerability Scan", "L2", ["ra-5"]),
    ("RA.L2-3.11.3", "Risk Assessment", "Risk Response", "L2", ["ra-5","si-2"]),
    ("CA.L2-3.12.1", "Security Assessment", "Security Control Assessment", "L2", ["ca-2"]),
    ("CA.L2-3.12.2", "Security Assessment", "Plan of Action", "L2", ["ca-5"]),
    ("CA.L2-3.12.3", "Security Assessment", "Continuous Monitoring", "L2", ["ca-7"]),
    ("CA.L2-3.12.4", "Security Assessment", "System Security Plan", "L2", ["pl-2"]),
    ("SC.L2-3.13.2", "System & Comms", "Security Engineering", "L2", ["sc-2","sc-3"]),
    ("SC.L2-3.13.3", "System & Comms", "Role Separation", "L2", ["sc-2"]),
    ("SC.L2-3.13.4", "System & Comms", "Shared Resource Control", "L2", ["sc-4"]),
    ("SC.L2-3.13.6", "System & Comms", "Network Communication by Exception", "L2", ["sc-7.5","cm-7"]),
    ("SC.L2-3.13.7", "System & Comms", "Split Tunneling", "L2", ["sc-7.7"]),
    ("SC.L2-3.13.8", "System & Comms", "Data in Transit", "L2", ["sc-8","sc-8.1"]),
    ("SC.L2-3.13.9", "System & Comms", "Connections Termination", "L2", ["sc-10"]),
    ("SC.L2-3.13.10","System & Comms", "Key Management", "L2", ["sc-12"]),
    ("SC.L2-3.13.11","System & Comms", "CUI Encryption", "L2", ["sc-13"]),
    ("SC.L2-3.13.12","System & Comms", "Collaborative Computing", "L2", ["sc-15"]),
    ("SC.L2-3.13.13","System & Comms", "Mobile Code", "L2", ["sc-18"]),
    ("SC.L2-3.13.14","System & Comms", "VoIP", "L2", ["sc-19"]),
    ("SC.L2-3.13.15","System & Comms", "Communications Authenticity", "L2", ["sc-23"]),
    ("SC.L2-3.13.16","System & Comms", "CUI at Rest", "L2", ["sc-28"]),
    ("SI.L2-3.14.4", "System & Info Integrity", "Update Malware Protection", "L2", ["si-3.2"]),
    ("SI.L2-3.14.5", "System & Info Integrity", "System Scanning", "L2", ["si-3.1","si-3.2"]),
    ("SI.L2-3.14.6", "System & Info Integrity", "Security Monitoring", "L2", ["si-4"]),
    ("SI.L2-3.14.7", "System & Info Integrity", "Identify Unauthorized Use", "L2", ["si-4"]),
    ("AT.L2-3.2.1",  "Awareness & Training", "Role-Based Risk Awareness", "L2", ["at-2"]),
    ("AT.L2-3.2.2",  "Awareness & Training", "Role-Based Training", "L2", ["at-3"]),
    ("AT.L2-3.2.3",  "Awareness & Training", "Insider Threat Awareness", "L2", ["at-2.2"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# ISO/IEC 27001:2022 → NIST 800-53r5 crosswalk
# Source: NIST SP 800-53r5 / ISO 27001:2022 crosswalk (NIST OLIR, 2023)
# 93 controls in Annex A, organized in 4 themes (Organizational, People, Physical, Tech)
# ─────────────────────────────────────────────────────────────────────────────
ISO27001_CONTROLS = [
    # 5 — Organizational Controls
    ("5.1",  "Organizational", "Policies for information security", None, ["pm-1","ac-1","au-1","ca-1","cm-1","ia-1","ir-1","ma-1","mp-1","pe-1","pl-1","ps-1","ra-1","sa-1","sc-1","si-1"]),
    ("5.2",  "Organizational", "Information security roles and responsibilities", None, ["pm-2","ac-5","ac-6"]),
    ("5.3",  "Organizational", "Segregation of duties", None, ["ac-5"]),
    ("5.4",  "Organizational", "Management responsibilities", None, ["pm-2","pm-3"]),
    ("5.5",  "Organizational", "Contact with authorities", None, ["ir-6","pm-15"]),
    ("5.6",  "Organizational", "Contact with special interest groups", None, ["pm-15"]),
    ("5.7",  "Organizational", "Threat intelligence", None, ["pm-16","ra-3","si-5"]),
    ("5.8",  "Organizational", "Information security in project management", None, ["pm-8","sa-3"]),
    ("5.9",  "Organizational", "Inventory of information and other associated assets", None, ["cm-8","pm-5"]),
    ("5.10", "Organizational", "Acceptable use of information and other associated assets", None, ["ac-8","pl-4"]),
    ("5.11", "Organizational", "Return of assets", None, ["ps-4","ps-5"]),
    ("5.12", "Organizational", "Classification of information", None, ["ra-2"]),
    ("5.13", "Organizational", "Labelling of information", None, ["mp-3"]),
    ("5.14", "Organizational", "Information transfer", None, ["ac-20","sa-9","sc-8"]),
    ("5.15", "Organizational", "Access control", None, ["ac-1","ac-2","ac-3"]),
    ("5.16", "Organizational", "Identity management", None, ["ia-1","ia-2","ia-4","ia-5"]),
    ("5.17", "Organizational", "Authentication information", None, ["ia-5"]),
    ("5.18", "Organizational", "Access rights", None, ["ac-2","ac-6"]),
    ("5.19", "Organizational", "Information security in supplier relationships", None, ["sa-9","sr-1"]),
    ("5.20", "Organizational", "Addressing information security within supplier agreements", None, ["sa-4","sa-9","sr-3"]),
    ("5.21", "Organizational", "Managing information security in the ICT supply chain", None, ["sa-12","sr-1","sr-2","sr-3"]),
    ("5.22", "Organizational", "Monitoring, review and change management of supplier services", None, ["ca-7","sa-9","sr-6"]),
    ("5.23", "Organizational", "Information security for use of cloud services", None, ["sa-9","sa-4","ac-20"]),
    ("5.24", "Organizational", "Information security incident management planning and preparation", None, ["ir-1","ir-4","ir-8"]),
    ("5.25", "Organizational", "Assessment and decision on information security events", None, ["ir-4","ir-5"]),
    ("5.26", "Organizational", "Response to information security incidents", None, ["ir-4","ir-6"]),
    ("5.27", "Organizational", "Learning from information security incidents", None, ["ir-4","pm-14"]),
    ("5.28", "Organizational", "Collection of evidence", None, ["ir-4","au-12"]),
    ("5.29", "Organizational", "Information security during disruption", None, ["cp-2","cp-10","ir-4"]),
    ("5.30", "Organizational", "ICT readiness for business continuity", None, ["cp-2","cp-7","cp-8"]),
    ("5.31", "Organizational", "Legal, statutory, regulatory and contractual requirements", None, ["pm-9","sa-9"]),
    ("5.32", "Organizational", "Intellectual property rights", None, ["sa-9"]),
    ("5.33", "Organizational", "Protection of records", None, ["au-9","mp-2","mp-4","si-12"]),
    ("5.34", "Organizational", "Privacy and protection of PII", None, ["pt-1","pt-2","pt-3","pt-4","pt-5"]),
    ("5.35", "Organizational", "Independent review of information security", None, ["ca-2"]),
    ("5.36", "Organizational", "Compliance with policies, rules and standards for information security", None, ["ca-2","pm-14"]),
    ("5.37", "Organizational", "Documented operating procedures", None, ["cm-6","pl-4"]),
    # 6 — People Controls
    ("6.1",  "People", "Screening", None, ["ps-3"]),
    ("6.2",  "People", "Terms and conditions of employment", None, ["ps-6","pl-4"]),
    ("6.3",  "People", "Information security awareness, education and training", None, ["at-1","at-2","at-3"]),
    ("6.4",  "People", "Disciplinary process", None, ["ps-8"]),
    ("6.5",  "People", "Responsibilities after termination or change of employment", None, ["ps-4","ps-5"]),
    ("6.6",  "People", "Confidentiality or non-disclosure agreements", None, ["ps-6"]),
    ("6.7",  "People", "Remote working", None, ["ac-17","pe-17"]),
    ("6.8",  "People", "Information security event reporting", None, ["ir-6","si-5"]),
    # 7 — Physical Controls
    ("7.1",  "Physical", "Physical security perimeters", None, ["pe-3"]),
    ("7.2",  "Physical", "Physical entry", None, ["pe-2","pe-3"]),
    ("7.3",  "Physical", "Securing offices, rooms and facilities", None, ["pe-3","pe-5"]),
    ("7.4",  "Physical", "Physical security monitoring", None, ["pe-6"]),
    ("7.5",  "Physical", "Protecting against physical and environmental threats", None, ["pe-13","pe-14","pe-15","pe-18"]),
    ("7.6",  "Physical", "Working in secure areas", None, ["pe-3","pe-5"]),
    ("7.7",  "Physical", "Clear desk and clear screen", None, ["ac-11","mp-2"]),
    ("7.8",  "Physical", "Equipment siting and protection", None, ["pe-5","pe-14","pe-15"]),
    ("7.9",  "Physical", "Security of assets off-premises", None, ["ac-19","mp-5","pe-17"]),
    ("7.10", "Physical", "Storage media", None, ["mp-2","mp-4","mp-5","mp-7"]),
    ("7.11", "Physical", "Supporting utilities", None, ["pe-9","pe-10","pe-11"]),
    ("7.12", "Physical", "Cabling security", None, ["pe-4"]),
    ("7.13", "Physical", "Equipment maintenance", None, ["ma-2","ma-6"]),
    ("7.14", "Physical", "Secure disposal or re-use of equipment", None, ["mp-6","si-12"]),
    # 8 — Technological Controls
    ("8.1",  "Technological", "User endpoint devices", None, ["ac-19","cm-6","cm-8","si-3"]),
    ("8.2",  "Technological", "Privileged access rights", None, ["ac-2","ac-6"]),
    ("8.3",  "Technological", "Information access restriction", None, ["ac-3","ac-4"]),
    ("8.4",  "Technological", "Access to source code", None, ["cm-5","sa-12"]),
    ("8.5",  "Technological", "Secure authentication", None, ["ia-2","ia-5","ia-8"]),
    ("8.6",  "Technological", "Capacity management", None, ["cp-2","sc-5"]),
    ("8.7",  "Technological", "Protection against malware", None, ["si-3","si-8"]),
    ("8.8",  "Technological", "Management of technical vulnerabilities", None, ["ra-5","si-2","si-5"]),
    ("8.9",  "Technological", "Configuration management", None, ["cm-2","cm-6","cm-7","cm-9"]),
    ("8.10", "Technological", "Information deletion", None, ["mp-6","si-12"]),
    ("8.11", "Technological", "Data masking", None, ["sc-28","ac-3"]),
    ("8.12", "Technological", "Data leakage prevention", None, ["ac-4","sc-7","si-4"]),
    ("8.13", "Technological", "Information backup", None, ["cp-9"]),
    ("8.14", "Technological", "Redundancy of information processing facilities", None, ["cp-7","cp-8","sc-5"]),
    ("8.15", "Technological", "Logging", None, ["au-2","au-3","au-12"]),
    ("8.16", "Technological", "Monitoring activities", None, ["au-6","ca-7","si-4"]),
    ("8.17", "Technological", "Clock synchronisation", None, ["au-8"]),
    ("8.18", "Technological", "Use of privileged utility programs", None, ["ac-6","cm-7","ma-3"]),
    ("8.19", "Technological", "Installation of software on operational systems", None, ["cm-10","cm-11","si-7"]),
    ("8.20", "Technological", "Networks security", None, ["sc-7","sc-8","sc-20"]),
    ("8.21", "Technological", "Security of network services", None, ["sa-9","sc-7","sc-8"]),
    ("8.22", "Technological", "Segregation of networks", None, ["ac-4","sc-7"]),
    ("8.23", "Technological", "Web filtering", None, ["sc-7","si-3"]),
    ("8.24", "Technological", "Use of cryptography", None, ["sc-8","sc-12","sc-13","sc-28"]),
    ("8.25", "Technological", "Secure development life cycle", None, ["sa-3","sa-8","sa-15"]),
    ("8.26", "Technological", "Application security requirements", None, ["sa-4","sa-8","sc-2"]),
    ("8.27", "Technological", "Secure system architecture and engineering principles", None, ["sa-8","sc-2","sc-3"]),
    ("8.28", "Technological", "Secure coding", None, ["sa-11","sa-15"]),
    ("8.29", "Technological", "Security testing in development and acceptance", None, ["ca-2","ca-8","sa-11"]),
    ("8.30", "Technological", "Outsourced development", None, ["sa-4","sa-9","sr-3"]),
    ("8.31", "Technological", "Separation of development, test and production environments", None, ["cm-4","sa-3","sc-2"]),
    ("8.32", "Technological", "Change management", None, ["cm-3","sa-10"]),
    ("8.33", "Technological", "Test information", None, ["sa-3","sa-11"]),
    ("8.34", "Technological", "Protection of information systems during audit testing", None, ["ca-2","ca-8"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# CIS Controls v8.1 → NIST 800-53r5 crosswalk
# Source: CIS Controls v8 Mapping to NIST SP 800-53 Rev 5 (CIS official, 2021)
# 18 controls, Implementation Groups IG1/IG2/IG3
# ─────────────────────────────────────────────────────────────────────────────
CIS8_CONTROLS = [
    # CIS Control 1 — Inventory and Control of Enterprise Assets
    ("CIS 1.1",  "Enterprise Asset Inventory", "Establish and Maintain Detailed Enterprise Asset Inventory", "IG1", ["cm-8"]),
    ("CIS 1.2",  "Enterprise Asset Inventory", "Address Unauthorized Assets", "IG1", ["cm-7","cm-8"]),
    ("CIS 1.3",  "Enterprise Asset Inventory", "Utilize an Active Discovery Tool", "IG2", ["ca-7","cm-8"]),
    ("CIS 1.4",  "Enterprise Asset Inventory", "Use Dynamic Host Configuration Protocol (DHCP) Logging", "IG2", ["au-12","cm-8"]),
    ("CIS 1.5",  "Enterprise Asset Inventory", "Use a Passive Asset Discovery Tool", "IG3", ["ca-7","cm-8"]),
    # CIS Control 2 — Inventory and Control of Software Assets
    ("CIS 2.1",  "Software Asset Inventory", "Establish and Maintain Software Inventory", "IG1", ["cm-8","pm-5"]),
    ("CIS 2.2",  "Software Asset Inventory", "Ensure Authorized Software is Currently Supported", "IG1", ["cm-8","si-2"]),
    ("CIS 2.3",  "Software Asset Inventory", "Address Unauthorized Software", "IG1", ["cm-7","cm-11"]),
    ("CIS 2.4",  "Software Asset Inventory", "Utilize Automated Software Inventory Tools", "IG2", ["cm-8"]),
    ("CIS 2.5",  "Software Asset Inventory", "Allowlist Authorized Software", "IG2", ["cm-7.5"]),
    ("CIS 2.6",  "Software Asset Inventory", "Allowlist Authorized Libraries", "IG2", ["cm-7","sa-12"]),
    ("CIS 2.7",  "Software Asset Inventory", "Allowlist Authorized Scripts", "IG3", ["cm-7","si-7"]),
    # CIS Control 3 — Data Protection
    ("CIS 3.1",  "Data Protection", "Establish and Maintain a Data Management Process", "IG1", ["pm-5","ra-2"]),
    ("CIS 3.2",  "Data Protection", "Establish and Maintain a Data Inventory", "IG1", ["cm-8","pm-5"]),
    ("CIS 3.3",  "Data Protection", "Configure Data Access Control Lists", "IG1", ["ac-2","ac-3","mp-2"]),
    ("CIS 3.4",  "Data Protection", "Enforce Data Retention", "IG1", ["au-11","si-12"]),
    ("CIS 3.5",  "Data Protection", "Securely Dispose of Data", "IG1", ["mp-6"]),
    ("CIS 3.6",  "Data Protection", "Encrypt Data on End-User Devices", "IG2", ["ac-19","sc-28"]),
    ("CIS 3.7",  "Data Protection", "Establish and Maintain a Data Classification Scheme", "IG2", ["ra-2"]),
    ("CIS 3.8",  "Data Protection", "Document Data Flows", "IG2", ["pl-8","sa-17"]),
    ("CIS 3.9",  "Data Protection", "Encrypt Data on Removable Media", "IG2", ["mp-5","sc-28"]),
    ("CIS 3.10", "Data Protection", "Encrypt Sensitive Data in Transit", "IG2", ["sc-8","sc-28"]),
    ("CIS 3.11", "Data Protection", "Encrypt Sensitive Data at Rest", "IG3", ["sc-28"]),
    ("CIS 3.12", "Data Protection", "Segment Data Processing and Storage Based on Sensitivity", "IG3", ["ac-4","sc-7"]),
    ("CIS 3.13", "Data Protection", "Deploy a Data Loss Prevention Solution", "IG3", ["ac-4","si-4"]),
    ("CIS 3.14", "Data Protection", "Log Sensitive Data Access", "IG3", ["au-2","au-12"]),
    # CIS Control 4 — Secure Configuration of Enterprise Assets and Software
    ("CIS 4.1",  "Secure Configuration", "Establish and Maintain a Secure Configuration Process", "IG1", ["cm-1","cm-2","cm-6"]),
    ("CIS 4.2",  "Secure Configuration", "Establish and Maintain a Secure Configuration Process for Network Infrastructure", "IG1", ["cm-2","cm-6","cm-9"]),
    ("CIS 4.3",  "Secure Configuration", "Configure Automatic Session Locking on Enterprise Assets", "IG1", ["ac-11"]),
    ("CIS 4.4",  "Secure Configuration", "Implement and Manage a Firewall on Servers", "IG1", ["sc-7"]),
    ("CIS 4.5",  "Secure Configuration", "Implement and Manage a Firewall on End-User Devices", "IG1", ["sc-7"]),
    ("CIS 4.6",  "Secure Configuration", "Securely Manage Enterprise Assets and Software", "IG2", ["cm-6","ma-6"]),
    ("CIS 4.7",  "Secure Configuration", "Manage Default Accounts on Enterprise Assets and Software", "IG1", ["ac-2","cm-6","ia-5"]),
    ("CIS 4.8",  "Secure Configuration", "Uninstall or Disable Unnecessary Services on Enterprise Assets", "IG2", ["cm-7"]),
    ("CIS 4.9",  "Secure Configuration", "Configure Trusted DNS Servers on Enterprise Assets", "IG2", ["sc-20","sc-21"]),
    ("CIS 4.10", "Secure Configuration", "Enforce Automatic Device Lockout on Portable End-User Devices", "IG2", ["ac-11"]),
    ("CIS 4.11", "Secure Configuration", "Enforce Remote Wipe Capability on Portable End-User Devices", "IG2", ["mp-6","ac-19"]),
    ("CIS 4.12", "Secure Configuration", "Separate Enterprise Workspaces on Mobile End-User Devices", "IG3", ["ac-19","sc-2"]),
    # CIS Control 5 — Account Management
    ("CIS 5.1",  "Account Management", "Establish and Maintain an Inventory of Accounts", "IG1", ["ac-2"]),
    ("CIS 5.2",  "Account Management", "Use Unique Passwords", "IG1", ["ia-5"]),
    ("CIS 5.3",  "Account Management", "Disable Dormant Accounts", "IG1", ["ac-2","ia-4"]),
    ("CIS 5.4",  "Account Management", "Restrict Administrator Privileges to Dedicated Administrator Accounts", "IG1", ["ac-6"]),
    ("CIS 5.5",  "Account Management", "Establish and Maintain an Inventory of Service Accounts", "IG2", ["ac-2","ia-4"]),
    ("CIS 5.6",  "Account Management", "Centralize Account Management", "IG2", ["ac-2","ia-4","ia-5"]),
    # CIS Control 6 — Access Control Management
    ("CIS 6.1",  "Access Control Management", "Establish an Access Granting Process", "IG1", ["ac-2","ac-6"]),
    ("CIS 6.2",  "Access Control Management", "Establish an Access Revoking Process", "IG1", ["ac-2","ac-6"]),
    ("CIS 6.3",  "Access Control Management", "Require MFA for Externally-Exposed Applications", "IG2", ["ia-2.1","ia-2.2"]),
    ("CIS 6.4",  "Access Control Management", "Require MFA for Remote Network Access", "IG2", ["ia-2.1","ia-2.2","ac-17"]),
    ("CIS 6.5",  "Access Control Management", "Require MFA for Administrative Access", "IG2", ["ia-2.1","ia-2.2","ac-6"]),
    ("CIS 6.6",  "Access Control Management", "Establish and Maintain an Inventory of Authentication and Authorization Systems", "IG3", ["ia-1","ia-4","pm-5"]),
    ("CIS 6.7",  "Access Control Management", "Centralize Access Control", "IG3", ["ac-1","ac-2","ia-4"]),
    ("CIS 6.8",  "Access Control Management", "Define and Maintain Role-Based Access Control", "IG3", ["ac-2","ac-3","ac-5","ac-6"]),
    # CIS Control 7 — Continuous Vulnerability Management
    ("CIS 7.1",  "Vulnerability Management", "Establish and Maintain a Vulnerability Management Process", "IG1", ["ra-1","ra-3","ra-5"]),
    ("CIS 7.2",  "Vulnerability Management", "Establish and Maintain a Remediation Process", "IG1", ["ra-5","si-2"]),
    ("CIS 7.3",  "Vulnerability Management", "Perform Automated Operating System Patch Management", "IG1", ["si-2","si-2.2"]),
    ("CIS 7.4",  "Vulnerability Management", "Perform Automated Application Patch Management", "IG2", ["si-2"]),
    ("CIS 7.5",  "Vulnerability Management", "Perform Automated Vulnerability Scans of Internal Enterprise Assets", "IG2", ["ra-5"]),
    ("CIS 7.6",  "Vulnerability Management", "Perform Automated Vulnerability Scans of Externally-Exposed Enterprise Assets", "IG2", ["ra-5"]),
    ("CIS 7.7",  "Vulnerability Management", "Remediate Detected Vulnerabilities", "IG2", ["ra-5","si-2"]),
    # CIS Control 8 — Audit Log Management
    ("CIS 8.1",  "Audit Log Management", "Establish and Maintain an Audit Log Management Process", "IG1", ["au-1","au-11"]),
    ("CIS 8.2",  "Audit Log Management", "Collect Audit Logs", "IG1", ["au-2","au-3","au-12"]),
    ("CIS 8.3",  "Audit Log Management", "Ensure Adequate Audit Log Storage", "IG2", ["au-4"]),
    ("CIS 8.4",  "Audit Log Management", "Standardize Time Synchronization", "IG2", ["au-8"]),
    ("CIS 8.5",  "Audit Log Management", "Collect Detailed Audit Logs", "IG2", ["au-2","au-3"]),
    ("CIS 8.6",  "Audit Log Management", "Collect DNS Query Audit Logs", "IG2", ["au-12"]),
    ("CIS 8.7",  "Audit Log Management", "Collect URL Request Audit Logs", "IG2", ["au-12"]),
    ("CIS 8.8",  "Audit Log Management", "Collect Command-Line Audit Logs", "IG2", ["au-12"]),
    ("CIS 8.9",  "Audit Log Management", "Centralize Audit Logs", "IG3", ["au-4","au-9"]),
    ("CIS 8.10", "Audit Log Management", "Retain Audit Logs", "IG3", ["au-11"]),
    ("CIS 8.11", "Audit Log Management", "Conduct Audit Log Reviews", "IG3", ["au-6"]),
    ("CIS 8.12", "Audit Log Management", "Collect Service Provider Logs", "IG3", ["au-12","sa-9"]),
    # CIS Control 9 — Email and Web Browser Protections
    ("CIS 9.1",  "Email & Web Browser", "Ensure Use of Only Fully Supported Browsers and Email Clients", "IG1", ["cm-8","si-2"]),
    ("CIS 9.2",  "Email & Web Browser", "Use DNS Filtering Services", "IG1", ["sc-7","sc-20"]),
    ("CIS 9.3",  "Email & Web Browser", "Maintain and Enforce Network-Based URL Filters", "IG2", ["sc-7","si-3"]),
    ("CIS 9.4",  "Email & Web Browser", "Restrict Unnecessary or Unauthorized Browser and Email Client Extensions", "IG2", ["cm-7","cm-11"]),
    ("CIS 9.5",  "Email & Web Browser", "Implement DMARC", "IG2", ["si-8"]),
    ("CIS 9.6",  "Email & Web Browser", "Block Unnecessary File Types", "IG2", ["sc-7","si-3"]),
    ("CIS 9.7",  "Email & Web Browser", "Deploy and Maintain Email Server Anti-Malware Protections", "IG3", ["si-3","si-8"]),
    # CIS Control 10 — Malware Defenses
    ("CIS 10.1", "Malware Defenses", "Deploy and Maintain Anti-Malware Software", "IG1", ["si-3"]),
    ("CIS 10.2", "Malware Defenses", "Configure Automatic Anti-Malware Signature Updates", "IG1", ["si-3.2"]),
    ("CIS 10.3", "Malware Defenses", "Disable Autorun and Autoplay for Removable Media", "IG1", ["mp-7","si-3"]),
    ("CIS 10.4", "Malware Defenses", "Configure Automatic Anti-Malware Scanning of Removable Media", "IG2", ["si-3","mp-7"]),
    ("CIS 10.5", "Malware Defenses", "Enable Anti-Exploitation Features", "IG2", ["si-7","si-16"]),
    ("CIS 10.6", "Malware Defenses", "Centrally Manage Anti-Malware Software", "IG2", ["si-3"]),
    ("CIS 10.7", "Malware Defenses", "Use Behavior-Based Anti-Malware Software", "IG3", ["si-3"]),
    # CIS Control 11 — Data Recovery
    ("CIS 11.1", "Data Recovery", "Establish and Maintain a Data Recovery Process", "IG1", ["cp-1","cp-9","cp-10"]),
    ("CIS 11.2", "Data Recovery", "Perform Automated Backups", "IG1", ["cp-9"]),
    ("CIS 11.3", "Data Recovery", "Protect Recovery Data", "IG1", ["cp-9.3"]),
    ("CIS 11.4", "Data Recovery", "Establish and Maintain an Isolated Instance of Recovery Data", "IG2", ["cp-9","cp-9.3"]),
    ("CIS 11.5", "Data Recovery", "Test Data Recovery", "IG2", ["cp-4","cp-9"]),
    # CIS Control 12 — Network Infrastructure Management
    ("CIS 12.1", "Network Infrastructure", "Ensure Network Infrastructure is Up-to-Date", "IG2", ["cm-2","si-2"]),
    ("CIS 12.2", "Network Infrastructure", "Establish and Maintain a Secure Network Architecture", "IG2", ["ac-4","sc-7","sc-8"]),
    ("CIS 12.3", "Network Infrastructure", "Securely Manage Network Infrastructure", "IG2", ["cm-6","ma-4","sc-7"]),
    ("CIS 12.4", "Network Infrastructure", "Establish and Maintain Architecture Diagram(s)", "IG2", ["pl-8","sa-17"]),
    ("CIS 12.5", "Network Infrastructure", "Centralize Network Authentication, Authorization, and Auditing (AAA)", "IG2", ["ac-2","ia-4","ia-5","au-2"]),
    ("CIS 12.6", "Network Infrastructure", "Use of Secure Network Management and Communication Protocols", "IG2", ["ma-4","sc-8"]),
    ("CIS 12.7", "Network Infrastructure", "Ensure Remote Devices Utilize a VPN and are Connecting to an Enterprise's AAA Infrastructure", "IG3", ["ac-17","ia-2"]),
    ("CIS 12.8", "Network Infrastructure", "Establish and Maintain Dedicated Computing Resources for All Administrative Work", "IG3", ["ac-6","ac-17"]),
    # CIS Control 13 — Network Monitoring and Defense
    ("CIS 13.1", "Network Monitoring", "Centralize Security Event Alerting", "IG2", ["au-6","si-4"]),
    ("CIS 13.2", "Network Monitoring", "Deploy a Host-Based Intrusion Detection Solution", "IG2", ["si-4"]),
    ("CIS 13.3", "Network Monitoring", "Deploy a Network Intrusion Detection Solution", "IG2", ["si-4"]),
    ("CIS 13.4", "Network Monitoring", "Perform Traffic Filtering Between Network Segments", "IG2", ["ac-4","sc-7"]),
    ("CIS 13.5", "Network Monitoring", "Manage Access Control for Remote Assets", "IG2", ["ac-17","sc-7"]),
    ("CIS 13.6", "Network Monitoring", "Collect Network Traffic Flow Logs", "IG2", ["au-12","si-4"]),
    ("CIS 13.7", "Network Monitoring", "Deploy a Host-Based Intrusion Prevention Solution", "IG3", ["si-4"]),
    ("CIS 13.8", "Network Monitoring", "Deploy a Network Intrusion Prevention Solution", "IG3", ["si-4","sc-7"]),
    ("CIS 13.9", "Network Monitoring", "Deploy Port-Level Access Control", "IG3", ["ac-3","sc-7"]),
    ("CIS 13.10","Network Monitoring", "Perform Application Layer Filtering", "IG3", ["sc-7","si-3"]),
    ("CIS 13.11","Network Monitoring", "Tune Security Event Alerting Thresholds", "IG3", ["au-6","si-4"]),
    # CIS Control 14 — Security Awareness and Skills Training
    ("CIS 14.1", "Security Awareness", "Establish and Maintain a Security Awareness Program", "IG1", ["at-1","at-2"]),
    ("CIS 14.2", "Security Awareness", "Train Workforce Members to Recognize Social Engineering Attacks", "IG1", ["at-2.2"]),
    ("CIS 14.3", "Security Awareness", "Train Workforce Members on Authentication Best Practices", "IG1", ["at-2"]),
    ("CIS 14.4", "Security Awareness", "Train Workforce on Data Handling Best Practices", "IG1", ["at-2"]),
    ("CIS 14.5", "Security Awareness", "Train Workforce Members on Causes of Unintentional Data Exposure", "IG1", ["at-2"]),
    ("CIS 14.6", "Security Awareness", "Train Workforce Members on Recognizing and Reporting Security Incidents", "IG1", ["at-2","ir-6"]),
    ("CIS 14.7", "Security Awareness", "Train Workforce on How to Identify and Report if their Enterprise Assets are Missing Security Updates", "IG2", ["at-2"]),
    ("CIS 14.8", "Security Awareness", "Train Workforce on the Dangers of Connecting to and Transmitting Enterprise Data Over Insecure Networks", "IG2", ["at-2"]),
    ("CIS 14.9", "Security Awareness", "Conduct Role-Specific Security Awareness and Skills Training", "IG3", ["at-3"]),
    # CIS Control 15 — Service Provider Management
    ("CIS 15.1", "Service Provider Management", "Establish and Maintain an Inventory of Service Providers", "IG2", ["sa-9","sr-1"]),
    ("CIS 15.2", "Service Provider Management", "Establish and Maintain a Service Provider Management Policy", "IG2", ["sa-9","sr-1"]),
    ("CIS 15.3", "Service Provider Management", "Classify Service Providers", "IG2", ["ra-9","sr-2"]),
    ("CIS 15.4", "Service Provider Management", "Ensure Service Provider Contracts Include Security Requirements", "IG2", ["sa-4","sa-9","sr-5"]),
    ("CIS 15.5", "Service Provider Management", "Assess Service Providers", "IG3", ["sa-9","sr-6"]),
    ("CIS 15.6", "Service Provider Management", "Monitor Service Providers", "IG3", ["ca-7","sa-9"]),
    ("CIS 15.7", "Service Provider Management", "Securely Decommission Service Providers", "IG3", ["sa-9","sr-3"]),
    # CIS Control 16 — Application Software Security
    ("CIS 16.1", "Application Security", "Establish and Maintain a Secure Application Development Process", "IG2", ["sa-3","sa-8","sa-15"]),
    ("CIS 16.2", "Application Security", "Establish and Maintain a Process to Accept and Address Software Vulnerabilities", "IG2", ["ra-5","sa-11"]),
    ("CIS 16.3", "Application Security", "Perform Root Cause Analysis on Security Vulnerabilities", "IG2", ["ra-5","sa-11"]),
    ("CIS 16.4", "Application Security", "Establish and Manage an Inventory of Third-Party Software Components", "IG2", ["sa-12","sr-4"]),
    ("CIS 16.5", "Application Security", "Use Up-to-Date and Trusted Third-Party Software Components", "IG2", ["sa-12","si-2"]),
    ("CIS 16.6", "Application Security", "Establish and Maintain a Severity Rating System and Process for Application Vulnerabilities", "IG2", ["ra-3","ra-5"]),
    ("CIS 16.7", "Application Security", "Use Standard Hardening Configuration Templates for Application Infrastructure", "IG2", ["cm-2","cm-6"]),
    ("CIS 16.8", "Application Security", "Separate Production and Non-Production Systems", "IG3", ["cm-4","sa-3","sc-2"]),
    ("CIS 16.9", "Application Security", "Train Developers in Application Security Concepts and Secure Coding", "IG3", ["at-3","sa-11"]),
    ("CIS 16.10","Application Security", "Apply Secure Design Principles in Application Architectures", "IG3", ["sa-8","sc-2"]),
    ("CIS 16.11","Application Security", "Leverage Vetted Modules or Services for Application Security Components", "IG3", ["sa-12","sr-4"]),
    ("CIS 16.12","Application Security", "Implement Code-Level Security Checks", "IG3", ["sa-11","sa-15"]),
    ("CIS 16.13","Application Security", "Conduct Application Penetration Testing", "IG3", ["ca-8"]),
    ("CIS 16.14","Application Security", "Conduct Threat Modeling", "IG3", ["ra-3","sa-8","sa-11"]),
    # CIS Control 17 — Incident Response Management
    ("CIS 17.1", "Incident Response", "Designate Personnel to Manage Incident Handling", "IG1", ["ir-7"]),
    ("CIS 17.2", "Incident Response", "Establish and Maintain Contact Information for Reporting Security Incidents", "IG1", ["ir-6"]),
    ("CIS 17.3", "Incident Response", "Establish and Maintain an Enterprise Process for Reporting Incidents", "IG1", ["ir-6","ir-7"]),
    ("CIS 17.4", "Incident Response", "Establish and Maintain an Incident Response Process", "IG2", ["ir-1","ir-4","ir-8"]),
    ("CIS 17.5", "Incident Response", "Assign Key Roles and Responsibilities", "IG2", ["ir-7","pm-2"]),
    ("CIS 17.6", "Incident Response", "Define Mechanisms for Communicating During Incident Response", "IG2", ["ir-4","ir-7"]),
    ("CIS 17.7", "Incident Response", "Conduct Routine Incident Response Exercises", "IG2", ["ir-3"]),
    ("CIS 17.8", "Incident Response", "Conduct Post-Incident Reviews", "IG3", ["ir-4","pm-14"]),
    ("CIS 17.9", "Incident Response", "Establish and Maintain Security Incident Thresholds", "IG3", ["ir-4","ir-5"]),
    # CIS Control 18 — Penetration Testing
    ("CIS 18.1", "Penetration Testing", "Establish and Maintain a Penetration Testing Program", "IG3", ["ca-8","ra-5"]),
    ("CIS 18.2", "Penetration Testing", "Perform Periodic External Penetration Tests", "IG3", ["ca-8"]),
    ("CIS 18.3", "Penetration Testing", "Remediate Penetration Test Findings", "IG3", ["ca-5","ra-5","si-2"]),
    ("CIS 18.4", "Penetration Testing", "Validate Security Measures", "IG3", ["ca-2","ca-8"]),
    ("CIS 18.5", "Penetration Testing", "Perform Periodic Internal Penetration Tests", "IG3", ["ca-8"]),
]

FRAMEWORK_DATA = {
    "csf2":     CSF2_CONTROLS,
    "sp800171": SP800171_CONTROLS,
    "cmmc2":    CMMC2_CONTROLS,
    "iso27001": ISO27001_CONTROLS,
    "cis8":     CIS8_CONTROLS,
}

SOURCE_MAP = {
    "csf2":     "nist_official",
    "sp800171": "nist_official",
    "cmmc2":    "nist_official",
    "iso27001": "nist_official",
    "cis8":     "cis",
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
                # Normalize: strip control enhancement suffix (e.g. "ia-2.1" → "ia-2")
                # System controls table tracks base controls only; enhancements collapse to parent
                nid = nist_id.lower()
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

    # Verification
    conn2 = sqlite3.connect(DB_PATH)
    cur2 = conn2.cursor()
    cur2.execute("SELECT short_name, name FROM compliance_frameworks ORDER BY short_name")
    print("\nFrameworks in DB:")
    for r in cur2.fetchall(): print(f"  {r[0]:12s}  {r[1]}")
    cur2.execute("""
        SELECT cf.short_name, COUNT(DISTINCT fc.id) as controls, COUNT(cx.id) as mappings
        FROM compliance_frameworks cf
        JOIN framework_controls fc ON fc.framework_id=cf.id
        JOIN control_crosswalks cx ON cx.framework_control_id=fc.id
        GROUP BY cf.short_name ORDER BY cf.short_name
    """)
    print("\nCoverage summary:")
    print(f"  {'framework':<12} {'controls':>9} {'crosswalks':>11}")
    for r in cur2.fetchall():
        print(f"  {r[0]:<12} {r[1]:>9} {r[2]:>11}")
    conn2.close()


if __name__ == "__main__":
    main()
