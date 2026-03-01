"""
BLACKSITE — SSP document parser.

Accepts .docx, .pdf, .txt, .xlsx, .csv files and extracts:
  - System name / description (best-effort)
  - Per-control sections: control ID, implementation status, responsible role, narrative text
  - N/A flag when a control is explicitly marked Not Applicable

Strategy:
  1. Extract all text from the document (preserving block order).
  2. Validate the document has meaningful content (abandon garbage files early).
  3. Scan for NIST control identifiers using flexible regex (handles typos/casing).
  4. Collect the text between each control ID and the next as its implementation block.
  5. Within each block, look for status/role keywords.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("blacksite.parser")

# Minimum useful text threshold — files below this are likely not SSPs
MIN_TEXT_CHARS = 200
# If fewer than this many control IDs are found, warn (not abandon)
MIN_CONTROLS_WARNING = 3

# ── Control ID pattern ─────────────────────────────────────────────────────────
# Primary: AC-1, AC-1(1), SA-22(1), PM-32, at-2, si-3(2), etc.
# Also catches: AC – 1, AC 1, AC_1 (common formatting variations)
CONTROL_RE = re.compile(
    r'\b([A-Z]{1,3})[\s\-–_]{0,2}(\d{1,2})(?:\s*[\(\[]\s*(\d{1,2})\s*[\)\]])?\b',
    re.IGNORECASE
)

# ── Implementation status keywords (order matters — most specific first) ────────
STATUS_PATTERNS = [
    (re.compile(r'\bnot\s+applicable\b', re.I),                "Not Applicable"),
    (re.compile(r'\bn\s*/\s*a\b', re.I),                       "Not Applicable"),
    (re.compile(r'\bnot\s+implemented\b', re.I),               "Not Implemented"),
    (re.compile(r'\bpartially\s+implemented\b', re.I),         "Partially Implemented"),
    (re.compile(r'\bpartial(ly)?\b', re.I),                    "Partially Implemented"),
    (re.compile(r'\balternative\s+implementation\b', re.I),    "Alternative Implementation"),
    (re.compile(r'\bplanned\b', re.I),                         "Planned"),
    (re.compile(r'\bfully\s+implemented\b', re.I),             "Implemented"),
    (re.compile(r'\bimplemented\b', re.I),                     "Implemented"),
    (re.compile(r'\bin\s+place\b', re.I),                      "Implemented"),
]

# ── Responsible role keywords ───────────────────────────────────────────────────
ROLE_RE = re.compile(
    r'(?:responsible\s+(?:party|role|entity|owner)|role|owner|poc)[:\s]+([^\n.;]{3,80})',
    re.I
)


# ── Text extraction ────────────────────────────────────────────────────────────

def _extract_docx(path: Path) -> str:
    """Extract text from a .docx file, including table cells."""
    try:
        from docx import Document  # python-docx
        doc = Document(str(path))
        blocks = []
        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
            if tag == "p":
                text = "".join(n.text or "" for n in element.iter() if hasattr(n, "text"))
                if text.strip():
                    blocks.append(text.strip())
            elif tag == "tbl":
                # Extract table cells in row order
                for row in element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr"):
                    cells = []
                    for cell in row.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc"):
                        cell_text = "".join(
                            n.text or "" for n in cell.iter() if hasattr(n, "text")
                        ).strip()
                        if cell_text:
                            cells.append(cell_text)
                    if cells:
                        blocks.append(" | ".join(cells))
        return "\n".join(blocks)
    except Exception as e:
        log.error("docx extraction failed: %s", e)
        return ""


def _extract_pdf(path: Path) -> str:
    """Extract text from a PDF using pdfplumber."""
    try:
        import pdfplumber
        texts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=3, y_tolerance=3)
                if t:
                    texts.append(t)
        return "\n".join(texts)
    except Exception as e:
        log.error("PDF extraction failed: %s", e)
        return ""


def _extract_txt(path: Path) -> str:
    for enc in ("utf-8", "latin-1", "cp1252", "utf-16"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def _extract_xlsx(path: Path) -> str:
    """Extract text from .xlsx (flat SSP spreadsheets)."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        rows = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
                if cells:
                    rows.append(" | ".join(cells))
        return "\n".join(rows)
    except ImportError:
        log.warning("openpyxl not installed — cannot parse .xlsx files. Install with: pip install openpyxl")
        return ""
    except Exception as e:
        log.error("xlsx extraction failed: %s", e)
        return ""


def _extract_csv(path: Path) -> str:
    """Extract text from .csv (tabular SSP exports)."""
    import csv
    rows = []
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, newline="", encoding=enc) as f:
                reader = csv.reader(f)
                for row in reader:
                    cells = [c.strip() for c in row if c.strip()]
                    if cells:
                        rows.append(" | ".join(cells))
            break
        except UnicodeDecodeError:
            continue
    return "\n".join(rows)


def extract_text(path: Path) -> str:
    """Dispatch to the correct extractor based on file suffix."""
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _extract_docx(path)
    elif suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".txt", ".md", ".rst"):
        return _extract_txt(path)
    elif suffix in (".xlsx", ".xls"):
        return _extract_xlsx(path)
    elif suffix == ".csv":
        return _extract_csv(path)
    else:
        log.warning("Unknown file type %s — attempting plain text extraction.", suffix)
        return _extract_txt(path)


# ── Control block extraction ────────────────────────────────────────────────────

def _normalise_control_id(family: str, num: str, enh: Optional[str] = None) -> str:
    """Normalise matched groups → 'ac-1' or 'ac-1(1)'."""
    cid = f"{family.lower()}-{num}"
    if enh:
        cid += f"({enh})"
    return cid


def _normalise_raw(raw: str) -> str:
    """Fallback normaliser for a raw matched string."""
    return re.sub(r'[\s\-–_]+', '-', raw.lower()).replace(' ', '')


def extract_system_name(text: str) -> str:
    """Best-effort extraction of system name from SSP text."""
    for pattern in [
        re.compile(r'system\s+name[:\s]+([^\n]{3,80})', re.I),
        re.compile(r'information\s+system\s+name[:\s]+([^\n]{3,80})', re.I),
        re.compile(r'system\s+title[:\s]+([^\n]{3,80})', re.I),
    ]:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return "Unknown System"


def extract_impact_level(text: str) -> str:
    """Extract FIPS 199 impact level."""
    m = re.search(r'impact\s+level[:\s]+(low|moderate|high)', text, re.I)
    if m:
        return m.group(1).capitalize()
    return "Unknown"


def _detect_status(block: str) -> Optional[str]:
    for pattern, label in STATUS_PATTERNS:
        if pattern.search(block):
            return label
    return None


def _detect_role(block: str) -> Optional[str]:
    m = ROLE_RE.search(block)
    if m:
        return m.group(1).strip().rstrip(".,;")
    return None


def _is_noise_block(block: str) -> bool:
    """Return True if a block is likely structural noise (header/footer/TOC entry)."""
    stripped = block.strip()
    # Very short blocks with no alphabetic content
    if len(stripped) < 10:
        return True
    # Purely numeric or just a page number
    if re.match(r'^[\d\s\-\.]+$', stripped):
        return True
    # Likely a TOC entry (short text followed by dots and page number)
    if re.match(r'^.{0,60}[\.]{4,}\s*\d+$', stripped):
        return True
    return False


def parse_ssp(path: Path) -> dict:
    """
    Parse an SSP document and return a structured result dict.

    Raises ValueError for completely invalid/unreadable files.

    Returns:
    {
        "system_name": str,
        "impact_level": str,
        "raw_text_length": int,
        "controls": {
            "ac-1": {
                "id": "ac-1",
                "raw_id": "AC-1",
                "implementation_status": str | None,
                "is_na": bool,
                "responsible_role": str | None,
                "narrative": str,
            },
            ...
        }
    }
    """
    log.info("Parsing SSP: %s", path.name)
    text = extract_text(path)

    # ── Abandonment check ───────────────────────────────────────────────────
    meaningful = re.sub(r'\s+', ' ', text).strip()
    if len(meaningful) < MIN_TEXT_CHARS:
        raise ValueError(
            f"Document '{path.name}' yielded only {len(meaningful)} characters of text — "
            "likely corrupted, password-protected, or not an SSP. Abandoning."
        )

    # Check if the content looks like binary garbage
    printable_ratio = sum(1 for c in meaningful[:500] if c.isprintable()) / min(len(meaningful), 500)
    if printable_ratio < 0.70:
        raise ValueError(
            f"Document '{path.name}' contains mostly non-printable characters "
            "(ratio {printable_ratio:.0%}) — likely a binary or encrypted file. Abandoning."
        )

    system_name  = extract_system_name(text)
    impact_level = extract_impact_level(text)

    # ── Find all control IDs and their positions ────────────────────────────
    # Known NIST families to filter out false positives
    VALID_FAMILIES = {
        'ac','at','au','ca','cm','cp','ia','ir','ma','mp','pe','pl','pm',
        'ps','pt','ra','sa','sc','si','sr'
    }

    matches = list(CONTROL_RE.finditer(text))
    anchors = []
    seen: set = set()

    for m in matches:
        family = m.group(1).lower()
        num    = m.group(2)
        enh    = m.group(3)  # enhancement number or None

        # Filter to valid NIST families only
        if family not in VALID_FAMILIES:
            continue

        nid    = _normalise_control_id(family, num, enh)
        raw_id = f"{family.upper()}-{num}" + (f"({enh})" if enh else "")

        if nid not in seen:
            anchors.append((m.start(), nid, raw_id, m.end()))
            seen.add(nid)

    if not anchors:
        return {
            "system_name":     system_name,
            "impact_level":    impact_level,
            "raw_text_length": len(text),
            "controls":        {},
            "warning":         "No NIST control identifiers found in document.",
        }

    if len(anchors) < MIN_CONTROLS_WARNING:
        log.warning("Only %d control references found in '%s' — document may be incomplete.", len(anchors), path.name)

    # ── Extract text blocks between anchors ─────────────────────────────────
    controls: dict = {}
    for i, (pos, nid, raw_id, end_of_id) in enumerate(anchors):
        next_pos = anchors[i + 1][0] if i + 1 < len(anchors) else len(text)
        block    = text[pos:next_pos].strip()

        # Remove the control ID label from the start
        block_body = text[end_of_id:next_pos].lstrip(": -–\t\n").strip()

        # Skip noise blocks
        if _is_noise_block(block_body):
            continue

        status = _detect_status(block_body)
        role   = _detect_role(block_body)
        is_na  = status == "Not Applicable"

        # Trim role line from narrative to reduce noise
        narrative = block_body
        if role:
            narrative = re.sub(ROLE_RE.pattern, "", narrative, flags=re.I).strip()

        # Deduplicate: keep the richer entry if control appears multiple times
        if nid in controls:
            existing = controls[nid]
            if len(narrative) > len(existing.get("narrative", "")):
                controls[nid]["narrative"] = narrative
            if not existing.get("implementation_status") and status:
                controls[nid]["implementation_status"] = status
            if not existing.get("responsible_role") and role:
                controls[nid]["responsible_role"] = role
        else:
            controls[nid] = {
                "id":                    nid,
                "raw_id":                raw_id,
                "implementation_status": status,
                "is_na":                 is_na,
                "responsible_role":      role,
                "narrative":             narrative,
            }

    log.info("Parsed %d unique control references from '%s'.", len(controls), path.name)
    return {
        "system_name":     system_name,
        "impact_level":    impact_level,
        "raw_text_length": len(text),
        "controls":        controls,
    }


# ── SSP Analyzer — per-control scoring + remediation guidance ──────────────────

# Key narrative quality indicators (more → higher quality evidence)
_QUALITY_KEYWORDS = re.compile(
    r'\b(policy|procedure|documented|authorized|enforced|configured|automated|'
    r'reviewed|annually|quarterly|monthly|upon\s+\w+|access\s+control|'
    r'least\s+privilege|separation|audit\s+log|encrypt|authenticate|'
    r'multi[\-\s]?factor|backup|recover|patch|scan|monitor|alert|incident|'
    r'training|awareness|review|approval|documented|baseline|configuration|'
    r'continuous|real[\-\s]?time|siem|firewall|segmentation|zero[\-\s]?trust)\b',
    re.I
)

# Remediation guidance library keyed by NIST 800-53r5 control family
_REMEDIATION: dict[str, dict] = {
    "ac": {
        "name": "Access Control",
        "baseline_issues": [
            "Policy document is missing or not referenced (AC-1 requires both policy and procedures)",
            "Responsible role/owner not identified for enforcement",
            "No mention of least-privilege or need-to-know principles",
            "Account provisioning and de-provisioning process not described",
        ],
        "fix": (
            "AC controls require explicit policy statements naming the responsible organizational role, "
            "procedures for user account lifecycle (creation, review, disabling, removal), "
            "and enforcement mechanisms. State the technology used (e.g., Active Directory, IAM platform) "
            "and cite the frequency of access reviews. For AC-2 specifically, document the account types "
            "(standard, privileged, service) and how each is authorized and reviewed."
        ),
        "risk": "Unauthorized access, privilege escalation, insider threat",
    },
    "at": {
        "name": "Awareness and Training",
        "baseline_issues": [
            "Training frequency not stated (NIST requires 'upon hire and annually thereafter')",
            "Training content scope not described",
            "No mention of role-based training for privileged users",
            "Completion tracking/documentation process missing",
        ],
        "fix": (
            "Describe the training platform (e.g., KnowBe4, agency LMS), content modules covered, "
            "and frequency (upon hire + annual). Reference SP 800-50. "
            "For AT-3, explicitly state that privileged users receive role-specific training "
            "and document how completion records are maintained and reported to the ISSO."
        ),
        "risk": "Social engineering attacks, insider negligence, regulatory non-compliance",
    },
    "au": {
        "name": "Audit and Accountability",
        "baseline_issues": [
            "Audit log event types not enumerated",
            "Log retention period not specified",
            "No SIEM or centralized logging platform mentioned",
            "Audit log review frequency not stated",
            "Log protection (integrity, encryption at rest) not addressed",
        ],
        "fix": (
            "Enumerate specific event types captured (logon/logoff, privilege use, object access, "
            "policy changes, account changes). State retention period (typically 90 days online + 1 year). "
            "Name the SIEM or log aggregation tool used. For AU-6, describe the review schedule "
            "(automated alerting + weekly human review minimum). Address AU-9 by stating how logs are "
            "protected from modification (e.g., write-once storage, SIEM immutability)."
        ),
        "risk": "Inability to detect/investigate incidents, audit failure, regulatory penalties",
    },
    "ca": {
        "name": "Assessment, Authorization, and Monitoring",
        "baseline_issues": [
            "ATO status and authorization boundary not referenced",
            "Assessment plan (SAP) and results (SAR) not linked",
            "Continuous monitoring strategy not described",
            "POA&M management process not documented",
        ],
        "fix": (
            "Reference the current ATO authorization date, authorizing official (AO), and authorization "
            "boundary. Link to the Security Assessment Plan and most recent SAR findings. "
            "For CA-7 continuous monitoring, describe the frequency of control assessments, automated "
            "scanning tools, and the ConMon reporting cadence. Document the POA&M review process "
            "(responsible team, review frequency, escalation path)."
        ),
        "risk": "Operating beyond authorization boundary, undetected control failures",
    },
    "cm": {
        "name": "Configuration Management",
        "baseline_issues": [
            "Configuration baseline not referenced (STIG, CIS benchmark, or agency baseline)",
            "Change management process not described",
            "No mention of configuration scanning or drift detection",
            "Software installation restrictions not stated",
        ],
        "fix": (
            "Identify the configuration baseline used (e.g., DISA STIG, CIS Level 1/2, agency hardening guide) "
            "and the version. Describe the change control process: who approves changes, what testing is required, "
            "and how rollback is handled. For CM-6, state that unauthorized configuration changes are detected "
            "via automated scanning (tool name + frequency). For CM-7, list restricted/prohibited functions "
            "and how they are enforced (GPO, MDM, SELinux, etc.)."
        ),
        "risk": "System misconfiguration, unauthorized software, configuration drift leading to vulnerabilities",
    },
    "cp": {
        "name": "Contingency Planning",
        "baseline_issues": [
            "RTO (Recovery Time Objective) and RPO (Recovery Point Objective) not stated",
            "Backup frequency and media not specified",
            "CP test date and results not referenced",
            "Alternate processing site not identified",
        ],
        "fix": (
            "State the system's RTO and RPO as derived from the BIA. Describe backup procedures: "
            "what is backed up (data, OS, config), frequency, retention, and off-site/cloud storage location. "
            "Reference the date of the most recent contingency plan test and summarize results. "
            "For CP-7, identify the alternate processing site (or cloud region) and how failover is triggered. "
            "Reference the full Contingency Plan document."
        ),
        "risk": "Data loss, extended outages, inability to recover from disasters",
    },
    "ia": {
        "name": "Identification and Authentication",
        "baseline_issues": [
            "Authentication mechanism not specified (MFA, PIV, passwords)",
            "Password complexity/rotation requirements not stated",
            "Privileged account authentication not differentiated from standard",
            "Remote access authentication not addressed",
        ],
        "fix": (
            "State the authentication mechanism: PIV/CAC for federal users, MFA method for contractors "
            "(TOTP, FIDO2, push notification). For IA-5, document password policy (min length, complexity, "
            "rotation period, reuse restriction). Separate privileged account requirements (IA-2(1): "
            "MFA for all privileged access). For remote access, state VPN + MFA combination. "
            "Reference the identity provider (IdP) used."
        ),
        "risk": "Credential theft, unauthorized access, account compromise, MITM attacks",
    },
    "ir": {
        "name": "Incident Response",
        "baseline_issues": [
            "Incident categories/severity levels not defined",
            "Reporting timeline (1 hour, 8 hour, 72 hour) not specified",
            "CIRT/SOC team or escalation contacts not identified",
            "IR plan test date not referenced",
        ],
        "fix": (
            "Define incident categories (DoD INFOCON, US-CERT taxonomy, or agency framework) and "
            "associated response timelines. For IR-6, state the reporting chain: ISSO → ISSM → AO → US-CERT "
            "and cite specific timeframes (e.g., 1-hour initial report, 8-hour status, 72-hour summary). "
            "Identify the CIRT or SOC responsible for response. Reference the Incident Response Plan "
            "and the date of the most recent tabletop or functional exercise."
        ),
        "risk": "Uncontained breaches, regulatory reporting violations, extended recovery time",
    },
    "ma": {
        "name": "Maintenance",
        "baseline_issues": [
            "Maintenance authorization process not described",
            "Remote maintenance controls not addressed",
            "Maintenance personnel screening requirements not stated",
            "Sanitization of maintenance media not addressed",
        ],
        "fix": (
            "Describe how maintenance is authorized: work order system, approval chain, and logging requirements. "
            "For MA-4, state how remote maintenance sessions are established (jump host, session recording, "
            "MFA), monitored, and terminated. Document requirements for maintenance personnel background checks. "
            "For MA-6, state how diagnostic media is sanitized (or destroyed) after use."
        ),
        "risk": "Unauthorized system access via maintenance channels, hardware tampering",
    },
    "mp": {
        "name": "Media Protection",
        "baseline_issues": [
            "Media classification and handling procedures not described",
            "Portable media policy not stated (USB restriction, encryption requirement)",
            "Media sanitization method not specified (NIST 800-88 compliance)",
            "Digital media chain of custody not addressed",
        ],
        "fix": (
            "State the media handling policy: whether removable media is allowed, what encryption is required "
            "(FIPS 140-3 validated for CUI/classified). For MP-6, cite the sanitization standard used "
            "(NIST SP 800-88 Guidelines for Media Sanitization) and the method: Clear, Purge, or Destroy. "
            "Document media disposal procedures including certificate of destruction for classified media."
        ),
        "risk": "Data leakage via removable media, CUI exposure, regulatory fines",
    },
    "pe": {
        "name": "Physical and Environmental Protection",
        "baseline_issues": [
            "Physical access authorization process not described",
            "Visitor escort policy not stated",
            "Environmental controls (fire, flood, temperature) not addressed",
            "Physical access log review not mentioned",
        ],
        "fix": (
            "Describe facility access controls: badge readers, man-trap, biometric, or combination. "
            "State who approves access, how access lists are reviewed (PE-2: at least annually), "
            "and visitor escort requirements. For PE-13/14/15, cite fire suppression systems, "
            "HVAC/temperature monitoring, and water damage mitigation measures in place."
        ),
        "risk": "Unauthorized physical access, equipment theft, environmental damage",
    },
    "pl": {
        "name": "Planning",
        "baseline_issues": [
            "System Security Plan (SSP) version and approval date not stated",
            "Rules of Behavior not referenced",
            "Privacy Impact Assessment linkage not present",
            "Security concept of operations missing",
        ],
        "fix": (
            "Reference the SSP version, approval date, and authorizing official. For PL-4, confirm that "
            "all users have signed Rules of Behavior and state the frequency of re-acknowledgment. "
            "Link to the Privacy Impact Assessment (PIA) and System of Records Notice (SORN) if applicable."
        ),
        "risk": "Missing authorization documentation, user non-compliance, ATO delays",
    },
    "pm": {
        "name": "Program Management",
        "baseline_issues": [
            "ISCM strategy not referenced at the organizational level",
            "Enterprise risk management framework not cited",
            "Security workforce plan not mentioned",
        ],
        "fix": (
            "Reference the organization-wide Information Security Continuous Monitoring (ISCM) strategy. "
            "For PM-9, cite the enterprise risk management framework in use and how system-level risks "
            "roll up to organizational risk decisions. State the security POC and their authority level."
        ),
        "risk": "Disconnected security programs, unmanaged enterprise risk",
    },
    "ps": {
        "name": "Personnel Security",
        "baseline_issues": [
            "Position risk designation not stated",
            "Personnel screening type/frequency not specified",
            "Termination/transfer procedures not described",
            "Third-party personnel requirements not addressed",
        ],
        "fix": (
            "State the position sensitivity level (Public Trust, Secret, Top Secret) and corresponding "
            "background investigation type (NACI, MBI, BI, SSBI). For PS-4, describe termination procedures: "
            "account disable timeline (same-day for terminations), credential revocation, and access badge "
            "collection. For contractors and third parties (PS-7), state the flow-down requirements "
            "for background checks and how compliance is verified."
        ),
        "risk": "Insider threats from inadequately screened personnel, unrevoked access after departure",
    },
    "pt": {
        "name": "PII Processing and Transparency",
        "baseline_issues": [
            "PII categories processed not enumerated",
            "Legal authority for PII collection not cited",
            "PII minimization approach not described",
            "Individual rights (access, correction, redress) not addressed",
        ],
        "fix": (
            "Enumerate all PII categories processed (name, SSN, address, financial, health, etc.) and "
            "cite the legal authority (statute, Executive Order, or regulation) authorizing collection. "
            "For PT-3, describe data minimization practices. Reference the SORN and PIA. "
            "Document how individuals exercise their rights under the Privacy Act."
        ),
        "risk": "Privacy Act violations, FTC enforcement, reputational damage, civil liability",
    },
    "ra": {
        "name": "Risk Assessment",
        "baseline_issues": [
            "Risk assessment date and methodology not stated",
            "Vulnerability scanning tool and frequency not specified",
            "Risk acceptance/mitigation decision process not described",
            "Threat sources/threat events not identified",
        ],
        "fix": (
            "Reference the most recent risk assessment date and the methodology used (NIST SP 800-30, "
            "CVSS, DREAD). For RA-5, name the vulnerability scanning tool (Tenable, Qualys, OpenVAS), "
            "scan frequency (at minimum quarterly for authenticated scans), and the remediation SLAs "
            "(e.g., Critical within 15 days, High within 30 days). Document how scan findings feed into POA&M."
        ),
        "risk": "Unidentified vulnerabilities, delayed remediation, exploitable attack surface",
    },
    "sa": {
        "name": "System and Services Acquisition",
        "baseline_issues": [
            "Software development/acquisition security requirements not stated",
            "Third-party service provider security requirements not described",
            "SCRM (Supply Chain Risk Management) controls not addressed",
            "System development lifecycle (SDLC) security integration not mentioned",
        ],
        "fix": (
            "Describe how security requirements are incorporated into acquisition contracts (SA-4: "
            "include security functional requirements, assurance requirements, documentation requirements). "
            "For SA-9, list significant external services and state how security requirements are flowed down "
            "(contractual SLAs, ATO/FedRAMP compliance). For SA-11, describe SAST/DAST in the SDLC pipeline."
        ),
        "risk": "Insecure third-party components, supply chain compromise, unvalidated COTS software",
    },
    "sc": {
        "name": "System and Communications Protection",
        "baseline_issues": [
            "Network segmentation/DMZ architecture not described",
            "Encryption in transit not specified (TLS version, cipher suites)",
            "Encryption at rest not addressed",
            "Boundary protection mechanisms not listed",
        ],
        "fix": (
            "Describe the network architecture: DMZ, enclave boundaries, VLAN segmentation. "
            "For SC-8, state that all data in transit uses TLS 1.2 or higher with FIPS-approved cipher suites. "
            "For SC-28, state that all sensitive data at rest is encrypted (AES-256 or equivalent, "
            "FIPS 140-3 validated module). Name the firewall/WAF/IPS at the boundary (SC-7)."
        ),
        "risk": "Data interception, MitM attacks, lateral movement, unencrypted sensitive data",
    },
    "si": {
        "name": "System and Information Integrity",
        "baseline_issues": [
            "Malware protection tool and update frequency not specified",
            "Security alert/advisory monitoring process not described",
            "Software patch/update process and SLA not stated",
            "Spam and phishing protection not addressed",
        ],
        "fix": (
            "Name the antivirus/EDR solution and state update frequency (SI-3: updated within 24 hours "
            "of signature release). For SI-2, state the patch management process: scan frequency, "
            "severity-based SLAs (Critical ≤15 days, High ≤30 days), and the change control gate. "
            "For SI-4, describe IDS/IPS deployment and alert routing to the SOC/SIEM. "
            "For SI-8, describe email filtering (SPF, DKIM, DMARC, anti-phishing)."
        ),
        "risk": "Malware infection, unpatched vulnerabilities, phishing compromise, data corruption",
    },
    "sr": {
        "name": "Supply Chain Risk Management",
        "baseline_issues": [
            "SCRM policy and plan not referenced",
            "Critical suppliers not identified",
            "Component provenance/authenticity verification not described",
            "Incident response for supply chain compromise not addressed",
        ],
        "fix": (
            "Reference the organization's SCRM policy and plan (SP 800-161r1). For SR-6, describe how "
            "supplier assessments are conducted and documented. For SR-10, describe tamper-evident packaging "
            "and provenance verification for critical components. State how supply chain incidents would be "
            "reported and handled differently from standard cyber incidents."
        ),
        "risk": "Trojanized hardware/software, nation-state supply chain attacks, counterfeit components",
    },
}

# Gap severity thresholds based on composite quality score
_GRADE_THRESHOLDS = [
    (80, "ADEQUATE",      "Adequate",      "success"),
    (55, "MEDIUM_GAP",    "Medium Gap",    "warning"),
    (30, "HIGH_GAP",      "High Gap",      "danger"),
    (0,  "CRITICAL_GAP",  "Critical Gap",  "critical"),
]


def _score_control(ctrl: dict) -> tuple[int, str, str, str, list[str]]:
    """
    Score a single parsed control entry.

    Returns (score_0_100, grade, label, badge_class, issues_list)
    """
    narrative = ctrl.get("narrative", "") or ""
    status    = ctrl.get("implementation_status") or ""
    role      = ctrl.get("responsible_role") or ""
    is_na     = ctrl.get("is_na", False)

    if is_na:
        return 100, "NA", "Not Applicable", "muted", []

    issues = []
    score  = 0

    # 1. Narrative depth (0-40 points)
    nlen = len(narrative.strip())
    if nlen >= 600:
        score += 40
    elif nlen >= 300:
        score += 28
        issues.append("Narrative is brief — expand with specific mechanisms, tools, and enforcement details")
    elif nlen >= 100:
        score += 14
        issues.append("Narrative is thin — add implementation specifics, system components, and responsible parties")
    else:
        score += 0
        issues.append("Narrative is nearly absent — a meaningful implementation description is required")

    # 2. Quality keyword density (0-25 points)
    kw_hits = len(_QUALITY_KEYWORDS.findall(narrative))
    if kw_hits >= 6:
        score += 25
    elif kw_hits >= 3:
        score += 16
        issues.append("Lacks specificity — add technology names, frequencies, and enforcement mechanisms")
    elif kw_hits >= 1:
        score += 8
        issues.append("Vague language — replace generic statements with specific controls and tools")
    else:
        score += 0
        issues.append("No concrete implementation evidence found — cite specific tools, policies, and procedures")

    # 3. Responsible role identified (0-20 points)
    if role:
        score += 20
    else:
        issues.append("Responsible role/owner not identified — name the position responsible for this control")

    # 4. Implementation status declared (0-15 points)
    if status:
        if status in ("Implemented", "Fully Implemented"):
            score += 15
        elif status in ("Partially Implemented", "Alternative Implementation"):
            score += 9
            issues.append(f"Status is '{status}' — document compensating controls and planned remediation date")
        elif status in ("Planned",):
            score += 5
            issues.append("Status is 'Planned' — provide implementation timeline and interim risk acceptance")
        elif status in ("Not Implemented",):
            score += 0
            issues.append("Control is NOT IMPLEMENTED — a POA&M entry is required with scheduled completion date")
    else:
        issues.append("Implementation status not declared — explicitly state Implemented / Partially Implemented / Planned")

    for threshold, grade, label, badge in _GRADE_THRESHOLDS:
        if score >= threshold:
            return score, grade, label, badge, issues

    return score, "CRITICAL_GAP", "Critical Gap", "critical", issues


def analyze_ssp(path: Path) -> dict:
    """
    Full SSP quality analysis.

    Returns a rich dict with per-control findings and overall stats,
    suitable for storage as JSON and rendering in the review template.
    """
    parsed = parse_ssp(path)
    controls_raw = parsed.get("controls", {})

    findings = []
    counts   = {"ADEQUATE": 0, "MEDIUM_GAP": 0, "HIGH_GAP": 0, "CRITICAL_GAP": 0, "NA": 0, "NOT_FOUND": 0}
    total_score = 0
    scored = 0

    for ctrl_id, ctrl in controls_raw.items():
        family = ctrl_id.split("-")[0].lower() if "-" in ctrl_id else "??"
        score, grade, label, badge, issues = _score_control(ctrl)

        # Fetch family-level remediation
        fam_info  = _REMEDIATION.get(family, {})
        fam_name  = fam_info.get("name", family.upper())
        fix_text  = fam_info.get("fix", "Review NIST SP 800-53r5 guidance for this control family.")
        risk_text = fam_info.get("risk", "Unknown risk impact.")

        counts[grade] = counts.get(grade, 0) + 1
        if grade not in ("NA",):
            total_score += score
            scored += 1

        findings.append({
            "control_id":   ctrl_id.upper(),
            "family":       family.upper(),
            "family_name":  fam_name,
            "raw_id":       ctrl.get("raw_id", ctrl_id.upper()),
            "status":       ctrl.get("implementation_status") or "Not Declared",
            "role":         ctrl.get("responsible_role") or "",
            "narrative_len": len((ctrl.get("narrative") or "").strip()),
            "score":        score,
            "grade":        grade,
            "label":        label,
            "badge":        badge,
            "issues":       issues,
            "fix":          fix_text,
            "risk":         risk_text,
        })

    # Sort: critical first, then high, medium, adequate
    _order = {"CRITICAL_GAP": 0, "HIGH_GAP": 1, "MEDIUM_GAP": 2, "NOT_FOUND": 3, "ADEQUATE": 4, "NA": 5}
    findings.sort(key=lambda f: (_order.get(f["grade"], 9), f["control_id"]))

    overall = round(total_score / scored, 1) if scored else 0.0

    return {
        "system_name":   parsed.get("system_name", "Unknown System"),
        "impact_level":  parsed.get("impact_level", "Unknown"),
        "text_length":   parsed.get("raw_text_length", 0),
        "overall_score": overall,
        "counts":        counts,
        "total":         len(findings),
        "findings":      findings,
    }
