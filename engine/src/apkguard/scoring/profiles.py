"""App-category profiles: is this permission normal for this kind of app?

A flashlight asking for SMS access is a much stronger signal than a messenger
asking for the same thing, so the same permission is re-weighted by category.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources

from ..models import Finding, Report, Severity

UNKNOWN = "unknown"
MIN_SUBSTRING_KEYWORD = 5  # shorter keywords must match a whole token
MIN_ANOMALOUS_FOR_MISMATCH = 2


@lru_cache(maxsize=1)
def categories() -> dict[str, dict]:
    path = resources.files("apkguard") / "rules" / "profiles.json"
    return json.loads(path.read_text(encoding="utf-8"))["categories"]


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def _hits(tokens: list[str], keywords: list[str]) -> int:
    count = 0
    for kw in keywords:
        kw = kw.replace(" ", "")
        for tok in tokens:
            if tok == kw or (len(kw) >= MIN_SUBSTRING_KEYWORD and kw in tok):
                count += 1
                break
    return count


def detect(app: dict) -> dict:
    """Guess the category from package name and label; `unknown` if no match."""
    pkg_tokens = _tokens(app.get("package") or "")
    label_tokens = _tokens(app.get("name") or "")
    best, best_score = None, 0
    for cid, prof in categories().items():
        in_label = _hits(label_tokens, prof["keywords"])
        in_pkg = _hits(pkg_tokens, prof["keywords"])
        score = 2 * in_label + in_pkg
        if score > best_score:
            best, best_score = (cid, "high" if in_label and in_pkg else "medium"), score
    if best is None:
        return {"id": UNKNOWN, "source": "auto", "confidence": "none"}
    return {"id": best[0], "source": "auto", "confidence": best[1]}


def _raise(severity: Severity) -> Severity:
    return Severity(min(severity + 1, Severity.HIGH))


def apply(report: Report, category: dict) -> None:
    """Re-weight permission findings and flag permissions out of line.

    A category is only a guess from the app's own name, which a malicious app
    controls. Out-of-place permissions therefore always raise severity, but
    expected ones are only downgraded when the match is strong (name and label
    both match) or the user chose the category.
    """
    profile = categories().get(category["id"])
    if profile is None:
        return
    trusted = category.get("confidence") == "high"
    expected, unusual = set(profile["expected"]), set(profile["unusual"])
    anomalous: list[str] = []
    for finding in report.findings:
        if finding.id != "manifest.permission":
            continue
        perm = finding.params["permission"]
        finding.params["category"] = category["id"]
        if perm in expected and trusted:
            finding.severity = Severity.INFO
            finding.params["profile"] = "expected"
        elif perm in expected:
            finding.params["profile"] = "neutral"
        elif perm in unusual or finding.severity < Severity.MEDIUM:
            finding.params["profile"] = "unusual" if perm in unusual else "neutral"
        else:
            finding.severity = _raise(finding.severity)
            finding.params["profile"] = "anomalous"
            anomalous.append(perm)
    if len(anomalous) >= MIN_ANOMALOUS_FOR_MISMATCH:
        report.add(Finding("profile.mismatch", Severity.HIGH, "scoring",
                           {"category": category["id"], "permissions": sorted(anomalous)}))
