"""Scoring: category profiles, signal combinations, risk score and verdict."""

from __future__ import annotations

from ..models import Report
from . import combos, profiles, verdict


def score_report(report: Report, category_override: str | None = None) -> None:
    """Fill `report.category` and `report.verdict` and add synthetic findings."""
    if category_override and category_override in profiles.categories():
        category = {"id": category_override, "source": "user", "confidence": "high"}
    else:
        category = profiles.detect(report.app)
    report.category = category
    profiles.apply(report, category)
    combos.detect(report, category["id"])
    report.verdict = verdict.compute(report)
