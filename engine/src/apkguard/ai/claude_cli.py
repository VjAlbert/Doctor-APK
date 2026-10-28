"""Runs the user's installed Claude Code (`claude -p`) as a one-shot text assistant.

Rules this module keeps, on purpose:

* It never reads, copies or stores credentials. Sign-in happens through
  Anthropic's own flow (`claude auth login`, done by the user in a terminal);
  here we only ask the program for its status.
* The program is run unmodified and with its default authentication, so the
  usage is billed to the signed-in user, never to APKGuard.
* Calls are user-initiated, one at a time, and run with every tool disabled in
  an empty throw-away directory, so the model can neither read nor change files.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

BIN_ENV = "APKGUARD_CLAUDE_BIN"
STATUS_TIMEOUT = 20
ASK_TIMEOUT = 120
MAX_PROMPT_CHARS = 120_000
OUTPUT_CAP = 20_000

_busy = threading.Lock()  # "ordinary individual usage": one request at a time


class AiError(Exception):
    """`code` is an i18n key under `ai.error.`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def find_claude() -> str | None:
    override = os.environ.get(BIN_ENV)
    if override:
        return override if Path(override).is_file() else None
    return shutil.which("claude")


def _run(args: list[str], *, stdin: str | None = None, timeout: float, cwd: str | None = None):
    return subprocess.run(
        args, input=stdin, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, cwd=cwd, check=False,
    )


def _auth_kind(method: str) -> str:
    lowered = method.lower()
    if "oauth" in lowered or "claude" in lowered or "subscription" in lowered:
        return "subscription"
    if "api" in lowered or "key" in lowered:
        return "api_key"
    return "other"


def status() -> dict:
    """Is Claude Code installed and signed in? Never includes paths or credentials."""
    path = find_claude()
    if not path:
        return {"state": "not_installed"}
    try:
        version = _run([path, "--version"], timeout=STATUS_TIMEOUT).stdout.strip().splitlines()
        auth = _run([path, "auth", "status"], timeout=STATUS_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return {"state": "not_installed"}

    try:
        data = json.loads(auth.stdout)
    except ValueError:
        data = {}
    logged_in = bool(data.get("loggedIn")) if isinstance(data, dict) else False
    method = str(data.get("authMethod", "")) if isinstance(data, dict) else ""
    return {
        "state": "connected" if logged_in else "not_logged_in",
        "version": version[0][:60] if version else None,
        "auth": _auth_kind(method) if logged_in else None,
    }


def ask(system: str, prompt: str) -> dict:
    """One tool-less question. Returns {"text", "cost_usd", "duration_ms"} or raises AiError."""
    if len(prompt) > MAX_PROMPT_CHARS:
        raise AiError("too_large")
    path = find_claude()
    if not path:
        raise AiError("not_installed")
    if not _busy.acquire(blocking=False):
        raise AiError("busy")
    try:
        with tempfile.TemporaryDirectory(prefix="apkguard-ai-") as workdir:
            args = [
                path, "-p", "--output-format", "json",
                "--system-prompt", system,
                "--tools", "",                    # no file, shell or web access
                "--permission-mode", "dontAsk",
                "--no-session-persistence",
                "--disable-slash-commands",
                "--strict-mcp-config",            # no MCP servers from the user's setup
            ]
            try:
                done = _run(args, stdin=prompt, timeout=ASK_TIMEOUT, cwd=workdir)
            except subprocess.TimeoutExpired as exc:
                raise AiError("timeout") from exc
            except OSError as exc:
                raise AiError("not_installed") from exc
    finally:
        _busy.release()

    try:
        data = json.loads(done.stdout)
    except ValueError as exc:
        raise AiError("failed") from exc
    if not isinstance(data, dict):
        raise AiError("failed")
    text = str(data.get("result", "")).strip()
    if data.get("is_error") or done.returncode != 0:
        lowered = text.lower()
        raise AiError("not_logged_in" if any(w in lowered for w in ("log in", "login", "/login", "authenticat")) else "failed")
    if not text:
        raise AiError("failed")
    cost = data.get("total_cost_usd")
    return {
        "text": text[:OUTPUT_CAP],
        "cost_usd": round(float(cost), 4) if isinstance(cost, (int, float)) else None,
        "duration_ms": int(data["duration_ms"]) if isinstance(data.get("duration_ms"), (int, float)) else None,
    }
