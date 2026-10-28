"""Local HTTP bridge between the UI and the engine (development and browser use).

`POST /analyze` takes the raw APK as the request body and streams the same
line-delimited JSON events as the CLI. The server only binds to loopback and
rejects requests whose Host or Origin is not local, so a web page cannot use
it to reach the engine through DNS rebinding or cross-site requests.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from androguard.core.apk import APK
from loguru import logger

from . import version_info
from .ai import claude_cli, explain
from .code import CodeError, narrate
from .code.index import CodeIndex, build_index
from .code.slices import slice_for
from .cli import build_report_event
from .i18n import SUPPORTED, t
from .ingest import MAX_FILE_SIZE, IngestError, ingest
from .pipeline import analyze_apk
from .scoring.profiles import categories
from .workspace import WorkspaceError, service
from .workspace.store import Workspace

VT_KEY = re.compile(r"^[A-Za-z0-9]{16,128}$")
MAX_JSON_BODY = 2 * 1024 * 1024
AI_STATUS = {"not_installed": 503, "not_logged_in": 503, "busy": 429, "timeout": 504,
             "too_large": 413, "failed": 502, "bad_request": 400}
CODE_ID = re.compile(r"^[0-9a-f]{64}$")
CODE_STATUS = {"no_code": 422, "too_large": 413, "unreadable": 422, "not_found": 404, "bad_capability": 400}
MAX_INDEXES = 2  # analysed apps kept in memory so the UI can ask follow-up questions
_indexes: "OrderedDict[str, CodeIndex]" = OrderedDict()
_indexes_lock = threading.Lock()
WS_STATUS = {"not_found": 404, "stale": 409, "conflict": 409, "not_open": 409, "ownership": 403,
             "malicious": 403, "bad_reply": 502, "nothing_to_undo": 409}
WS_ROUTE = re.compile(r"^/workspaces(?:/([a-z0-9-]+)(?:/(file|ideas|undo|export\.zip|proposals)(?:/([0-9a-f]{12}|export|import)(?:/(draft|approve|reject))?)?)?)?$")
LOCAL_HOSTS = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$")
LOCAL_ORIGINS = re.compile(r"^(https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?|tauri://localhost|https?://tauri\.localhost)$")


class Handler(BaseHTTPRequestHandler):
    server_version = "apkguard"

    def log_message(self, *args) -> None:  # keep the console quiet
        pass

    # --- helpers -----------------------------------------------------------

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        return bool(LOCAL_HOSTS.match(self.headers.get("Host", ""))) and (
            origin is None or bool(LOCAL_ORIGINS.match(origin)))

    def _cors(self) -> None:
        origin = self.headers.get("Origin")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # --- routes ------------------------------------------------------------

    def do_OPTIONS(self) -> None:
        if not self._origin_ok():
            return self._json(403, {"error": "forbidden"})
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename, X-VT-Key")
        self.end_headers()

    def do_GET(self) -> None:
        if not self._origin_ok():
            return self._json(403, {"error": "forbidden"})
        path = urlparse(self.path).path
        if path.startswith("/workspaces"):
            return self._workspaces("GET", path, parse_qs(urlparse(self.path).query))
        if path == "/health":
            return self._json(200, {"ok": True, "categories": list(categories()), **version_info()})
        if path == "/ai/status":
            return self._json(200, claude_cli.status())
        slice_route = re.match(r"^/code/([0-9a-f]{64})/slice$", path)
        if slice_route:
            return self._code_slice(slice_route.group(1), parse_qs(urlparse(self.path).query))
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._origin_ok():
            return self._json(403, {"error": "forbidden"})
        url = urlparse(self.path)
        if url.path.startswith("/workspaces"):
            return self._workspaces("POST", url.path, parse_qs(url.query))
        if url.path == "/ai/explain":
            return self._ai_explain()
        if url.path == "/code/index":
            return self._code_index(parse_qs(url.query))
        explain_route = re.match(r"^/code/([0-9a-f]{64})/explain$", url.path)
        if explain_route:
            return self._code_explain(explain_route.group(1))
        if url.path != "/analyze":
            return self._json(404, {"error": "not found"})
        query = parse_qs(url.query)
        lang = query.get("lang", ["en"])[0]
        lang = lang if lang in SUPPORTED else "en"
        category = query.get("category", ["auto"])[0]
        category = None if category == "auto" else category

        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._json(411, {"error": "length required"})
        if length <= 0 or length > MAX_FILE_SIZE:
            return self._stream_error("too_large" if length else "empty", lang)

        fd, path = tempfile.mkstemp(prefix="apkguard-upload-", suffix=".apk")
        try:
            with os.fdopen(fd, "wb") as out:
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1 << 20, remaining))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            name = os.path.basename(unquote(self.headers.get("X-Filename", "")) or "upload.apk")
            key = self.headers.get("X-VT-Key", "")
            self._run(path, name, lang, category, key if VT_KEY.match(key) else None)
        finally:
            os.unlink(path)

    def _code_error(self, code: str, lang: str) -> None:
        self._json(CODE_STATUS.get(code, 400), {"error": code, "message": t(f"code.error.{code}", lang)})

    def _get_index(self, index_id: str) -> CodeIndex | None:
        with _indexes_lock:
            index = _indexes.get(index_id)
            if index:
                _indexes.move_to_end(index_id)
            return index

    def _code_index(self, query: dict) -> None:
        """Indexes the uploaded APK's code and returns what it can do and what starts it."""
        lang = query.get("lang", ["en"])[0]
        lang = lang if lang in SUPPORTED else "en"
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._json(411, {"error": "length required"})
        if not 0 < length <= MAX_FILE_SIZE:
            return self._code_error("too_large", lang)
        fd, path = tempfile.mkstemp(prefix="apkguard-code-", suffix=".apk")
        result = None
        try:
            with os.fdopen(fd, "wb") as out:
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1 << 20, remaining))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)
            result = ingest(path)
            index = build_index(APK(str(result.apk_path)), result.sha256)
        except IngestError as exc:
            return self._json(400, {"error": exc.code, "message": t(f"error.{exc.code}", lang, **exc.params)})
        except CodeError as exc:
            return self._code_error(exc.code, lang)
        except Exception:
            logger.opt(exception=True).debug("code index failed")
            return self._code_error("unreadable", lang)
        finally:
            if result:
                result.cleanup()
            os.unlink(path)
        with _indexes_lock:
            _indexes[index.sha256] = index
            _indexes.move_to_end(index.sha256)
            while len(_indexes) > MAX_INDEXES:
                _indexes.popitem(last=False)
        self._json(200, narrate.code_map(index, lang))

    def _code_slice(self, index_id: str, query: dict) -> None:
        lang = query.get("lang", ["en"])[0]
        lang = lang if lang in SUPPORTED else "en"
        index = self._get_index(index_id)
        if index is None:
            return self._code_error("not_found", lang)
        capability = query.get("cap", [""])[0]
        if capability not in index.capabilities:
            return self._code_error("bad_capability", lang)
        self._json(200, {"capability": capability, "methods": slice_for(index, capability)})

    def _code_explain(self, index_id: str) -> None:
        """Asks the user's Claude Code to explain one capability's code, or the whole app."""
        lang = "en"
        try:
            length = int(self.headers.get("Content-Length", ""))
            if not 0 < length <= MAX_JSON_BODY:
                return self._ai_error("too_large" if length > 0 else "bad_request", lang)
            body = json.loads(self.rfile.read(length))
            lang = body.get("lang") if body.get("lang") in SUPPORTED else "en"
            capability = body.get("cap")
            if capability is not None and not isinstance(capability, str):
                raise TypeError
        except (ValueError, TypeError, AttributeError):
            return self._ai_error("bad_request", lang)
        index = self._get_index(index_id)
        if index is None:
            return self._code_error("not_found", lang)
        if capability is not None and capability not in index.capabilities:
            return self._code_error("bad_capability", lang)
        system, prompt = (narrate.build_capability(index, capability, lang) if capability
                          else narrate.build_overview(index, lang))
        if body.get("dry_run") is True:
            return self._json(200, {"system": system, "prompt": prompt})
        try:
            self._json(200, claude_cli.ask(system, prompt))
        except claude_cli.AiError as exc:
            self._ai_error(exc.code, lang)

    def _ws_error(self, code: str, lang: str, **params) -> None:
        self._json(WS_STATUS.get(code, 400), {"error": code, "message": t(f"workspace.error.{code}", lang, **params)})

    def _read_body(self, limit: int = MAX_JSON_BODY):
        """Parsed JSON object from the body ({} when empty), or None if too large or invalid."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > limit:
                return None
            if length == 0:
                return {}
            data = json.loads(self.rfile.read(length))
            return data if isinstance(data, dict) else None
        except ValueError:
            return None

    def _workspaces(self, method: str, path: str, query: dict) -> None:
        """Projects: create, ideas, drafts, review (approve/reject), undo and sharing."""
        lang = query.get("lang", ["en"])[0]
        lang = lang if lang in SUPPORTED else "en"
        route = WS_ROUTE.match(path)
        if not route:
            return self._json(404, {"error": "not found"})
        ws_id, section, item, action = route.groups()
        body: dict = {}
        if method == "POST":
            parsed = self._read_body()
            if parsed is None:
                return self._ws_error("bad_request", lang)
            body = parsed
            if body.get("lang") in SUPPORTED:
                lang = body["lang"]
        try:
            return self._workspace_action(method, ws_id, section, item, action, query, body, lang)
        except WorkspaceError as exc:
            return self._ws_error(exc.code, lang, **exc.params)
        except claude_cli.AiError as exc:
            return self._ai_error(exc.code, lang)

    def _workspace_action(self, method, ws_id, section, item, action, query, body, lang) -> None:
        if ws_id is None:
            if method == "GET":
                return self._json(200, {"projects": Workspace.list_all()})
            code_map = None
            index = self._get_index(str(body.get("code_id", ""))) if body.get("code_id") else None
            if index:
                code_map = narrate.code_map(index, lang)
            project, source = service.create_project(
                body.get("report") if isinstance(body.get("report"), dict) else {}, code_map,
                str(body.get("name", "")), lang, owner_confirmed=body.get("owner_confirmed"),
                use_ai=body.get("use_ai") is True)
            return self._json(200, {**project.summary(), "spec": source})

        project = Workspace.open(ws_id)
        if section is None:
            return self._json(200, {**project.summary(), "files": project.file_list(), "ideas": project.ideas(),
                                    "proposals": project.proposals(), "history": project.history()})
        if section == "file" and method == "GET":
            return self._json(200, {"path": query.get("path", [""])[0],
                                    "content": project.read_file(query.get("path", [""])[0])})
        if section == "export.zip" and method == "GET":
            data = project.export_zip()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{project.id}.zip"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if section == "undo" and method == "POST":
            return self._json(200, project.undo())
        if section == "ideas":
            if item == "export" and method == "GET":
                return self._json(200, project.export_ideas())
            if item == "import" and method == "POST":
                return self._json(200, project.import_ideas(body))
            if item is None and method == "POST":
                return self._json(200, project.add_idea(str(body.get("text", "")), str(body.get("author", ""))))
            if item and action == "draft" and method == "POST":
                return self._json(200, service.draft_idea(project, item, lang))
        if section == "proposals" and item:
            if action is None and method == "GET":
                return self._json(200, self._translated(project.proposal_view(item), lang))
            if action == "approve" and method == "POST":
                return self._json(200, project.approve(item))
            if action == "reject" and method == "POST":
                return self._json(200, project.reject(item))
        self._json(404, {"error": "not found"})

    @staticmethod
    def _translated(view: dict, lang: str) -> dict:
        """Warnings come with ready-to-show text in the user's language."""
        for w in view["warnings"]:
            w["text"] = t(f"workspace.warning.{w['id']}", lang, items=", ".join(w["items"]))
        return view

    def _ai_error(self, code: str, lang: str) -> None:
        self._json(AI_STATUS.get(code, 502), {"error": code, "message": t(f"ai.error.{code}", lang)})

    def _ai_explain(self) -> None:
        """Explains a report in plain language through the user's own Claude Code."""
        lang = "en"
        try:
            length = int(self.headers.get("Content-Length", ""))
            if not 0 < length <= MAX_JSON_BODY:
                return self._ai_error("too_large" if length > 0 else "bad_request", lang)
            body = json.loads(self.rfile.read(length))
            lang = body.get("lang") if body.get("lang") in SUPPORTED else "en"
            system, prompt = explain.build(body["report"], lang)
        except (ValueError, KeyError, TypeError, AttributeError):
            return self._ai_error("bad_request", lang)
        if body.get("dry_run") is True:  # lets the UI show exactly what would be sent
            return self._json(200, {"system": system, "prompt": prompt})
        try:
            self._json(200, claude_cli.ask(system, prompt))
        except claude_cli.AiError as exc:
            self._ai_error(exc.code, lang)

    def _emit(self, event: dict) -> None:
        self.wfile.write((json.dumps(event, ensure_ascii=False) + "\n").encode())
        self.wfile.flush()

    def _stream_error(self, code: str, lang: str, **params) -> None:
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        self._emit({"event": "error", "code": code, "message": t(f"error.{code}", lang, **params)})

    def _run(self, path: str, name: str, lang: str, category: str | None, vt_key: str | None) -> None:
        try:
            report = analyze_apk(path, progress=self._emit, category=category, virustotal_key=vt_key)
        except IngestError as exc:
            return self._emit({"event": "error", "code": exc.code,
                               "message": t(f"error.{exc.code}", lang, **exc.params)})
        except Exception:  # never leak internals to the page
            logger.opt(exception=True).debug("analysis failed")
            return self._emit({"event": "error", "code": "internal",
                               "message": t("error.internal", lang)})
        event = build_report_event(report, lang)
        event["report"]["file"]["name"] = name  # the temp path is meaningless to the user
        self._emit(event)


def make_server(port: int = 0) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(port: int = 8765) -> None:
    logger.remove()
    httpd = make_server(port)
    print(f"apkguard bridge listening on http://127.0.0.1:{httpd.server_address[1]}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
