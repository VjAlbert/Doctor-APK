"""Runs every analyzer in order and streams progress events."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from androguard.core.apk import APK

from . import version_info
from .analyzers import authenticity, certificate, dex, manifest, payloads, reputation, strings, yara_scan
from .data.fingerprints import Database
from .ingest import IngestError, ingest
from .models import Report
from .scoring import score_report

ProgressCallback = Callable[[dict[str, Any]], None]

STEPS = ("ingest", "manifest", "certificate", "authenticity", "dex", "strings", "payloads", "yara", "reputation", "scoring")


def analyze_apk(
    path: str | os.PathLike[str],
    progress: ProgressCallback | None = None,
    category: str | None = None,
    fingerprints: Database | None = None,
    virustotal_key: str | None = None,
    reputation_fetch: reputation.Fetch | None = None,
) -> Report:
    """Analyze `path`. Raises IngestError when the input is unusable."""

    def emit(step: str, state: str) -> None:
        if progress:
            progress({"event": "progress", "module": step, "state": state,
                      "index": STEPS.index(step) + 1, "total": len(STEPS)})

    report = Report(engine=version_info())

    emit("ingest", "start")
    result = ingest(path)
    try:
        report.file = {
            "name": result.original.name,
            "size": result.size,
            "kind": result.kind,
            "md5": result.md5,
            "sha1": result.sha1,
            "sha256": result.sha256,
        }
        for finding in result.findings:
            report.add(finding)
        emit("ingest", "done")

        try:
            apk = APK(str(result.apk_path))
        except Exception as exc:  # androguard raises many exception types
            raise IngestError("not_apk", detail=str(exc)) from exc

        emit("manifest", "start")
        manifest.analyze(apk, report)
        emit("manifest", "done")

        emit("certificate", "start")
        certificate.analyze(apk, report)
        emit("certificate", "done")

        emit("authenticity", "start")
        authenticity.analyze(report, fingerprints)
        emit("authenticity", "done")

        emit("dex", "start")
        facts = dex.load_facts(apk)
        dex.analyze(facts, report)
        emit("dex", "done")

        emit("strings", "start")
        strings.analyze(facts, report)
        emit("strings", "done")

        emit("payloads", "start")
        payloads.analyze(result.apk_path, report)
        emit("payloads", "done")

        emit("yara", "start")
        yara_scan.analyze(facts, report)
        emit("yara", "done")

        emit("reputation", "start")
        reputation.analyze(report, virustotal_key, reputation_fetch or reputation._http_get)
        emit("reputation", "done")

        emit("scoring", "start")
        score_report(report, category)
        emit("scoring", "done")
    finally:
        result.cleanup()
    return report
