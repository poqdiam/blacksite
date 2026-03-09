"""
BLACKSITE — NIST 800-53r5 OSCAL controls updater.

Downloads and caches the NIST SP 800-53 Rev 5 OSCAL catalog from the
usnistgov/oscal-content GitHub repository. Checks for updates via the
GitHub commit API before downloading. Runs offline if the cache exists.
"""

from __future__ import annotations

import json
import os
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

log = logging.getLogger("blacksite.updater")

CATALOG_URL = (
    "https://raw.githubusercontent.com/usnistgov/oscal-content/main"
    "/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"
)
GITHUB_API_URL = (
    "https://api.github.com/repos/usnistgov/oscal-content/commits"
    "?path=nist.gov%2FSP800-53%2Frev5%2Fjson%2FNIST_SP-800-53_rev5_catalog.json"
    "&per_page=1"
)

# NIST SP 800-53 Rev 4 — static (no longer updated; download once)
REV4_CATALOG_URL = (
    "https://raw.githubusercontent.com/usnistgov/oscal-content/main"
    "/nist.gov/SP800-53/rev4/json/NIST_SP-800-53_rev4_catalog.json"
)
REV4_LOCAL_PATH = "nist_800_53r4.json"

_BASE = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json"
BASELINE_PROFILE_URLS: Dict[str, str] = {
    "nist_low":     f"{_BASE}/NIST_SP-800-53_rev5_LOW-baseline_profile.json",
    "nist_mod":     f"{_BASE}/NIST_SP-800-53_rev5_MODERATE-baseline_profile.json",
    "nist_high":    f"{_BASE}/NIST_SP-800-53_rev5_HIGH-baseline_profile.json",
    "nist_privacy": f"{_BASE}/NIST_SP-800-53_rev5_PRIVACY-baseline_profile.json",
}


def load_meta(meta_path: Path) -> dict:
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text())
        except Exception:
            pass
    return {}


def save_meta(meta_path: Path, data: dict):
    meta_path.write_text(json.dumps(data, indent=2))


def latest_remote_sha(timeout: int = 10, retries: int = 3) -> Optional[str]:
    """Return the latest git SHA for the catalog file, or None on error."""
    import time as _time
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(GITHUB_API_URL, timeout=timeout,
                             headers={"Accept": "application/vnd.github+json"})
            r.raise_for_status()
            commits = r.json()
            if commits:
                return commits[0]["sha"]
            return None
        except Exception as e:
            last_err = e
            if attempt < retries:
                _time.sleep(2 ** (attempt - 1))   # 1s, 2s backoff
    log.warning("Could not check remote NIST SHA after %d attempts: %s", retries, last_err)
    return None


def download_catalog(catalog_path: Path, timeout: int = 60) -> bool:
    """Download NIST OSCAL catalog to disk. Returns True on success."""
    try:
        log.info("Downloading NIST 800-53r5 OSCAL catalog…")
        r = requests.get(CATALOG_URL, timeout=timeout, stream=True)
        r.raise_for_status()
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        with open(catalog_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        log.info("Downloaded catalog → %s", catalog_path)
        return True
    except Exception as e:
        log.error("Failed to download catalog: %s", e)
        return False


def download_baselines(controls_dir: Path, timeout: int = 60) -> Dict[str, bool]:
    """Download NIST SP 800-53B OSCAL baseline profiles. Only fetches missing files."""
    results: Dict[str, bool] = {}
    for name, url in BASELINE_PROFILE_URLS.items():
        dest = controls_dir / f"{name}_profile.json"
        if dest.exists():
            results[name] = True
            continue
        try:
            log.info("Downloading %s baseline profile…", name)
            r = requests.get(url, timeout=timeout, stream=True)
            r.raise_for_status()
            controls_dir.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
            log.info("Downloaded %s baseline → %s", name, dest)
            results[name] = True
        except Exception as e:
            log.error("Failed to download %s baseline: %s", name, e)
            results[name] = False
    return results


def load_baselines(controls_dir: Path) -> Dict[str, list]:
    """
    Parse downloaded NIST SP 800-53B OSCAL baseline profile files.
    Returns {short_name: [control_id, ...]} for each available profile.
    """
    out: Dict[str, list] = {}
    for name in BASELINE_PROFILE_URLS:
        path = controls_dir / f"{name}_profile.json"
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            profile = raw.get("profile", raw)
            ids: list = []
            for imp in profile.get("imports", []):
                for ic in imp.get("include-controls", []):
                    for cid in ic.get("with-ids", []):
                        ids.append(cid.lower())
            out[name] = ids
            log.info("Loaded %d controls from %s baseline.", len(ids), name)
        except Exception as e:
            log.error("Failed to parse %s baseline profile: %s", name, e)
    return out


def update_if_needed(config: dict) -> bool:
    """
    Check if the local catalog is current. If not, download the latest.
    Returns True if catalog is available (whether updated or cached).
    """
    controls_dir = Path(config.get("nist", {}).get("controls_dir", "controls"))
    catalog_path = controls_dir / "nist_800_53r5.json"
    meta_path    = controls_dir / "meta.json"
    meta = load_meta(meta_path)

    # Always try to update if catalog is missing
    if not catalog_path.exists():
        log.info("Catalog not found — performing initial download.")
        ok = download_catalog(catalog_path)
        if ok:
            sha = latest_remote_sha() or "unknown"
            save_meta(meta_path, {
                "git_sha": sha,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "source": CATALOG_URL,
            })
        download_baselines(controls_dir)
        return ok

    # Check remote SHA — skip download if unchanged
    remote_sha = latest_remote_sha()
    if remote_sha and remote_sha == meta.get("git_sha"):
        log.info("NIST catalog is current (SHA %s).", remote_sha[:8])
        download_baselines(controls_dir)   # no-op if all profiles already cached
        return True

    # Update needed
    ok = download_catalog(catalog_path)
    if ok:
        save_meta(meta_path, {
            "git_sha": remote_sha or "unknown",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": CATALOG_URL,
        })

    # Always ensure baseline profiles are present (only downloads if missing)
    download_baselines(controls_dir)

    return ok


# ── Catalog parsing ────────────────────────────────────────────────────────────

def _get_label(part: dict) -> str:
    """Extract the 'label' prop value from a part (e.g. 'a.', '1.')."""
    for prop in part.get("props", []):
        if prop.get("name") == "label":
            return prop.get("value", "")
    return ""


def _extract_prose(part: dict, _depth: int = 0) -> str:
    """Recursively extract prose from an OSCAL part, preserving label hierarchy."""
    lines = []
    label  = _get_label(part)
    prose  = (part.get("prose") or "").strip()
    indent = "   " * _depth

    if prose:
        if label:
            lines.append(f"{indent}{label} {prose}")
        else:
            lines.append(f"{indent}{prose}")

    for sub in part.get("parts", []):
        sub_text = _extract_prose(sub, _depth + 1)
        if sub_text:
            lines.append(sub_text)

    return "\n".join(l for l in lines if l)


def _extract_controls(group: dict, family_id: str, family_title: str, out: dict):
    """Recursively extract controls (including enhancements) from a group."""
    for ctrl in group.get("controls", []):
        ctrl_id = ctrl.get("id", "").lower()
        parts   = ctrl.get("parts", [])

        statement = next(
            (_extract_prose(p) for p in parts if p.get("name") == "statement"), ""
        )
        guidance = next(
            (_extract_prose(p) for p in parts if p.get("name") == "guidance"), ""
        )

        # Parameters: id + human label
        # For params with no label, fall back to select choices (e.g. "remove | disable")
        # then to the raw param ID as last resort.
        params = []
        for p in ctrl.get("params", []):
            pid = p.get("id", "")
            if not pid:
                continue
            label = p.get("label", "")
            if not label:
                choices = p.get("select", {}).get("choice", [])
                label = " | ".join(choices) if choices else pid
            params.append({"id": pid, "label": label})

        # Related controls from links (href like "#ac-3")
        related = [
            lnk["href"].lstrip("#")
            for lnk in ctrl.get("links", [])
            if lnk.get("rel") == "related" and lnk.get("href", "").startswith("#")
        ]

        out[ctrl_id] = {
            "id":              ctrl_id,
            "title":           ctrl.get("title", ""),
            "family_id":       family_id.upper(),
            "family_title":    family_title,
            "statement":       statement,
            "guidance":        guidance,
            "parameters":      params,
            "related_controls": related,
        }

        # Control enhancements live under controls[].controls[]
        _extract_controls(ctrl, family_id, family_title, out)


def load_catalog(config: dict) -> dict:
    """
    Load and parse the NIST OSCAL catalog from disk.
    Returns a flat dict keyed by control ID, e.g. {"ac-1": {...}, ...}.
    Falls back to empty dict if catalog is unavailable.
    """
    controls_dir = Path(config.get("nist", {}).get("controls_dir", "controls"))
    catalog_path = controls_dir / "nist_800_53r5.json"

    if not catalog_path.exists():
        log.warning("NIST catalog not found at %s — running without controls.", catalog_path)
        return {}

    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Failed to parse NIST catalog: %s", e)
        return {}

    catalog = raw.get("catalog", raw)
    controls: dict = {}

    for group in catalog.get("groups", []):
        family_id    = group.get("id", "??")
        family_title = group.get("title", "Unknown")
        _extract_controls(group, family_id, family_title, controls)

    log.info("Loaded %d controls from NIST catalog.", len(controls))
    return controls


def get_control_families(catalog: dict) -> Dict[str, str]:
    """Return {family_id: family_title} mapping."""
    seen: dict[str, str] = {}
    for ctrl in catalog.values():
        fid = ctrl["family_id"]
        if fid not in seen:
            seen[fid] = ctrl["family_title"]
    return dict(sorted(seen.items()))


def ensure_rev4_catalog(controls_dir: Path, timeout: int = 60) -> bool:
    """Download Rev 4 catalog if not already on disk. Rev 4 is static — download once."""
    dest = controls_dir / REV4_LOCAL_PATH
    if dest.exists():
        return True
    try:
        log.info("Downloading NIST 800-53 Rev 4 OSCAL catalog (one-time)…")
        r = requests.get(REV4_CATALOG_URL, timeout=timeout, stream=True)
        r.raise_for_status()
        controls_dir.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        log.info("Rev 4 catalog saved → %s", dest)
        return True
    except Exception as e:
        log.warning("Could not download Rev 4 catalog: %s", e)
        return False


def load_rev4_catalog(controls_dir: Path) -> dict:
    """Load and parse the NIST 800-53 Rev 4 OSCAL catalog from disk.
    Returns the same flat dict format as load_catalog() — keyed by lowercase control ID."""
    path = controls_dir / REV4_LOCAL_PATH
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Failed to parse Rev 4 catalog: %s", e)
        return {}
    catalog = raw.get("catalog", raw)
    controls: dict = {}
    for group in catalog.get("groups", []):
        family_id    = group.get("id", "??")
        family_title = group.get("title", "Unknown")
        _extract_controls(group, family_id, family_title, controls)
    log.info("Loaded %d controls from NIST 800-53 Rev 4 catalog.", len(controls))
    return controls


# ── Supplemental catalog definitions ──────────────────────────────────────────

SUPPLEMENTAL_CATALOGS: Dict[str, dict] = {
    "sp800_171r2": {
        "url": "https://raw.githubusercontent.com/FATHOM5CORP/oscal/main/content/SP800-171/oscal-content/catalogs/NIST_SP-800-171_rev2_catalog.json",
        "local": "sp800_171r2.json",
        "label": "NIST SP 800-171 Rev 2",
    },
    "sp800_171r3": {
        "url": "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-171/rev3/json/NIST_SP800-171_rev3_catalog.json",
        "local": "sp800_171r3.json",
        "label": "NIST SP 800-171 Rev 3",
    },
    "csf2": {
        "url": "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/CSF/v2.0/json/NIST_CSF_v2.0_catalog.json",
        "local": "csf_2_0.json",
        "label": "NIST CSF 2.0",
    },
    "fedramp_high": {
        "url": "https://raw.githubusercontent.com/GSA/fedramp-automation/master/dist/content/rev5/baselines/json/FedRAMP_rev5_HIGH-baseline-resolved-profile_catalog.json",
        "local": "fedramp_high_resolved.json",
        "label": "FedRAMP High",
    },
    "fedramp_mod": {
        "url": "https://raw.githubusercontent.com/GSA/fedramp-automation/master/dist/content/rev5/baselines/json/FedRAMP_rev5_MODERATE-baseline-resolved-profile_catalog.json",
        "local": "fedramp_mod_resolved.json",
        "label": "FedRAMP Moderate",
    },
    "fedramp_low": {
        "url": "https://raw.githubusercontent.com/GSA/fedramp-automation/master/dist/content/rev5/baselines/json/FedRAMP_rev5_LOW-baseline-resolved-profile_catalog.json",
        "local": "fedramp_low_resolved.json",
        "label": "FedRAMP Low",
    },
}


def ensure_supplemental_catalogs(controls_dir: Path, timeout: int = 120) -> None:
    """Download any missing supplemental catalog files. Skips files already on disk."""
    controls_dir.mkdir(parents=True, exist_ok=True)
    for key, meta in SUPPLEMENTAL_CATALOGS.items():
        dest = controls_dir / meta["local"]
        if dest.exists():
            log.info("Supplemental catalog already cached: %s", meta["label"])
            continue
        try:
            log.info("Downloading %s…", meta["label"])
            r = requests.get(meta["url"], timeout=timeout, stream=True)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
            log.info("Downloaded %s → %s", meta["label"], dest)
        except Exception as e:
            log.warning("Could not download %s: %s", meta["label"], e)


def _parse_oscal_group(group: dict, family_id: str, family_title: str, out: dict) -> None:
    """Recursively parse an OSCAL group — handles sub-groups and controls."""
    # Recurse into nested groups (CSF 2.0 pattern: groups inside groups)
    for sub_group in group.get("groups", []):
        sub_fid   = sub_group.get("id", family_id)
        sub_ftit  = sub_group.get("title", family_title)
        _parse_oscal_group(sub_group, sub_fid, sub_ftit, out)

    # Extract controls at this level
    for ctrl in group.get("controls", []):
        ctrl_id = ctrl.get("id", "").lower()
        if not ctrl_id:
            continue
        parts = ctrl.get("parts", [])
        statement = next(
            (_extract_prose(p) for p in parts if p.get("name") == "statement"), ""
        )
        guidance = next(
            (_extract_prose(p) for p in parts if p.get("name") == "guidance"), ""
        )
        out[ctrl_id] = {
            "id":           ctrl_id,
            "title":        ctrl.get("title", ""),
            "family_id":    family_id.upper(),
            "family_title": family_title,
            "statement":    statement,
            "guidance":     guidance,
        }
        # Control enhancements (controls nested under controls)
        _parse_oscal_group(ctrl, family_id, family_title, out)


def load_oscal_catalog_file(path: Path) -> dict:
    """
    Generic OSCAL catalog parser — handles both:
      - Standard pattern: catalog.groups[].controls[] (800-53, 800-171)
      - Nested groups:    catalog.groups[].groups[].controls[] (CSF 2.0)
    Returns a flat dict keyed by lowercase control/requirement ID:
      {ctrl_id: {id, title, family_id, family_title, statement, guidance}}
    """
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Failed to parse OSCAL file %s: %s", path, e)
        return {}

    catalog = raw.get("catalog", raw)
    out: dict = {}
    for group in catalog.get("groups", []):
        family_id    = group.get("id", "??")
        family_title = group.get("title", "Unknown")
        _parse_oscal_group(group, family_id, family_title, out)

    return out


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    cfg = {"nist": {"controls_dir": "controls"}}
    ok = update_if_needed(cfg)
    if ok:
        cat = load_catalog(cfg)
        print(f"Loaded {len(cat)} controls.")
        print("Sample — AC-1:", cat.get("ac-1", {}).get("title"))
    else:
        print("Update failed — check connectivity.", file=sys.stderr)
        sys.exit(1)
