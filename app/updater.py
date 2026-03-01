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


def load_meta(meta_path: Path) -> dict:
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text())
        except Exception:
            pass
    return {}


def save_meta(meta_path: Path, data: dict):
    meta_path.write_text(json.dumps(data, indent=2))


def latest_remote_sha(timeout: int = 10) -> Optional[str]:
    """Return the latest git SHA for the catalog file, or None on error."""
    try:
        r = requests.get(GITHUB_API_URL, timeout=timeout,
                         headers={"Accept": "application/vnd.github+json"})
        r.raise_for_status()
        commits = r.json()
        if commits:
            return commits[0]["sha"]
    except Exception as e:
        log.warning("Could not check remote NIST SHA: %s", e)
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
        return ok

    # Check remote SHA — skip download if unchanged
    remote_sha = latest_remote_sha()
    if remote_sha and remote_sha == meta.get("git_sha"):
        log.info("NIST catalog is current (SHA %s).", remote_sha[:8])
        return True

    # Update needed
    ok = download_catalog(catalog_path)
    if ok:
        save_meta(meta_path, {
            "git_sha": remote_sha or "unknown",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": CATALOG_URL,
        })
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
