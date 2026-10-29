import json
import re

import pytest

from apkguard import cli
from apkguard.analyzers import authenticity
from apkguard.data.fingerprints import Database, load_database
from apkguard.i18n import SUPPORTED, catalog, render_authenticity
from apkguard.models import Finding, Report, Severity
from apkguard.pipeline import analyze_apk
from apkguard.scoring import combos

A = "a" * 64
B = "b" * 64


def db(packages, coverage="store", sources=None):
    d = Database()
    d.merge({"schema": 1,
             "sources": sources or {"src": {"name": "Test Store", "coverage": coverage}},
             "packages": packages})
    return d


def report(package="com.acme.app", fingerprints=(A,)):
    r = Report(app={"package": package})
    r.certificates = [{"sha256": fp} for fp in fingerprints]
    return r


def run(r, database):
    authenticity.analyze(r, database)
    return r.authenticity["status"], {f.id: f for f in r.findings}


# --- database ---------------------------------------------------------------

def test_invalid_entries_are_skipped_and_counted():
    d = db({"p": [{"sha256": "zz", "source": "src"}, {"sha256": A.upper(), "source": "src"},
                  {"sha256": A, "source": ""}, {"sha256": A, "source": "src"}]})
    assert [e.sha256 for e in d.lookup("p")] == [A]  # upper-case normalised, duplicate dropped
    assert d.skipped == 2


def test_wrong_schema_is_rejected():
    with pytest.raises(ValueError):
        Database().merge({"schema": 99, "packages": {}})


def test_undeclared_source_is_treated_as_store_coverage():
    d = db({"p": [{"sha256": A, "source": "mystery"}]})
    assert d.coverage("mystery") == "store" and d.display_name("mystery") == "mystery"


def test_extra_file_is_merged(tmp_path):
    extra = tmp_path / "mine.json"
    extra.write_text(json.dumps({"schema": 1, "packages": {"x.y": [{"sha256": B, "source": "mine"}]}}))
    assert load_database(extra).lookup("x.y")[0].sha256 == B


def test_bundled_database_is_valid():
    d = load_database()
    assert d.skipped == 0
    for entries in d.packages.values():
        assert all(re.fullmatch(r"[0-9a-f]{64}", e.sha256) and e.source in d.sources for e in entries)
    assert d.coverage("curated") == "developer" and d.coverage("fdroid") == "store"


# --- analyzer ---------------------------------------------------------------

def test_match():
    status, found = run(report(), db({"com.acme.app": [{"sha256": A, "source": "src"}]}))
    assert status == "match" and found["authenticity.match"].params["sources"] == ["Test Store"]


def test_match_with_any_of_several_signers():
    status, _ = run(report(fingerprints=(B, A)), db({"com.acme.app": [{"sha256": A, "source": "src"}]}))
    assert status == "match"


def test_different_key_against_store_is_only_medium():
    status, found = run(report(fingerprints=(B,)), db({"com.acme.app": [{"sha256": A, "source": "src"}]}))
    assert status == "other_channel" and found["authenticity.other_channel"].severity == Severity.LOW


def test_different_key_against_developer_is_high():
    status, found = run(report(fingerprints=(B,)),
                        db({"com.acme.app": [{"sha256": A, "source": "src"}]}, coverage="developer"))
    assert status == "mismatch" and found["authenticity.mismatch"].severity == Severity.HIGH


def test_unknown_package_is_informational():
    status, found = run(report(), db({}))
    assert status == "unknown" and found["authenticity.unknown"].severity == Severity.INFO


def test_unsigned_app_gets_no_authenticity_finding():
    status, found = run(report(fingerprints=()), db({"com.acme.app": [{"sha256": A, "source": "src"}]}))
    assert status == "unsigned" and not found


# --- combination ------------------------------------------------------------

def test_tampered_known_app_needs_another_serious_signal():
    r = report(fingerprints=(B,))
    authenticity.analyze(r, db({"com.acme.app": [{"sha256": A, "source": "src"}]}, coverage="developer"))
    combos.detect(r, "unknown")
    assert "combo.tampered_known_app" not in {f.id for f in r.findings}
    r.add(Finding("strings.telegram_bot", Severity.HIGH, "strings"))
    combos.detect(r, "unknown")
    assert "combo.tampered_known_app" in {f.id for f in r.findings}


def test_store_mismatch_never_becomes_critical():
    r = report(fingerprints=(B,))
    authenticity.analyze(r, db({"com.acme.app": [{"sha256": A, "source": "src"}]}))
    r.add(Finding("strings.telegram_bot", Severity.HIGH, "strings"))
    combos.detect(r, "unknown")
    assert "combo.tampered_known_app" not in {f.id for f in r.findings}


# --- end to end -------------------------------------------------------------

def signer_of(apk):
    return analyze_apk(apk).certificates[0]["sha256"]


def test_pipeline_match_keeps_a_clean_verdict(benign_apk):
    database = db({"com.example.benign": [{"sha256": signer_of(benign_apk), "source": "src"}]})
    r = analyze_apk(benign_apk, fingerprints=database)
    assert r.authenticity["status"] == "match" and r.verdict["id"] == "no_known_threats"


def test_pipeline_developer_mismatch_demands_caution(benign_apk):
    database = db({"com.example.benign": [{"sha256": A, "source": "src"}]}, coverage="developer")
    r = analyze_apk(benign_apk, fingerprints=database)
    assert r.authenticity["status"] == "mismatch" and r.verdict["id"] == "caution"
    assert r.verdict["reasons"][0]["id"] == "authenticity.mismatch"


def test_pipeline_forged_dropper_is_critical(dropper_apk):
    database = db({"com.example.dropper": [{"sha256": A, "source": "src"}]}, coverage="developer")
    r = analyze_apk(dropper_apk, fingerprints=database)
    assert "combo.tampered_known_app" in {f.id for f in r.findings}


# --- rendering and CLI ------------------------------------------------------

def test_all_authenticity_statuses_are_translated():
    for lang in SUPPORTED:
        for status in ("match", "other_channel", "mismatch", "unknown", "unsigned"):
            assert f"authenticity.status.{status}" in catalog(lang)
            assert render_authenticity({"status": status}, lang) != f"authenticity.status.{status}"


def test_cli_fingerprint(benign_apk, capsys):
    assert cli.main(["fingerprint", str(benign_apk)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["package"] == "com.example.benign" and out["sha256"] == [signer_of(benign_apk)]


def test_cli_fingerprint_error(plain_text, capsys):
    assert cli.main(["fingerprint", str(plain_text)]) == 2
    assert json.loads(capsys.readouterr().out)["code"] == "not_zip"


def test_cli_report_includes_authenticity_label(benign_apk, capsys):
    assert cli.main(["analyze", str(benign_apk), "--lang", "it"]) == 0
    final = json.loads(capsys.readouterr().out.splitlines()[-1])["report"]
    assert final["authenticity"]["status"] == "unknown" and final["authenticity"]["label"] == "Non verificabile"


def test_fdroid_index_conversion():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "import_fdroid", Path(__file__).resolve().parents[2] / "tools/import_fdroid.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    good, other = "a" * 64, "B" * 64
    out = mod.convert({"repo": {"timestamp": 1}, "packages": {
        "org.a": [{"signer": good}, {"signer": good}, {"signer": other}, {"signer": "bad"}],
        "org.b": [{"sig": "md5only"}]}})
    assert out["packages"] == {"org.a": [{"sha256": good, "source": "fdroid"},
                                         {"sha256": other.lower(), "source": "fdroid"}]}
    assert out["sources"]["fdroid"]["coverage"] == "store"
