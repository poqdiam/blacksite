#!/usr/bin/env python3
import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://app.xylok.io"

CONTROLS_INDEX = "/reference/controls/"
CCIS_INDEX = "/reference/controls/ccis/"
BENCHMARKS_INDEX = "/reference/benchmark/"

CONTROL_URL_RE = re.compile(r"^/reference/controls/control/([A-Z]{2,3}-\d+[A-Z0-9()]*)/?$")
CCI_URL_RE = re.compile(r"^/reference/controls/cci/(\d+)/?$")
BENCHMARK_URL_RE = re.compile(r"^/reference/benchmark/([^/]+)/?$")

PAGES_RE = re.compile(r"Pages\s*\(\s*\d+\s*/\s*(\d+)\s*\)", re.IGNORECASE)
CHECKS_COUNT_RE = re.compile(r"Checks\s*\(\s*(\d+)\s*\)", re.IGNORECASE)

CONTROL_ID_TITLE_RE = re.compile(r"^([A-Z]{2,3}-\d+[A-Z0-9()]*)\s*:\s*(.+)$")
CONTROL_IN_LINE_RE = re.compile(r"^([A-Z]{2,3}-\d+[A-Z0-9()]*)\s+(.*)$")
CIA_LINE_RE = re.compile(r"^(Confidentiality|Integrity|Availability)\s+(.+)$", re.IGNORECASE)
CCI_LINE_RE = re.compile(r"^(CCI-\d{6})\b\s*(.*)$", re.IGNORECASE)


def clean_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    out: List[str] = []
    last = None
    for ln in lines:
        if ln == last:
            continue
        out.append(ln)
        last = ln
    return out


def parse_total_pages(html: str) -> int:
    m = PAGES_RE.search(html)
    if not m:
        return 1
    try:
        return int(m.group(1))
    except Exception:
        return 1


class Fetcher:
    def __init__(self, delay_s: float, timeout_s: int, retries: int):
        self.delay_s = delay_s
        self.timeout_s = timeout_s
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "blacksite-xylok-scraper/2.0",
                "Accept": "text/html,application/xhtml+xml",
            }
        )

    def get(self, url: str, soft_fail: bool) -> Optional[str]:
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

        if soft_fail:
            return None
        raise RuntimeError(f"GET failed after {self.retries} retries: {url} | {last_err}")


def extract_links(html: str, href_re: re.Pattern) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    out: List[str] = []
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if href_re.match(href):
            out.append(urljoin(BASE_URL, href))
    return out


def scrape_index_links(fetcher: Fetcher, index_path: str, href_re: re.Pattern, errors: List[Dict]) -> List[str]:
    first_url = f"{BASE_URL}{index_path}?page=1"
    first_html = fetcher.get(first_url, soft_fail=False)
    total_pages = parse_total_pages(first_html)

    seen: Set[str] = set()
    all_links: List[str] = []

    for page in range(1, total_pages + 1):
        url = f"{BASE_URL}{index_path}?page={page}"
        html = fetcher.get(url, soft_fail=True)
        if html is None:
            errors.append({"type": "index_page_fetch_failed", "url": url})
            continue
        for full in extract_links(html, href_re):
            if full in seen:
                continue
            seen.add(full)
            all_links.append(full)

    return all_links


def idx_of(lines: List[str], target: str) -> int:
    for i, ln in enumerate(lines):
        if ln == target:
            return i
    return -1


def parse_list_value(lines: List[str], header: str) -> List[str]:
    i = idx_of(lines, header)
    if i == -1 or i + 1 >= len(lines):
        return []
    v = lines[i + 1].strip()
    if not v or v.lower() == "none":
        return []
    return [p.strip() for p in v.split(",") if p.strip()]


def parse_control_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "lxml")
    lines = clean_lines(soup.get_text(separator="\n"))

    control_id = ""
    title = ""
    title_idx = -1
    for i, ln in enumerate(lines):
        m = CONTROL_ID_TITLE_RE.match(ln)
        if m:
            control_id = m.group(1)
            title = m.group(2).strip()
            title_idx = i
            break
    if not control_id:
        raise ValueError("control id not found")

    supplemental_idx = idx_of(lines, "#### Supplemental")
    cia_idx = idx_of(lines, "CIA Levels")
    overlays_idx = idx_of(lines, "Overlays")
    csf_idx = idx_of(lines, "CSF Categories")
    related_idx = idx_of(lines, "Related Controls")
    enh_idx = idx_of(lines, "Enhancements")
    ccis_idx = idx_of(lines, "Related CCIs")

    cut_points = [x for x in [supplemental_idx, cia_idx, related_idx, enh_idx, ccis_idx] if x != -1]
    statement_end = min(cut_points) if cut_points else len(lines)
    statement = "\n".join(lines[title_idx + 1 : statement_end]).strip()

    supplemental = ""
    if supplemental_idx != -1:
        end_candidates = [x for x in [cia_idx, related_idx, enh_idx, ccis_idx] if x != -1 and x > supplemental_idx]
        end = min(end_candidates) if end_candidates else len(lines)
        supplemental = "\n".join(lines[supplemental_idx + 1 : end]).strip()

    cia: Dict[str, str] = {}
    if cia_idx != -1:
        i = cia_idx + 1
        while i < len(lines):
            ln = lines[i]
            if ln in {"Overlays", "CSF Categories", "Related Controls", "Enhancements", "Related CCIs"}:
                break
            m = CIA_LINE_RE.match(ln)
            if m:
                cia[m.group(1).lower()] = m.group(2).strip().lower()
            i += 1

    overlays = parse_list_value(lines, "Overlays")
    csf_categories = parse_list_value(lines, "CSF Categories")

    related_controls = []
    if related_idx != -1:
        related_controls = parse_control_table(lines, related_idx + 1, stop_headers={"Enhancements", "Related CCIs", "CIA Levels", "Overlays", "CSF Categories", "Related Controls"})

    enhancements = []
    if enh_idx != -1:
        enhancements = parse_control_table(lines, enh_idx + 1, stop_headers={"Related CCIs", "CIA Levels", "Overlays", "CSF Categories", "Related Controls", "Enhancements"})

    related_ccis = []
    if ccis_idx != -1:
        related_ccis = parse_cci_table(lines, ccis_idx + 1, stop_headers={"CIA Levels", "Overlays", "CSF Categories", "Related Controls", "Enhancements", "Related CCIs"})

    return {
        "control_id": control_id,
        "title": title,
        "statement": statement,
        "supplemental": supplemental,
        "cia": cia,
        "overlays": overlays,
        "csf_categories": csf_categories,
        "related_controls": related_controls,
        "enhancements": enhancements,
        "related_ccis": related_ccis,
        "source_url": url,
    }


def parse_control_table(lines: List[str], start_idx: int, stop_headers: Set[str]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    i = start_idx

    while i < len(lines) and lines[i] != "Control Description":
        if lines[i] in stop_headers:
            return items
        i += 1
    if i < len(lines) and lines[i] == "Control Description":
        i += 1

    while i < len(lines):
        ln = lines[i]
        if ln in stop_headers:
            break
        m = CONTROL_IN_LINE_RE.match(ln)
        if m:
            cid = m.group(1)
            desc = m.group(2).strip()
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt in stop_headers or nxt == "Control Description":
                    break
                if CONTROL_IN_LINE_RE.match(nxt) or CCI_LINE_RE.match(nxt):
                    break
                desc = (desc + " " + nxt).strip() if desc else nxt
                j += 1
            items.append({"control_id": cid, "description": desc})
            i = j
            continue
        i += 1

    return items


def parse_cci_table(lines: List[str], start_idx: int, stop_headers: Set[str]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    i = start_idx

    while i < len(lines) and lines[i] != "CCI Definition":
        if lines[i] in stop_headers:
            return items
        i += 1
    if i < len(lines) and lines[i] == "CCI Definition":
        i += 1

    while i < len(lines):
        ln = lines[i]
        if ln in stop_headers:
            break
        m = CCI_LINE_RE.match(ln)
        if m:
            cci_id = m.group(1).upper()
            definition = m.group(2).strip()
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt in stop_headers or nxt == "CCI Definition":
                    break
                if CCI_LINE_RE.match(nxt) or CONTROL_IN_LINE_RE.match(nxt):
                    break
                definition = (definition + " " + nxt).strip() if definition else nxt
                j += 1
            items.append({"cci_id": cci_id, "definition": definition})
            i = j
            continue
        i += 1

    return items


def parse_cci_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "lxml")
    lines = clean_lines(soup.get_text(separator="\n"))

    cci_id = ""
    for ln in lines:
        m = re.match(r"^(CCI-\d{6})$", ln, re.IGNORECASE)
        if m:
            cci_id = m.group(1).upper()
            break

    definition = ""
    def_idx = idx_of(lines, "Definition")
    if def_idx == -1:
        for i, ln in enumerate(lines):
            if ln.endswith(" Definition") and ln.startswith("CCI-"):
                def_idx = i
                break
    if def_idx != -1:
        buf: List[str] = []
        for ln in lines[def_idx + 1 :]:
            if ln in {"Status", "Master Assessment Datasheet", "Related Controls"}:
                break
            buf.append(ln)
        definition = "\n".join(buf).strip()

    status = ""
    cci_type = ""
    for i, ln in enumerate(lines):
        if ln == "Status" and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            status = nxt
            if "CheckType." in nxt:
                cci_type = nxt.split("CheckType.", 1)[-1].strip()
        if ln.startswith("Type") and "CheckType." in ln:
            cci_type = ln.split("CheckType.", 1)[-1].strip()

    ig = slice_after(lines, "Implementation Guidance", stop_headers={"Validation Procedures", "Related Controls"})
    vp = slice_after(lines, "Validation Procedures", stop_headers={"Related Controls"})

    related_controls = []
    rc_idx = idx_of(lines, "Related Controls")
    if rc_idx != -1:
        related_controls = parse_control_table(lines, rc_idx + 1, stop_headers={"Master Assessment Datasheet", "Related Controls"})

    return {
        "cci_id": cci_id or "UNKNOWN",
        "definition": definition,
        "status": status,
        "cci_type": cci_type,
        "implementation_guidance": ig,
        "validation_procedures": vp,
        "related_controls": related_controls,
        "source_url": url,
    }


def slice_after(lines: List[str], header: str, stop_headers: Set[str]) -> str:
    for i, ln in enumerate(lines):
        if ln == header or ln.endswith(header):
            buf: List[str] = []
            for nxt in lines[i + 1 :]:
                if nxt in stop_headers:
                    break
                buf.append(nxt)
            return "\n".join(buf).strip()
    return ""


def parse_benchmark_index_row(anchor) -> Optional[Tuple[str, str, str, str, str]]:
    href = (anchor.get("href") or "").strip()
    m = BENCHMARK_URL_RE.match(href)
    if not m:
        return None
    bench_id = m.group(1)
    row = anchor.parent
    parts = clean_lines(row.get_text(separator="\n"))
    if len(parts) < 4:
        return None
    short_title = parts[1]
    title = parts[2]
    latest = parts[3]
    return bench_id, short_title, title, latest, urljoin(BASE_URL, href)


def scrape_benchmarks(fetcher: Fetcher, errors: List[Dict]) -> List[Dict]:
    first_url = f"{BASE_URL}{BENCHMARKS_INDEX}?page=1"
    first_html = fetcher.get(first_url, soft_fail=False)
    total_pages = parse_total_pages(first_html)

    seen: Set[str] = set()
    benches: List[Dict] = []

    for page in range(1, total_pages + 1):
        url = f"{BASE_URL}{BENCHMARKS_INDEX}?page={page}"
        html = fetcher.get(url, soft_fail=True)
        if html is None:
            errors.append({"type": "benchmark_index_page_fetch_failed", "url": url})
            continue
        soup = BeautifulSoup(html, "lxml")
        for a in soup.select('a[href^="/reference/benchmark/"]'):
            parsed = parse_benchmark_index_row(a)
            if not parsed:
                continue
            bench_id, short_title, title, latest, bench_url = parsed
            if bench_id in seen:
                continue
            seen.add(bench_id)
            benches.append(
                {
                    "benchmark_id": bench_id,
                    "short_title": short_title,
                    "title": title,
                    "latest_version_date": latest,
                    "checks_count": 0,
                    "pages_total": 0,
                    "source_url": bench_url,
                }
            )

    for b in benches:
        html = fetcher.get(b["source_url"], soft_fail=True)
        if html is None:
            errors.append({"type": "benchmark_page_fetch_failed", "url": b["source_url"]})
            continue
        m = CHECKS_COUNT_RE.search(html)
        if m:
            try:
                b["checks_count"] = int(m.group(1))
            except Exception:
                pass
        b["pages_total"] = parse_total_pages(html)

    return benches


def overlay_url(name: str) -> str:
    return f"{BASE_URL}/reference/controls/overlay/{quote(name, safe='')}/"


def parse_overlay_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "lxml")
    lines = clean_lines(soup.get_text(separator="\n"))

    overlay_name = ""
    for ln in lines[:50]:
        if ln.startswith("Overlay "):
            overlay_name = ln.replace("Overlay ", "").strip()
            break
    if not overlay_name:
        overlay_name = url.split("/overlay/")[-1].strip("/")

    additions = parse_overlay_section(lines, "Additions", stop_headers={"Removals", "Modifications"})
    removals = parse_overlay_section(lines, "Removals", stop_headers={"Additions", "Modifications"})
    modifications = parse_overlay_section(lines, "Modifications", stop_headers={"Additions", "Removals"})

    return {
        "overlay_name": overlay_name,
        "additions": additions,
        "removals": removals,
        "modifications": modifications,
        "source_url": url,
    }


def parse_overlay_section(lines: List[str], header: str, stop_headers: Set[str]) -> List[Dict[str, str]]:
    start = idx_of(lines, header)
    if start == -1:
        return []
    i = start + 1

    while i < len(lines) and lines[i] != "Control Description":
        if lines[i] in stop_headers:
            return []
        i += 1
    if i < len(lines) and lines[i] == "Control Description":
        i += 1

    out: List[Dict[str, str]] = []
    while i < len(lines):
        ln = lines[i]
        if ln in stop_headers:
            break
        if ln in {"Control Description", "This overlay adds the following controls.", "This overlay removes the following controls."}:
            i += 1
            continue
        m = CONTROL_IN_LINE_RE.match(ln)
        if m:
            cid = m.group(1)
            desc = m.group(2).strip()
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt in stop_headers or nxt == "Control Description":
                    break
                if CONTROL_IN_LINE_RE.match(nxt):
                    break
                desc = (desc + " " + nxt).strip() if desc else nxt
                j += 1
            out.append({"control_id": cid, "description": desc})
            i = j
            continue
        i += 1

    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-file", required=True)
    ap.add_argument("--delay", type=float, default=0.7)
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--retries", type=int, default=5)
    args = ap.parse_args()

    out_dir = os.path.dirname(os.path.abspath(args.out_file))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    fetcher = Fetcher(delay_s=args.delay, timeout_s=args.timeout, retries=args.retries)
    errors: List[Dict] = []

    control_urls = scrape_index_links(fetcher, CONTROLS_INDEX, CONTROL_URL_RE, errors)
    cci_urls = scrape_index_links(fetcher, CCIS_INDEX, CCI_URL_RE, errors)

    controls: List[Dict] = []
    overlay_names: Set[str] = set()

    for url in control_urls:
        html = fetcher.get(url, soft_fail=True)
        if html is None:
            errors.append({"type": "control_page_fetch_failed", "url": url})
            continue
        try:
            rec = parse_control_page(html, url)
            controls.append(rec)
            for ov in rec.get("overlays", []):
                if ov:
                    overlay_names.add(ov)
        except Exception as e:
            errors.append({"type": "control_parse_failed", "url": url, "error": str(e)})

    ccis: List[Dict] = []
    for url in cci_urls:
        html = fetcher.get(url, soft_fail=True)
        if html is None:
            errors.append({"type": "cci_page_fetch_failed", "url": url})
            continue
        try:
            ccis.append(parse_cci_page(html, url))
        except Exception as e:
            errors.append({"type": "cci_parse_failed", "url": url, "error": str(e)})

    benchmarks = scrape_benchmarks(fetcher, errors)

    overlays: List[Dict] = []
    for name in sorted(overlay_names):
        url = overlay_url(name)
        html = fetcher.get(url, soft_fail=True)
        if html is None:
            errors.append({"type": "overlay_page_fetch_failed", "overlay": name, "url": url})
            continue
        try:
            overlays.append(parse_overlay_page(html, url))
        except Exception as e:
            errors.append({"type": "overlay_parse_failed", "overlay": name, "url": url, "error": str(e)})

    bundle = {
        "scraped_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "app.xylok.io",
        "counts": {
            "controls": len(controls),
            "ccis": len(ccis),
            "benchmarks": len(benchmarks),
            "overlays": len(overlays),
            "errors": len(errors),
        },
        "controls": controls,
        "ccis": ccis,
        "benchmarks": benchmarks,
        "overlays": overlays,
        "errors": errors,
    }

    with open(args.out_file, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    print("Saved")
    print(args.out_file)
    print("Counts")
    print(bundle["counts"])


if __name__ == "__main__":
    main()
