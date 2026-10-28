"""Readable views of the code behind a capability: decompiled where possible, else bytecode."""

from __future__ import annotations

from androguard.decompiler.decompile import DvMethod

from .index import Caller, CodeIndex

MAX_METHODS = 4
MAX_LINES = 70
MAX_CHARS = 6000

DECOMPILED = "decompiled"
BYTECODE = "bytecode"


def _method_analysis(index: CodeIndex, caller: Caller):
    cls = index.analysis.get_class_analysis(caller.cls)
    if cls is None:
        return None
    for method in cls.get_methods():
        if method.name == caller.method and method.get_descriptor() == caller.desc:
            return method
    return None


def _bytecode(method) -> str:
    return "\n".join(f"{ins.get_name()} {ins.get_output()}".rstrip() for ins in method.get_method().get_instructions())


def _clip(text: str) -> str:
    lines = text.splitlines()
    clipped = "\n".join(lines[:MAX_LINES])
    if len(lines) > MAX_LINES or len(clipped) > MAX_CHARS:
        clipped = clipped[:MAX_CHARS].rstrip() + "\n// …"
    return clipped


def view_of(index: CodeIndex, caller: Caller) -> dict | None:
    """A readable view of one method, or None if it has no code."""
    method = _method_analysis(index, caller)
    if method is None or method.is_external():
        return None
    try:
        decompiler = DvMethod(method)
        decompiler.process()
        source, kind = decompiler.get_source(), DECOMPILED
        if not source or not source.strip():
            raise ValueError("empty")
    except Exception:  # the decompiler gives up on some methods; the bytecode always exists
        source, kind = _bytecode(method), BYTECODE
    return {
        "class": caller.cls[1:-1].replace("/", "."),
        "method": caller.method,
        "signature": f"{caller.method}{caller.desc}",
        "kind": kind,
        "own": caller.own,
        "third_party": caller.third_party,
        "source": _clip(source.strip("\n")),
    }


def slice_for(index: CodeIndex, capability: str, limit: int = MAX_METHODS) -> list[dict]:
    """The most relevant methods for a capability: the app's own code first."""
    views = []
    for caller in index.capabilities.get(capability, []):
        view = view_of(index, caller)
        if view:
            views.append(view)
        if len(views) >= limit:
            break
    return views
