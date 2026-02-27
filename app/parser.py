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
