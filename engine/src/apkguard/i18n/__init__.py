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


def category_name(category_id: str, lang: str = DEFAULT_LANG) -> str:
    return t(f"category.{category_id}", lang)


def render_finding(finding: Finding, lang: str = DEFAULT_LANG) -> dict[str, str]:
    base = _base(finding)
    params = {k: ", ".join(map(str, v)) if isinstance(v, list) else v
              for k, v in finding.params.items()}
    category = finding.params.get("category")
    if category:
        params["category"] = category_name(category, lang)
    text = {part: t(f"{base}.{part}", lang, **params)
            for part in ("title", "description", "advice")}
    profile = finding.params.get("profile")
    text["note"] = (t(f"note.profile.{profile}", lang, **params)
                    if profile in ("expected", "anomalous") else "")
    return text


def render_verdict(verdict: dict, category: dict, lang: str = DEFAULT_LANG) -> dict[str, str]:
    vid = verdict["id"]
    return {
        "title": t(f"verdict.{vid}.title", lang),
        "summary": t(f"verdict.{vid}.summary", lang),
        "limitations": t("verdict.limitations", lang),
        "category": category_name(category.get("id", "unknown"), lang),
    }


def render_authenticity(auth: dict, lang: str = DEFAULT_LANG) -> str:
    return t(f"authenticity.status.{auth.get('status', 'unknown')}", lang)
