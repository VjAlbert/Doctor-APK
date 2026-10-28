"""Writes the build identifier into the engine, so every build can say which commit it came from.

Run before installing the engine:  python packaging/stamp_build.py [id]
The id defaults to $GITHUB_SHA, then `git rev-parse HEAD`; only its first 7 characters are kept.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "engine" / "src" / "apkguard" / "_build.py"


def current_id() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "dev"


def main() -> int:
    build = current_id()[:7] or "dev"
    TARGET.write_text(
        '"""Build identifier. Overwritten by packaging/stamp_build.py in CI with the commit being built."""\n\n'
        f'BUILD = "{build}"\n', encoding="utf-8")
    print(f"stamped build {build}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
