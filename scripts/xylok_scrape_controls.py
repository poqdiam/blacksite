#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://app.xylok.io"
INDEX_PATH = "/reference/controls/"

CONTROL_URL_RE = re.compile(r"^/reference/controls/control/([A-Z]{2,3}-\d+[A-Z0-9()]*)/?$")
CCI_URL_RE = re.compile(r"^/reference/controls/cci/(\d+)/?$")

SECTION_MARKERS = {
    "supplemental": {"Supplemental", "#### Supplemental"},
    "cia": {"CIA Levels"},
    "overlays": {"Overlays"},
    "csf": {"CSF Categories"},
    "related_controls": {"Related Controls"},
    "enhancements": {"Enhancements"},
    "related_ccis": {"Related CCIs", "CCIs"},
    "master_assessment_datasheet": {"Master Assessment Datasheet"},
    "implementation_guidance": {"Implementation Guidance"},
    "validation_procedures": {"Validation Procedures"},
}

CONTROL_ID_LINE_RE = re.compile(r"^([A-Z]{2,3}-\d+[A-Z0-9()]*)\s*:\s*(.+)$")
RELATED_CONTROL_LINE_RE = re.compile(r"^([A-Z]{2,3}-\d+[A-Z0-9()]*)\b\s*(.*)$")
CCI_LINE_RE = re.compile(r"^(CCI-\d{6})\b\s*(.*)$")
CIA_LINE_RE = re.compile(r"^(Confidentiality|Integrity|Availability)\s+(.+)$", re.IGNORECASE)


@dataclass
class ControlRecord:
    control_id: str
    title: str
    statement: str
    supplemental: str
    cia: Dict[str, str]
    overlays: List[str]
    csf_categories: List[str]
    related_controls: List[Dict[str, str]]
    enhancements: List[Dict[str, str]]
    related_ccis: List[Dict[str, str]]
    source_url: str


@dataclass
class CciRecord:
    cci_id: str
    definition: str
    status: str
    cci_type: str
    implementation_guidance: str
    validation_procedures: str
    related_controls: List[Dict[str, str]]
    source_url: str


def _clean_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    deduped: List[str] = []
    last = None
    for ln in lines:
        if ln == last:
            continue
        deduped.append(ln)
        last = ln
    return deduped


class Fetcher:
    def __init__(self, delay_s: float, timeout_s: int, retries: int, errors_path: Optional[str] = None):
        self.delay_s = delay_s
        self.timeout_s = timeout_s
        self.retries = retries
        self.errors_path = errors_path
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "xylok-controls-scraper/1.1",
                "Accept": "text/html,application/xhtml+xml",
            }
        )

    def _log_error(self, msg: str) -> None:
        if not self.errors_path:
            return
        try:
            with open(self.errors_path, "a", encoding="utf-8") as f:
                f.write(msg.rstrip() + "\n")
        except Exception:
            pass

    def get(self, url: str, soft_fail: bool = False) -> Optional[str]:
        last_err: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout_s)
                if resp.status_code == 429:
                    time.sleep(max(self.delay_s, 2.0) * attempt)
                    continue
                if resp.status_code >= 500:
                    raise requests.HTTPError(f"{resp.status_code} Server Error", response=resp)
                resp.raise_for_status()
                time.sleep(self.delay_s)
                return resp.text
            except Exception as e:
                last_err = e
                time.sleep(max(self.delay_s, 1.0) * attempt)

        msg = f"GET failed after {self.retries} retries: {url} | {last_err}"
        self._log_error(msg)
        if soft_fail:
            return None
        raise RuntimeError(msg)


def _extract_control_urls_from_index(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: List[str] = []
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if CONTROL_URL_RE.match(href):
            urls.append(urljoin(BASE_URL, href))
    return urls


def scrape_control_links(fetcher: Fetcher, start_page: int = 1, max_pages: int = 0) -> List[str]:
    page = start_page
    seen: Set[str] = set()
    links: List[str] = []

    while True:
        if max_pages and (page - start_page + 1) > max_pages:
            break

        url = f"{BASE_URL}{INDEX_PATH}?page={page}"
        html = fetcher.get(url, soft_fail=True)

        if html is None:
            # Treat index failure as end of pagination.
            break

        page_links = _extract_control_urls_from_index(html)

        new_count = 0
        for u in page_links:
            if u in seen:
                continue
            seen.add(u)
            links.append(u)
            new_count += 1

        if new_count == 0:
            # No new items, stop.
            break

        page += 1

    return links


def _find_first_control_title_line(lines: List[str]) -> Tuple[int, str, str]:
    for i, ln in enumerate(lines):
        m = CONTROL_ID_LINE_RE.match(ln)
        if m:
            return i, m.group(1), m.group(2).strip()
    raise ValueError("Control title line not found")


def _slice_section(lines: List[str], start_idx: int, end_markers: Set[str]) -> Tuple[str, int]:
    buf: List[str] = []
    i = start_idx
    while i < len(lines):
        ln = lines[i]
        if ln in end_markers:
            break
        buf.append(ln)
        i += 1
    return "\n".join(buf).strip(), i


def _index_of_marker(lines: List[str], marker_set: Set[str]) -> int:
    for i, ln in enumerate(lines):
        if ln in marker_set:
            return i
    return -1


def _parse_list_line(line: str) -> List[str]:
    parts = [p.strip() for p in re.split(r",\s*", line) if p.strip()]
    return parts


def _parse_related_controls(lines: List[str], start_idx: int) -> Tuple[List[Dict[str, str]], int]:
    items: List[Dict[str, str]] = []
    i = start_idx

    while i < len(lines) and lines[i] != "Control Description":
        if lines[i] in SECTION_MARKERS["enhancements"] or lines[i] in SECTION_MARKERS["related_ccis"]:
            return items, i
        i += 1

    if i < len(lines) and lines[i] == "Control Description":
        i += 1

    stop_markers = (
        SECTION_MARKERS["enhancements"]
        | SECTION_MARKERS["related_ccis"]
        | SECTION_MARKERS["cia"]
        | SECTION_MARKERS["overlays"]
        | SECTION_MARKERS["csf"]
        | SECTION_MARKERS["related_controls"]
    )

    while i < len(lines):
        ln = lines[i]
        if ln in stop_markers:
            break

        m = RELATED_CONTROL_LINE_RE.match(ln)
        if m:
            cid = m.group(1)
            desc = m.group(2).strip()

            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt in stop_markers:
                    break
                if RELATED_CONTROL_LINE_RE.match(nxt) or CCI_LINE_RE.match(nxt):
                    break
                desc = (desc + " " + nxt).strip() if desc else nxt
                j += 1

            items.append({"control_id": cid, "description": desc})
            i = j
            continue

        i += 1

    return items, i


def _parse_ccis(lines: List[str], start_idx: int) -> Tuple[List[Dict[str, str]], int]:
    items: List[Dict[str, str]] = []
    i = start_idx

    while i < len(lines) and lines[i] != "CCI Definition":
        i += 1
    if i < len(lines) and lines[i] == "CCI Definition":
        i += 1

    stop_markers = SECTION_MARKERS["related_controls"] | SECTION_MARKERS["enhancements"] | SECTION_MARKERS["cia"]

    while i < len(lines):
        ln = lines[i]
        if ln in stop_markers:
            break

        m = CCI_LINE_RE.match(ln)
        if m:
            cci = m.group(1)
            desc = m.group(2).strip()

            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt in stop_markers:
                    break
                if CCI_LINE_RE.match(nxt) or RELATED_CONTROL_LINE_RE.match(nxt):
                    break
                desc = (desc + " " + nxt).strip() if desc else nxt
                j += 1

            items.append({"cci_id": cci, "definition": desc})
            i = j
            continue

        i += 1

    return items, i


def parse_control_page(html: str, url: str) -> Tuple[ControlRecord, List[str]]:
    soup = BeautifulSoup(html, "lxml")
    lines = _clean_lines(soup.get_text(separator="\n"))

    title_idx, control_id, title = _find_first_control_title_line(lines)

    supplemental_idx = _index_of_marker(lines, SECTION_MARKERS["supplemental"])
    cia_idx = _index_of_marker(lines, SECTION_MARKERS["cia"])
    overlays_idx = _index_of_marker(lines, SECTION_MARKERS["overlays"])
    csf_idx = _index_of_marker(lines, SECTION_MARKERS["csf"])
    related_idx = _index_of_marker(lines, SECTION_MARKERS["related_controls"])
    enh_idx = _index_of_marker(lines, SECTION_MARKERS["enhancements"])
    ccis_idx = _index_of_marker(lines, SECTION_MARKERS["related_ccis"])

    statement_end = min([x for x in [supplemental_idx, cia_idx, related_idx, enh_idx, ccis_idx] if x != -1] or [len(lines)])
    statement_lines = lines[title_idx + 1 : statement_end]
    statement = "\n".join(statement_lines).strip()

    supplemental = ""
    if supplemental_idx != -1:
        start = supplemental_idx + 1
        end = min([x for x in [cia_idx, related_idx, enh_idx, ccis_idx] if x != -1 and x > supplemental_idx] or [len(lines)])
        supplemental = "\n".join(lines[start:end]).strip()

    cia: Dict[str, str] = {}
    if cia_idx != -1:
        i = cia_idx + 1
        while i < len(lines):
            ln = lines[i]
            if ln in SECTION_MARKERS["overlays"] or ln in SECTION_MARKERS["csf"] or ln in SECTION_MARKERS["related_controls"]:
                break
            m = CIA_LINE_RE.match(ln)
            if m:
                cia[m.group(1).lower()] = m.group(2).strip().lower()
            i += 1

    overlays: List[str] = []
    if overlays_idx != -1 and overlays_idx + 1 < len(lines):
        overlays = _parse_list_line(lines[overlays_idx + 1])

    csf_categories: List[str] = []
    if csf_idx != -1 and csf_idx + 1 < len(lines):
        csf_categories = _parse_list_line(lines[csf_idx + 1])

    related_controls: List[Dict[str, str]] = []
    cci_links: List[str] = []
    if related_idx != -1:
        related_controls, _ = _parse_related_controls(lines, related_idx + 1)

    enhancements: List[Dict[str, str]] = []
    if enh_idx != -1:
        enhancements, _ = _parse_related_controls(lines, enh_idx + 1)

    related_ccis: List[Dict[str, str]] = []
    if ccis_idx != -1:
        related_ccis, _ = _parse_ccis(lines, ccis_idx + 1)

    for a in soup.select('a[href^="/reference/controls/cci/"]'):
        href = (a.get("href") or "").strip()
        if CCI_URL_RE.match(href):
            cci_links.append(urljoin(BASE_URL, href))

    cci_links = sorted(set(cci_links))

    rec = ControlRecord(
        control_id=control_id,
        title=title,
        statement=statement,
        supplemental=supplemental,
        cia=cia,
        overlays=overlays,
        csf_categories=csf_categories,
        related_controls=related_controls,
        enhancements=enhancements,
        related_ccis=related_ccis,
        source_url=url,
    )
    return rec, cci_links


def parse_cci_page(html: str, url: str) -> CciRecord:
    soup = BeautifulSoup(html, "lxml")
    lines = _clean_lines(soup.get_text(separator="\n"))

    cci_id = ""
    for ln in lines:
        m = re.match(r"^(CCI-\d{6})$", ln)
        if m:
            cci_id = m.group(1)
            break

    def_idx = _index_of_marker(lines, {"CCI Definition", "Definition"})
    definition = ""
    if def_idx != -1 and def_idx + 1 < len(lines):
        definition, _ = _slice_section(lines, def_idx + 1, {"Status", "Master Assessment Datasheet", "Related Controls"})

    status = ""
    cci_type = ""
    for i, ln in enumerate(lines):
        if ln == "Status" and i + 1 < len(lines):
            status = lines[i + 1].strip()
        if ln.startswith("Type"):
            cci_type = ln.replace("Type", "").strip()

    ig_idx = _index_of_marker(lines, SECTION_MARKERS["implementation_guidance"])
    vp_idx = _index_of_marker(lines, SECTION_MARKERS["validation_procedures"])
    related_idx = _index_of_marker(lines, SECTION_MARKERS["related_controls"])

    implementation_guidance = ""
    validation_procedures = ""

    if ig_idx != -1:
        end = min([x for x in [vp_idx, related_idx] if x != -1 and x > ig_idx] or [len(lines)])
        implementation_guidance = "\n".join(lines[ig_idx + 1 : end]).strip()

    if vp_idx != -1:
        end = min([x for x in [related_idx] if x != -1 and x > vp_idx] or [len(lines)])
        validation_procedures = "\n".join(lines[vp_idx + 1 : end]).strip()

    related_controls: List[Dict[str, str]] = []
    if related_idx != -1:
        related_controls, _ = _parse_related_controls(lines, related_idx + 1)

    return CciRecord(
        cci_id=cci_id or "UNKNOWN",
        definition=definition,
        status=status,
        cci_type=cci_type,
        implementation_guidance=implementation_guidance,
        validation_procedures=validation_procedures,
        related_controls=related_controls,
        source_url=url,
    )


def write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_controls_csv(path: str, controls: List[ControlRecord]) -> None:
    fieldnames = [
        "control_id",
        "title",
        "confidentiality",
        "integrity",
        "availability",
        "overlays",
        "csf_categories",
        "source_url",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for c in controls:
            w.writerow(
                {
                    "control_id": c.control_id,
                    "title": c.title,
                    "confidentiality": c.cia.get("confidentiality", ""),
                    "integrity": c.cia.get("integrity", ""),
                    "availability": c.cia.get("availability", ""),
                    "overlays": ", ".join(c.overlays),
                    "csf_categories": ", ".join(c.csf_categories),
                    "source_url": c.source_url,
                }
            )


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape Xylok controls reference pages into JSON.")
    ap.add_argument("--out-dir", default="xylok_dump", help="Output folder")
    ap.add_argument("--delay", type=float, default=0.6, help="Delay between requests in seconds")
    ap.add_argument("--timeout", type=int, default=25, help="Request timeout in seconds")
    ap.add_argument("--retries", type=int, default=5, help="Retries per request")
    ap.add_argument("--start-page", type=int, default=1, help="Index page to start from")
    ap.add_argument("--max-pages", type=int, default=0, help="Stop after N index pages (0 = no limit)")
    ap.add_argument("--include-ccis", action="store_true", help="Scrape CCI detail pages too")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    errors_path = os.path.join(args.out_dir, "errors.log")

    fetcher = Fetcher(delay_s=args.delay, timeout_s=args.timeout, retries=args.retries, errors_path=errors_path)

    control_urls = scrape_control_links(fetcher, start_page=args.start_page, max_pages=args.max_pages)
    if not control_urls:
        raise SystemExit(f"No controls found. Check {errors_path}")

    controls: List[ControlRecord] = []
    cci_urls: Set[str] = set()

    for url in tqdm(control_urls, desc="Controls"):
        html = fetcher.get(url, soft_fail=True)
        if html is None:
            continue
        try:
            rec, cci_links = parse_control_page(html, url)
            controls.append(rec)
            for c in cci_links:
                cci_urls.add(c)
        except Exception as e:
            fetcher._log_error(f"Parse failed: {url} | {e}")

    write_json(os.path.join(args.out_dir, "controls.json"), [asdict(c) for c in controls])
    write_controls_csv(os.path.join(args.out_dir, "controls.csv"), controls)

    if args.include_ccis:
        ccis: List[CciRecord] = []
        for url in tqdm(sorted(cci_urls), desc="CCIs"):
            html = fetcher.get(url, soft_fail=True)
            if html is None:
                continue
            try:
                ccis.append(parse_cci_page(html, url))
            except Exception as e:
                fetcher._log_error(f"CCI parse failed: {url} | {e}")
        write_json(os.path.join(args.out_dir, "ccis.json"), [asdict(c) for c in ccis])

    print(f"Done. Controls: {len(controls)}")
    if args.include_ccis:
        print(f"CCI pages queued: {len(cci_urls)}")
    print(f"Errors log: {errors_path}")


if __name__ == "__main__":
    main()
