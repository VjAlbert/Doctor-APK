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


def t(key: str, lang: str = DEFAULT_LANG, **params: object) -> str:
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


def finding_key(finding: Finding) -> str:
    """Catalog prefix for a finding; permission findings are per-permission."""
    if finding.id == "manifest.permission":
        return f"finding.permission.{finding.params['permission']}"
    return f"finding.{finding.id}"


def render_finding(finding: Finding, lang: str = DEFAULT_LANG) -> dict[str, str]:
    base = finding_key(finding)
    if finding.id == "manifest.permission" and base + ".title" not in catalog(DEFAULT_LANG):
        base = "finding.permission.generic"
    return {
        "title": t(base + ".title", lang, **finding.params),
        "description": t(base + ".description", lang, **finding.params),
        "advice": t(base + ".advice", lang, **finding.params),
    }
