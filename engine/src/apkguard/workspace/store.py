"""On-disk project: files, ideas, proposals and history. Plain files, no database, no git needed."""

from __future__ import annotations

import difflib
import io
import json
import os
import re
import secrets
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import WorkspaceError
from .safety import MAX_FILE_BYTES, MAX_WORKSPACE_FILES, ALLOWED_EXT, review_warnings, safe_path, validate_changes

SCHEMA = 1
META = ".apkguard"
ID = re.compile(r"^[0-9a-f]{12}$")
WS_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,60}$")
MAX_IDEA_CHARS = 2000
MAX_DIFF_LINES = 1500
_lock = threading.RLock()  # one change at a time; this is a single-user desktop app


def home() -> Path:
    return Path(os.environ.get("APKGUARD_HOME") or Path.home() / "APKGuard") / "projects"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "project"
    return f"{base}-{secrets.token_hex(2)}"


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)  # never leave a half-written file behind


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.id = root.name

    # --- lifecycle -----------------------------------------------------------

    @classmethod
    def create(cls, name: str, package: str, files: dict[str, str], source: dict, ownership: dict) -> "Workspace":
        with _lock:
            root = home() / _slug(name)
            root.mkdir(parents=True, exist_ok=False)
            ws = cls(root)
            _write_json(root / META / "workspace.json", {
                "schema": SCHEMA, "name": name[:80], "package": package[:200], "created": _now(),
                "source": source, "ownership": ownership,
            })
            for path, content in files.items():
                ws._write_file(safe_path(path), content)
            return ws

    @classmethod
    def open(cls, workspace_id: str) -> "Workspace":
        if not WS_ID.match(workspace_id):
            raise WorkspaceError("not_found")
        root = home() / workspace_id
        if not (root / META / "workspace.json").is_file():
            raise WorkspaceError("not_found")
        return cls(root)

    @classmethod
    def list_all(cls) -> list[dict]:
        base = home()
        found = []
        for root in sorted(base.iterdir()) if base.is_dir() else []:
            if (root / META / "workspace.json").is_file():
                found.append(cls(root).summary())
        return sorted(found, key=lambda w: w["created"], reverse=True)

    @property
    def meta(self) -> dict:
        return _read_json(self.root / META / "workspace.json", {})

    def summary(self) -> dict:
        proposals = self.proposals()
        return {
            "id": self.id, "name": self.meta.get("name", self.id), "package": self.meta.get("package", ""),
            "created": self.meta.get("created", ""),
            "open_ideas": sum(i["status"] == "new" for i in self.ideas()),
            "open_proposals": sum(p["status"] == "open" for p in proposals),
        }

    # --- files ---------------------------------------------------------------

    def _file(self, path: str) -> Path:
        target = (self.root / safe_path(path)).resolve()
        if self.root.resolve() not in target.parents:
            raise WorkspaceError("bad_path")
        return target

    def _write_file(self, path: str, content: str) -> None:
        target = self._file(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")

    def read_file(self, path: str) -> str:
        target = self._file(path)
        if not target.is_file():
            raise WorkspaceError("not_found")
        return target.read_text(encoding="utf-8", errors="replace")

    def file_list(self) -> list[dict]:
        files = []
        for p in sorted(self.root.rglob("*")):
            rel = p.relative_to(self.root)
            if not p.is_file() or rel.parts[0] == META or p.suffix.lower() not in ALLOWED_EXT:
                continue
            if p.is_symlink() or self.root.resolve() not in p.resolve().parents:
                continue  # never follow a link out of the project
            files.append({"path": rel.as_posix(), "size": p.stat().st_size})
            if len(files) >= MAX_WORKSPACE_FILES:
                break
        return files

    def read_all(self, limit_bytes: int = 60_000) -> dict[str, str]:
        """Project files for a prompt: SPEC.md first, then the rest, within a size budget."""
        out, used = {}, 0
        for item in sorted(self.file_list(), key=lambda f: (f["path"] != "SPEC.md", f["path"])):
            text = self.read_file(item["path"])
            if used + len(text) > limit_bytes:
                continue
            out[item["path"]] = text
            used += len(text)
        return out

    # --- ideas ---------------------------------------------------------------

    def ideas(self) -> list[dict]:
        base = self.root / META / "ideas"
        items = [_read_json(p, None) for p in sorted(base.glob("*.json"))] if base.is_dir() else []
        return sorted((i for i in items if i), key=lambda i: i["created"])

    def add_idea(self, text: str, author: str, *, idea_id: str | None = None, created: str | None = None) -> dict:
        text = (text or "").strip()
        if not text or len(text) > MAX_IDEA_CHARS:
            raise WorkspaceError("bad_idea")
        idea = {"id": idea_id or secrets.token_hex(6), "text": text, "author": (author or "").strip()[:60] or "?",
                "created": created or _now(), "status": "new", "proposal_id": None}
        with _lock:
            _write_json(self.root / META / "ideas" / f"{idea['id']}.json", idea)
        return idea

    def get_idea(self, idea_id: str) -> dict:
        idea = _read_json(self.root / META / "ideas" / f"{idea_id}.json", None) if ID.match(idea_id) else None
        if not idea:
            raise WorkspaceError("not_found")
        return idea

    def update_idea(self, idea: dict) -> None:
        with _lock:
            _write_json(self.root / META / "ideas" / f"{idea['id']}.json", idea)

    def export_ideas(self) -> dict:
        return {"schema": SCHEMA, "project": self.meta.get("name", ""), "exported": _now(),
                "ideas": [{k: i[k] for k in ("id", "text", "author", "created")} for i in self.ideas()]}

    def import_ideas(self, data: object) -> dict:
        """Merges ideas sent by collaborators; ones already present are skipped."""
        if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("ideas"), list):
            raise WorkspaceError("bad_import")
        have = {i["id"] for i in self.ideas()}
        added = skipped = 0
        for item in data["ideas"][:200]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not ID.match(item["id"]):
                skipped += 1
                continue
            if item["id"] in have:
                skipped += 1
                continue
            try:
                self.add_idea(str(item.get("text", "")), str(item.get("author", "")), idea_id=item["id"],
                              created=str(item.get("created") or _now())[:40])
                added += 1
            except WorkspaceError:
                skipped += 1
        return {"added": added, "skipped": skipped}

    # --- proposals -----------------------------------------------------------

    def _proposal_path(self, pid: str) -> Path:
        return self.root / META / "proposals" / f"{pid}.json"

    def proposals(self) -> list[dict]:
        base = self.root / META / "proposals"
        items = [_read_json(p, None) for p in sorted(base.glob("*.json"))] if base.is_dir() else []
        return sorted((self._brief(i) for i in items if i), key=lambda i: i["created"], reverse=True)

    @staticmethod
    def _brief(p: dict) -> dict:
        return {k: p[k] for k in ("id", "idea_id", "status", "created", "summary")} | {
            "files": [c["path"] for c in p["changes"]], "warnings": len(p.get("warnings", []))}

    def create_proposal(self, idea_id: str, summary: str, files: object) -> dict:
        changes_in = validate_changes(files)
        with _lock:
            current = {}
            changes = []
            for path, content in changes_in:
                try:
                    old = self.read_file(path)
                except WorkspaceError:
                    old = None
                if old == content:
                    continue  # no real change
                current[path] = old or ""
                changes.append({"path": path, "old": old, "new": content})
            if not changes:
                raise WorkspaceError("no_changes")
            proposal = {
                "id": secrets.token_hex(6), "idea_id": idea_id, "status": "open", "created": _now(),
                "summary": (summary or "").strip()[:600],
                "warnings": review_warnings(current, {c["path"]: c["new"] for c in changes}),
                "changes": changes,
            }
            _write_json(self._proposal_path(proposal["id"]), proposal)
            return proposal

    def get_proposal(self, pid: str) -> dict:
        proposal = _read_json(self._proposal_path(pid), None) if ID.match(pid) else None
        if not proposal:
            raise WorkspaceError("not_found")
        return proposal

    def proposal_view(self, pid: str) -> dict:
        """The proposal with ready-to-show differences."""
        proposal = self.get_proposal(pid)
        changes = []
        for c in proposal["changes"]:
            diff = list(difflib.unified_diff(
                (c["old"] or "").splitlines(), c["new"].splitlines(),
                fromfile=f"a/{c['path']}" if c["old"] is not None else "/dev/null", tofile=f"b/{c['path']}",
                lineterm="", n=3))
            changes.append({"path": c["path"], "is_new": c["old"] is None, "diff": diff[:MAX_DIFF_LINES],
                            "truncated": len(diff) > MAX_DIFF_LINES,
                            "added": sum(1 for d in diff if d.startswith("+") and not d.startswith("+++")),
                            "removed": sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))})
        return {k: proposal[k] for k in ("id", "idea_id", "status", "created", "summary", "warnings")} | {"changes": changes}

    def _set_status(self, proposal: dict, status: str) -> None:
        proposal["status"] = status
        _write_json(self._proposal_path(proposal["id"]), proposal)
        try:
            idea = self.get_idea(proposal["idea_id"])
            idea["status"] = {"approved": "accepted", "rejected": "rejected"}.get(status, idea["status"])
            idea["proposal_id"] = proposal["id"]
            self.update_idea(idea)
        except WorkspaceError:
            pass

    def approve(self, pid: str) -> dict:
        with _lock:
            proposal = self.get_proposal(pid)
            if proposal["status"] != "open":
                raise WorkspaceError("not_open")
            before = {}
            for c in proposal["changes"]:
                try:
                    now = self.read_file(c["path"])
                except WorkspaceError:
                    now = None
                if now != c["old"]:  # someone changed the file since the draft
                    self._set_status(proposal, "stale")
                    raise WorkspaceError("stale")
                before[c["path"]] = now
            for c in proposal["changes"]:
                self._write_file(c["path"], c["new"])
            seq = len(list((self.root / META / "history").glob("*.json"))) + 1 if (self.root / META / "history").is_dir() else 1
            _write_json(self.root / META / "history" / f"{seq:05d}.json",
                        {"seq": seq, "proposal_id": pid, "at": _now(), "before": before,
                         "after": {c["path"]: c["new"] for c in proposal["changes"]}, "undone": False})
            self._set_status(proposal, "approved")
            return {"status": "approved", "files": list(before)}

    def reject(self, pid: str) -> dict:
        with _lock:
            proposal = self.get_proposal(pid)
            if proposal["status"] != "open":
                raise WorkspaceError("not_open")
            self._set_status(proposal, "rejected")
            return {"status": "rejected"}

    # --- history -------------------------------------------------------------

    def history(self) -> list[dict]:
        base = self.root / META / "history"
        items = [_read_json(p, None) for p in sorted(base.glob("*.json"))] if base.is_dir() else []
        return [{"seq": i["seq"], "proposal_id": i["proposal_id"], "at": i["at"], "files": list(i["before"]),
                 "undone": i["undone"]} for i in items if i][::-1]

    def undo(self) -> dict:
        """Reverts the most recent approved change that is still in effect."""
        with _lock:
            base = self.root / META / "history"
            entries = sorted(base.glob("*.json")) if base.is_dir() else []
            for path in reversed(entries):
                entry = _read_json(path, None)
                if not entry or entry["undone"]:
                    continue
                for p, content in entry["after"].items():  # refuse if the files moved on since
                    try:
                        if self.read_file(p) != content:
                            raise WorkspaceError("conflict")
                    except WorkspaceError as exc:
                        if exc.code == "conflict" or content is not None:
                            raise WorkspaceError("conflict") from exc
                for p, content in entry["before"].items():
                    if content is None:
                        self._file(p).unlink(missing_ok=True)
                    else:
                        self._write_file(p, content)
                entry["undone"] = True
                _write_json(path, entry)
                proposal = self.get_proposal(entry["proposal_id"])
                proposal["status"] = "reverted"
                _write_json(self._proposal_path(proposal["id"]), proposal)
                return {"reverted": list(entry["before"]), "proposal_id": entry["proposal_id"]}
            raise WorkspaceError("nothing_to_undo")

    # --- sharing ---------------------------------------------------------------

    def export_zip(self) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in self.file_list():
                zf.writestr(item["path"], self.read_file(item["path"]))
        return buffer.getvalue()
