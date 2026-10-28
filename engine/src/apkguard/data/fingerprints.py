"""Database of known signing-certificate fingerprints per package name.

Two files are merged at load time, both under `data/`:

* `fingerprints.json` - generated from public sources (see tools/).
* `curated_fingerprints.json` - entries added by hand, each verified against
  an official APK (use `apkguard fingerprint <apk>` to read one).

Format::

    {"schema": 1,
     "sources": {"fdroid": {"name": "F-Droid", "coverage": "store"}},
     "packages": {"org.example.app": [{"sha256": "<64 hex>", "source": "fdroid"}]}}

`coverage` says what a fingerprint proves. "store" means the key belongs to the
distribution channel, which may re-sign apps: a different key then only shows
the APK came from elsewhere. "developer" means it is the developer's own key,
so a different key under the same package name means the app was altered.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

SCHEMA = 1
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FILES = ("fingerprints.json", "curated_fingerprints.json")
DEFAULT_COVERAGE = "store"  # the conservative reading when a source is undeclared


@dataclass(frozen=True)
class Entry:
    sha256: str
    source: str


@dataclass
class Database:
    sources: dict[str, dict] = field(default_factory=dict)
    packages: dict[str, list[Entry]] = field(default_factory=dict)
    skipped: int = 0

    def lookup(self, package: str) -> list[Entry]:
        return self.packages.get(package, [])

    def coverage(self, source: str) -> str:
        return self.sources.get(source, {}).get("coverage", DEFAULT_COVERAGE)

    def display_name(self, source: str) -> str:
        return self.sources.get(source, {}).get("name", source)

    def merge(self, raw: dict) -> None:
        if raw.get("schema") != SCHEMA:
            raise ValueError(f"unsupported fingerprint schema: {raw.get('schema')!r}")
        self.sources.update(raw.get("sources", {}))
        for package, entries in raw.get("packages", {}).items():
            for item in entries:
                sha = str(item.get("sha256", "")).lower()
                if not HEX64.match(sha) or not item.get("source"):
                    self.skipped += 1
                    continue
                entry = Entry(sha, item["source"])
                known = self.packages.setdefault(package, [])
                if entry not in known:
                    known.append(entry)


def load_database(extra: Path | None = None) -> Database:
    """Load the bundled files plus `extra` (or $APKGUARD_FINGERPRINTS_FILE)."""
    db = Database()
    for name in FILES:
        path = resources.files("apkguard.data") / name
        if path.is_file():
            db.merge(json.loads(path.read_text(encoding="utf-8")))
    extra = extra or (Path(os.environ["APKGUARD_FINGERPRINTS_FILE"])
                      if os.environ.get("APKGUARD_FINGERPRINTS_FILE") else None)
    if extra:
        db.merge(json.loads(Path(extra).read_text(encoding="utf-8")))
    return db
