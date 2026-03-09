#!/usr/bin/env python3
"""
Catalog Gap Migration — BLACKSITE
Fills all identified control catalog gaps:
  1. iso27001_annex_a crosswalks (copy from iso27001 by control_id match)
  2. iso27001_core crosswalks    (copy from iso27001 by control_id match)
  3. iso27701 crosswalks         (map to NIST 800-53 privacy controls)
  4. npf crosswalks              (map to NIST 800-53 privacy controls)
  5. HITRUST CSF framework + controls + crosswalks
  6. nist_ics controls (SP 800-82 ICS/SCADA overlay)
  7. dod_srg controls (DoD Cloud Computing SRG overlay)
"""

import sqlite3
import uuid
from datetime import datetime

DB = "/home/graycat/projects/blacksite/blacksite.db"

NOW = datetime.utcnow().isoformat()


def run(conn):
    cur = conn.cursor()
    print("=== BLACKSITE Catalog Gap Migration ===\n")

    # ── 1. iso27001_annex_a crosswalks ──────────────────────────────────────
    print("[1] Building iso27001_annex_a crosswalks …")

    # annex_a uses same control_id scheme as iso27001 (5.x, 6.x, 7.x, 8.x)
    cur.execute("""
        SELECT fc_src.control_id, cw.nist_control_id, cw.mapping_type, cw.confidence, cw.source, cw.notes
        FROM framework_controls fc_src
        JOIN control_crosswalks cw ON cw.framework_control_id = fc_src.id
        WHERE fc_src.framework_id = '1ffd6850-b08d-5c55-a2ce-4b39b562b3c0'
    """)
    iso27001_xwalks = cur.fetchall()  # (control_id, nist_control_id, mapping_type, confidence, source, notes)

    # Build lookup: control_id → list of crosswalk rows
    iso27001_map = {}
    for row in iso27001_xwalks:
        iso27001_map.setdefault(row[0], []).append(row[1:])

    # Get annex_a controls
    cur.execute("""
        SELECT id, control_id FROM framework_controls
        WHERE framework_id = 'bfdb796991bb0ce6098064a9ac71ea11'
    """)
    annex_a_controls = cur.fetchall()

    annex_a_inserted = 0
    for fc_id, ctrl_id in annex_a_controls:
        if ctrl_id in iso27001_map:
            for (nist_id, mtype, conf, src, notes) in iso27001_map[ctrl_id]:
                cur.execute("""
                    INSERT OR IGNORE INTO control_crosswalks
                      (framework_control_id, nist_control_id, mapping_type, confidence, source, notes, created_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (fc_id, nist_id, mtype or 'direct', conf or 'high', src or 'nist_official', notes, NOW))
                annex_a_inserted += cur.rowcount
    print(f"    ✓ iso27001_annex_a: {annex_a_inserted} crosswalks inserted")

    # ── 2. iso27001_core crosswalks ──────────────────────────────────────────
    print("[2] Building iso27001_core crosswalks …")

    # core uses A.5.x scheme — iso27001 also has A.5.x controls
    cur.execute("""
        SELECT id, control_id FROM framework_controls
        WHERE framework_id = '1ebac8ce9e4b2141defa58476d337b2d'
    """)
    core_controls = cur.fetchall()

    # iso27001_core uses A.5.x format; crosswalks live on 5.x format in iso27001 — strip "A." prefix to match
    core_inserted = 0
    for fc_id, ctrl_id in core_controls:
        lookup_id = ctrl_id[2:] if ctrl_id.startswith("A.") else ctrl_id
        if lookup_id in iso27001_map:
            for (nist_id, mtype, conf, src, notes) in iso27001_map[lookup_id]:
                cur.execute("""
                    INSERT OR IGNORE INTO control_crosswalks
                      (framework_control_id, nist_control_id, mapping_type, confidence, source, notes, created_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (fc_id, nist_id, mtype or 'direct', conf or 'high', src or 'nist_official', notes, NOW))
                core_inserted += cur.rowcount
    print(f"    ✓ iso27001_core: {core_inserted} crosswalks inserted")

    # ── 3. iso27701 crosswalks ───────────────────────────────────────────────
    print("[3] Building iso27701 crosswalks …")

    # ISO 27701 → NIST 800-53 Rev 5 privacy controls mapping
    # Source: NIST SP 800-53 Rev 5 Appendix O + ISO/IEC 27701:2019 Annex D
    ISO27701_XWALKS = {
        # Section 7: PII Controller
        "7.2.1": ["pt-3", "pm-25"],                               # Purpose identification
        "7.2.2": ["pt-2"],                                         # Lawful basis
        "7.2.3": ["pt-4"],                                         # Consent
        "7.2.4": ["pt-3", "sa-8.33"],                             # Necessity/proportionality
        "7.2.5": ["ra-8", "ra-3"],                                 # Privacy risk assessment
        "7.2.6": ["pl-8", "sa-3"],                                 # Privacy by design
        "7.2.7": ["pm-5.1"],                                       # PII inventories
        "7.2.8": ["si-12", "si-12.3"],                            # Use/retention/disposal
        "7.3.1": ["pt-2"],                                         # Legitimate interest
        "7.3.2": ["pm-19"],                                        # Controller responsibilities
        "7.3.3": ["pt-5"],                                         # Privacy notice
        "7.3.4": ["pt-4"],                                         # Withdraw consent
        "7.3.5": ["pt-5"],                                         # Privacy notice specific
        "7.4.1": ["sa-8.33", "pm-25"],                            # Limit collection
        "7.4.2": ["sa-8.33"],                                      # Limit processing
        "7.4.3": ["si-18"],                                        # Accuracy/quality
        "7.4.4": ["pm-25", "sa-8.33"],                            # Minimization objectives
        "7.4.5": ["si-12.3", "si-19"],                            # De-identification/deletion
        "7.4.6": ["si-12"],                                        # Temporary files
        "7.4.7": ["si-12", "au-11"],                              # Retention
        "7.4.8": ["si-12.3"],                                      # Disposal
        "7.4.9": ["sc-7.24"],                                      # Transmission controls
        "7.5.1": ["pt-6"],                                         # Cross-jurisdiction transfer basis
        "7.5.2": ["pt-6"],                                         # Countries for transfer
        "7.5.3": ["pt-6", "pm-21"],                               # Records of transfer
        "7.6.1": ["sa-9"],                                         # Sharing with third parties
        "7.6.2": ["sa-9", "ps-6"],                                 # Sharing PII with third parties
        "7.6.3": ["pt-6"],                                         # Third-party notification
        "7.7.1": ["si-18.4", "pt-4"],                             # Individual rights requests
        "7.7.2": ["si-18.4"],                                      # Fulfilling requests
        "7.7.3": ["pt-5"],                                         # Communication to subjects
        "7.8.1": ["ra-8"],                                         # Data protection impact
        "7.8.2": ["pm-21", "au-2"],                               # Records of processing
        "7.8.3": ["si-1", "sa-4"],                                # Security of processing
        "7.8.4": ["pm-21"],                                        # Transfer records
        "7.8.5": ["ir-6", "ir-8.1"],                              # Breach notification
        # Section 8: PII Processor
        "8.2.1": ["sa-9", "ps-6"],                                 # Customer agreement
        "8.2.2": ["pt-3"],                                         # Processor purposes
        "8.2.3": ["pt-4"],                                         # Marketing restriction
        "8.2.4": ["sa-4"],                                         # Infringing instructions
        "8.2.5": ["sa-9"],                                         # Customer obligations
        "8.2.6": ["au-2", "pm-21"],                               # Processor records
        "8.3.1": ["si-18.4"],                                      # Obligations to principals
        "8.4.1": ["pt-6"],                                         # Jurisdiction transfer
        "8.4.2": ["pt-6"],                                         # Countries/orgs (processor)
        "8.4.3": ["pm-21"],                                        # Transfer records (processor)
        "8.5.1": ["sa-9"],                                         # Sub-processor management
        "8.5.2": ["sa-9", "ps-6"],                                 # Sub-processor agreements
        "8.5.3": ["ac-1", "sa-9"],                                 # Sub-processor access
        "8.5.4": ["sa-9"],                                         # Sub-processor change
        "8.5.5": ["sa-9", "ps-6"],                                 # Contracts with customers
        "8.5.6": ["pt-3"],                                         # Independent determination
        "8.5.7": ["sa-9"],                                         # Sub-processor notification
    }

    cur.execute("""
        SELECT id, control_id FROM framework_controls
        WHERE framework_id = '97d41b155b4fcdf8272fbe3755af54cc'
    """)
    iso27701_controls = {r[1]: r[0] for r in cur.fetchall()}

    iso27701_inserted = 0
    for ctrl_id, nist_ids in ISO27701_XWALKS.items():
        fc_id = iso27701_controls.get(ctrl_id)
        if not fc_id:
            continue
        for nist_id in nist_ids:
            cur.execute("""
                INSERT OR IGNORE INTO control_crosswalks
                  (framework_control_id, nist_control_id, mapping_type, confidence, source, notes, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (fc_id, nist_id, 'direct', 'high', 'iso27701_annex_d', None, NOW))
            iso27701_inserted += cur.rowcount
    print(f"    ✓ iso27701: {iso27701_inserted} crosswalks inserted")

    # ── 4. NPF crosswalks ────────────────────────────────────────────────────
    print("[4] Building NPF crosswalks …")

    # NIST Privacy Framework v1.0 → NIST 800-53 Rev 5 mapping
    # Source: NISTIR 8278A (Crosswalk: NPF → SP 800-53 Rev 5)
    NPF_XWALKS = {
        # IDENTIFY function
        "ID.IM-P1": ["pm-5.1", "cm-8"],
        "ID.IM-P2": ["pm-5.1", "pm-11"],
        "ID.IM-P3": ["pm-9", "pm-11"],
        "ID.IM-P4": ["pm-9", "ra-3"],
        "ID.IM-P5": ["pt-3", "pm-25"],
        "ID.IM-P6": ["sa-9", "pm-5.1"],
        "ID.IM-P7": ["sa-9"],
        "ID.IM-P8": ["pm-5.1", "sa-9"],
        "ID.BE-P1": ["pm-9", "pm-11"],
        "ID.BE-P2": ["pm-11"],
        "ID.BE-P3": ["pm-8", "cp-2"],
        "ID.BE-P4": ["cp-2", "pm-8"],
        "ID.RA-P1": ["ra-3", "ra-8"],
        "ID.RA-P2": ["ra-3", "ra-8"],
        "ID.RA-P3": ["ra-3"],
        "ID.RA-P4": ["ra-3", "pm-28"],
        "ID.RA-P5": ["ra-3"],
        "ID.RA-P6": ["ra-7"],
        "ID.DE-P1": ["sa-9", "pm-9"],
        "ID.DE-P2": ["sa-9"],
        "ID.DE-P3": ["sa-9", "ps-6"],
        "ID.DE-P4": ["ca-7", "sa-9"],
        "ID.DE-P5": ["cp-2", "ir-8"],
        # GOVERN function
        "GV.PO-P1": ["pm-18", "pl-1"],
        "GV.PO-P2": ["sa-3", "pl-8"],
        "GV.PO-P3": ["pm-19", "ps-1"],
        "GV.PO-P4": ["pm-9", "ra-3"],
        "GV.PO-P5": ["pm-18", "pm-27"],
        "GV.PO-P6": ["pm-9", "ra-7"],
        "GV.RM-P1": ["pm-9", "ra-3"],
        "GV.RM-P2": ["pm-9"],
        "GV.RM-P3": ["pm-9", "sa-9"],
        "GV.AT-P1": ["at-2", "at-3"],
        "GV.AT-P2": ["pm-13", "at-3"],
        "GV.AT-P3": ["pm-13", "at-3"],
        "GV.AT-P4": ["at-2", "at-4"],
        "GV.MT-P1": ["ca-7", "pm-31"],
        "GV.MT-P2": ["ca-7", "pm-14"],
        "GV.MT-P3": ["ca-2", "ca-7"],
        "GV.MT-P4": ["pm-26"],
        "GV.MT-P5": ["pm-6"],
        "GV.MT-P6": ["ir-8.1", "pm-26"],
        # CONTROL function
        "CT.PO-P1": ["pt-2", "ac-1"],
        "CT.PO-P2": ["si-18.4", "pt-4"],
        "CT.PO-P3": ["si-18", "si-12"],
        "CT.PO-P4": ["pt-5", "pt-3"],
        "CT.DM-P1": ["sa-8.33", "pt-3"],
        "CT.DM-P2": ["si-19", "ac-3.14"],
        "CT.DM-P3": ["sa-8.33"],
        "CT.DM-P4": ["sa-3", "pl-8"],
        "CT.DM-P5": ["si-12", "au-11"],
        "CT.DM-P6": ["si-12.3", "si-19"],
        "CT.DM-P7": ["si-18.4", "pt-4"],
        "CT.DM-P8": ["pt-4", "si-18"],
        "CT.DM-P9": ["au-2", "au-11"],
        "CT.DM-P10": ["ca-2", "ca-7"],
        "CT.DP-P1": ["si-19", "sa-8.33"],
        "CT.DP-P2": ["si-19", "ac-3.14"],
        "CT.DP-P3": ["si-19"],
        "CT.DP-P4": ["si-19", "sa-3"],
        "CT.DP-P5": ["pl-8", "sa-3"],
        # COMMUNICATE function
        "CM.PO-P1": ["pt-5", "pm-20"],
        "CM.PO-P2": ["pt-5", "pm-20"],
        "CM.PO-P3": ["pt-3", "pm-20"],
        "CM.PO-P4": ["pm-26", "ir-8"],
        "CM.AW-P1": ["pt-5"],
        "CM.AW-P2": ["pt-5", "pt-6"],
        "CM.AW-P3": ["pt-5"],
        "CM.AW-P4": ["pm-20.1", "pt-5"],
        "CM.AW-P5": ["pt-4"],
        "CM.AW-P6": ["pt-5", "pt-4"],
        # PROTECT function
        "PR.PO-P1": ["cm-2", "cm-6"],
        "PR.PO-P2": ["sa-3", "sa-11"],
        "PR.PO-P3": ["cm-3", "cm-4"],
        "PR.PO-P4": ["cp-9"],
        "PR.PO-P5": ["pe-1"],
        "PR.PO-P6": ["mp-6", "si-12.3"],
        "PR.PO-P7": ["ca-7"],
        "PR.PO-P8": ["pm-14"],
        "PR.PO-P9": ["ir-8", "cp-2"],
        "PR.PO-P10": ["ir-3", "cp-4"],
        "PR.AC-P1": ["ia-1", "ia-2"],
        "PR.AC-P2": ["pe-2", "pe-3"],
        "PR.AC-P3": ["ac-17"],
        "PR.AC-P4": ["ac-2", "ac-3"],
        "PR.AC-P5": ["sc-7"],
        "PR.AC-P6": ["ia-3"],
        "PR.DS-P1": ["sc-28"],
        "PR.DS-P2": ["sc-8"],
        "PR.DS-P3": ["mp-6", "cm-8"],
        "PR.DS-P4": ["si-12.1"],
        "PR.DS-P5": ["si-12.2", "sc-7.24"],
        "PR.DS-P6": ["si-7"],
        "PR.DS-P7": ["sa-3"],
        "PR.DS-P8": ["si-7"],
    }

    cur.execute("""
        SELECT id, control_id FROM framework_controls
        WHERE framework_id = 'a7c421c92d9a10b15b37f247dfa380cc'
    """)
    npf_controls = {r[1]: r[0] for r in cur.fetchall()}

    npf_inserted = 0
    for ctrl_id, nist_ids in NPF_XWALKS.items():
        fc_id = npf_controls.get(ctrl_id)
        if not fc_id:
            continue
        for nist_id in nist_ids:
            cur.execute("""
                INSERT OR IGNORE INTO control_crosswalks
                  (framework_control_id, nist_control_id, mapping_type, confidence, source, notes, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (fc_id, nist_id, 'direct', 'high', 'nistir8278a', None, NOW))
            npf_inserted += cur.rowcount
    print(f"    ✓ npf: {npf_inserted} crosswalks inserted")

    # ── 5. HITRUST CSF framework + controls + crosswalks ────────────────────
    print("[5] Adding HITRUST CSF framework, controls, and crosswalks …")

    HITRUST_FW_ID = "hitrust_csf_v11_framework_uuid"

    # Check if already exists
    cur.execute("SELECT id FROM compliance_frameworks WHERE short_name='hitrust'")
    existing = cur.fetchone()
    if existing:
        HITRUST_FW_ID = existing[0]
        print(f"    (HITRUST framework already exists: {HITRUST_FW_ID})")
    else:
        cur.execute("""
            INSERT INTO compliance_frameworks
              (id, name, short_name, version, category, published_by, description, source_url, is_active, kind)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            HITRUST_FW_ID,
            "HITRUST CSF",
            "hitrust",
            "v11",
            "healthcare",
            "Health Information Trust Alliance (HITRUST)",
            "HITRUST Common Security Framework — an industry-standard certifiable framework combining HIPAA, NIST, PCI DSS, ISO 27001, and other regulatory requirements for healthcare and regulated industries.",
            "https://hitrustalliance.net/hitrust-csf/",
            1,
            "framework"
        ))
        print(f"    ✓ HITRUST CSF framework created")

    # Enable in org_enabled_frameworks if not already
    cur.execute("""
        INSERT OR IGNORE INTO org_enabled_frameworks (framework_id, is_enabled)
        VALUES (?, 1)
    """, (HITRUST_FW_ID,))
    if cur.rowcount:
        print(f"    ✓ HITRUST enabled in org_enabled_frameworks")

    # HITRUST CSF v11 Control Requirements (representative — 19 domains, ~135 requirements)
    # Domains 00-13 + supplementary domains
    HITRUST_CONTROLS = [
        # 00 — Information Protection Program
        ("00.a", "Information Security Management Program",
         "Establish and maintain an information security management program aligned to organizational risk.",
         "00 - Information Protection Program", "1"),
        ("00.b", "Risk Management Program",
         "Implement a risk management program that identifies, assesses, and treats information security risks.",
         "00 - Information Protection Program", "1"),
        ("00.c", "Oversight and Accountability",
         "Define and assign security roles and responsibilities for the information security management program.",
         "00 - Information Protection Program", "1"),

        # 01 — Access Control
        ("01.a", "Access Control Policy",
         "Establish, document, and implement an access control policy based on business and security requirements.",
         "01 - Access Control", "1"),
        ("01.b", "User Registration and Deregistration",
         "Implement a formal user registration and deregistration process for granting and revoking access.",
         "01 - Access Control", "1"),
        ("01.c", "User Access Provisioning",
         "Implement a formal process for assigning or revoking access rights for all user types.",
         "01 - Access Control", "1"),
        ("01.d", "Management of Privileged Access Rights",
         "Restrict and control the allocation and use of privileged access rights.",
         "01 - Access Control", "1"),
        ("01.e", "Review of User Access Rights",
         "Conduct regular reviews of user access rights.",
         "01 - Access Control", "2"),
        ("01.f", "Removal/Adjustment of Access Rights",
         "Remove or adjust access rights upon employment termination, change of role, or contract expiration.",
         "01 - Access Control", "1"),
        ("01.g", "Use of Secret Authentication Information",
         "Enforce secure use and management of secret authentication information (passwords, tokens).",
         "01 - Access Control", "1"),
        ("01.h", "Access Control to Networks and Network Services",
         "Restrict user access to only those network services that they have been specifically authorized to use.",
         "01 - Access Control", "1"),
        ("01.i", "User Authentication for External Connections",
         "Use appropriate authentication methods to control access by remote users.",
         "01 - Access Control", "2"),
        ("01.j", "Network Segregation",
         "Segregate networks into security zones using firewalls and network access controls.",
         "01 - Access Control", "2"),

        # 02 — Audit Logging & Monitoring
        ("02.a", "Audit Logging",
         "Produce, protect, and review logs recording user activities, exceptions, and security events.",
         "02 - Audit Logging & Monitoring", "1"),
        ("02.b", "Monitoring System Use",
         "Establish procedures for monitoring use of information processing facilities and regularly review results.",
         "02 - Audit Logging & Monitoring", "1"),
        ("02.c", "Protection of Log Information",
         "Protect logging facilities and log information against tampering and unauthorized access.",
         "02 - Audit Logging & Monitoring", "2"),
        ("02.d", "Administrator and Operator Logs",
         "Log and review activities of system administrators and system operators.",
         "02 - Audit Logging & Monitoring", "2"),
        ("02.e", "Fault Logging",
         "Log faults and take corrective action.",
         "02 - Audit Logging & Monitoring", "3"),
        ("02.f", "Clock Synchronization",
         "Synchronize clocks of information processing systems using a consistent time source.",
         "02 - Audit Logging & Monitoring", "2"),

        # 03 — Education, Training & Awareness
        ("03.a", "Information Security Awareness and Training",
         "Provide security awareness education and training to all employees and contractors.",
         "03 - Education, Training & Awareness", "1"),
        ("03.b", "Education and Training",
         "Ensure that all employees receive appropriate training and regular updates on organizational policies.",
         "03 - Education, Training & Awareness", "1"),
        ("03.c", "Personnel Security",
         "Implement screening and background check processes for employees accessing sensitive information.",
         "03 - Education, Training & Awareness", "1"),

        # 04 — Incident Management
        ("04.a", "Reporting Information Security Events",
         "Report information security events through appropriate management channels quickly.",
         "04 - Incident Management", "1"),
        ("04.b", "Reporting Information Security Weaknesses",
         "Require employees and contractors to report any observed or suspected security weaknesses.",
         "04 - Incident Management", "1"),
        ("04.c", "Assessment of and Decision on Information Security Events",
         "Assess and determine whether information security events should be classified as incidents.",
         "04 - Incident Management", "2"),
        ("04.d", "Response to Information Security Incidents",
         "Respond to incidents in accordance with documented procedures and escalation paths.",
         "04 - Incident Management", "1"),
        ("04.e", "Learning from Information Security Incidents",
         "Capture and apply knowledge gained from analyzing and resolving incidents.",
         "04 - Incident Management", "2"),
        ("04.f", "Collection of Evidence",
         "Define and apply procedures for the collection, acquisition, and preservation of evidence.",
         "04 - Incident Management", "3"),

        # 05 — Information Security Policies
        ("05.a", "Information Security Policy Document",
         "Define, approve, publish, and communicate an information security policy.",
         "05 - Information Security Policies", "1"),
        ("05.b", "Review of the Information Security Policy",
         "Review information security policies at planned intervals or upon significant changes.",
         "05 - Information Security Policies", "2"),

        # 06 — Operational and Communications Security
        ("06.a", "Documented Operating Procedures",
         "Document, maintain, and make available operating procedures for all users who need them.",
         "06 - Operational and Communications Security", "1"),
        ("06.b", "Change Management",
         "Control changes to the organization, business processes, information processing facilities, and systems.",
         "06 - Operational and Communications Security", "1"),
        ("06.c", "Capacity Management",
         "Monitor, tune, and project future capacity requirements.",
         "06 - Operational and Communications Security", "2"),
        ("06.d", "Separation of Development, Testing, and Operational Environments",
         "Separate development, testing, and operational environments to reduce risks.",
         "06 - Operational and Communications Security", "1"),
        ("06.e", "Malware Protection",
         "Implement controls against malware, combined with user awareness.",
         "06 - Operational and Communications Security", "1"),
        ("06.f", "Information Backup",
         "Make and regularly test backup copies of information, software, and system images.",
         "06 - Operational and Communications Security", "1"),
        ("06.g", "Event Logging",
         "Produce event logs recording user activities, exceptions, faults, and information security events.",
         "06 - Operational and Communications Security", "1"),
        ("06.h", "Technical Vulnerability Management",
         "Obtain timely information about technical vulnerabilities and take appropriate measures.",
         "06 - Operational and Communications Security", "1"),
        ("06.i", "Restrictions on Software Installation",
         "Implement rules governing installation of software by users.",
         "06 - Operational and Communications Security", "2"),

        # 07 — Risk Management
        ("07.a", "Risk Assessment",
         "Perform information security risk assessments that identify, analyze, and evaluate risks.",
         "07 - Risk Management", "1"),
        ("07.b", "Risk Treatment",
         "Define and apply an information security risk treatment process.",
         "07 - Risk Management", "1"),

        # 08 — Configuration Management
        ("08.a", "Security Requirements Analysis and Specification",
         "Include information security requirements in requirements for new systems or enhancements.",
         "08 - Configuration Management", "1"),
        ("08.b", "Secure System Engineering Principles",
         "Establish, document, maintain, and apply secure engineering principles.",
         "08 - Configuration Management", "2"),
        ("08.c", "Configuration of Security Options",
         "Implement standard hardening procedures for operating systems, applications, and databases.",
         "08 - Configuration Management", "1"),
        ("08.d", "Technical Review of Applications after OS Changes",
         "Review and test business-critical applications when changes are made to the operating platform.",
         "08 - Configuration Management", "2"),
        ("08.e", "Software Development and Acquisition",
         "Supervise and monitor outsourced software development activities.",
         "08 - Configuration Management", "2"),

        # 09 — Mobile Device Security
        ("09.a", "Mobile Device Policy",
         "Establish and implement a policy and supporting security measures to manage mobile device risks.",
         "09 - Mobile Device Security", "1"),
        ("09.b", "Teleworking",
         "Implement a policy and supporting security measures for teleworking.",
         "09 - Mobile Device Security", "1"),

        # 10 — Network Protection
        ("10.a", "Network Controls",
         "Manage and control networks to protect information in systems and applications.",
         "10 - Network Protection", "1"),
        ("10.b", "Security of Network Services",
         "Identify security mechanisms, service levels, and management requirements for all network services.",
         "10 - Network Protection", "1"),
        ("10.c", "Segregation in Networks",
         "Segregate groups of information services, users, and information systems on networks.",
         "10 - Network Protection", "2"),
        ("10.d", "Electronic Messaging",
         "Protect information involved in electronic messaging.",
         "10 - Network Protection", "2"),
        ("10.e", "Interconnected Business Information Systems",
         "Identify and implement controls for exchanging information with external parties.",
         "10 - Network Protection", "2"),

        # 11 — Physical and Environmental Security
        ("11.a", "Physical Security Perimeter",
         "Define and use security perimeters to protect areas that contain sensitive information.",
         "11 - Physical & Environmental Security", "1"),
        ("11.b", "Physical Entry Controls",
         "Secure areas protected by appropriate entry controls to ensure only authorized personnel are allowed.",
         "11 - Physical & Environmental Security", "1"),
        ("11.c", "Clear Desk and Clear Screen Policy",
         "Adopt a clear desk policy for papers and removable storage media and clear screen policy.",
         "11 - Physical & Environmental Security", "2"),
        ("11.d", "Equipment Siting and Protection",
         "Site and protect equipment to reduce risks from environmental threats and unauthorized access.",
         "11 - Physical & Environmental Security", "1"),

        # 12 — Data Protection and Privacy
        ("12.a", "Information Classification",
         "Classify information in terms of legal requirements, value, criticality, and sensitivity.",
         "12 - Data Protection & Privacy", "1"),
        ("12.b", "Labelling of Information",
         "Develop and implement an appropriate set of procedures for information labelling.",
         "12 - Data Protection & Privacy", "1"),
        ("12.c", "Handling of Assets",
         "Develop and implement procedures for handling assets in accordance with the classification scheme.",
         "12 - Data Protection & Privacy", "1"),
        ("12.d", "Media Handling",
         "Implement procedures for management of removable media.",
         "12 - Data Protection & Privacy", "1"),
        ("12.e", "Privacy and Protection of Personally Identifiable Information",
         "Ensure privacy and protection of personally identifiable information as required by law and regulation.",
         "12 - Data Protection & Privacy", "1"),
        ("12.f", "Regulation of Cryptographic Controls",
         "Comply with agreements, laws, and regulations on cryptographic controls.",
         "12 - Data Protection & Privacy", "2"),

        # 13 — Third-Party Assurance
        ("13.a", "Information Security in Supplier Relationships",
         "Agree on and document information security requirements with each supplier.",
         "13 - Third-Party Assurance", "1"),
        ("13.b", "Addressing Security within Supplier Agreements",
         "Include requirements to address risks associated with ICT products and services in supplier agreements.",
         "13 - Third-Party Assurance", "1"),
        ("13.c", "Monitoring and Review of Supplier Services",
         "Regularly monitor, review, and audit supplier service delivery.",
         "13 - Third-Party Assurance", "2"),
        ("13.d", "Managing Changes to Supplier Services",
         "Manage changes to supplier service provision, maintaining and improving policies and procedures.",
         "13 - Third-Party Assurance", "2"),
    ]

    # HITRUST → NIST 800-53 crosswalk data
    HITRUST_XWALKS = {
        "00.a": ["pm-1", "pm-9", "pl-2"],
        "00.b": ["ra-1", "ra-3", "pm-28"],
        "00.c": ["pm-2", "pm-19", "ps-2"],
        "01.a": ["ac-1"],
        "01.b": ["ac-2"],
        "01.c": ["ac-2"],
        "01.d": ["ac-6"],
        "01.e": ["ac-2"],
        "01.f": ["ac-2", "ps-4"],
        "01.g": ["ia-5"],
        "01.h": ["ac-17", "sc-7"],
        "01.i": ["ia-2", "ia-3"],
        "01.j": ["sc-7", "sc-7.5"],
        "02.a": ["au-2", "au-3"],
        "02.b": ["au-6"],
        "02.c": ["au-9"],
        "02.d": ["au-6"],
        "02.e": ["au-5"],
        "02.f": ["au-8"],
        "03.a": ["at-2"],
        "03.b": ["at-3", "at-4"],
        "03.c": ["ps-3"],
        "04.a": ["ir-6"],
        "04.b": ["ir-6"],
        "04.c": ["ir-4", "ir-5"],
        "04.d": ["ir-4"],
        "04.e": ["ir-4"],
        "04.f": ["ir-4", "au-7"],
        "05.a": ["pl-1", "pm-1"],
        "05.b": ["pl-1"],
        "06.a": ["cm-1"],
        "06.b": ["cm-3"],
        "06.c": ["cp-2", "pe-12"],
        "06.d": ["cm-2", "sa-3"],
        "06.e": ["si-3"],
        "06.f": ["cp-9"],
        "06.g": ["au-2"],
        "06.h": ["ra-5", "si-2"],
        "06.i": ["cm-11"],
        "07.a": ["ra-1", "ra-3"],
        "07.b": ["ra-3", "ra-7"],
        "08.a": ["sa-1", "sa-4"],
        "08.b": ["sa-8"],
        "08.c": ["cm-6", "cm-7"],
        "08.d": ["cm-3"],
        "08.e": ["sa-12"],
        "09.a": ["ac-19"],
        "09.b": ["ac-17"],
        "10.a": ["sc-7"],
        "10.b": ["sc-7", "sa-9"],
        "10.c": ["sc-7"],
        "10.d": ["sc-8"],
        "10.e": ["ca-3", "sc-7"],
        "11.a": ["pe-1", "pe-3"],
        "11.b": ["pe-2", "pe-3"],
        "11.c": ["pe-5"],
        "11.d": ["pe-1", "pe-14"],
        "12.a": ["ra-2"],
        "12.b": ["mp-3"],
        "12.c": ["mp-2"],
        "12.d": ["mp-5"],
        "12.e": ["pt-1", "pm-18"],
        "12.f": ["sc-13"],
        "13.a": ["sa-9", "ca-3"],
        "13.b": ["sa-9"],
        "13.c": ["ca-7", "sa-9"],
        "13.d": ["sa-9"],
    }

    # Insert HITRUST controls
    hitrust_inserted_controls = 0
    hitrust_fc_map = {}  # control_id → fc_id

    # Check existing controls
    cur.execute("SELECT id, control_id FROM framework_controls WHERE framework_id=?", (HITRUST_FW_ID,))
    existing_controls = {r[1]: r[0] for r in cur.fetchall()}

    for (ctrl_id, title, desc, domain, level) in HITRUST_CONTROLS:
        if ctrl_id in existing_controls:
            hitrust_fc_map[ctrl_id] = existing_controls[ctrl_id]
            continue
        cur.execute("""
            INSERT INTO framework_controls
              (framework_id, control_id, title, description, domain, level, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (HITRUST_FW_ID, ctrl_id, title, desc, domain, level, NOW))
        fc_id = cur.lastrowid
        hitrust_fc_map[ctrl_id] = fc_id
        hitrust_inserted_controls += 1

    # Insert HITRUST crosswalks
    hitrust_xwalk_inserted = 0
    for ctrl_id, nist_ids in HITRUST_XWALKS.items():
        fc_id = hitrust_fc_map.get(ctrl_id)
        if not fc_id:
            continue
        for nist_id in nist_ids:
            cur.execute("""
                INSERT OR IGNORE INTO control_crosswalks
                  (framework_control_id, nist_control_id, mapping_type, confidence, source, notes, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (fc_id, nist_id, 'direct', 'high', 'hitrust_csf_v11', None, NOW))
            hitrust_xwalk_inserted += cur.rowcount

    print(f"    ✓ HITRUST CSF: {hitrust_inserted_controls} controls, {hitrust_xwalk_inserted} crosswalks inserted")

    # ── 6. nist_ics controls (SP 800-82 ICS/SCADA overlay) ──────────────────
    print("[6] Adding nist_ics controls …")

    NIST_ICS_FW_ID = "b892565ecc8c9480cef16950ccc62c07"

    NIST_ICS_CONTROLS = [
        # Access Control — ICS enhancements
        ("ICS-AC-1",  "ICS Access Control Policy",
         "Implement access control policies and procedures tailored for ICS environments, including physical and logical access to control systems.",
         "Access Control", "1"),
        ("ICS-AC-2",  "ICS Account Management",
         "Manage accounts for ICS components including PLCs, HMIs, historians, and engineering workstations. Limit shared accounts.",
         "Access Control", "1"),
        ("ICS-AC-3",  "ICS Access Enforcement",
         "Enforce approved authorizations for logical and physical access to ICS assets, using allowlists of authorized connections.",
         "Access Control", "1"),
        ("ICS-AC-17", "ICS Remote Access",
         "Implement controls for remote access to ICS environments; prefer jump servers with MFA. Document all remote access paths.",
         "Access Control", "2"),

        # Configuration Management — ICS
        ("ICS-CM-1",  "ICS Configuration Management Policy",
         "Establish ICS-specific configuration management policies that account for operational constraints and change windows.",
         "Configuration Management", "1"),
        ("ICS-CM-2",  "ICS Baseline Configurations",
         "Develop and document baseline configurations for ICS components; maintain hardware/software inventory by zone.",
         "Configuration Management", "1"),
        ("ICS-CM-6",  "ICS Configuration Settings",
         "Establish and document configuration settings for ICS devices; disable unnecessary services, ports, and protocols.",
         "Configuration Management", "1"),
        ("ICS-CM-7",  "Least Functionality for ICS",
         "Configure ICS systems to provide only essential capabilities; disable unused protocols (e.g., unused SCADA protocols).",
         "Configuration Management", "1"),
        ("ICS-CM-10", "Software Usage Restrictions for ICS",
         "Establish restrictions on software use in ICS environments; restrict unauthorized or unlicensed software.",
         "Configuration Management", "2"),

        # Incident Response — ICS
        ("ICS-IR-1",  "ICS Incident Response Policy",
         "Develop ICS-specific incident response procedures that address operational continuity during cyber incidents.",
         "Incident Response", "1"),
        ("ICS-IR-4",  "ICS Incident Handling",
         "Implement incident handling capabilities for ICS; coordinate with process safety team for cyber-physical incidents.",
         "Incident Response", "1"),
        ("ICS-IR-6",  "ICS Incident Reporting",
         "Report ICS security incidents to ICS-CERT and relevant regulatory authorities (NERC, NRC, TSA as applicable).",
         "Incident Response", "2"),

        # Maintenance — ICS
        ("ICS-MA-1",  "ICS Maintenance Policy",
         "Establish maintenance policies for ICS components; require controlled maintenance windows with safety isolation procedures.",
         "Maintenance", "1"),
        ("ICS-MA-3",  "ICS Maintenance Tools",
         "Approve, control, and monitor tools used for ICS maintenance; scan tools for malware before use.",
         "Maintenance", "2"),
        ("ICS-MA-4",  "ICS Nonlocal Maintenance",
         "Authorize, monitor, and control nonlocal maintenance of ICS; terminate remote sessions when maintenance is complete.",
         "Maintenance", "1"),

        # Media Protection — ICS
        ("ICS-MP-1",  "ICS Media Protection Policy",
         "Establish policies for managing removable media in ICS environments; limit and control USB/removable media use.",
         "Media Protection", "1"),
        ("ICS-MP-6",  "ICS Media Sanitization",
         "Sanitize ICS media prior to disposal or reuse to prevent unauthorized disclosure of data.",
         "Media Protection", "1"),

        # Physical and Environmental Protection — ICS
        ("ICS-PE-1",  "ICS Physical Access Policy",
         "Implement physical security controls for ICS facilities including control rooms, substations, and remote RTUs.",
         "Physical & Environmental Protection", "1"),
        ("ICS-PE-3",  "ICS Physical Access Control",
         "Enforce physical access authorizations at all ICS access points including control room, field sites, and data historian rooms.",
         "Physical & Environmental Protection", "1"),
        ("ICS-PE-10", "ICS Emergency Shutoff",
         "Provide the capability to shut off power to ICS components in emergency situations without injury to personnel.",
         "Physical & Environmental Protection", "1"),

        # Risk Assessment — ICS
        ("ICS-RA-1",  "ICS Risk Assessment Policy",
         "Develop risk assessment policies tailored for ICS; incorporate both cyber and process safety risk perspectives.",
         "Risk Assessment", "1"),
        ("ICS-RA-3",  "ICS Risk Assessment",
         "Conduct ICS risk assessments that include cyber-physical risk scenarios; update assessments when significant changes occur.",
         "Risk Assessment", "1"),
        ("ICS-RA-5",  "ICS Vulnerability Scanning",
         "Perform vulnerability scanning in ICS environments with care to avoid disrupting operations; use passive scanning techniques.",
         "Risk Assessment", "2"),

        # System and Communications Protection — ICS
        ("ICS-SC-1",  "ICS Network Architecture",
         "Implement network segmentation between corporate IT and OT/ICS networks using demilitarized zones (DMZ).",
         "System & Communications Protection", "1"),
        ("ICS-SC-7",  "ICS Boundary Protection",
         "Monitor and control communications at external boundaries and key internal boundaries of ICS networks.",
         "System & Communications Protection", "1"),
        ("ICS-SC-10", "ICS Network Disconnect",
         "Terminate ICS network connections after a defined period of inactivity or when no longer needed.",
         "System & Communications Protection", "2"),

        # System and Information Integrity — ICS
        ("ICS-SI-1",  "ICS System Integrity Policy",
         "Implement integrity monitoring for ICS firmware, software, and configurations; alert on unauthorized changes.",
         "System & Information Integrity", "1"),
        ("ICS-SI-2",  "ICS Flaw Remediation",
         "Identify, report, and correct flaws in ICS software and firmware; coordinate patching with operational schedules.",
         "System & Information Integrity", "1"),
        ("ICS-SI-3",  "ICS Malware Protection",
         "Implement malware protection in ICS environments; prefer application whitelisting where antivirus is impractical.",
         "System & Information Integrity", "1"),
        ("ICS-SI-4",  "ICS Monitoring",
         "Monitor ICS for anomalous behavior and unauthorized connections; use protocol-aware ICS security monitoring tools.",
         "System & Information Integrity", "2"),

        # Contingency Planning — ICS
        ("ICS-CP-1",  "ICS Contingency Planning Policy",
         "Develop contingency plans for ICS that address both cyber incidents and process safety impacts.",
         "Contingency Planning", "1"),
        ("ICS-CP-2",  "ICS Contingency Plan",
         "Develop and implement an ICS contingency plan; integrate with overall BCP and emergency response procedures.",
         "Contingency Planning", "1"),
        ("ICS-CP-10", "ICS System Recovery and Reconstitution",
         "Provide for recovery and reconstitution of ICS after a disruption; maintain offline backups of configurations.",
         "Contingency Planning", "2"),
    ]

    # nist_ics → NIST 800-53 crosswalks (these map to the parent NIST controls)
    NIST_ICS_XWALKS = {
        "ICS-AC-1":  ["ac-1"],
        "ICS-AC-2":  ["ac-2"],
        "ICS-AC-3":  ["ac-3"],
        "ICS-AC-17": ["ac-17"],
        "ICS-CM-1":  ["cm-1"],
        "ICS-CM-2":  ["cm-2"],
        "ICS-CM-6":  ["cm-6"],
        "ICS-CM-7":  ["cm-7"],
        "ICS-CM-10": ["cm-10"],
        "ICS-IR-1":  ["ir-1"],
        "ICS-IR-4":  ["ir-4"],
        "ICS-IR-6":  ["ir-6"],
        "ICS-MA-1":  ["ma-1"],
        "ICS-MA-3":  ["ma-3"],
        "ICS-MA-4":  ["ma-4"],
        "ICS-MP-1":  ["mp-1"],
        "ICS-MP-6":  ["mp-6"],
        "ICS-PE-1":  ["pe-1"],
        "ICS-PE-3":  ["pe-3"],
        "ICS-PE-10": ["pe-10"],
        "ICS-RA-1":  ["ra-1"],
        "ICS-RA-3":  ["ra-3"],
        "ICS-RA-5":  ["ra-5"],
        "ICS-SC-1":  ["sc-7"],
        "ICS-SC-7":  ["sc-7"],
        "ICS-SC-10": ["sc-10"],
        "ICS-SI-1":  ["si-7"],
        "ICS-SI-2":  ["si-2"],
        "ICS-SI-3":  ["si-3"],
        "ICS-SI-4":  ["si-4"],
        "ICS-CP-1":  ["cp-1"],
        "ICS-CP-2":  ["cp-2"],
        "ICS-CP-10": ["cp-10"],
    }

    # Check existing ics controls
    cur.execute("SELECT control_id FROM framework_controls WHERE framework_id=?", (NIST_ICS_FW_ID,))
    existing_ics = {r[0] for r in cur.fetchall()}

    ics_ctrl_inserted = 0
    ics_xwalk_inserted = 0
    for (ctrl_id, title, desc, domain, level) in NIST_ICS_CONTROLS:
        if ctrl_id in existing_ics:
            continue
        cur.execute("""
            INSERT INTO framework_controls
              (framework_id, control_id, title, description, domain, level, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (NIST_ICS_FW_ID, ctrl_id, title, desc, domain, level, NOW))
        fc_id = cur.lastrowid
        ics_ctrl_inserted += 1
        for nist_id in NIST_ICS_XWALKS.get(ctrl_id, []):
            cur.execute("""
                INSERT OR IGNORE INTO control_crosswalks
                  (framework_control_id, nist_control_id, mapping_type, confidence, source, notes, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (fc_id, nist_id, 'direct', 'high', 'nist_sp800_82r3', None, NOW))
            ics_xwalk_inserted += cur.rowcount

    print(f"    ✓ nist_ics: {ics_ctrl_inserted} controls, {ics_xwalk_inserted} crosswalks inserted")

    # ── 7. dod_srg controls (DoD Cloud SRG overlay) ──────────────────────────
    print("[7] Adding dod_srg controls …")

    DOD_SRG_FW_ID = "7778289b241d66446f3f662a514ff817"

    DOD_SRG_CONTROLS = [
        # Cloud Security Requirements Guide — Impact Levels
        # CCI-based requirements mapped to SRG ID
        ("SRG-OS-000001", "Account Management — Authorized Users",
         "The operating system must automatically audit account creation, modification, enabling, disabling, and removal actions.",
         "Access Control", "IL2"),
        ("SRG-OS-000002", "Privileged Account Management",
         "The organization must restrict privileged access to authorized individuals with documented need.",
         "Access Control", "IL2"),
        ("SRG-OS-000021", "Session Lock After Inactivity",
         "The information system must initiate a session lock after 15 minutes of inactivity for DoD systems.",
         "Access Control", "IL2"),
        ("SRG-OS-000023", "Login Warning Banner",
         "Display the Standard Mandatory DoD Notice and Consent Banner before granting access.",
         "Access Control", "IL2"),
        ("SRG-OS-000057", "Audit Log Capability",
         "The operating system must produce audit records containing information to establish what events occurred.",
         "Audit & Accountability", "IL2"),
        ("SRG-OS-000058", "Audit Log Protection",
         "The operating system must protect audit log files from unauthorized read, modification, and deletion.",
         "Audit & Accountability", "IL2"),
        ("SRG-OS-000059", "Audit Log Retention",
         "Retain audit records for at least one year with at least 90 days online.",
         "Audit & Accountability", "IL2"),
        ("SRG-OS-000078", "Password Minimum Length",
         "The operating system must enforce a minimum 15-character password length for DoD accounts.",
         "Identification & Authentication", "IL2"),
        ("SRG-OS-000080", "Password Complexity",
         "Enforce password complexity requirements including mixed case, numbers, and special characters.",
         "Identification & Authentication", "IL2"),
        ("SRG-OS-000104", "Unique Identification",
         "Uniquely identify and authenticate organizational users and processes.",
         "Identification & Authentication", "IL2"),
        ("SRG-OS-000105", "Multi-Factor Authentication",
         "Implement MFA for privileged and non-privileged accounts accessing DoD IL4/IL5 environments.",
         "Identification & Authentication", "IL4"),
        ("SRG-OS-000109", "Identifier Management",
         "Manage user identifiers by prohibiting reuse of identifiers for a defined period.",
         "Identification & Authentication", "IL2"),
        ("SRG-OS-000185", "Encryption of Data at Rest",
         "Implement FIPS 140-2/140-3 validated cryptography to protect data at rest in DoD cloud environments.",
         "System & Communications Protection", "IL2"),
        ("SRG-OS-000250", "Encryption in Transit",
         "Implement FIPS 140-2/140-3 validated cryptographic mechanisms to protect data in transit.",
         "System & Communications Protection", "IL2"),
        ("SRG-OS-000278", "Software Integrity",
         "Verify the integrity of software, firmware, and information using cryptographic mechanisms.",
         "System & Information Integrity", "IL2"),
        ("SRG-OS-000312", "Access Enforcement",
         "Enforce approved authorizations for logical access to DoD information and system resources.",
         "Access Control", "IL2"),
        ("SRG-OS-000324", "Least Privilege",
         "Employ the principle of least privilege for implementation of the information system.",
         "Access Control", "IL2"),
        ("SRG-OS-000329", "Unsuccessful Logon Attempts",
         "Enforce a limit of not more than 3 consecutive invalid logon attempts within a 15-minute period.",
         "Access Control", "IL2"),
        ("SRG-OS-000368", "Software Restrictions",
         "Prevent execution of unauthorized software; implement application whitelisting for DoD workloads.",
         "Configuration Management", "IL4"),
        ("SRG-OS-000373", "Controlled Use of Maintenance Tools",
         "Control and monitor the use of maintenance diagnostic tools authorized for DoD environments.",
         "Maintenance", "IL2"),
        ("SRG-OS-000375", "Remote Maintenance Authentication",
         "Require MFA for all remote maintenance sessions on DoD systems.",
         "Maintenance", "IL4"),
        ("SRG-OS-000393", "Flaw Remediation",
         "Identify and correct flaws; install security patches within DoD-mandated timeframes (critical: 21 days).",
         "System & Information Integrity", "IL2"),
        ("SRG-OS-000394", "Malware Protection",
         "Implement malicious code protection mechanisms for DoD information systems.",
         "System & Information Integrity", "IL2"),
        ("SRG-OS-000420", "Network Boundary Protection",
         "Monitor and control communications at external boundaries and key internal boundaries of DoD cloud networks.",
         "System & Communications Protection", "IL2"),
        ("SRG-OS-000423", "Cryptographic Key Management",
         "Produce, control, and distribute asymmetric and symmetric cryptographic keys using DoD PKI-approved processes.",
         "System & Communications Protection", "IL4"),
        ("SRG-OS-000445", "System Monitoring",
         "Monitor the information system to detect attacks and indicators of potential attacks.",
         "System & Information Integrity", "IL2"),
        ("SRG-OS-000446", "Intrusion Detection Tools",
         "Employ automated monitoring tools to support near real-time analysis of events in DoD cloud.",
         "System & Information Integrity", "IL4"),
        ("SRG-OS-000480", "Configuration Baseline",
         "Configure systems in accordance with DoD STIG/SRG baselines and document deviations.",
         "Configuration Management", "IL2"),
        ("SRG-OS-000481", "Configuration Change Control",
         "Document and control changes to DoD cloud system configurations; implement change control processes.",
         "Configuration Management", "IL2"),
        ("SRG-IL5-001",   "IL5 CUI Data Handling",
         "Apply DoD IL5 controls for Controlled Unclassified Information (CUI) requiring higher protection than IL4.",
         "Data Protection", "IL5"),
        ("SRG-IL5-002",   "IL5 Personnel Security",
         "Ensure personnel accessing IL5 systems hold appropriate clearances or access approvals per DoD requirements.",
         "Personnel Security", "IL5"),
        ("SRG-IL5-003",   "IL5 Incident Reporting",
         "Report security incidents involving IL5 systems to US-CERT and DoD DCSA within 1 hour of detection.",
         "Incident Response", "IL5"),
    ]

    DOD_SRG_XWALKS = {
        "SRG-OS-000001": ["ac-2"],
        "SRG-OS-000002": ["ac-6"],
        "SRG-OS-000021": ["ac-11"],
        "SRG-OS-000023": ["ac-8"],
        "SRG-OS-000057": ["au-2", "au-3"],
        "SRG-OS-000058": ["au-9"],
        "SRG-OS-000059": ["au-11"],
        "SRG-OS-000078": ["ia-5"],
        "SRG-OS-000080": ["ia-5"],
        "SRG-OS-000104": ["ia-2"],
        "SRG-OS-000105": ["ia-2", "ia-12"],
        "SRG-OS-000109": ["ia-4"],
        "SRG-OS-000185": ["sc-28"],
        "SRG-OS-000250": ["sc-8"],
        "SRG-OS-000278": ["si-7"],
        "SRG-OS-000312": ["ac-3"],
        "SRG-OS-000324": ["ac-6"],
        "SRG-OS-000329": ["ac-7"],
        "SRG-OS-000368": ["cm-7"],
        "SRG-OS-000373": ["ma-3"],
        "SRG-OS-000375": ["ma-4"],
        "SRG-OS-000393": ["si-2"],
        "SRG-OS-000394": ["si-3"],
        "SRG-OS-000420": ["sc-7"],
        "SRG-OS-000423": ["sc-12"],
        "SRG-OS-000445": ["si-4"],
        "SRG-OS-000446": ["si-4"],
        "SRG-OS-000480": ["cm-2", "cm-6"],
        "SRG-OS-000481": ["cm-3"],
        "SRG-IL5-001":   ["mp-2", "ac-3"],
        "SRG-IL5-002":   ["ps-3"],
        "SRG-IL5-003":   ["ir-6"],
    }

    cur.execute("SELECT control_id FROM framework_controls WHERE framework_id=?", (DOD_SRG_FW_ID,))
    existing_srg = {r[0] for r in cur.fetchall()}

    srg_ctrl_inserted = 0
    srg_xwalk_inserted = 0
    for (ctrl_id, title, desc, domain, level) in DOD_SRG_CONTROLS:
        if ctrl_id in existing_srg:
            continue
        cur.execute("""
            INSERT INTO framework_controls
              (framework_id, control_id, title, description, domain, level, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (DOD_SRG_FW_ID, ctrl_id, title, desc, domain, level, NOW))
        fc_id = cur.lastrowid
        srg_ctrl_inserted += 1
        for nist_id in DOD_SRG_XWALKS.get(ctrl_id, []):
            cur.execute("""
                INSERT OR IGNORE INTO control_crosswalks
                  (framework_control_id, nist_control_id, mapping_type, confidence, source, notes, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (fc_id, nist_id, 'direct', 'high', 'dod_cloud_srg_v1r5', None, NOW))
            srg_xwalk_inserted += cur.rowcount

    print(f"    ✓ dod_srg: {srg_ctrl_inserted} controls, {srg_xwalk_inserted} crosswalks inserted")

    conn.commit()
    print("\n=== Migration complete ===")

    # Summary
    cur.execute("""
        SELECT f.short_name, COUNT(DISTINCT fc.id) as ctrl_cnt, COUNT(DISTINCT cw.id) as xwalk_cnt
        FROM compliance_frameworks f
        LEFT JOIN framework_controls fc ON fc.framework_id = f.id
        LEFT JOIN control_crosswalks cw ON cw.framework_control_id = fc.id
        WHERE f.short_name IN ('iso27001_annex_a','iso27001_core','iso27701','npf','hitrust','nist_ics','dod_srg')
        GROUP BY f.short_name
        ORDER BY f.short_name
    """)
    print("\nPost-migration summary:")
    print(f"{'Framework':<22} {'Controls':>10} {'Crosswalks':>12}")
    print("-" * 46)
    for r in cur.fetchall():
        print(f"{r[0]:<22} {r[1]:>10} {r[2]:>12}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    try:
        run(conn)
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()
