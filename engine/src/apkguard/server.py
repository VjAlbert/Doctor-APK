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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from loguru import logger

from .cli import build_report_event
from .i18n import SUPPORTED, t
from .ingest import MAX_FILE_SIZE, IngestError
from .pipeline import analyze_apk
from .scoring.profiles import categories

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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")
        self.end_headers()

    def do_GET(self) -> None:
        if not self._origin_ok():
            return self._json(403, {"error": "forbidden"})
        if urlparse(self.path).path == "/health":
            return self._json(200, {"ok": True, "categories": list(categories())})
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._origin_ok():
            return self._json(403, {"error": "forbidden"})
        url = urlparse(self.path)
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
            self._run(path, name, lang, category)
        finally:
            os.unlink(path)

    def _emit(self, event: dict) -> None:
        self.wfile.write((json.dumps(event, ensure_ascii=False) + "\n").encode())
        self.wfile.flush()

    def _stream_error(self, code: str, lang: str, **params) -> None:
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        self._emit({"event": "error", "code": code, "message": t(f"error.{code}", lang, **params)})

    def _run(self, path: str, name: str, lang: str, category: str | None) -> None:
        try:
            report = analyze_apk(path, progress=self._emit, category=category)
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
