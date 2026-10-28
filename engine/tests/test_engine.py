import json

import pytest

from apkguard import cli
from apkguard.data.permissions import SENSITIVE_PERMISSIONS
from apkguard.i18n import SUPPORTED, catalog, render_finding
from apkguard.ingest import IngestError, ingest
from apkguard.models import Severity
from apkguard.pipeline import analyze_apk


def ids(report):
    return {f.id for f in report.findings}


def by_id(report, fid):
    return [f for f in report.findings if f.id == fid]


# --- ingest -----------------------------------------------------------------

def test_hashes_and_kind(benign_apk):
    res = ingest(benign_apk)
    assert res.kind == "apk" and len(res.sha256) == 64 and res.size > 0


def test_xapk_base_extracted(xapk):
    res = ingest(xapk)
    try:
        assert res.kind == "xapk" and res.apk_path.name == "base.apk"
    finally:
        res.cleanup()
    assert not res.apk_path.exists()


@pytest.mark.parametrize("fixture,code", [("plain_text", "not_zip"), ("zip_bomb", "zip_bomb")])
def test_rejected_inputs(request, fixture, code):
    with pytest.raises(IngestError) as exc:
        ingest(request.getfixturevalue(fixture))
    assert exc.value.code == code


def test_missing_and_empty(tmp_path):
    with pytest.raises(IngestError) as exc:
        ingest(tmp_path / "nope.apk")
    assert exc.value.code == "not_found"
    empty = tmp_path / "e.apk"
    empty.write_bytes(b"")
    with pytest.raises(IngestError) as exc:
        ingest(empty)
    assert exc.value.code == "empty"


def test_path_traversal_flagged(traversal_zip):
    assert "ingest.path_traversal" in ids(analyze_apk(traversal_zip))


# --- manifest ---------------------------------------------------------------

def test_benign_app_info(benign_apk):
    report = analyze_apk(benign_apk)
    assert report.app["package"] == "com.example.benign"
    assert report.app["version_name"] == "1.2.3"
    assert report.app["target_sdk"] == 34
    assert "android.permission.INTERNET" in report.permissions
    assert not [f for f in report.findings if f.severity >= Severity.MEDIUM]


def test_suspicious_manifest_findings(suspicious_apk):
    report = analyze_apk(suspicious_apk)
    perms = {f.params["permission"] for f in by_id(report, "manifest.permission")}
    assert perms == {"READ_SMS", "SEND_SMS", "SYSTEM_ALERT_WINDOW"}
    assert {"manifest.debuggable", "manifest.old_target_sdk", "manifest.exported_components"} <= ids(report)


# --- certificate ------------------------------------------------------------

def test_normal_certificate(benign_apk):
    report = analyze_apk(benign_apk)
    assert len(report.certificates) == 1
    assert "Test Developer" in report.certificates[0]["subject"]
    assert "certificate.debug" not in ids(report)
    assert "certificate.unsigned" not in ids(report)


def test_debug_certificate(suspicious_apk):
    assert "certificate.debug" in ids(analyze_apk(suspicious_apk))


def test_unsigned(unsigned_apk):
    assert "certificate.unsigned" in ids(analyze_apk(unsigned_apk))


# --- i18n -------------------------------------------------------------------

def test_catalogs_have_same_keys():
    assert set(catalog("it")) == set(catalog("en"))


def test_every_sensitive_permission_is_translated():
    for lang in SUPPORTED:
        for perm in SENSITIVE_PERMISSIONS:
            for part in ("title", "description", "advice"):
                assert f"finding.permission.{perm}.{part}" in catalog(lang)


def test_all_findings_render_in_both_languages(suspicious_apk, unsigned_apk, traversal_zip):
    findings = []
    for apk in (suspicious_apk, unsigned_apk, traversal_zip):
        findings += analyze_apk(apk).findings
    for finding in findings:
        for lang in SUPPORTED:
            text = render_finding(finding, lang)
            assert all(v and not v.startswith("finding.") for v in text.values()), finding.id


# --- CLI --------------------------------------------------------------------

def test_cli_streams_events_and_report(suspicious_apk, capsys):
    assert cli.main(["analyze", str(suspicious_apk), "--lang", "it"]) == 0
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[0]["event"] == "progress"
    final = events[-1]
    assert final["event"] == "report" and final["lang"] == "it"
    top = final["report"]["findings"][0]
    assert top["severity"] == "high" and top["text"]["title"]


def test_cli_error_event(plain_text, capsys):
    assert cli.main(["analyze", str(plain_text), "--lang", "en"]) == 2
    event = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert event["event"] == "error" and event["code"] == "not_zip"
