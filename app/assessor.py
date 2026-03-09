"""
BLACKSITE — NIST 800-53r5 SSP assessment engine.

Scoring rubric (0–5 per control):
  +1  Control is present in the SSP with non-trivial text (>50 chars)
  +1  Implementation status is explicitly stated
  +1  Responsible role is identified
  +1  Narrative length is substantive (>150 chars)
  +1  Narrative addresses ≥40% of key terms extracted from the NIST control statement

Grades:
  COMPLETE      5       Proctor should still verify — AI is a baseline, not a verdict.
  PARTIAL       3–4
  INSUFFICIENT  1–2
  NOT_FOUND     0       Control not present in SSP at all.
  NA                    Control explicitly marked Not Applicable — excluded from scoring.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Optional, Dict, List

log = logging.getLogger("blacksite.assessor")

# Tokens to strip when extracting control keywords
_STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "be",
    "shall", "should", "must", "will", "that", "this", "with", "for",
    "as", "at", "by", "from", "on", "its", "their", "have", "has",
    "been", "not", "do", "does", "which", "where", "when", "how",
    "all", "each", "any", "other", "such", "these", "those", "also",
    "including", "organization", "system", "information", "security",
}


_MAX_KEYWORDS = 100   # cap to prevent runaway scoring on pathological inputs


def _keywords(text: str) -> list[str]:
    """
    Extract meaningful keywords from a NIST control statement.
    Returns unique lowercase tokens ≥4 chars, excluding stop words (capped at _MAX_KEYWORDS).
    """
    tokens = re.findall(r'[a-zA-Z]{4,}', text.lower())
    seen = set()
    out = []
    for t in tokens:
        if t not in _STOP_WORDS and t not in seen:
            seen.add(t)
            out.append(t)
            if len(out) >= _MAX_KEYWORDS:
                break
    return out


def assess_control(
    control_meta: dict,
    ssp_entry: Optional[dict],
) -> Dict[str, Any]:
    """
    Score a single control.

    Args:
        control_meta: Entry from the NIST catalog (id, title, family_id, statement, …)
        ssp_entry:    Parsed SSP block for this control, or None if not found.

    Returns dict with:
        grade, score, max_score, percentage, issues, elements_covered, narrative_excerpt
    """
    ctrl_id    = control_meta["id"]
    ctrl_title = control_meta.get("title", ctrl_id)
    statement  = control_meta.get("statement", "")

    # Control not present in SSP at all
    if ssp_entry is None:
        return {
            "control_id":        ctrl_id,
            "control_title":     ctrl_title,
            "control_family":    control_meta.get("family_id", "??"),
            "found_in_ssp":      False,
            "is_na":             False,
            "score":             0,
            "max_score":         5,
            "percentage":        0,
            "grade":             "NOT_FOUND",
            "issues":            ["Control not referenced in SSP"],
            "elements_covered":  "0/0",
            "narrative_excerpt": "",
            "implementation_status": None,
            "responsible_role":      None,
        }

    # Control explicitly marked Not Applicable
    if ssp_entry.get("is_na") or ssp_entry.get("implementation_status") == "Not Applicable":
        return {
            "control_id":        ctrl_id,
            "control_title":     ctrl_title,
            "control_family":    control_meta.get("family_id", "??"),
            "found_in_ssp":      True,
            "is_na":             True,
            "score":             0,
            "max_score":         5,
            "percentage":        0,
            "grade":             "NA",
            "issues":            [],
            "elements_covered":  "N/A",
            "narrative_excerpt": ssp_entry.get("narrative", "")[:200],
            "implementation_status": "Not Applicable",
            "responsible_role":      ssp_entry.get("responsible_role"),
        }

    narrative = ssp_entry.get("narrative", "").strip()
    status    = ssp_entry.get("implementation_status")
    role      = ssp_entry.get("responsible_role")
    score     = 0
    issues    = []

    # ── Criterion 1: Non-trivial narrative present ─────────────────────────────
    if len(narrative) >= 50:
        score += 1
    else:
        issues.append("Narrative is absent or too brief (<50 chars)")

    # ── Criterion 2: Implementation status ────────────────────────────────────
    if status:
        score += 1
    else:
        issues.append("Implementation status not explicitly stated")

    # ── Criterion 3: Responsible role ─────────────────────────────────────────
    if role:
        score += 1
    else:
        issues.append("Responsible role not identified")

    # ── Criterion 4: Substantive narrative ────────────────────────────────────
    if len(narrative) >= 150:
        score += 1
    else:
        issues.append("Narrative lacks depth (<150 chars)")

    # ── Criterion 5: Key element coverage ─────────────────────────────────────
    control_kws = _keywords(statement)
    if control_kws:
        narrative_lower = narrative.lower()
        matched = [kw for kw in control_kws if kw in narrative_lower]
        coverage = len(matched) / len(control_kws)
        elements_covered = f"{len(matched)}/{len(control_kws)}"
        if coverage >= 0.40:
            score += 1
        else:
            issues.append(
                f"Narrative covers only {len(matched)}/{len(control_kws)} "
                f"key control elements ({coverage:.0%})"
            )
    else:
        # No keywords to check (very short control statement) — give benefit of doubt
        score += 1
        elements_covered = "N/A"

    # ── Grade ──────────────────────────────────────────────────────────────────
    if score == 5:
        grade = "COMPLETE"
    elif score >= 3:
        grade = "PARTIAL"
    elif score >= 1:
        grade = "INSUFFICIENT"
    else:
        grade = "NOT_FOUND"

    return {
        "control_id":            ctrl_id,
        "control_title":         ctrl_title,
        "control_family":        control_meta.get("family_id", "??"),
        "found_in_ssp":          True,
        "is_na":                 False,
        "score":                 score,
        "max_score":             5,
        "percentage":            round(score / 5 * 100),
        "grade":                 grade,
        "issues":                issues,
        "elements_covered":      elements_covered,
        "narrative_excerpt":     narrative[:500],
        "implementation_status": status,
        "responsible_role":      role,
    }


def run_assessment(
    catalog: dict,
    parsed_ssp: dict,
    include_not_found: bool = True,
) -> Dict[str, Any]:
    """
    Run the full assessment of an SSP against the NIST catalog.

    Args:
        catalog:           Flat dict of NIST controls keyed by control ID.
        parsed_ssp:        Output of parser.parse_ssp().
        include_not_found: If True, flag every catalog control not in the SSP.

    Returns a summary dict with a 'results' list and aggregate scores.
    """
    from collections import defaultdict

    ssp_controls  = parsed_ssp.get("controls", {})
    results       = []
    grades_count  = {"COMPLETE": 0, "PARTIAL": 0, "INSUFFICIENT": 0, "NOT_FOUND": 0, "NA": 0}
    family_stats: Dict[str, Dict] = defaultdict(lambda: {
        "COMPLETE": 0, "PARTIAL": 0, "INSUFFICIENT": 0, "NOT_FOUND": 0, "NA": 0, "total": 0
    })

    # Assess controls that appear in the SSP (matched against catalog)
    assessed_ids: set = set()
    for ctrl_id, ssp_entry in ssp_controls.items():
        meta = catalog.get(ctrl_id)
        if meta is None:
            log.debug("SSP references %s — not in NIST catalog (may be enhancement label).", ctrl_id)
            continue
        result = assess_control(meta, ssp_entry)
        results.append(result)
        grades_count[result["grade"]] = grades_count.get(result["grade"], 0) + 1
        family_stats[result["control_family"]][result["grade"]] += 1
        family_stats[result["control_family"]]["total"] += 1
        assessed_ids.add(ctrl_id)

    # Flag catalog controls missing entirely from SSP
    if include_not_found:
        for ctrl_id, meta in catalog.items():
            if ctrl_id not in assessed_ids:
                result = assess_control(meta, None)
                results.append(result)
                grades_count["NOT_FOUND"] += 1
                family_stats[result["control_family"]]["NOT_FOUND"] += 1
                family_stats[result["control_family"]]["total"] += 1

    # Sort: INSUFFICIENT first, then PARTIAL, COMPLETE, NA, NOT_FOUND
    _order = {"INSUFFICIENT": 0, "PARTIAL": 1, "COMPLETE": 2, "NA": 3, "NOT_FOUND": 4}
    def _ctrl_sort_key(cid: str) -> tuple:
        m = re.match(r'^([a-z]+)-(\d+)(?:\.(\d+))?$', cid.lower())
        return (m.group(1), int(m.group(2)), int(m.group(3) or 0)) if m else (cid, 0, 0)
    results.sort(key=lambda r: (_order.get(r["grade"], 5), _ctrl_sort_key(r["control_id"])))

    # Compute overall SSP score — exclude NOT_FOUND and NA controls
    scored = [r for r in results if r["grade"] not in ("NOT_FOUND", "NA")]
    if scored:
        total_pts = sum(r["score"]     for r in scored)
        total_max = sum(r["max_score"] for r in scored)
        ssp_score = round(total_pts / total_max * 100, 1) if total_max else 0.0
    else:
        ssp_score = 0.0

    return {
        "results":               results,
        "total_controls":        len(results),
        "controls_in_ssp":       len(assessed_ids),
        "controls_complete":     grades_count["COMPLETE"],
        "controls_partial":      grades_count["PARTIAL"],
        "controls_insufficient": grades_count["INSUFFICIENT"],
        "controls_not_found":    grades_count["NOT_FOUND"],
        "controls_na":           grades_count["NA"],
        "family_stats":          dict(family_stats),
        "ssp_score":             ssp_score,
    }


def compute_combined_score(ssp_score: float, quiz_score: float, config: dict) -> float:
    """Compute the weighted combined score."""
    w_ssp  = config.get("scoring", {}).get("ssp_weight",  0.70)
    w_quiz = config.get("scoring", {}).get("quiz_weight", 0.30)
    return round(ssp_score * w_ssp + quiz_score * w_quiz, 1)


def is_allstar(combined_score: float, quiz_score: float, config: dict) -> bool:
    min_combined = config.get("scoring", {}).get("allstar_combined_min", 80)
    min_quiz     = config.get("scoring", {}).get("allstar_quiz_min",     80)
    return combined_score >= min_combined and quiz_score >= min_quiz
