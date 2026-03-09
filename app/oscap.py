"""
BLACKSITE — Phase 35: OpenSCAP / SCAP Security Guide integration.

Provides:
  - list_datastreams()   → available .xml datastream files in SCAP_CONTENT_DIR
  - list_profiles()      → profiles in a datastream (via oscap info)
  - run_local_scan()     → scan localhost, return ARF XML path
  - run_remote_scan()    → scan remote host via oscap-ssh, return ARF XML path
  - parse_arf()          → parse ARF results into structured finding dicts
  - nist_refs_for_rule() → extract NIST 800-53 control references from rule element

Scan results are stored as ARF XML in SCAP_RESULTS_DIR and referenced by scan_id.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree as ET

log = logging.getLogger("blacksite.oscap")

SCAP_CONTENT_DIR = Path(os.environ.get("SCAP_CONTENT_DIR", "/opt/scap-content"))
SCAP_RESULTS_DIR = Path(os.environ.get("SCAP_RESULTS_DIR", "/home/graycat/projects/blacksite/scap-results"))

# XCCDF / ARF XML namespace map
_NS = {
    "arf":   "http://scap.nist.gov/schema/asset-reporting-format/1.1",
    "xccdf": "http://checklists.nist.gov/xccdf/1.2",
    "xccdf11": "http://checklists.nist.gov/xccdf/1.1",
    "oval":  "http://oval.mitre.org/XMLSchema/oval-results-5",
    "dc":    "http://purl.org/dc/elements/1.1/",
    "cpe":   "http://cpe.mitre.org/language/2.0",
}

# Severity map from XCCDF severity attribute to POA&M severity
_XCCDF_SEVERITY = {
    "high":   "High",
    "medium": "Moderate",
    "low":    "Low",
    "info":   "Informational",
    "unknown": "Informational",
}

# Known NIST 800-53 rev 5 reference hrefs in SSG content
_NIST_HREF_PATTERNS = [
    "800-53",
    "nist.gov",
    "csrc.nist",
]


def list_datastreams() -> list[dict]:
    """Return list of available SCAP datastream files with metadata."""
    if not SCAP_CONTENT_DIR.exists():
        return []
    result = []
    for p in sorted(SCAP_CONTENT_DIR.glob("ssg-*.xml")):
        name = p.stem  # e.g. ssg-ubuntu2004-ds
        # Derive a human label from filename
        m = re.match(r"ssg-([a-z]+)(\d+).*", name)
        if m:
            os_family = m.group(1).capitalize()
            os_version = m.group(2)
            # Insert a dot in version if numeric looks like "2004" → "20.04"
            if len(os_version) == 4:
                os_version = f"{os_version[:2]}.{os_version[2:]}"
            label = f"{os_family} {os_version}"
        else:
            label = name
        result.append({
            "path":  str(p),
            "name":  p.name,
            "label": label,
            "size":  p.stat().st_size,
        })
    return result


def list_profiles(datastream_path: str) -> list[dict]:
    """
    Run `oscap info` on a datastream and return available profiles.
    Returns list of {id, title} dicts.
    """
    try:
        out = subprocess.check_output(
            ["oscap", "info", "--fetch-remote-resources", datastream_path],
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).decode(errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        log.warning("oscap info failed for %s: %s", datastream_path, e)
        return []

    profiles = []
    current_title = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Title:"):
            current_title = line.split("Title:", 1)[1].strip()
        elif line.startswith("Id:") and current_title:
            profiles.append({"id": line.split("Id:", 1)[1].strip(), "title": current_title})
            current_title = None
    return profiles


def _ensure_results_dir() -> Path:
    SCAP_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCAP_RESULTS_DIR


async def run_local_scan(
    datastream_path: str,
    profile_id: str,
    scan_id: str,
) -> dict:
    """
    Run oscap xccdf eval on the local host.
    Returns dict with {arf_path, html_path, exit_code, error}.
    """
    results_dir = _ensure_results_dir()
    arf_path  = str(results_dir / f"{scan_id}-arf.xml")
    html_path = str(results_dir / f"{scan_id}-report.html")

    cmd = [
        "oscap", "xccdf", "eval",
        "--profile",       profile_id,
        "--results-arf",   arf_path,
        "--report",        html_path,
        "--fetch-remote-resources",
        datastream_path,
    ]
    log.info("Starting local SCAP scan %s: %s", scan_id, " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        exit_code = proc.returncode
        # oscap exits 2 when there are rule failures (not an error condition)
        error = stderr.decode(errors="replace") if exit_code not in (0, 2) else None
        log.info("SCAP scan %s finished, exit=%s", scan_id, exit_code)
        return {
            "arf_path":  arf_path  if Path(arf_path).exists()  else None,
            "html_path": html_path if Path(html_path).exists() else None,
            "exit_code": exit_code,
            "error":     error,
        }
    except asyncio.TimeoutError:
        return {"arf_path": None, "html_path": None, "exit_code": -1, "error": "Scan timed out (600s)"}
    except Exception as e:
        return {"arf_path": None, "html_path": None, "exit_code": -1, "error": str(e)}


async def run_remote_scan(
    target_host: str,
    ssh_port: int,
    ssh_user: str,
    datastream_path: str,
    profile_id: str,
    scan_id: str,
) -> dict:
    """
    Run oscap-ssh to scan a remote host.
    The datastream is transferred by oscap-ssh automatically.
    Returns dict with {arf_path, html_path, exit_code, error}.
    """
    results_dir = _ensure_results_dir()
    arf_path  = str(results_dir / f"{scan_id}-arf.xml")
    html_path = str(results_dir / f"{scan_id}-report.html")

    cmd = [
        "oscap-ssh",
        f"{ssh_user}@{target_host}", str(ssh_port),
        "xccdf", "eval",
        "--profile",       profile_id,
        "--results-arf",   arf_path,
        "--report",        html_path,
        "--fetch-remote-resources",
        datastream_path,
    ]
    log.info("Starting remote SCAP scan %s → %s:%s: %s", scan_id, target_host, ssh_port, " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=900)
        exit_code = proc.returncode
        error = stderr.decode(errors="replace") if exit_code not in (0, 2) else None
        log.info("Remote SCAP scan %s finished, exit=%s", scan_id, exit_code)
        return {
            "arf_path":  arf_path  if Path(arf_path).exists()  else None,
            "html_path": html_path if Path(html_path).exists() else None,
            "exit_code": exit_code,
            "error":     error,
        }
    except asyncio.TimeoutError:
        return {"arf_path": None, "html_path": None, "exit_code": -1, "error": "Scan timed out (900s)"}
    except Exception as e:
        return {"arf_path": None, "html_path": None, "exit_code": -1, "error": str(e)}


def _is_nist_ref(href: str) -> bool:
    return any(pat in href for pat in _NIST_HREF_PATTERNS)


def _extract_nist_controls(rule_el: ET.Element) -> list[str]:
    """
    Extract NIST 800-53 control references from an XCCDF rule element.
    Returns list of normalized control IDs like ["AC-2", "SI-3"].
    """
    controls = []
    for ns_prefix in ("xccdf", "xccdf11"):
        ns = _NS[ns_prefix]
        for ref in rule_el.findall(f"{{{ns}}}reference"):
            href = ref.get("href", "")
            if _is_nist_ref(href):
                text = (ref.text or "").strip()
                if text:
                    # Some refs have comma-separated or space-separated lists
                    for part in re.split(r"[,\s]+", text):
                        part = part.strip().upper()
                        if re.match(r"^[A-Z]{1,4}-\d+", part):
                            controls.append(part)
    return list(dict.fromkeys(controls))  # deduplicate preserving order


def _load_rule_defs_from_datastream(datastream_path: str) -> dict:
    """
    Parse the source SCAP datastream XML to extract rule metadata:
    title, description, fix text, severity, NIST control references.

    Returns dict keyed by rule_id.
    """
    rule_defs: dict[str, dict] = {}
    try:
        tree = ET.parse(datastream_path)
    except Exception as e:
        log.warning("Could not parse datastream %s for rule defs: %s", datastream_path, e)
        return rule_defs

    root = tree.getroot()
    for ns_prefix in ("xccdf", "xccdf11"):
        ns = _NS[ns_prefix]
        for rule_el in root.iter(f"{{{ns}}}Rule"):
            rule_id = rule_el.get("id", "")
            if not rule_id:
                continue
            title_el = rule_el.find(f"{{{ns}}}title")
            # description may have nested HTML — grab text + tail recursively
            desc_el  = rule_el.find(f"{{{ns}}}description")
            desc_text = "".join(desc_el.itertext()).strip()[:800] if desc_el is not None else ""
            fix_el   = rule_el.find(f"{{{ns}}}fixtext")
            fix_text = "".join(fix_el.itertext()).strip()[:800] if fix_el is not None else ""
            ident_el = rule_el.find(f"{{{ns}}}ident")
            severity = _XCCDF_SEVERITY.get(rule_el.get("severity", ""), "Informational")
            rule_defs[rule_id] = {
                "title":         (title_el.text or "").strip()[:300] if title_el is not None else rule_id,
                "description":   desc_text,
                "fix_text":      fix_text,
                "ident":         (ident_el.text or "").strip() if ident_el is not None else "",
                "severity":      severity,
                "nist_controls": _extract_nist_controls(rule_el),
            }
    log.debug("Loaded %d rule definitions from datastream %s", len(rule_defs), datastream_path)
    return rule_defs


def parse_arf(arf_path: str, datastream_path: str = "") -> dict:
    """
    Parse an ARF (Asset Reporting Format) XML file produced by oscap.

    Returns:
      {
        "scan_time":    ISO datetime string,
        "target_host":  hostname/FQDN from ARF,
        "profile_id":   profile XCCDF ID,
        "profile_title": human title,
        "summary": {"pass": N, "fail": N, "error": N, "notchecked": N, "informational": N},
        "findings": [
          {
            "rule_id":       str,
            "title":         str,
            "result":        "pass|fail|error|notchecked|informational|notapplicable",
            "severity":      "High|Moderate|Low|Informational",
            "nist_controls": ["AC-2", ...],
            "description":   str (first 800 chars),
            "fix_text":      str (first 800 chars),
            "ident":         str (CCE or CVE if present),
          },
          ...
        ]
      }
    """
    try:
        tree = ET.parse(arf_path)
    except Exception as e:
        log.error("Failed to parse ARF %s: %s", arf_path, e)
        return {"error": str(e), "findings": [], "summary": {}}

    root = tree.getroot()

    # Locate the XCCDF TestResult element (may be wrapped in ARF)
    test_result = None
    xccdf_ns = _NS["xccdf"]
    xccdf11_ns = _NS["xccdf11"]

    for ns in (xccdf_ns, xccdf11_ns):
        test_result = root.find(f".//{{{ns}}}TestResult")
        if test_result is not None:
            xccdf_ns_used = ns
            break
    if test_result is None:
        return {"error": "No TestResult found in ARF", "findings": [], "summary": {}}

    # Scan metadata
    scan_time = test_result.get("start-time") or test_result.get("end-time", "")
    target_el = test_result.find(f"{{{xccdf_ns_used}}}target")
    target_host = target_el.text.strip() if target_el is not None else "unknown"

    profile_el = test_result.find(f"{{{xccdf_ns_used}}}profile")
    profile_id = profile_el.get("idref", "") if profile_el is not None else ""

    # Build rule definition lookup: title, description, fix text, NIST refs.
    # ARF files do NOT embed the full Benchmark — load from the source datastream.
    rule_defs: dict[str, dict] = {}
    if datastream_path and Path(datastream_path).exists():
        rule_defs = _load_rule_defs_from_datastream(datastream_path)
    else:
        # Fallback: try to find an embedded Benchmark (rare, but some oscap versions include it)
        benchmark_el = root.find(f".//{{{xccdf_ns_used}}}Benchmark") or root.find(".//Benchmark")
        if benchmark_el is not None:
            for rule_el in benchmark_el.iter(f"{{{xccdf_ns_used}}}Rule"):
                rule_id = rule_el.get("id", "")
                title_el = rule_el.find(f"{{{xccdf_ns_used}}}title")
                desc_el  = rule_el.find(f"{{{xccdf_ns_used}}}description")
                fix_el   = rule_el.find(f"{{{xccdf_ns_used}}}fixtext")
                ident_el = rule_el.find(f"{{{xccdf_ns_used}}}ident")
                rule_defs[rule_id] = {
                    "title":         (title_el.text or "").strip()[:300] if title_el is not None else rule_id,
                    "description":   (desc_el.text  or "").strip()[:800] if desc_el  is not None else "",
                    "fix_text":      (fix_el.text   or "").strip()[:800] if fix_el   is not None else "",
                    "ident":         (ident_el.text  or "").strip()      if ident_el is not None else "",
                    "severity":      _XCCDF_SEVERITY.get(rule_el.get("severity", ""), "Informational"),
                    "nist_controls": _extract_nist_controls(rule_el),
                }

    # Collect RuleResult elements
    summary: dict[str, int] = {}
    findings = []

    for rr in test_result.findall(f"{{{xccdf_ns_used}}}rule-result"):
        rule_id = rr.get("idref", "")
        result_el = rr.find(f"{{{xccdf_ns_used}}}result")
        result_str = (result_el.text or "notchecked").strip().lower() if result_el is not None else "notchecked"

        summary[result_str] = summary.get(result_str, 0) + 1

        # Get rule definition metadata (title, severity, etc.)
        meta = rule_defs.get(rule_id, {})

        # Severity may also be on the rule-result element itself
        severity = _XCCDF_SEVERITY.get(rr.get("severity", ""), meta.get("severity", "Informational"))

        # Extract NIST refs from rule-result inline idents (if present)
        nist_controls = meta.get("nist_controls", [])

        # Short human-readable rule name from ID: strip the ssgproject prefix
        short_id = re.sub(r"^xccdf_org\.ssgproject\.content_rule_", "", rule_id)

        findings.append({
            "rule_id":       rule_id,
            "short_id":      short_id,
            "title":         meta.get("title", short_id.replace("_", " ").title()),
            "result":        result_str,
            "severity":      severity,
            "nist_controls": nist_controls,
            "description":   meta.get("description", ""),
            "fix_text":      meta.get("fix_text", ""),
            "ident":         meta.get("ident", ""),
        })

    # Sort: fail first, then error, pass, notapplicable, notchecked
    _result_order = {"fail": 0, "error": 1, "pass": 2, "informational": 3, "notapplicable": 4, "notchecked": 5}
    findings.sort(key=lambda f: (_result_order.get(f["result"], 9), f["short_id"]))

    return {
        "scan_time":     scan_time,
        "target_host":   target_host,
        "profile_id":    profile_id,
        "profile_title": "",  # filled in by caller if needed
        "summary":       summary,
        "findings":      findings,
    }


def findings_to_poam_candidates(findings: list[dict], system_id: str) -> list[dict]:
    """
    Convert failed SCAP findings into POA&M item candidates.
    Only returns findings with result == 'fail' or 'error'.
    """
    candidates = []
    for f in findings:
        if f["result"] not in ("fail", "error"):
            continue
        candidates.append({
            "system_id":            system_id,
            "control_id":           ", ".join(f["nist_controls"]) or None,
            "weakness_name":        f"SCAP Failure: {f['title'][:150]}",
            "weakness_description": (
                f"SCAP rule {f['short_id']} failed.\n\n"
                f"{f['description']}\n\n"
                f"Remediation: {f['fix_text']}"
            ).strip()[:3000],
            "detection_source":     "scan",
            "severity":             f["severity"],
            "rule_id":              f["rule_id"],
        })
    return candidates
