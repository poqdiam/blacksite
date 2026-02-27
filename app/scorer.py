"""
BLACKSITE — Rule-based assessment analyzer (NIST SA-11).

No LLM. Deterministic algorithms for anomaly detection, coverage gaps,
and quality scoring. Results used by /api/review/{assessment_id}.
"""
from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from typing import List


# NIST 800-53r5 Priority 1 controls (highest criticality)
_P1_CONTROLS = {
    "ac-1", "ac-2", "ac-3", "ac-6", "ac-17", "ac-19",
    "at-2", "at-3",
    "au-2", "au-6", "au-9", "au-11",
    "ca-2", "ca-3", "ca-5", "ca-6", "ca-7", "ca-9",
    "cm-2", "cm-6", "cm-7", "cm-8",
    "cp-2", "cp-9", "cp-10",
    "ia-2", "ia-4", "ia-5", "ia-8",
    "ir-4", "ir-5", "ir-6",
    "ma-4",
    "mp-6",
    "pe-2", "pe-3", "pe-6", "pe-13",
    "pl-2", "pl-8",
    "ps-3", "ps-4", "ps-5", "ps-7",
    "ra-3", "ra-5",
    "sa-8", "sa-9",
    "sc-5", "sc-7", "sc-8", "sc-13", "sc-28",
    "si-2", "si-3", "si-4", "si-7", "si-10",
}


def _similarity(a: str, b: str) -> float:
    """Compute normalized similarity ratio between two text strings."""
    return SequenceMatcher(None, a[:500], b[:500]).ratio()


def compute_risk_level(score: int) -> str:
    """Map risk score (likelihood × impact, 1-25) to level label."""
    if score <= 4:
        return "Low"
    elif score <= 9:
        return "Moderate"
    elif score <= 14:
        return "High"
    else:
        return "Critical"


def compute_overall_impact(c: str, i: str, a: str) -> str:
    """FIPS 199 overall impact = max(C, I, A)."""
    order = {"Low": 1, "Moderate": 2, "High": 3}
    vals = [order.get(x, 0) for x in (c, i, a) if x]
    if not vals:
        return "Low"
    max_val = max(vals)
    return {1: "Low", 2: "Moderate", 3: "High"}.get(max_val, "Low")


def analyze_assessment(assessment, controls: list) -> dict:
    """
    Return anomaly flags, coverage gaps, and quality signals.

    Checks performed:
      1. Score anomaly: long narrative with very low score (possible missed keywords)
      2. Boilerplate detection: near-identical narratives across controls
      3. Family coverage gap: families where >50% controls are NOT_FOUND
      4. High-priority incomplete: P1 controls graded INSUFFICIENT or NOT_FOUND
      5. Quick wins: INSUFFICIENT controls needing only 1 more element for PARTIAL
    """
    narratives: list[tuple[str, str]] = []
    family_grades: dict[str, list[str]] = defaultdict(list)
    p1_failures: list[dict] = []
    quick_wins: list[dict] = []
    anomalies: list[dict] = []

    for c in controls:
        grade     = (c.ai_grade or "NOT_FOUND").upper()
        narrative = (c.narrative_excerpt or "").strip()
        ctrl_id   = (c.control_id or "").lower()
        family    = (c.control_family or "??").upper()

        family_grades[family].append(grade)

        # 1. Score anomaly: long narrative but low score
        if (len(narrative) > 200
                and c.ai_score <= 1
                and grade in ("INSUFFICIENT", "NOT_FOUND")):
            anomalies.append({
                "type":       "score_anomaly",
                "control_id": ctrl_id,
                "message":    (
                    f"Long narrative ({len(narrative)} chars) but graded {grade} — "
                    "possible keyword mismatch or off-topic content"
                ),
            })

        # Collect for boilerplate check
        if narrative:
            narratives.append((ctrl_id, narrative))

        # 4. High-priority P1 failures
        if ctrl_id in _P1_CONTROLS and grade in ("INSUFFICIENT", "NOT_FOUND"):
            p1_failures.append({
                "control_id": ctrl_id,
                "grade":      grade,
                "title":      c.control_title or ctrl_id.upper(),
            })

        # 5. Quick wins: one element away from PARTIAL
        if grade == "INSUFFICIENT" and c.ai_elements_covered:
            try:
                covered, total = (int(x) for x in c.ai_elements_covered.split("/"))
                if total > 0 and (total - covered) <= 1:
                    quick_wins.append({
                        "control_id":       ctrl_id,
                        "elements_covered": c.ai_elements_covered,
                        "message": (
                            f"Only {total - covered} element(s) missing to reach PARTIAL"
                        ),
                    })
            except (ValueError, IndexError):
                pass

    # 2. Boilerplate detection: narratives >80% similar to another control
    boilerplate_ids: set[str] = set()
    for i, (id_a, text_a) in enumerate(narratives):
        for id_b, text_b in narratives[i + 1:]:
            if _similarity(text_a, text_b) > 0.80:
                boilerplate_ids.add(id_a)
                boilerplate_ids.add(id_b)

    for ctrl_id in boilerplate_ids:
        anomalies.append({
            "type":       "boilerplate",
            "control_id": ctrl_id,
            "message":    "Narrative appears copy-pasted from another control",
        })

    # 3. Family coverage gaps: >50% NOT_FOUND
    coverage_gaps: list[dict] = []
    for family, grades in family_grades.items():
        not_found_ct = grades.count("NOT_FOUND")
        if not_found_ct / len(grades) > 0.50:
            coverage_gaps.append({
                "family":    family,
                "not_found": not_found_ct,
                "total":     len(grades),
                "pct":       round(not_found_ct / len(grades) * 100),
            })

    # Quality score (0-100): proportion of COMPLETE + 0.5×PARTIAL
    total = len(controls)
    if total == 0:
        quality_score = 0
    else:
        complete_ct = sum(1 for c in controls if (c.ai_grade or "").upper() == "COMPLETE")
        partial_ct  = sum(1 for c in controls if (c.ai_grade or "").upper() == "PARTIAL")
        quality_score = int(round((complete_ct + partial_ct * 0.5) / total * 100))

    return {
        "anomalies":               anomalies,
        "coverage_gaps":           coverage_gaps,
        "high_priority_incomplete": p1_failures,
        "quick_wins":              quick_wins,
        "quality_score":           quality_score,
    }
