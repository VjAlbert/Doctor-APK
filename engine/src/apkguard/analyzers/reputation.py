"""Optional online reputation lookup (VirusTotal), by file hash only.

Only the SHA-256 of the file is sent: the APK itself never leaves the machine.
The check is off unless the user supplies an API key. A hash VirusTotal has
never seen proves nothing, and a clean record only means "no engine flagged it
yet", so neither outcome is ever presented as a safety guarantee.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from ..models import Finding, Report, Severity

MODULE = "reputation"
URL = "https://www.virustotal.com/api/v3/files/{sha256}"
TIMEOUT = 10
CRITICAL_AT = 5  # engines flagging it as malicious
SUSPICIOUS_AT = 3

# (status code, parsed JSON body or None)
Fetch = Callable[[str, dict[str, str], float], tuple[int, dict | None]]


def _http_get(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict | None]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return 0, None


def _error(report: Report, reason: str) -> None:
    report.reputation = {"status": "error", "reason": reason}
    report.add(Finding("reputation.error", Severity.INFO, MODULE, {"reason": reason}))


def analyze(report: Report, api_key: str | None, fetch: Fetch = _http_get) -> None:
    if not api_key:
        report.reputation = {"status": "disabled"}
        return
    status, body = fetch(
        URL.format(sha256=report.file["sha256"]),
        {"x-apikey": api_key, "accept": "application/json"},
        TIMEOUT,
    )
    if status == 404:
        report.reputation = {"status": "unknown"}
        report.add(Finding("reputation.unknown", Severity.INFO, MODULE))
        return
    if status in (401, 403):
        return _error(report, "invalid_key")
    if status == 429:
        return _error(report, "rate_limited")
    if status != 200 or not isinstance(body, dict):
        return _error(report, "network" if status == 0 else "unexpected")

    try:
        stats = body["data"]["attributes"]["last_analysis_stats"]
        malicious, suspicious = int(stats.get("malicious", 0)), int(stats.get("suspicious", 0))
        total = sum(int(v) for v in stats.values())
    except (KeyError, TypeError, ValueError):
        return _error(report, "unexpected")

    params = {"malicious": malicious, "suspicious": suspicious, "total": total}
    report.reputation = {"status": "known", **params}
    if malicious >= CRITICAL_AT:
        report.add(Finding("reputation.malicious", Severity.CRITICAL, MODULE, params))
    elif malicious >= 1:
        report.add(Finding("reputation.malicious", Severity.HIGH, MODULE, params))
    elif suspicious >= SUSPICIOUS_AT:
        report.add(Finding("reputation.suspicious", Severity.MEDIUM, MODULE, params))
    else:
        report.add(Finding("reputation.clean", Severity.INFO, MODULE, params))
