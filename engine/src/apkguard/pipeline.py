"""Runs every analyzer in order and streams progress events."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from androguard.core.apk import APK

from .analyzers import certificate, manifest
from .ingest import IngestError, ingest
from .models import Report

ProgressCallback = Callable[[dict[str, Any]], None]

STEPS = ("ingest", "manifest", "certificate")


def analyze_apk(
    path: str | os.PathLike[str], progress: ProgressCallback | None = None
) -> Report:
    """Analyze `path`. Raises IngestError when the input is unusable."""

    def emit(step: str, state: str) -> None:
        if progress:
            progress({"event": "progress", "module": step, "state": state,
                      "index": STEPS.index(step) + 1, "total": len(STEPS)})

    report = Report()

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
    finally:
        result.cleanup()
    return report
