"""Input validation: is this a sane APK, and what are its hashes?

Everything here runs before any parser touches the file, so it must be strict
about size and archive structure (zip bombs, path traversal).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .models import Finding, Severity

MAX_FILE_SIZE = 600 * 1024 * 1024  # compressed, on disk
MAX_UNCOMPRESSED = 4 * 1024 * 1024 * 1024
MAX_RATIO = 200  # uncompressed / compressed, whole archive
MAX_ENTRIES = 100_000
MAX_SPLIT_APK = 600 * 1024 * 1024


class IngestError(Exception):
    """Fatal input problem; `code` is an i18n key under `error.`."""

    def __init__(self, code: str, **params: object) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


@dataclass
class IngestResult:
    original: Path
    apk_path: Path
    kind: str  # "apk" or "xapk"
    size: int
    md5: str
    sha1: str
    sha256: str
    findings: list[Finding] = field(default_factory=list)
    _tmpdir: str | None = None

    def cleanup(self) -> None:
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None


def hash_file(path: Path) -> tuple[str, str, str]:
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()


def _check_archive(zf: zipfile.ZipFile, size: int) -> list[Finding]:
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise IngestError("zip_bomb")
    total = sum(i.file_size for i in infos)
    if total > MAX_UNCOMPRESSED or (size and total / size > MAX_RATIO):
        raise IngestError("zip_bomb")
    findings: list[Finding] = []
    bad = [
        i.filename
        for i in infos
        if i.filename.startswith(("/", "\\"))
        or ".." in Path(i.filename.replace("\\", "/")).parts
    ]
    if bad:
        findings.append(
            Finding(
                "ingest.path_traversal",
                Severity.HIGH,
                "ingest",
                {"count": len(bad), "example": bad[0]},
            )
        )
    return findings


def _extract_base_apk(zf: zipfile.ZipFile, tmpdir: str) -> Path:
    """Pick the base APK out of an XAPK bundle (manifest.json or largest .apk)."""
    apks = [i for i in zf.infolist() if i.filename.lower().endswith(".apk")]
    if not apks:
        raise IngestError("not_apk")
    chosen = None
    if "manifest.json" in zf.namelist():
        try:
            manifest = json.loads(zf.read("manifest.json"))
            wanted = {
                s.get("file")
                for s in manifest.get("split_apks", [])
                if s.get("id") == "base"
            }
            chosen = next((i for i in apks if i.filename in wanted), None)
        except (ValueError, AttributeError):
            chosen = None
    if chosen is None:
        chosen = max(apks, key=lambda i: i.file_size)
    if chosen.file_size > MAX_SPLIT_APK:
        raise IngestError("too_large")
    target = Path(tmpdir) / "base.apk"
    with zf.open(chosen) as src, open(target, "wb") as dst:
        shutil.copyfileobj(src, dst)
    return target


def ingest(path: str | os.PathLike[str]) -> IngestResult:
    p = Path(path)
    if not p.is_file():
        raise IngestError("not_found", path=str(p))
    size = p.stat().st_size
    if size == 0 or size > MAX_FILE_SIZE:
        raise IngestError("too_large" if size else "empty")
    if not zipfile.is_zipfile(p):
        raise IngestError("not_zip")

    md5, sha1, sha256 = hash_file(p)
    tmpdir = None
    try:
        with zipfile.ZipFile(p) as zf:
            findings = _check_archive(zf, size)
            names = set(zf.namelist())
            if "AndroidManifest.xml" in names:
                kind, apk_path = "apk", p
            else:
                tmpdir = tempfile.mkdtemp(prefix="apkguard-")
                apk_path = _extract_base_apk(zf, tmpdir)
                kind = "xapk"
    except zipfile.BadZipFile as exc:
        raise IngestError("not_zip") from exc
    except Exception:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
        raise

    return IngestResult(
        original=p,
        apk_path=apk_path,
        kind=kind,
        size=size,
        md5=md5,
        sha1=sha1,
        sha256=sha256,
        findings=findings,
        _tmpdir=tmpdir,
    )
