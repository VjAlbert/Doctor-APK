"""Archive contents: hidden executables, packers, encrypted blobs."""

from __future__ import annotations

import io
import math
import re
import zipfile
from collections import Counter
from pathlib import PurePosixPath

from ..data.apis import PACKER_LIBS
from ..models import Finding, Report, Severity

MODULE = "payloads"
SAMPLE = 1024 * 1024  # bytes read for magic/entropy checks
MAX_NESTED_APK = 50 * 1024 * 1024
MIN_BLOB = 50 * 1024
ENTROPY_THRESHOLD = 7.5
DEX_MAGIC = re.compile(rb"dex\n0\d\d\0")

# Formats that are legitimately high-entropy. Generic names such as .dat and
# .bin are deliberately absent: they are what encrypted payloads hide behind.
COMPRESSED_EXT = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp3", ".mp4", ".ogg", ".m4a",
    ".webm", ".mkv", ".aac", ".flac", ".ttf", ".otf", ".woff", ".woff2",
    ".pdf", ".zip", ".gz", ".br", ".ogv", ".opus", ".jar", ".dex", ".apk",
    ".so", ".arsc", ".mid", ".wav", ".obb",
}
EXPECTED_EXEC_EXT = {".dex", ".jar", ".apk", ".so"}


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in Counter(data).values())


def _kind(zf: zipfile.ZipFile, info: zipfile.ZipInfo, head: bytes) -> str | None:
    if DEX_MAGIC.match(head):
        return "dex"
    if head.startswith(b"\x7fELF"):
        return "elf"
    if head.startswith(b"PK\x03\x04") and info.file_size <= MAX_NESTED_APK:
        try:
            with zipfile.ZipFile(io.BytesIO(zf.read(info))) as inner:
                if "AndroidManifest.xml" in inner.namelist():
                    return "apk"
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
            return None
    return None


def analyze(path, report: Report) -> None:
    with zipfile.ZipFile(path) as zf:
        _scan(zf, report)


def _scan(zf: zipfile.ZipFile, report: Report) -> None:
    packers: set[str] = set()
    embedded: dict[str, list[dict]] = {"apk": [], "dex": [], "elf": []}
    blobs: list[str] = []
    native = 0

    for info in zf.infolist():
        if info.is_dir() or info.file_size == 0:
            continue
        name = info.filename
        pure = PurePosixPath(name)
        ext = pure.suffix.lower()

        if name.startswith("lib/") and ext == ".so":
            native += 1
            if (packer := PACKER_LIBS.get(pure.name)):
                packers.add(packer)
            continue
        if name == "AndroidManifest.xml" or (name.startswith("classes") and ext == ".dex"):
            continue
        if name.startswith("META-INF/"):
            continue

        try:
            with zf.open(info) as fh:
                head = fh.read(SAMPLE)
        except (RuntimeError, NotImplementedError, zipfile.BadZipFile):
            continue
        kind = _kind(zf, info, head)
        if kind:
            disguised = ext not in EXPECTED_EXEC_EXT
            embedded[kind].append({"name": name, "disguised": disguised})
        elif (info.file_size >= MIN_BLOB and ext not in COMPRESSED_EXT
              and entropy(head) >= ENTROPY_THRESHOLD):
            blobs.append(name)

    for packer in sorted(packers):
        report.add(Finding("packer.known", Severity.MEDIUM, MODULE,
                           {"packer": packer, "source": "native_lib"}))
    for kind, severity in (("apk", Severity.HIGH), ("dex", Severity.HIGH), ("elf", Severity.MEDIUM)):
        if embedded[kind]:
            files = embedded[kind]
            report.add(Finding(f"payloads.embedded_{kind}", severity, MODULE, {
                "count": len(files),
                "files": [f["name"] for f in files[:5]],
                "disguised": any(f["disguised"] for f in files),
            }))
    if blobs:
        report.add(Finding("payloads.encrypted_blob", Severity.LOW, MODULE,
                           {"count": len(blobs), "files": blobs[:5]}))
    report.stats["native_libs"] = native
