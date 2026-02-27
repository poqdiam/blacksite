"""
BLACKSITE — RSS/Advisory Feed Module

Fetches and caches vulnerability advisories from reputable security sources.
Cache is file-based (JSON), refreshed every 60 minutes per feed.
Feeds are filtered by keywords derived from system names/descriptions.

Sources:
  - CISA Alerts          (https://www.cisa.gov/uscert/ncas/alerts.xml)
  - CISA Advisories      (https://www.cisa.gov/uscert/ncas/advisories.xml)
  - SANS ISC             (https://isc.sans.edu/rssfeed_full.xml)
  - US-CERT Bulletins    (https://www.cisa.gov/uscert/ncas/bulletins.xml)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import urllib.request
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

log = logging.getLogger("blacksite.rss")

CACHE_DIR   = Path("static/feed_cache")
CACHE_TTL   = 3600  # seconds (1 hour)
MAX_ITEMS   = 40    # items per feed fetch
FETCH_TIMEOUT = 8   # seconds

FEEDS = [
    {
        "id":    "cisa-alerts",
        "name":  "CISA Alerts",
        "url":   "https://www.cisa.gov/uscert/ncas/alerts.xml",
        "color": "var(--red)",
    },
    {
        "id":    "cisa-advisories",
        "name":  "CISA Advisories",
        "url":   "https://www.cisa.gov/uscert/ncas/advisories.xml",
        "color": "var(--yellow)",
    },
    {
        "id":    "sans-isc",
        "name":  "SANS ISC",
        "url":   "https://isc.sans.edu/rssfeed_full.xml",
        "color": "var(--cyan)",
    },
    {
        "id":    "cisa-bulletins",
        "name":  "US-CERT Bulletins",
        "url":   "https://www.cisa.gov/uscert/ncas/bulletins.xml",
        "color": "var(--muted)",
    },
]


def _cache_path(feed_id: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{feed_id}.json"


def _is_stale(path: Path) -> bool:
    if not path.exists():
        return True
    return time.time() - path.stat().st_mtime > CACHE_TTL


def _ns_strip(tag: str) -> str:
    """Strip XML namespace from tag."""
    return re.sub(r"\{[^}]+\}", "", tag)


def _fetch_feed(url: str) -> list[dict]:
    """Fetch and parse a single RSS/Atom feed. Returns list of item dicts."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BLACKSITE-GRC/1.0 (security advisory monitor)"},
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read(512 * 1024)  # cap at 512 KB
    except Exception as e:
        log.warning("Feed fetch failed %s: %s", url, e)
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log.warning("Feed parse failed %s: %s", url, e)
        return []

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
                               "desc":  _clean_html(desc)[:300], "pub": pub})

    # Atom
    elif tag == "feed":
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns)[:MAX_ITEMS]:
            title = entry.findtext("a:title", "", ns).strip()
            link_el = entry.find("a:link", ns)
            link  = link_el.get("href", "") if link_el is not None else ""
            summ  = entry.findtext("a:summary", "", ns).strip()
            pub   = entry.findtext("a:published", "", ns).strip()
            if title:
                items.append({"title": title, "link": link,
                               "desc":  _clean_html(summ)[:300], "pub": pub})

    return items


def _clean_html(text: str) -> str:
    """Strip HTML tags from a string."""
    return re.sub(r"<[^>]+>", " ", text).strip()


def _get_cached(feed: dict) -> list[dict]:
    """Return cached items for a feed, refreshing if stale."""
    path = _cache_path(feed["id"])
    if not _is_stale(path):
        try:
            return json.loads(path.read_text())
        except Exception:
            pass

    items = _fetch_feed(feed["url"])
    if items:
        try:
            path.write_text(json.dumps(items))
        except Exception:
            pass
        return items

    # Return stale cache on fetch failure
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []


def _system_keywords(systems: list) -> set[str]:
    """Extract searchable keywords from a list of system objects."""
    kw = set()
    for s in systems:
        # Name words (2+ chars, strip [SEED] prefix)
        name = (s.name or "").replace("[SEED]", "").strip()
        for word in re.split(r"[\s\-_/]+", name):
            if len(word) >= 4:
                kw.add(word.lower())
        # Abbreviation
        if s.abbreviation:
            kw.add(s.abbreviation.lower())
        # Description keywords
        if s.description:
            for word in re.split(r"\W+", s.description):
                if len(word) >= 5:
                    kw.add(word.lower())
    # Remove stop words
    stops = {"system","platform","service","management","general","support",
              "application","network","information","security","national","federal"}
    return kw - stops


def _score_item(item: dict, keywords: set[str]) -> int:
    """Score an item by keyword relevance. Higher = more relevant."""
    text = (item["title"] + " " + item["desc"]).lower()
    return sum(1 for kw in keywords if kw in text)


def get_feed_items(
    systems: list = None,
    max_items: int = 20,
    min_score: int = 0,
) -> list[dict]:
    """
    Return merged, deduplicated feed items across all sources.
    If systems are provided, items are scored by keyword relevance and sorted.
    Items with score=0 are still included unless min_score > 0.
    """
    keywords = _system_keywords(systems) if systems else set()

    merged: list[dict] = []
    seen_links: set[str] = set()

    for feed in FEEDS:
        items = _get_cached(feed)
        for item in items:
            link = item.get("link", "")
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)
            score = _score_item(item, keywords)
            if score >= min_score:
                merged.append({
                    **item,
                    "source":       feed["name"],
                    "source_color": feed["color"],
                    "score":        score,
                })

    # Sort: relevant items first, then by position in feed (preserved by order)
    if keywords:
        merged.sort(key=lambda x: -x["score"])

    return merged[:max_items]


def get_all_feed_items(max_items: int = 30) -> list[dict]:
    """Return all feed items merged, for the global advisory view."""
    return get_feed_items(systems=None, max_items=max_items, min_score=0)
