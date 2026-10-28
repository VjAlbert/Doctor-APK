"""Signing-certificate analysis."""

from __future__ import annotations

from datetime import datetime, timezone

from androguard.core.apk import APK

from ..models import Finding, Report, Severity

MODULE = "certificate"


def _fingerprint(cert, algorithm: str) -> str:
    return getattr(cert, f"{algorithm}_fingerprint").replace(" ", "").lower()


def _describe(cert) -> dict:
    validity = cert["tbs_certificate"]["validity"]
    return {
        "subject": cert.subject.human_friendly,
        "issuer": cert.issuer.human_friendly,
        "sha256": _fingerprint(cert, "sha256"),
        "sha1": _fingerprint(cert, "sha1"),
        "not_before": validity["not_before"].native.isoformat(),
        "not_after": validity["not_after"].native.isoformat(),
        "self_signed": cert.subject == cert.issuer,
    }


def _is_debug(info: dict) -> bool:
    return "CN=Android Debug" in info["subject"] or "Common Name: Android Debug" in info["subject"]


def analyze(apk: APK, report: Report) -> None:
    certs = apk.get_certificates()
    if not certs:
        report.add(Finding("certificate.unsigned", Severity.HIGH, MODULE))
        return

    now = datetime.now(timezone.utc)
    for cert in certs:
        info = _describe(cert)
        report.certificates.append(info)
        if _is_debug(info):
            report.add(Finding("certificate.debug", Severity.HIGH, MODULE, {"sha256": info["sha256"]}))
        elif info["self_signed"]:
            # Nearly every Android app is self-signed: informational only.
            report.add(Finding("certificate.self_signed", Severity.INFO, MODULE, {"sha256": info["sha256"]}))
        if cert["tbs_certificate"]["validity"]["not_after"].native < now:
            report.add(
                Finding(
                    "certificate.expired",
                    Severity.LOW,
                    MODULE,
                    {"not_after": info["not_after"]},
                )
            )

    if apk.is_signed_v1() and not (apk.is_signed_v2() or apk.is_signed_v3()):
        # v1-only signatures are exposed to the "Janus" flaw on Android 5.0-8.0.
        report.add(Finding("certificate.v1_only", Severity.LOW, MODULE))
