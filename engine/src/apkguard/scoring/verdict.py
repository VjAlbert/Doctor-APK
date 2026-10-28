"""Risk score and final verdict.

Weights and thresholds are provisional: they are calibrated against real
benign/malicious corpora in the validation milestone.
"""

from __future__ import annotations

import math

from ..models import Finding, Report, Severity

WEIGHTS = {
    Severity.INFO: 0,
    Severity.LOW: 2,
    Severity.MEDIUM: 8,
    Severity.HIGH: 22,
    Severity.CRITICAL: 60,
}
SATURATION = 40  # score = 100 * (1 - exp(-total / SATURATION))
CAUTION_AT = 25
REFUSE_AT = 60
CRITICAL_FLOOR = 85
MAX_REASONS = 3


def _score(findings: list[Finding]) -> int:
    total = sum(WEIGHTS[f.severity] for f in findings)
    score = round(100 * (1 - math.exp(-total / SATURATION)))
    if any(f.severity == Severity.CRITICAL for f in findings):
        score = max(score, CRITICAL_FLOOR)
    return score


def _reasons(findings: list[Finding]) -> list[Finding]:
    """Most severe findings first; combos and profile findings lead their tier."""
    def rank(f: Finding):
        synthetic = f.id.startswith(("combo.", "profile."))
        return (-f.severity, not synthetic, f.id)

    chosen, seen = [], set()
    for f in sorted((f for f in findings if f.severity >= Severity.LOW), key=rank):
        key = (f.id, f.params.get("permission"))
        if key in seen:
            continue
        seen.add(key)
        chosen.append(f)
        if len(chosen) == MAX_REASONS:
            break
    return chosen


def compute(report: Report) -> dict:
    score = _score(report.findings)
    worst = max((f.severity for f in report.findings), default=Severity.INFO)
    if worst == Severity.CRITICAL or score >= REFUSE_AT:
        verdict = "do_not_install"
        level = "critical" if worst == Severity.CRITICAL else "high"
    elif score >= CAUTION_AT:
        verdict, level = "caution", "medium"
    else:
        verdict, level = "no_known_threats", "low"
    counts = {s.label: 0 for s in Severity}
    for f in report.findings:
        counts[f.severity.label] += 1
    return {
        "id": verdict,
        "level": level,
        "score": score,
        "counts": counts,
        "reasons": [f.to_dict() for f in _reasons(report.findings)],
    }
