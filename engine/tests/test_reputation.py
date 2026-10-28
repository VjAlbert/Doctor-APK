import json
import threading

import pytest

from apkguard.analyzers import authenticity, reputation
from apkguard.data.fingerprints import Database
from apkguard.i18n import SUPPORTED, render_finding
from apkguard.models import Report
from apkguard.pipeline import analyze_apk
from apkguard.server import make_server

HASH = "c" * 64


def vt_body(malicious=0, suspicious=0, undetected=60):
    return {"data": {"attributes": {"last_analysis_stats": {
        "malicious": malicious, "suspicious": suspicious, "undetected": undetected, "harmless": 0}}}}


def run(fetch, key="k" * 32):
    report = Report(file={"sha256": HASH})
    reputation.analyze(report, key, fetch)
    return report


def test_disabled_without_key_and_makes_no_request():
    def boom(*a):
        raise AssertionError("must not call the network")
    report = Report(file={"sha256": HASH})
    reputation.analyze(report, None, boom)
    assert report.reputation == {"status": "disabled"} and not report.findings


def test_only_the_hash_and_key_header_are_sent():
    seen = {}

    def fetch(url, headers, timeout):
        seen.update(url=url, headers=headers)
        return 200, vt_body()
    run(fetch, key="secretkey" * 4)
    assert seen["url"].endswith(f"/files/{HASH}")
    assert seen["headers"]["x-apikey"] == "secretkey" * 4


@pytest.mark.parametrize("malicious,suspicious,fid,severity", [
    (0, 0, "reputation.clean", "info"),
    (0, 2, "reputation.clean", "info"),
    (0, 3, "reputation.suspicious", "medium"),
    (1, 0, "reputation.malicious", "high"),
    (4, 0, "reputation.malicious", "high"),
    (5, 0, "reputation.malicious", "critical"),
    (40, 3, "reputation.malicious", "critical"),
])
def test_thresholds(malicious, suspicious, fid, severity):
    report = run(lambda *a: (200, vt_body(malicious, suspicious)))
    finding = report.findings[0]
    assert finding.id == fid and finding.severity.label == severity
    assert report.reputation["status"] == "known" and report.reputation["malicious"] == malicious


def test_unknown_hash():
    report = run(lambda *a: (404, None))
    assert report.reputation["status"] == "unknown" and report.findings[0].id == "reputation.unknown"


@pytest.mark.parametrize("status,body,reason", [
    (401, None, "invalid_key"), (403, None, "invalid_key"), (429, None, "rate_limited"),
    (0, None, "network"), (500, None, "unexpected"),
    (200, {"unexpected": True}, "unexpected"), (200, {"data": {"attributes": {"last_analysis_stats": {"malicious": "x"}}}}, "unexpected"),
])
def test_errors_never_break_the_analysis(status, body, reason):
    report = run(lambda *a: (status, body))
    assert report.reputation == {"status": "error", "reason": reason}
    assert report.findings[0].severity.label == "info"


def test_error_texts_are_translated():
    for lang in SUPPORTED:
        for reason in ("invalid_key", "rate_limited", "network", "unexpected"):
            finding = run(lambda *a, r=reason: {"invalid_key": (401, None), "rate_limited": (429, None),
                                                "network": (0, None), "unexpected": (500, None)}[r]).findings[0]
            text = render_finding(finding, lang)
            assert "reputation.reason" not in text["description"] and text["description"]


def test_all_reputation_findings_render_in_both_languages():
    for body in (vt_body(0), vt_body(0, 4), vt_body(2), vt_body(9)):
        finding = run(lambda *a, b=body: (200, b)).findings[0]
        for lang in SUPPORTED:
            text = render_finding(finding, lang)
            assert all(text[p] and not text[p].startswith("finding.") for p in ("title", "description", "advice"))


def test_pipeline_uses_reputation_for_verdict(benign_apk):
    report = analyze_apk(benign_apk, virustotal_key="k" * 32,
                         reputation_fetch=lambda *a: (200, vt_body(12)))
    assert report.verdict["id"] == "do_not_install" and report.verdict["reasons"][0]["id"] == "reputation.malicious"


def test_pipeline_without_key_is_unaffected(benign_apk):
    report = analyze_apk(benign_apk)
    assert report.reputation == {"status": "disabled"} and report.verdict["id"] == "no_known_threats"


def test_authenticity_reports_expected_fingerprints():
    db = Database()
    db.merge({"schema": 1, "sources": {"s": {"name": "Test Store", "coverage": "store"}},
              "packages": {"com.acme": [{"sha256": "a" * 64, "source": "s"}]}})
    report = Report(app={"package": "com.acme"})
    report.certificates = [{"sha256": "b" * 64}]
    authenticity.analyze(report, db)
    assert report.authenticity["expected"] == [{"sha256": "a" * 64, "source": "Test Store"}]


def test_bridge_passes_key_only_when_well_formed(benign_apk):
    import http.client
    from unittest import mock

    httpd = make_server(0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    keys = []

    def fake_analyze(path, **kwargs):
        keys.append(kwargs["virustotal_key"])
        return analyze_apk(path)

    try:
        with mock.patch("apkguard.server.analyze_apk", fake_analyze):
            for header in ("a" * 32, "bad key!", ""):
                conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=30)
                conn.request("POST", "/analyze", body=benign_apk.read_bytes(), headers={"X-VT-Key": header})
                json.loads(conn.getresponse().read().decode().splitlines()[-1])
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert keys == ["a" * 32, None, None]
