"""Rules every proposed change must pass, and warnings for what a reviewer should look at."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from ..data.capabilities import SENSITIVE_IDS, RULES
from . import WorkspaceError

ALLOWED_EXT = {".md", ".txt", ".kt", ".java", ".xml", ".json", ".gradle", ".kts", ".properties",
               ".yml", ".yaml", ".toml", ".pro", ".html", ".css", ".js", ".ts"}
RESERVED = {".apkguard", ".git"}
MAX_FILE_BYTES = 100 * 1024
MAX_FILES_PER_PROPOSAL = 12
MAX_PROPOSAL_BYTES = 300 * 1024
MAX_WORKSPACE_FILES = 200
MAX_DEPTH = 8
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ \-]*$")

URL = re.compile(r"https?://[^\s\"'<>)\]]+")
# XML namespace identifiers appear in every Android manifest and layout; they are not network addresses.
NAMESPACE_URLS = ("http://schemas.android.com/", "http://www.w3.org/", "https://schemas.android.com/")
PERMISSION = re.compile(r"android\.permission\.[A-Z_]+")


def safe_path(raw: object) -> str:
    """A normalised relative path inside the project, or WorkspaceError('bad_path')."""
    if not isinstance(raw, str) or not raw or len(raw) > 200 or "\x00" in raw or "\\" in raw:
        raise WorkspaceError("bad_path")
    if "//" in raw or "/./" in raw or raw.startswith("./") or raw.endswith("/"):
        raise WorkspaceError("bad_path")  # only canonical paths: no tricks that normalise away
    path = PurePosixPath(raw)
    parts = path.parts
    if path.is_absolute() or not parts or len(parts) > MAX_DEPTH:
        raise WorkspaceError("bad_path")
    if any(p in ("..", ".") or p.startswith("~") or not _NAME.match(p) for p in parts):
        raise WorkspaceError("bad_path")
    if parts[0].lower() in RESERVED or path.suffix.lower() not in ALLOWED_EXT:
        raise WorkspaceError("bad_path")
    return str(path)


def validate_changes(changes: object) -> list[tuple[str, str]]:
    """Checks the model's proposed files. Returns [(path, content)] or raises WorkspaceError."""
    if not isinstance(changes, list):
        raise WorkspaceError("bad_proposal")
    if len(changes) > MAX_FILES_PER_PROPOSAL:
        raise WorkspaceError("too_many_files")
    seen: set[str] = set()
    result, total = [], 0
    for item in changes:
        if not isinstance(item, dict) or not isinstance(item.get("content"), str):
            raise WorkspaceError("bad_proposal")
        path = safe_path(item.get("path"))
        content = item["content"].replace("\r\n", "\n")
        size = len(content.encode("utf-8"))
        if path.lower() in seen or size > MAX_FILE_BYTES:
            raise WorkspaceError("bad_proposal" if path.lower() in seen else "file_too_large")
        seen.add(path.lower())
        total += size
        result.append((path, content))
    if total > MAX_PROPOSAL_BYTES:
        raise WorkspaceError("file_too_large")
    return result


def _dangerous_classes() -> dict[str, str]:
    """Class names of sensitive framework APIs, to spot them in newly written code."""
    names = {}
    for cid, targets in RULES:
        if cid in SENSITIVE_IDS:
            for cls in targets:
                names[cls[1:-1].replace("/", ".")] = cid
                names[cls[1:-1].rsplit("/", 1)[-1].split("$")[0]] = cid
    return names


def _use(name: str) -> str:
    """A class name as it appears in code (followed by a call, member access or constructor)."""
    return rf"\b{re.escape(name)}\s*(?:[.(]|::)"


def review_warnings(before: dict[str, str], after: dict[str, str]) -> list[dict]:
    """What a proposal adds that deserves a careful look: addresses, permissions, sensitive APIs."""
    old_text = "\n".join(before.values())
    new_text = "\n".join(after.values())
    warnings: list[dict] = []

    new_urls = sorted(u for u in set(URL.findall(new_text)) - set(URL.findall(old_text))
                      if not u.startswith(NAMESPACE_URLS))
    if new_urls:
        warnings.append({"id": "new_url", "items": new_urls[:8]})
    new_perms = sorted(set(PERMISSION.findall(new_text)) - set(PERMISSION.findall(old_text)))
    if new_perms:
        warnings.append({"id": "new_permission", "items": new_perms[:8]})
    sensitive = sorted({
        cid for name, cid in _dangerous_classes().items()
        if re.search(_use(name), new_text) and not re.search(_use(name), old_text)
    })
    if sensitive:
        warnings.append({"id": "sensitive_api", "items": sensitive})
    if re.search(r"[A-Za-z0-9+/]{200,}={0,2}", new_text) and not re.search(r"[A-Za-z0-9+/]{200,}={0,2}", old_text):
        warnings.append({"id": "encoded_blob", "items": []})
    return warnings
