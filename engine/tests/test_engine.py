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
            for part in ("title", "description", "advice"):
                assert text[part] and not text[part].startswith("finding."), (finding.id, part)


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


# --- M1: code, strings, payloads, YARA -------------------------------------

def test_benign_has_no_m1_findings(benign_apk):
    report = analyze_apk(benign_apk)
    assert not [f for f in report.findings if f.module in {"dex", "strings", "payloads", "yara"}]


def test_api_findings(dropper_apk):
    report = analyze_apk(dropper_apk)
    found = ids(report)
    assert {"dex.dynamic_loading", "dex.shell_exec", "dex.sms_api"} <= found
    loader = by_id(report, "dex.dynamic_loading")[0]
    assert loader.params["apis"] == ["dalvik.system.DexClassLoader.<init>"]


def test_string_indicators(dropper_apk):
    report = analyze_apk(dropper_apk)
    assert {"strings.telegram_bot", "strings.ip_endpoint", "strings.dynamic_dns"} <= ids(report)
    assert "93.184.216.34" in report.iocs["ips"]
    assert "evil-host.duckdns.org" in report.iocs["domains"]
    assert "example.com" in report.iocs["domains"]


def test_private_ips_are_not_indicators(work, good_keystore):
    from apkguard.analyzers.strings import _public_ip
    assert _public_ip("192.168.1.10") is None and _public_ip("127.0.0.1") is None
    assert _public_ip("8.8.8.8") == "8.8.8.8"


def test_anti_analysis_needs_two_markers(dropper_apk):
    assert "dex.anti_analysis" in ids(analyze_apk(dropper_apk))


def test_embedded_payloads(dropper_apk):
    report = analyze_apk(dropper_apk)
    apk = by_id(report, "payloads.embedded_apk")[0]
    assert apk.params["files"] == ["assets/logo.png"] and apk.params["disguised"] is True
    assert "assets/stage2" in by_id(report, "payloads.embedded_dex")[0].params["files"]
    assert "assets/helper.bin" in by_id(report, "payloads.embedded_elf")[0].params["files"]
    assert "assets/payload.dat" in by_id(report, "payloads.encrypted_blob")[0].params["files"]


def test_packer_by_native_library(dropper_apk):
    packers = by_id(analyze_apk(dropper_apk), "packer.known")
    assert [p.params["packer"] for p in packers] == ["360 Jiagu"]


def test_yara_sms_exfiltration(dropper_apk):
    matches = by_id(analyze_apk(dropper_apk), "yara.match")
    assert "sms_exfiltration" in {m.params["rule"] for m in matches}
    assert all(m.severity == Severity.HIGH for m in matches if m.params["rule"] == "sms_exfiltration")


def test_dropper_is_critical(dropper_apk):
    report = analyze_apk(dropper_apk)
    assert max(f.severity for f in report.findings) == Severity.CRITICAL
    assert report.verdict["id"] == "do_not_install"


def test_every_emitted_finding_id_is_translated():
    import re
    from pathlib import Path
    import apkguard

    emitted = set()
    for src in Path(apkguard.__file__).parent.rglob("*.py"):
        emitted.update(re.findall(r'Finding\(\s*(?:f)?"([a-z_]+\.[a-z_]+)"', src.read_text()))
    emitted.update(f"finding.{i}" for i in ())
    for lang in SUPPORTED:
        for fid in emitted - {"manifest.permission", "yara.match"}:
            assert f"finding.{fid}.title" in catalog(lang), (lang, fid)


def test_yara_rules_all_have_text():
    import re
    from importlib import resources

    text = (resources.files("apkguard") / "rules" / "apkguard_generic.yar").read_text()
    for key in re.findall(r'key = "([a-z_]+)"', text):
        for lang in SUPPORTED:
            assert f"finding.yara.{key}.title" in catalog(lang), key


def test_unknown_yara_rule_falls_back_to_generic():
    from apkguard.models import Finding
    f = Finding("yara.match", Severity.MEDIUM, "yara", {"rule": "custom_rule", "key": "custom_rule"})
    assert "custom_rule" in render_finding(f, "it")["title"]


def test_single_miner_name_is_not_a_miner(work, good_keystore):
    import apkbuilder as b
    from apkbuilder import build_dex
    for strings, expected in ((["coinhive"], False), (["coinhive", "xmrig"], True),
                              (["stratum+tcp://pool.example:3333"], True)):
        apk = b.build_apk(work / f"m{len(strings)}{expected}.apk", b.manifest_tree("com.example.m"), good_keystore,
                          dex=build_dex(strings=strings))
        rules = {m.params["rule"] for m in by_id(analyze_apk(apk), "yara.match")}
        assert ("crypto_miner" in rules) is expected, strings
