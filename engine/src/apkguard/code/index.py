"""Indexes an APK's code: which capabilities it has, who implements them, and what starts them."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from androguard.core.analysis.analysis import Analysis
from androguard.core.apk import APK
from androguard.core.dex import DEX

from ..analyzers.manifest import ANDROID_NS
from ..data.capabilities import RULES, THIRD_PARTY_PREFIXES, TRIGGERS
from . import CodeError

MAX_DEX_BYTES = 60 * 1024 * 1024
MAX_CALLERS = 200  # per capability, to bound the size of the map


@dataclass(frozen=True)
class Caller:
    cls: str          # Lcom/example/Foo;
    method: str
    desc: str
    own: bool         # inside the app's own package
    third_party: bool

    @property
    def ref(self) -> str:
        return f"{self.cls[1:-1].replace('/', '.')}.{self.method}"


@dataclass
class EntryPoint:
    kind: str                       # launcher | activity | service | receiver | provider
    name: str                       # dotted class name
    exported: bool
    triggers: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)   # capability ids implemented in this class


@dataclass
class CodeIndex:
    sha256: str
    package: str
    analysis: Analysis
    capabilities: dict[str, list[Caller]]
    entry_points: list[EntryPoint]
    stats: dict[str, int]


def _is_third_party(cls: str) -> bool:
    return cls.startswith(THIRD_PARTY_PREFIXES)


def _find_callers(analysis: Analysis, targets: dict[str, set[str]], package_prefix: str) -> list[Caller]:
    found: dict[tuple, Caller] = {}
    for cls, names in targets.items():
        pattern = "^" + re.escape(cls) + "$"
        for name in names:
            for method in analysis.find_methods(classname=pattern, methodname="^" + re.escape(name) + "$"):
                for caller_cls, caller_method, _offset in method.get_xref_from():
                    c = caller_cls.name
                    key = (c, caller_method.name, caller_method.get_descriptor())
                    if key not in found and len(found) < MAX_CALLERS:
                        found[key] = Caller(
                            cls=c, method=caller_method.name, desc=caller_method.get_descriptor(),
                            own=bool(package_prefix) and c.startswith(package_prefix),
                            third_party=_is_third_party(c),
                        )
    return sorted(found.values(), key=lambda c: (not c.own, c.third_party, c.cls, c.method))


def _entry_points(apk: APK) -> list[EntryPoint]:
    xml = apk.get_android_manifest_xml()
    app = xml.find("application")
    if app is None:
        return []
    package = apk.get_package() or ""

    def dotted(name: str | None) -> str:
        name = name or ""
        return package + name if name.startswith(".") else name

    result: list[EntryPoint] = []
    for tag in ("activity", "activity-alias", "service", "receiver", "provider"):
        for comp in app.findall(tag):
            actions, categories = [], []
            for flt in comp.findall("intent-filter"):
                actions += [a.get(ANDROID_NS + "name", "") for a in flt.findall("action")]
                categories += [c.get(ANDROID_NS + "name", "") for c in flt.findall("category")]
            launcher = "android.intent.action.MAIN" in actions and "android.intent.category.LAUNCHER" in categories
            kind = "launcher" if launcher else ("activity" if tag == "activity-alias" else tag)
            exported = comp.get(ANDROID_NS + "exported")
            result.append(EntryPoint(
                kind=kind,
                name=dotted(comp.get(ANDROID_NS + "name")),
                exported=(exported == "true") if exported is not None else bool(actions),
                triggers=sorted({TRIGGERS[a] for a in actions if a in TRIGGERS} | ({"user_opens"} if launcher else set())),
            ))
    return result


def build_index(apk: APK, sha256: str) -> CodeIndex:
    blobs = [b for b in apk.get_all_dex() if len(b) >= 0x70 and b[:4] == b"dex\n"]
    if not blobs:
        raise CodeError("no_code")
    if sum(map(len, blobs)) > MAX_DEX_BYTES:
        raise CodeError("too_large")

    analysis = Analysis()
    for blob in blobs:
        try:
            analysis.add(DEX(blob))
        except Exception as exc:  # malformed or deliberately broken DEX
            raise CodeError("unreadable") from exc
    analysis.create_xref()

    package = apk.get_package() or ""
    prefix = "L" + package.replace(".", "/") + "/" if package else ""
    capabilities = {}
    for cid, targets in RULES:
        callers = _find_callers(analysis, targets, prefix)
        if callers:
            capabilities[cid] = callers

    points = _entry_points(apk)
    for point in points:
        descriptor = "L" + point.name.replace(".", "/")
        for cid, callers in capabilities.items():
            if any(c.cls == descriptor + ";" or c.cls.startswith(descriptor + "$") for c in callers):
                point.links.append(cid)

    classes = [c for c in analysis.get_classes() if not c.is_external()]
    return CodeIndex(
        sha256=sha256, package=package, analysis=analysis, capabilities=capabilities, entry_points=points,
        stats={"classes": len(classes), "methods": sum(len(list(c.get_methods())) for c in classes),
               "dex_files": len(blobs)},
    )
