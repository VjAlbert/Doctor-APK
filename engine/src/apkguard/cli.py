"""Command line interface.

The desktop app launches this as a sidecar and reads stdout, one JSON object
per line: progress events first, then a final `report` (or `error`) event.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from loguru import logger

from . import BUILD, __version__
from .i18n import SUPPORTED, render_authenticity, render_finding, render_verdict, t
from .ingest import IngestError
from .models import Finding, Severity
from .pipeline import analyze_apk
from .scoring.profiles import categories


def _write(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apkguard", description="Static APK analyzer")
    parser.add_argument("--version", action="version", version=f"apkguard {__version__} (build {BUILD})")
    sub = parser.add_subparsers(dest="command", required=True)
    fp = sub.add_parser("fingerprint", help="print the signing fingerprints of an APK")
    fp.add_argument("apk")
    analyze = sub.add_parser("analyze", help="analyze an APK file")
    analyze.add_argument("apk")
    analyze.add_argument("--lang", choices=SUPPORTED, default="en")
    serve = sub.add_parser("serve", help="run the local bridge used by the desktop UI")
    serve.add_argument("--port", type=int, default=8765)
    analyze.add_argument("--virustotal", action="store_true",
                         help="look up the file hash on VirusTotal (key from $APKGUARD_VT_KEY)")
    analyze.add_argument("--category", choices=["auto", *categories()], default="auto",
                         help="app category used to judge permissions (default: guess it)")
    return parser


def _fingerprint(path: str) -> int:
    from androguard.core.apk import APK

    from .analyzers.certificate import _describe
    from .ingest import ingest

    try:
        result = ingest(path)
    except IngestError as exc:
        _write({"event": "error", "code": exc.code, "message": t(f"error.{exc.code}", "en", **exc.params)})
        return 2
    try:
        apk = APK(str(result.apk_path))
        _write({"package": apk.get_package(), "version_name": apk.get_androidversion_name(),
                "sha256": [_describe(c)["sha256"] for c in apk.get_certificates()]})
    finally:
        result.cleanup()
    return 0


def build_report_event(report, lang: str) -> dict:
    """The final `report` event: report data plus texts rendered in `lang`."""
    data = report.to_dict()
    for entry, finding in zip(data["findings"], sorted(
            report.findings, key=lambda f: (-f.severity, f.id))):
        entry["text"] = render_finding(finding, lang)
    reasons = [Finding(r["id"], Severity[r["severity"].upper()], r["module"], r["params"])
               for r in data["verdict"]["reasons"]]
    for entry, finding in zip(data["verdict"]["reasons"], reasons):
        entry["text"] = render_finding(finding, lang)
    data["authenticity"]["label"] = render_authenticity(data["authenticity"], lang)
    data["verdict"]["text"] = render_verdict(data["verdict"], data["category"], lang)
    return {"event": "report", "lang": lang, "report": data}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logger.remove()  # androguard logs to stderr via loguru; keep stdout/stderr clean
    if args.command == "fingerprint":
        return _fingerprint(args.apk)
    if args.command == "serve":
        from .server import serve
        serve(args.port)
        return 0
    try:
        report = analyze_apk(args.apk, progress=_write,
                             category=None if args.category == "auto" else args.category,
                             virustotal_key=os.environ.get("APKGUARD_VT_KEY") if args.virustotal else None)
    except IngestError as exc:
        _write({"event": "error", "code": exc.code,
                "message": t(f"error.{exc.code}", args.lang, **exc.params)})
        return 2

    _write(build_report_event(report, args.lang))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
