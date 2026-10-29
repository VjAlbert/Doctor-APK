"""Build engine/src/apkguard/data/fingerprints.json from an F-Droid `index-v1.json`.

Usage: python tools/import_fdroid.py path/to/index-v1.json

`signer` in the index is the SHA-256 of the APK signing certificate, the same value
`apkguard fingerprint` prints. The source is declared as store coverage: F-Droid may
re-sign apps, so a different key only says the APK came through another channel.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")
OUT = Path(__file__).resolve().parents[1] / "engine/src/apkguard/data/fingerprints.json"


def convert(index: dict) -> dict:
    packages: dict[str, list[dict]] = {}
    for package, versions in sorted(index.get("packages", {}).items()):
        signers = sorted({str(v.get("signer", "")).lower() for v in versions})
        entries = [{"sha256": s, "source": "fdroid"} for s in signers if HEX64.match(s)]
        if entries:
            packages[package] = entries
    return {
        "schema": 1,
        "generated_from": {"index": "f-droid.org index-v1",
                           "timestamp_ms": index.get("repo", {}).get("timestamp")},
        "sources": {"fdroid": {"name": "F-Droid", "coverage": "store"}},
        "packages": packages,
    }


def main(path: str) -> int:
    data = convert(json.loads(Path(path).read_text(encoding="utf-8")))
    OUT.write_text(json.dumps(data, indent=0, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(data['packages'])} packages -> {OUT} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else print(__doc__) or 2)
