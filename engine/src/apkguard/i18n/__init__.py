"""Minimal JSON-catalog translations (Italian and English)."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from ..models import Finding

SUPPORTED = ("it", "en")
DEFAULT_LANG = "en"


@lru_cache(maxsize=None)
def catalog(lang: str) -> dict[str, str]:
    path = resources.files(__package__) / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, lang: str = DEFAULT_LANG, /, **params: object) -> str:
    """Translate `key`, falling back to English and then to the key itself."""
    for code in (lang, DEFAULT_LANG):
        if code in SUPPORTED:
            text = catalog(code).get(key)
            if text is not None:
                try:
                    return text.format(**params)
                except (KeyError, IndexError):
                    return text
    return key


def _base(finding: Finding) -> str:
    """Catalog prefix for a finding.

    Permission and YARA findings have one entry per permission/rule, falling
    back to a generic entry for ones without dedicated text.
    """
    if finding.id == "manifest.permission":
        specific, generic = f"finding.permission.{finding.params['permission']}", "finding.permission.generic"
    elif finding.id == "yara.match":
        specific, generic = f"finding.yara.{finding.params['key']}", "finding.yara.generic"
    else:
        return f"finding.{finding.id}"
    return specific if specific + ".title" in catalog(DEFAULT_LANG) else generic


def render_finding(finding: Finding, lang: str = DEFAULT_LANG) -> dict[str, str]:
    base = _base(finding)
    params = {k: ", ".join(map(str, v)) if isinstance(v, list) else v
              for k, v in finding.params.items()}
    return {part: t(f"{base}.{part}", lang, **params)
            for part in ("title", "description", "advice")}
