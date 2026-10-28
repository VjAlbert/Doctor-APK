"""Data model shared by every analyzer.

Findings carry an id and parameters, never display text: the text is resolved
from the i18n catalogs at render time so the same report can be shown in any
language.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass
class Finding:
    id: str
    severity: Severity
    module: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.label,
            "module": self.module,
            "params": self.params,
        }


@dataclass
class Report:
    file: dict[str, Any] = field(default_factory=dict)
    app: dict[str, Any] = field(default_factory=dict)
    certificates: list[dict[str, Any]] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["findings"] = [
            f.to_dict()
            for f in sorted(self.findings, key=lambda f: (-f.severity, f.id))
        ]
        return data
