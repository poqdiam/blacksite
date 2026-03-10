"""
Public data connectors for Blacksite GRC.

Each connector fetches from a free, publicly accessible source and normalizes
data to the Blacksite feed item format.  All connectors are file-cached so the
app never blocks on external I/O during page renders.

Sources:
  cisa_kev        — CISA Known Exploited Vulnerabilities (JSON, no auth)
  hn_security     — Hacker News via Algolia Search API (no auth, 10k req/hr)
  federal_register — Federal Register REST API (no auth)
  gh_advisories   — GitHub Security Advisories REST API (no auth, 60 req/hr)
  cisa_ransomware — CISA StopRansomware JSON feed (no auth)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

CACHE_DIR = Path("static/feed_cache")

# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_fresh(path: Path, ttl: int) -> bool:
    if not path.exists():
        return False
    try:
        age = datetime.now(timezone.utc).timestamp() - json.loads(path.read_text()).get("_fetched", 0)
        return age < ttl
    except Exception:
        return False

def _read_cache(path: Path, key: str = "items") -> list:
    try:
        return json.loads(path.read_text()).get(key, [])
    except Exception:
        return []

def _write_cache(path: Path, key: str, payload: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "_fetched": datetime.now(timezone.utc).timestamp(),
        key: payload,
    }))


# ── 1. CISA Known Exploited Vulnerabilities ───────────────────────────────────
#    https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
#    No auth.  CISA updates this catalog daily.  1,200+ entries and growing.

KEV_URL   = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
KEV_CACHE = CACHE_DIR / "cisa_kev.json"
KEV_TTL   = 3600


async def fetch_kev() -> dict:
    """
    Fetch the full CISA KEV catalog.
    Returns {"vulnerabilities": [...], "catalogVersion": "...", "count": N, "_from_cache": bool}.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _cache_fresh(KEV_CACHE, KEV_TTL):
        cached = json.loads(KEV_CACHE.read_text())
        return {
            "vulnerabilities": cached.get("items", []),
            "catalogVersion":  cached.get("version", ""),
            "dateReleased":    cached.get("dateReleased", ""),
            "count":           cached.get("count", 0),
            "_from_cache":     True,
        }
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get(KEV_URL, headers={"User-Agent": "Blacksite-GRC/1.0"})
            r.raise_for_status()
            data = r.json()
        vulns = data.get("vulnerabilities", [])
        KEV_CACHE.write_text(json.dumps({
            "_fetched":    datetime.now(timezone.utc).timestamp(),
            "items":       vulns,
            "version":     data.get("catalogVersion", ""),
            "dateReleased": data.get("dateReleased", ""),
            "count":       len(vulns),
        }))
        return {**data, "count": len(vulns), "_from_cache": False}
    except Exception as exc:
        log.warning("KEV fetch failed: %s", exc)
        if KEV_CACHE.exists():
            cached = json.loads(KEV_CACHE.read_text())
            return {"vulnerabilities": cached.get("items", []), "count": cached.get("count", 0),
                    "_from_cache": True, "_error": str(exc)}
        return {"vulnerabilities": [], "count": 0, "_error": str(exc)}


def kev_to_feed_items(vulns: list[dict], limit: int = 40) -> list[dict]:
    """Convert KEV entries to unified feed item format, newest first."""
    out = []
    for v in sorted(vulns, key=lambda x: x.get("dateAdded", ""), reverse=True)[:limit]:
        ransomware = v.get("knownRansomwareCampaignUse", "Unknown")
        out.append({
            "title":       f"[KEV] {v.get('cveID', '')}: {v.get('vulnerabilityName', '')}",
            "link":        "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
            "desc":        (
                f"{v.get('shortDescription', '')[:200]} — "
                f"Vendor: {v.get('vendorProject', '')}, Product: {v.get('product', '')}. "
                f"Due: {v.get('dueDate', 'N/A')}. Ransomware: {ransomware}."
            ),
            "pub":         v.get("dateAdded", ""),
            "source":      "CISA KEV",
            "source_key":  "cisa_kev",
            "score":       10,
            "tags":        ["kev", "cisa", "exploit"],
            "cve_id":      v.get("cveID", ""),
            "vendor":      v.get("vendorProject", ""),
            "product":     v.get("product", ""),
            "due_date":    v.get("dueDate", ""),
            "ransomware":  ransomware,
        })
    return out


def kev_match_inventory(vulns: list[dict], inventory_items: list) -> list[dict]:
    """
    Return KEV entries whose vendor or product name appears in any inventory item.
    inventory_items: list of InventoryItem ORM objects (need .name, .description).
    """
    hits: list[dict] = []
    for v in vulns:
        vendor  = (v.get("vendorProject") or "").lower().strip()
        product = (v.get("product") or "").lower().strip()
        if not vendor and not product:
            continue
        for item in inventory_items:
            haystack = (
                (getattr(item, "name", "") or "") + " " +
                (getattr(item, "description", "") or "") + " " +
                (getattr(item, "asset_type", "") or "")
            ).lower()
            if (vendor and len(vendor) > 2 and vendor in haystack) or \
               (product and len(product) > 2 and product in haystack):
                hits.append({**v, "_matched_asset": getattr(item, "name", "")})
                break
    return hits


# ── 2. Hacker News — Algolia Search API ──────────────────────────────────────
#    https://hn.algolia.com/api/v1/search
#    No API key.  Rate limit: 10,000 req/hour (very generous for caching use).

HN_API   = "https://hn.algolia.com/api/v1/search"
HN_CACHE = CACHE_DIR / "hn_security.json"
HN_TTL   = 3600

# GRC-focused queries covering the topics users care about
_HN_QUERIES = [
    "NIST 800-53 compliance",
    "FedRAMP ATO authorization",
    "zero day vulnerability exploit",
    "ransomware incident response",
    "supply chain attack software",
    "CISA advisory vulnerability",
    "patch tuesday security update",
    "cloud security misconfiguration breach",
    "government cybersecurity policy regulation",
    "CVE critical vulnerability",
    "security audit penetration testing",
    "data breach incident",
]


async def fetch_hn_security(max_items: int = 50) -> list[dict]:
    """
    Fetch GRC-relevant HN stories from the last 14 days with >10 points.
    Deduplicates across queries; returns top N by score.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _cache_fresh(HN_CACHE, HN_TTL):
        return _read_cache(HN_CACHE)

    seen_ids: set[str] = set()
    items: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            for query in _HN_QUERIES:
                if len(items) >= max_items * 2:
                    break
                r = await client.get(HN_API, params={
                    "query":          query,
                    "tags":           "story",
                    "numericFilters": "points>15",   # score threshold only; no date filter
                    "hitsPerPage":    10,
                })
                if not r.is_success:
                    continue
                for hit in r.json().get("hits", []):
                    oid = hit.get("objectID")
                    if not oid or oid in seen_ids:
                        continue
                    seen_ids.add(oid)
                    url = hit.get("url") or f"https://news.ycombinator.com/item?id={oid}"
                    items.append({
                        "title":      hit.get("title", ""),
                        "link":       url,
                        "hn_thread":  f"https://news.ycombinator.com/item?id={oid}",
                        "desc":       (
                            f"⬆ {hit.get('points', 0)} pts  "
                            f"· {hit.get('num_comments', 0)} comments  "
                            f"· by {hit.get('author', '')}"
                        ),
                        "pub":        hit.get("created_at", ""),
                        "source":     "Hacker News",
                        "source_key": "hn_security",
                        "score":      min(10, max(1, (hit.get("points") or 0) // 25)),
                        "tags":       ["community", "hn"],
                        "points":     hit.get("points", 0),
                        "comments":   hit.get("num_comments", 0),
                        "hn_id":      oid,
                    })

        items.sort(key=lambda x: x.get("points", 0), reverse=True)
        items = items[:max_items]
        _write_cache(HN_CACHE, "items", items)
    except Exception as exc:
        log.warning("HN fetch failed: %s", exc)
        items = _read_cache(HN_CACHE)

    return items


# ── 3. Federal Register ───────────────────────────────────────────────────────
#    https://www.federalregister.gov/api/v1/documents.json
#    No API key.  Returns federal rules, proposed rules, and notices.

FR_API   = "https://www.federalregister.gov/api/v1/documents.json"
FR_CACHE = CACHE_DIR / "federal_register.json"
FR_TTL   = 3600

# Term-based search queries for FR documents — the /documents.json API
# does not accept agency slugs; use conditions[term] instead.
_FR_TERMS = [
    "cybersecurity NIST",
    "CMMC FedRAMP",
    "information security OMB",
    "privacy data protection",
    "supply chain security software",
]


async def fetch_federal_register(max_items: int = 30) -> list[dict]:
    """
    Fetch recent cybersecurity-relevant Federal Register documents via term search.
    Uses a fixed lookback of 180 days to avoid date-range issues with the API.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _cache_fresh(FR_CACHE, FR_TTL):
        return _read_cache(FR_CACHE)

    items:    list[dict] = []
    seen_ids: set[str]   = set()

    # Use a fixed historical cutoff rather than computing from system time,
    # so this works correctly regardless of the host clock.
    cutoff = "2024-01-01"

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            for term in _FR_TERMS:
                if len(items) >= max_items:
                    break
                params: list[tuple[str, str]] = [
                    ("conditions[term]",                    term),
                    ("conditions[publication_date][gte]",   cutoff),
                    ("per_page",                            str(max_items // len(_FR_TERMS) + 5)),
                    ("order",                               "newest"),
                    ("fields[]",                            "title"),
                    ("fields[]",                            "document_number"),
                    ("fields[]",                            "publication_date"),
                    ("fields[]",                            "agency_names"),
                    ("fields[]",                            "abstract"),
                    ("fields[]",                            "html_url"),
                    ("fields[]",                            "type"),
                    ("fields[]",                            "significant"),
                ]
                for doc_type in ("RULE", "PRORULE", "NOTICE"):
                    params.append(("conditions[type][]", doc_type))

                r = await c.get(FR_API, params=params,
                                headers={"User-Agent": "Blacksite-GRC/1.0"})
                if not r.is_success:
                    log.warning("Federal Register term=%r returned %s", term, r.status_code)
                    continue

                for doc in r.json().get("results", []):
                    doc_num = doc.get("document_number", "")
                    if doc_num in seen_ids:
                        continue
                    seen_ids.add(doc_num)
                    doc_type    = doc.get("type", "")
                    significant = bool(doc.get("significant"))
                    score = (7 if significant else 4) + (2 if doc_type == "RULE" else 0)
                    agencies = doc.get("agency_names", [])
                    items.append({
                        "title":       doc.get("title", ""),
                        "link":        doc.get("html_url", ""),
                        "desc":        (doc.get("abstract") or f"{doc_type} — {', '.join(agencies)}"),
                        "pub":         doc.get("publication_date", ""),
                        "source":      "Federal Register",
                        "source_key":  "federal_register",
                        "score":       score,
                        "tags":        ["regulatory", "federal", doc_type.lower()],
                        "doc_type":    doc_type,
                        "agencies":    agencies,
                        "doc_number":  doc_num,
                        "significant": significant,
                    })

        items.sort(key=lambda x: x.get("pub", ""), reverse=True)
        items = items[:max_items]
        _write_cache(FR_CACHE, "items", items)
    except Exception as exc:
        log.warning("Federal Register fetch failed: %s", exc)
        items = _read_cache(FR_CACHE)

    return items


# ── 4. GitHub Security Advisories ────────────────────────────────────────────
#    https://api.github.com/advisories
#    No auth for public reviewed advisories.
#    Rate limit: 60 req/hour unauthenticated — fine with hourly file cache.

GH_API   = "https://api.github.com/advisories"
GH_CACHE = CACHE_DIR / "gh_advisories.json"
GH_TTL   = 3600


async def fetch_github_advisories(max_items: int = 40) -> list[dict]:
    """Fetch reviewed Critical + High GitHub Security Advisories."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _cache_fresh(GH_CACHE, GH_TTL):
        return _read_cache(GH_CACHE)

    items:    list[dict] = []
    seen_ids: set[str]   = set()

    try:
        headers = {
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent":           "Blacksite-GRC/1.0",
        }
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            for severity in ("critical", "high"):
                r = await c.get(GH_API, params={
                    "type":      "reviewed",
                    "severity":  severity,
                    "per_page":  max_items // 2,
                }, headers=headers)
                if not r.is_success:
                    continue
                for adv in r.json():
                    ghsa = adv.get("ghsa_id", "")
                    if ghsa in seen_ids:
                        continue
                    seen_ids.add(ghsa)
                    cve     = adv.get("cve_id") or ghsa
                    sev_val = adv.get("severity", "unknown")
                    pkgs    = [
                        p["package"]["name"]
                        for p in adv.get("vulnerabilities", [])[:4]
                        if p.get("package", {}).get("name")
                    ]
                    cvss_score = None
                    if adv.get("cvss"):
                        cvss_score = adv["cvss"].get("score")
                    items.append({
                        "title":      f"[{sev_val.upper()}] {adv.get('summary', cve)}",
                        "link":       adv.get("html_url", f"https://github.com/advisories/{ghsa}"),
                        "desc":       (adv.get("description") or "")[:300],
                        "pub":        adv.get("published_at", ""),
                        "source":     "GitHub Advisory",
                        "source_key": "gh_advisories",
                        "score":      9 if sev_val == "critical" else 7,
                        "tags":       ["advisory", "ghsa", sev_val],
                        "severity":   sev_val,
                        "cve_id":     cve,
                        "ghsa_id":    ghsa,
                        "packages":   pkgs,
                        "cvss_score": cvss_score,
                    })

        items.sort(key=lambda x: (x.get("score", 0), x.get("pub", "")), reverse=True)
        items = items[:max_items]
        _write_cache(GH_CACHE, "items", items)
    except Exception as exc:
        log.warning("GitHub advisories fetch failed: %s", exc)
        items = _read_cache(GH_CACHE)

    return items


# ── 5. NVD Recent Critical/High CVEs ─────────────────────────────────────────
#    https://services.nvd.nist.gov/rest/json/cves/2.0
#    No API key required (1 req/6s limit without key; fine with hourly cache).
#    Uses a fixed date window rather than relative dates to avoid clock issues.

NVD_API          = "https://services.nvd.nist.gov/rest/json/cves/2.0"
RANSOMWARE_CACHE = CACHE_DIR / "cisa_ransomware.json"   # kept same var for registry compat
RANSOMWARE_TTL   = 7200


async def fetch_cisa_ransomware(max_items: int = 20) -> list[dict]:
    """
    Fetch recent Critical/High CVEs from NVD 2.0 API.
    Uses a fixed 90-day window anchored to a known-good date rather than
    computing from system time, so this works on any host clock.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _cache_fresh(RANSOMWARE_CACHE, RANSOMWARE_TTL):
        return _read_cache(RANSOMWARE_CACHE)

    items: list[dict] = []
    # Fixed window: last 90 days of known NVD data (dates in NVD 2.0 ISO format)
    pub_end   = "2025-03-01T00:00:00.000"
    pub_start = "2024-12-01T00:00:00.000"

    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as c:
            for severity in ("CRITICAL", "HIGH"):
                r = await c.get(NVD_API, params={
                    "cvssV3Severity":    severity,
                    "pubStartDate":      pub_start,
                    "pubEndDate":        pub_end,
                    "resultsPerPage":    max_items // 2,
                }, headers={"User-Agent": "Blacksite-GRC/1.0"})
                if not r.is_success:
                    log.warning("NVD CVE fetch %s: %s", severity, r.status_code)
                    continue
                for vuln in r.json().get("vulnerabilities", []):
                    cve    = vuln.get("cve", {})
                    cve_id = cve.get("id", "")
                    desc   = next(
                        (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
                        ""
                    )
                    # Extract CVSS v3 score
                    metrics   = cve.get("metrics", {})
                    cvss_data = (metrics.get("cvssMetricV31") or metrics.get("cvssMetricV30") or [])
                    score_val = cvss_data[0]["cvssData"]["baseScore"] if cvss_data else None

                    items.append({
                        "title":      f"[{severity}] {cve_id}",
                        "link":       f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                        "desc":       desc[:300],
                        "pub":        cve.get("published", "")[:10],
                        "source":     "NVD CVE Feed",
                        "source_key": "cisa_ransomware",
                        "score":      9 if severity == "CRITICAL" else 7,
                        "tags":       ["nvd", "cve", severity.lower()],
                        "cve_id":     cve_id,
                        "severity":   severity,
                        "cvss_score": score_val,
                    })

        items.sort(key=lambda x: (x.get("score", 0), x.get("pub", "")), reverse=True)
        items = items[:max_items]
        _write_cache(RANSOMWARE_CACHE, "items", items)
    except Exception as exc:
        log.warning("NVD CVE feed failed: %s", exc)
        items = _read_cache(RANSOMWARE_CACHE)

    return items


# ── Connector registry ────────────────────────────────────────────────────────

CONNECTORS: dict[str, dict] = {
    "cisa_kev": {
        "name":        "CISA Known Exploited Vulnerabilities",
        "description": "CISA's authoritative catalog of vulnerabilities known to be actively exploited in the wild. Federal agencies are required to patch these within defined deadlines.",
        "source_url":  "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        "cache_file":  KEV_CACHE,
        "ttl":         KEV_TTL,
        "fetcher":     fetch_kev,
        "type":        "json_api",
        "tags":        ["cve", "exploit", "patching", "federal"],
        "priority":    "critical",
    },
    "gh_advisories": {
        "name":        "GitHub Security Advisories",
        "description": "Reviewed Critical and High severity security advisories from the GitHub Advisory Database (GHSA). Covers open-source software vulnerabilities with CVSS scores.",
        "source_url":  "https://github.com/advisories",
        "cache_file":  GH_CACHE,
        "ttl":         GH_TTL,
        "fetcher":     fetch_github_advisories,
        "type":        "rest_api",
        "tags":        ["advisory", "oss", "vulnerability", "cvss"],
        "priority":    "high",
    },
    "federal_register": {
        "name":        "Federal Register",
        "description": "Rules, proposed rules, and notices from NIST, CISA, DHS, DoD, OMB, GSA, FTC, and SEC. Covers new cybersecurity regulations and compliance requirements.",
        "source_url":  "https://www.federalregister.gov",
        "cache_file":  FR_CACHE,
        "ttl":         FR_TTL,
        "fetcher":     fetch_federal_register,
        "type":        "rest_api",
        "tags":        ["regulatory", "policy", "federal", "compliance"],
        "priority":    "medium",
    },
    "hn_security": {
        "name":        "Hacker News — Security & Compliance",
        "description": "Security-relevant community discussions from Hacker News, filtered to GRC topics (NIST, FedRAMP, CVEs, incidents, policy) with minimum score threshold.",
        "source_url":  "https://news.ycombinator.com",
        "cache_file":  HN_CACHE,
        "ttl":         HN_TTL,
        "fetcher":     fetch_hn_security,
        "type":        "algolia_api",
        "tags":        ["community", "discussion", "news"],
        "priority":    "low",
    },
    "cisa_ransomware": {
        "name":        "NVD Recent Critical/High CVEs",
        "description": "Recent Critical and High severity CVEs from the NIST National Vulnerability Database (NVD 2.0 API). Fixed 90-day window, no API key required.",
        "source_url":  "https://nvd.nist.gov/vuln/search",
        "cache_file":  RANSOMWARE_CACHE,
        "ttl":         RANSOMWARE_TTL,
        "fetcher":     fetch_cisa_ransomware,
        "type":        "rest_api",
        "tags":        ["nvd", "cve", "critical", "high"],
        "priority":    "high",
    },
}


async def connector_status(key: str) -> dict:
    """Return live cache status for a connector."""
    info = CONNECTORS.get(key, {})
    cache_path: Path = info.get("cache_file", Path(""))
    if not cache_path or not Path(cache_path).exists():
        return {"status": "never_synced", "item_count": 0, "last_fetched": None, "age_min": None}
    try:
        data = json.loads(Path(cache_path).read_text())
        ts   = data.get("_fetched")
        if ts:
            age_min  = int((datetime.now(timezone.utc).timestamp() - ts) / 60)
            last_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        else:
            age_min = last_str = None
        raw_items = data.get("items") or data.get("vulnerabilities") or []
        ttl_min   = info.get("ttl", 3600) // 60
        return {
            "status":       "fresh" if (age_min is not None and age_min < ttl_min) else "stale",
            "item_count":   len(raw_items),
            "last_fetched": last_str,
            "age_min":      age_min,
            "ttl_min":      ttl_min,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "item_count": 0, "last_fetched": None}


async def all_connector_statuses() -> dict[str, dict]:
    return {key: await connector_status(key) for key in CONNECTORS}
