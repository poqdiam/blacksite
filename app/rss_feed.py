"""
BLACKSITE — RSS/Advisory Feed Module  (LIST4-ITEM3 rewrite)

Feed sources are admin-configurable via the feed_sources DB table.
The allowlist (FEED_ALLOWLIST in models.py) defines what sources can be enabled.

Fetch rules:
  - Per-source file cache, 1-hour TTL (CACHE_TTL).
  - Hard cap: MAX_ITEMS items per feed per fetch.
  - HTTP timeout: FETCH_TIMEOUT seconds.
  - Consecutive failure backoff: skip fetch if error_count >= BACKOFF_THRESHOLD.
  - Deduplication: URL + SHA1(title) across all sources.
  - HTML sanitized; summaries capped at 300 chars.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

log = logging.getLogger("blacksite.rss")

CACHE_DIR             = Path("static/feed_cache")
CACHE_TTL             = 3600         # seconds (1 hour)
MAX_ITEMS             = 40           # items per feed fetch
FETCH_TIMEOUT         = 8            # seconds
BACKOFF_THRESHOLD     = 3            # skip fetch if consecutive errors >= this
MAX_CACHE_FILE_BYTES  = 512 * 1024   # 512 KB — refuse to write oversized cache files


def _cache_path(feed_key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{feed_key}.json"


def _is_stale(path: Path) -> bool:
    if not path.exists():
        return True
    return time.time() - path.stat().st_mtime > CACHE_TTL


def _ns_strip(tag: str) -> str:
    return re.sub(r"\{[^}]+\}", "", tag)


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def _item_dedup_key(item: dict) -> str:
    """Dedup key: URL if present, else SHA1(title). Never deduplicates on empty link."""
    link = (item.get("link") or "").strip()
    if link:
        return link
    title = (item.get("title") or "").strip()
    return "title:" + hashlib.sha1(title.encode("utf-8", errors="replace")).hexdigest()


def _fetch_feed(url: str) -> list[dict]:
    """Fetch and parse a single RSS/Atom feed. Returns list of item dicts."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BLACKSITE-GRC/1.0 (security advisory monitor)"},
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read(2 * 1024 * 1024)  # cap at 2 MB
    except Exception as e:
        log.warning("Feed fetch failed %s: %s", url, e)
        raise

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log.warning("Feed XML parse failed %s: %s", url, e)
        raise ValueError(f"XML parse error: {e}") from e

    items = []
    tag = _ns_strip(root.tag).lower()

    # RSS 2.0
    if tag == "rss":
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item")[:MAX_ITEMS]:
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "").strip()
            desc  = item.findtext("description", "").strip()
            pub   = item.findtext("pubDate", "").strip()
            if title:
                items.append({"title": title, "link": link,
                               "desc": _clean_html(desc)[:300], "pub": pub})

    # Atom
    elif tag == "feed":
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns)[:MAX_ITEMS]:
            title   = entry.findtext("a:title", "", ns).strip()
            link_el = entry.find("a:link", ns)
            link    = link_el.get("href", "") if link_el is not None else ""
            summ    = entry.findtext("a:summary", "", ns).strip()
            pub     = entry.findtext("a:published", "", ns).strip()
            if title:
                items.append({"title": title, "link": link,
                               "desc": _clean_html(summ)[:300], "pub": pub})

    return items


def _get_cached(feed_key: str, url: str) -> tuple[list[dict], Optional[str]]:
    """
    Return (items, error). Refreshes cache if stale.
    On fetch failure returns stale cache + error string.
    """
    path = _cache_path(feed_key)
    if not _is_stale(path):
        try:
            return json.loads(path.read_text()), None
        except Exception:
            pass

    try:
        items = _fetch_feed(url)
        if items:
            try:
                payload = json.dumps(items)
                if len(payload.encode()) <= MAX_CACHE_FILE_BYTES:
                    path.write_text(payload)
                else:
                    log.warning("Feed cache for '%s' exceeds %d KB — skipping write.",
                                feed_key, MAX_CACHE_FILE_BYTES // 1024)
            except Exception:
                pass
        return items, None
    except Exception as e:
        err_str = str(e)[:300]
        # Fall back to stale cache
        if path.exists():
            try:
                return json.loads(path.read_text()), err_str
            except Exception:
                pass
        return [], err_str


def _system_keywords(systems: list) -> set[str]:
    kw = set()
    for s in systems:
        name = (s.name or "").replace("[SEED]", "").strip()
        for word in re.split(r"[\s\-_/]+", name):
            if len(word) >= 4:
                kw.add(word.lower())
        if s.abbreviation:
            kw.add(s.abbreviation.lower())
        if s.description:
            for word in re.split(r"\W+", s.description):
                if len(word) >= 5:
                    kw.add(word.lower())
    stops = {"system", "platform", "service", "management", "general", "support",
             "application", "network", "information", "security", "national", "federal"}
    return kw - stops


def _score_item(item: dict, keywords: set[str]) -> int:
    text = (item["title"] + " " + item["desc"]).lower()
    return sum(1 for kw in keywords if kw in text)


def get_feed_items(
    sources: list[dict] | None = None,
    systems: list = None,
    max_items: int = 20,
    min_score: int = 0,
) -> list[dict]:
    """
    Merge and deduplicate items from the given sources list.
    Each source dict must have: key, name, url, enabled, error_count.
    If sources is None, falls back to the static FEEDS list (backward compat).
    """
    if sources is None:
        sources = _FALLBACK_FEEDS

    keywords = _system_keywords(systems) if systems else set()
    merged: list[dict] = []
    seen: set[str] = set()

    for src in sources:
        if not src.get("enabled", True):
            continue
        if (src.get("error_count") or 0) >= BACKOFF_THRESHOLD:
            log.debug("Skipping %s — error_count=%d >= backoff threshold",
                      src["key"], src["error_count"])
            continue

        items, _err = _get_cached(src["key"], src["url"])
        for item in items:
            dk = _item_dedup_key(item)
            if dk in seen:
                continue
            seen.add(dk)
            score = _score_item(item, keywords)
            if score >= min_score:
                merged.append({
                    **item,
                    "source":       src["name"],
                    "source_key":   src["key"],
                    "score":        score,
                })

    if keywords:
        merged.sort(key=lambda x: -x["score"])
    return merged[:max_items]


def get_all_feed_items(
    sources: list[dict] | None = None,
    max_items: int = 30,
) -> list[dict]:
    return get_feed_items(sources=sources, systems=None,
                          max_items=max_items, min_score=0)


def fetch_one_for_test(url: str) -> dict:
    """
    Attempt to fetch a single feed URL and return a result summary dict.
    Used by the admin test-fetch action — does NOT use or update the cache.
    """
    try:
        items = _fetch_feed(url)
        return {"ok": True, "item_count": len(items),
                "sample": items[0]["title"] if items else "(no items)"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# Fallback static feeds (used if DB query fails or during first startup)
_FALLBACK_FEEDS = [
    {"key": "cisa_alerts",   "name": "CISA Alerts",     "url": "https://www.cisa.gov/uscert/ncas/alerts.xml",      "enabled": True, "error_count": 0},
    {"key": "cisa_adv",      "name": "CISA Advisories",  "url": "https://www.cisa.gov/uscert/ncas/advisories.xml",  "enabled": True, "error_count": 0},
    {"key": "sans",          "name": "SANS ISC",          "url": "https://isc.sans.edu/rssfeed_full.xml",            "enabled": True, "error_count": 0},
]
