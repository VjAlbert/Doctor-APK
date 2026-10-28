"""Command line interface.

The desktop app launches this as a sidecar and reads stdout, one JSON object
per line: progress events first, then a final `report` (or `error`) event.
"""

from __future__ import annotations

import argparse
import json
import sys

from loguru import logger

from . import __version__
from .i18n import SUPPORTED, render_finding, render_verdict, t
from .ingest import IngestError
from .models import Finding, Severity
from .pipeline import analyze_apk
from .scoring.profiles import categories


def _write(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apkguard", description="Static APK analyzer")
    parser.add_argument("--version", action="version", version=f"apkguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="analyze an APK file")
    analyze.add_argument("apk")
    analyze.add_argument("--lang", choices=SUPPORTED, default="en")
    analyze.add_argument("--category", choices=["auto", *categories()], default="auto",
                         help="app category used to judge permissions (default: guess it)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logger.remove()  # androguard logs to stderr via loguru; keep stdout/stderr clean
    try:
        report = analyze_apk(args.apk, progress=_write,
                             category=None if args.category == "auto" else args.category)
    except IngestError as exc:
        _write({"event": "error", "code": exc.code,
                "message": t(f"error.{exc.code}", args.lang, **exc.params)})
        return 2

    data = report.to_dict()
    for entry, finding in zip(data["findings"], sorted(
            report.findings, key=lambda f: (-f.severity, f.id))):
        entry["text"] = render_finding(finding, args.lang)
    reasons = [Finding(r["id"], Severity[r["severity"].upper()], r["module"], r["params"])
               for r in data["verdict"]["reasons"]]
    for entry, finding in zip(data["verdict"]["reasons"], reasons):
        entry["text"] = render_finding(finding, args.lang)
    data["verdict"]["text"] = render_verdict(data["verdict"], data["category"], args.lang)
    _write({"event": "report", "lang": args.lang, "report": data})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
