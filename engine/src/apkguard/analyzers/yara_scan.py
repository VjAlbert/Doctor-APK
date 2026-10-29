"""YARA scan of the DEX files.

Bundled rules are generic behavioural heuristics written for APKGuard, not
malware-family signatures. Extra rule files (.yar/.yara) can be dropped into a
directory named by $APKGUARD_RULES_DIR; they are compiled alongside.
"""

from __future__ import annotations

import os
from functools import lru_cache
from importlib import resources
from pathlib import Path

from ..models import Finding, Report, Severity
from .dex import DexFacts

MODULE = "yara"
SEVERITIES = {s.label: s for s in Severity}

try:
    import yara
except ImportError:  # optional at runtime; reported as a finding
    yara = None


def _rule_files() -> dict[str, str]:
    files: dict[str, str] = {}
    bundled = resources.files("apkguard") / "rules"
    for entry in bundled.iterdir():
        if entry.name.endswith((".yar", ".yara")):
            files[f"bundled_{entry.name}"] = str(entry)
    extra = os.environ.get("APKGUARD_RULES_DIR")
    if extra and Path(extra).is_dir():
        for p in sorted(Path(extra).glob("*.y*ar*")):
            files[f"extra_{p.name}"] = str(p)
    return files


@lru_cache(maxsize=4)
def _compiled(key: tuple):
    return yara.compile(filepaths=dict(key))


def analyze(facts: DexFacts, report: Report) -> None:
    if yara is None:
        report.add(Finding("yara.unavailable", Severity.INFO, MODULE))
        return
    rules = _compiled(tuple(sorted(_rule_files().items())))
    seen: set[str] = set()
    for data in facts.dex_files:
        for match in rules.match(data=data):
            if match.rule in seen:
                continue
            seen.add(match.rule)
            meta = match.meta
            hits = sorted({inst.matched_data.decode("latin-1")[:40]
                           for st in match.strings for inst in st.instances})[:5]
            report.add(Finding(
                "yara.match",
                SEVERITIES.get(str(meta.get("severity", "medium")).lower(), Severity.MEDIUM),
                MODULE,
                {"rule": match.rule, "key": meta.get("key", match.rule), "strings": hits},
            ))
    report.stats["yara_rule_files"] = len(_rule_files())
