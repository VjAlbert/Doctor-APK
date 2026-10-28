"""Authenticity: does the signing key match the one published for this package?

This is the main defence against repackaged apps: same package name and look,
different signer. What a difference *means* depends on the fingerprint's
coverage (see data/fingerprints.py): against a developer key it is decisive,
against a store key it only says the APK came through another channel.
"""

from __future__ import annotations

from ..data.fingerprints import Database, load_database
from ..models import Finding, Report, Severity

MODULE = "authenticity"


def analyze(report: Report, db: Database | None = None) -> None:
    db = db or load_database()
    package = report.app.get("package") or ""
    signers = {c["sha256"] for c in report.certificates}
    auth = {"package": package, "status": "unknown", "sources": [], "matched": None}
    report.authenticity = auth

    if not signers:
        auth["status"] = "unsigned"  # certificate.unsigned already covers it
        return
    entries = db.lookup(package)
    if not entries:
        report.add(Finding("authenticity.unknown", Severity.INFO, MODULE, {"package": package}))
        return

    matched = [e for e in entries if e.sha256 in signers]
    names = sorted({db.display_name(e.source) for e in (matched or entries)})
    auth["sources"] = names
    if matched:
        auth.update(status="match", matched=matched[0].sha256)
        report.add(Finding("authenticity.match", Severity.INFO, MODULE, {"sources": names}))
    elif any(db.coverage(e.source) == "developer" for e in entries):
        auth["status"] = "mismatch"
        report.add(Finding("authenticity.mismatch", Severity.HIGH, MODULE,
                           {"package": package, "sources": names}))
    else:
        auth["status"] = "other_channel"
        report.add(Finding("authenticity.other_channel", Severity.MEDIUM, MODULE,
                           {"package": package, "sources": names}))
