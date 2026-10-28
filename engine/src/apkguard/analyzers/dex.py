"""DEX analysis: sensitive APIs, packers, obfuscation, anti-analysis hints."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from androguard.core.apk import APK
from androguard.core.dex import DEX

from ..data.apis import (
    API_RULES, EMULATOR_MARKERS, PACKER_CLASSES, ROOT_MARKERS)
from ..models import Finding, Report, Severity

MODULE = "dex"
MAX_STRINGS = 2_000_000
MIN_CLASSES_FOR_OBFUSCATION = 50
OBFUSCATED_RATIO = 0.6

log = logging.getLogger(__name__)


@dataclass
class DexFacts:
    """Everything later analyzers need from the DEX files, extracted once."""

    dex_files: list[bytes] = field(default_factory=list)
    strings: set[str] = field(default_factory=set)
    methods: set[tuple[str, str]] = field(default_factory=set)
    classes: set[str] = field(default_factory=set)
    parse_errors: int = 0


def load_facts(apk: APK) -> DexFacts:
    facts = DexFacts()
    for data in apk.get_all_dex():
        if len(data) < 0x70 or data[:4] != b"dex\n":
            continue
        facts.dex_files.append(data)
        try:
            dex = DEX(data)
            for s in dex.get_strings():
                if len(facts.strings) >= MAX_STRINGS:
                    break
                facts.strings.add(str(s))
            for m in dex.get_methods_id_item().get_obj():
                facts.methods.add((m.get_class_name(), m.get_name()))
            facts.classes.update(dex.get_classes_names())
        except Exception as exc:  # malformed or deliberately broken DEX
            facts.parse_errors += 1
            log.debug("DEX parse failed: %s", exc)
    return facts


def _short_name(descriptor: str) -> str:
    return descriptor[1:-1].rsplit("/", 1)[-1]


def analyze(facts: DexFacts, report: Report) -> None:
    if not facts.dex_files:
        report.add(Finding("dex.missing", Severity.LOW, MODULE))
    if facts.parse_errors:
        report.add(Finding("dex.malformed", Severity.MEDIUM, MODULE,
                           {"count": facts.parse_errors}))

    for fid, severity, targets in API_RULES:
        hits = sorted(
            f"{cls[1:-1].replace('/', '.')}.{name}"
            for cls, names in targets.items()
            for name in names
            if (cls, name) in facts.methods
        )
        if hits:
            report.add(Finding(fid, severity, MODULE, {"apis": hits}))

    found = sorted({
        name for cls in facts.classes for prefix, name in PACKER_CLASSES.items()
        if cls.startswith(prefix)})
    for name in found:
        report.add(Finding("packer.known", Severity.MEDIUM, MODULE,
                           {"packer": name, "source": "classes"}))

    if len(facts.classes) >= MIN_CLASSES_FOR_OBFUSCATION:
        tiny = sum(1 for c in facts.classes if len(_short_name(c)) <= 2)
        ratio = tiny / len(facts.classes)
        if ratio >= OBFUSCATED_RATIO:
            report.add(Finding("dex.obfuscation", Severity.INFO, MODULE,
                               {"ratio": round(ratio, 2)}))

    emulator = sorted(m for m in EMULATOR_MARKERS if m in facts.strings)
    if len(emulator) >= 2:
        report.add(Finding("dex.anti_analysis", Severity.MEDIUM, MODULE,
                           {"markers": emulator}))
    root = sorted(m for m in ROOT_MARKERS if m in facts.strings)
    if len(root) >= 2:
        report.add(Finding("dex.root_tools", Severity.LOW, MODULE,
                           {"markers": root}))
