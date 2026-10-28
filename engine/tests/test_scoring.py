import json

import pytest

from apkguard import cli
from apkguard.i18n import SUPPORTED, catalog, render_finding, render_verdict
from apkguard.models import Finding, Report, Severity
from apkguard.pipeline import analyze_apk
from apkguard.scoring import combos, profiles, score_report, verdict


def perm(name, severity):
    return Finding("manifest.permission", severity, "manifest", {"permission": name})


def report_with(findings=(), permissions=(), app=None):
    r = Report(app=app or {"package": "com.acme.thing", "name": "Thing"})
    r.permissions = [f"android.permission.{p}" for p in permissions]
    for f in findings:
        r.add(f)
    return r


def f(fid, severity=Severity.MEDIUM, **params):
    return Finding(fid, severity, "test", params)


def ids(report):
    return {x.id for x in report.findings}


# --- category detection ------------------------------------------------------

@pytest.mark.parametrize("app,expected", [
    ({"package": "com.foo.flashlightpro", "name": "Pro"}, "flashlight"),
    ({"package": "com.foo.app", "name": "Calcolatrice Facile"}, "calculator"),
    ({"package": "org.thoughtcrime.securesms", "name": "Signal"}, "messaging"),
    ({"package": "com.example.benign", "name": "Test App"}, "unknown"),
    ({"package": "com.acme.payloads", "name": "Loader"}, "unknown"),  # 'pay' is not a substring match
])
def test_category_detection(app, expected):
    assert profiles.detect(app)["id"] == expected


# --- profiles ---------------------------------------------------------------

def test_same_permission_weighs_differently_by_category():
    chat = report_with([perm("READ_SMS", Severity.HIGH)])
    torch = report_with([perm("READ_SMS", Severity.HIGH)])
    profiles.apply(chat, {"id": "messaging", "confidence": "high"})
    profiles.apply(torch, {"id": "flashlight", "confidence": "high"})
    assert chat.findings[0].severity == Severity.INFO
    assert chat.findings[0].params["profile"] == "expected"
    assert torch.findings[0].severity == Severity.HIGH
    assert torch.findings[0].params["profile"] == "anomalous"


def test_weak_category_guess_never_downgrades():
    r = report_with([perm("READ_SMS", Severity.HIGH)])
    profiles.apply(r, {"id": "messaging", "confidence": "medium"})
    assert r.findings[0].severity == Severity.HIGH and r.findings[0].params["profile"] == "neutral"


def test_malware_named_like_a_messenger_is_still_caught(work, good_keystore):
    """Naming an app 'chat' must not hide an SMS stealer: combos ignore category."""
    r = report_with([perm("READ_SMS", Severity.HIGH), f("strings.telegram_bot", Severity.HIGH)],
                    ["READ_SMS"])
    score_report(r, "messaging")
    assert "combo.sms_stealer" in ids(r) and r.verdict["id"] == "do_not_install"


def test_medium_permission_is_raised_when_anomalous_and_capped_at_high():
    r = report_with([perm("READ_CONTACTS", Severity.MEDIUM), perm("READ_SMS", Severity.HIGH)])
    profiles.apply(r, {"id": "calculator", "confidence": "high"})
    assert [x.severity for x in r.findings if x.id == "manifest.permission"] == [Severity.HIGH, Severity.HIGH]
    assert "profile.mismatch" in ids(r)


def test_one_anomalous_permission_is_not_a_mismatch():
    r = report_with([perm("READ_CONTACTS", Severity.MEDIUM)])
    profiles.apply(r, {"id": "calculator"})
    assert "profile.mismatch" not in ids(r)


def test_unknown_category_changes_nothing():
    r = report_with([perm("READ_SMS", Severity.HIGH)])
    profiles.apply(r, {"id": "unknown"})
    assert r.findings[0].severity == Severity.HIGH and "profile" not in r.findings[0].params


def test_every_category_is_translated():
    for cid in [*profiles.categories(), "unknown"]:
        for lang in SUPPORTED:
            assert f"category.{cid}" in catalog(lang), cid


def test_profile_permissions_exist():
    from apkguard.data.permissions import SENSITIVE_PERMISSIONS
    for cid, prof in profiles.categories().items():
        for name in prof["expected"] + prof["unusual"]:
            assert name in SENSITIVE_PERMISSIONS, (cid, name)


# --- combinations -----------------------------------------------------------

def detect(permissions=(), finding_ids=(), category="unknown", yara_keys=()):
    r = report_with([f(i) for i in finding_ids] + [
        Finding("yara.match", Severity.HIGH, "yara", {"rule": k, "key": k}) for k in yara_keys],
        permissions)
    combos.detect(r, category)
    return ids(r)


def test_sms_stealer():
    assert "combo.sms_stealer" in detect(["RECEIVE_SMS"], ["strings.telegram_bot"])
    assert "combo.sms_stealer" not in detect(["RECEIVE_SMS"], [])
    assert "combo.sms_stealer" not in detect([], ["strings.telegram_bot"])


def test_banker():
    full = detect(["BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "READ_SMS"])
    assert "combo.banker" in full
    assert "combo.banker" not in detect(["BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW"])
    assert "combo.banker" in detect(["SYSTEM_ALERT_WINDOW"], yara_keys=["accessibility_overlay_banker"])


def test_dropper():
    assert "combo.dropper" in detect([], ["payloads.embedded_apk", "dex.dynamic_loading"])
    assert "combo.dropper" in detect(["REQUEST_INSTALL_PACKAGES"], ["payloads.embedded_dex"])
    assert "combo.dropper" not in detect([], ["payloads.embedded_apk"])


def test_spyware_is_not_flagged_for_messaging_apps():
    args = (["RECORD_AUDIO", "READ_CONTACTS"], ["strings.ip_endpoint"])
    assert "combo.spyware" in detect(*args)
    assert "combo.spyware" not in detect(*args, category="messaging")


def test_evasive_loader_and_repackaged():
    assert "combo.evasive_loader" in detect([], ["dex.dynamic_loading", "packer.known"])
    assert "combo.evasive_loader" not in detect([], ["dex.dynamic_loading"])
    r = report_with([f("certificate.debug", Severity.HIGH),
                     perm("READ_SMS", Severity.HIGH), perm("CALL_PHONE", Severity.MEDIUM)])
    combos.detect(r, "unknown")
    assert "combo.repackaged" in ids(r)


# --- verdict ----------------------------------------------------------------

def run(findings):
    r = report_with(findings)
    r.verdict = verdict.compute(r)
    return r.verdict


def test_clean_report():
    v = run([f("certificate.self_signed", Severity.INFO)])
    assert v["id"] == "no_known_threats" and v["score"] == 0 and v["level"] == "low"


def test_few_low_signals_stay_ok():
    assert run([f("a", Severity.LOW)] * 3)["id"] == "no_known_threats"


def test_single_high_signal_means_caution():
    assert run([f("a", Severity.HIGH)])["id"] == "caution"


def test_critical_always_refuses_with_high_score():
    v = run([f("combo.x", Severity.CRITICAL)])
    assert v["id"] == "do_not_install" and v["score"] >= verdict.CRITICAL_FLOOR and v["level"] == "critical"


def test_many_high_signals_refuse_without_critical():
    v = run([f(f"h{i}", Severity.HIGH) for i in range(4)])
    assert v["id"] == "do_not_install" and v["level"] == "high"


def test_score_is_monotonic_and_bounded():
    scores = [run([f(f"m{i}", Severity.MEDIUM) for i in range(n)])["score"] for n in range(0, 30, 3)]
    assert scores == sorted(scores) and scores[-1] <= 100


def test_reasons_lead_with_combos_and_are_distinct():
    r = report_with([f("a", Severity.HIGH), f("combo.sms_stealer", Severity.HIGH),
                     perm("READ_SMS", Severity.HIGH), perm("SEND_SMS", Severity.HIGH),
                     f("b", Severity.LOW)])
    v = verdict.compute(r)
    assert len(v["reasons"]) == verdict.MAX_REASONS
    assert v["reasons"][0]["id"] == "combo.sms_stealer"
    assert len({(x["id"], x["params"].get("permission")) for x in v["reasons"]}) == 3


# --- end to end -------------------------------------------------------------

def test_benign_apk_verdict(benign_apk):
    r = analyze_apk(benign_apk)
    assert r.verdict["id"] == "no_known_threats" and r.category["id"] == "unknown"


def test_messenger_with_sms_permissions_is_not_refused(messenger_apk):
    r = analyze_apk(messenger_apk)
    assert r.category["id"] == "messaging"
    sms = [x for x in r.findings if x.id == "manifest.permission" and x.params["permission"] == "READ_SMS"][0]
    assert sms.severity == Severity.INFO and sms.params["profile"] == "expected"
    assert "profile.mismatch" not in ids(r)
    assert r.verdict["id"] == "no_known_threats"


def test_torch_with_same_permissions_is_refused(torch_apk):
    r = analyze_apk(torch_apk)
    assert r.category["id"] == "flashlight"
    assert "profile.mismatch" in ids(r)
    assert r.verdict["id"] == "do_not_install"
    assert r.verdict["reasons"][0]["id"] == "profile.mismatch"


def test_user_can_override_category(torch_apk):
    r = analyze_apk(torch_apk, category="messaging")
    assert r.category == {"id": "messaging", "source": "user", "confidence": "high"}
    assert "profile.mismatch" not in ids(r)


def test_debug_signed_dropper_scores_critical(dropper_apk, suspicious_apk):
    assert analyze_apk(dropper_apk).verdict["level"] == "critical"
    assert analyze_apk(suspicious_apk).verdict["id"] == "do_not_install"


# --- rendering and CLI ------------------------------------------------------

def test_verdict_texts_in_both_languages():
    for lang in SUPPORTED:
        for vid in ("no_known_threats", "caution", "do_not_install"):
            text = render_verdict({"id": vid}, {"id": "flashlight"}, lang)
            assert text["title"] and text["summary"] and text["limitations"]
            assert not text["title"].startswith("verdict.")


def test_new_findings_render_with_localized_category(torch_apk):
    r = analyze_apk(torch_apk)
    mismatch = [x for x in r.findings if x.id == "profile.mismatch"][0]
    assert "torcia" in render_finding(mismatch, "it")["description"]
    assert "flashlight" in render_finding(mismatch, "en")["description"]
    perm_f = [x for x in r.findings if x.params.get("profile") == "anomalous"][0]
    assert "flashlight" in render_finding(perm_f, "en")["note"]


def test_cli_report_has_verdict_and_texts(torch_apk, capsys):
    assert cli.main(["analyze", str(torch_apk), "--lang", "it"]) == 0
    final = json.loads(capsys.readouterr().out.splitlines()[-1])["report"]
    assert final["verdict"]["id"] == "do_not_install"
    assert final["verdict"]["text"]["title"] == "Non installare"
    assert final["verdict"]["text"]["category"] == "torcia"
    assert all(x["text"]["title"] for x in final["verdict"]["reasons"])


def test_cli_category_flag(torch_apk, capsys):
    assert cli.main(["analyze", str(torch_apk), "--category", "messaging"]) == 0
    final = json.loads(capsys.readouterr().out.splitlines()[-1])["report"]
    assert final["category"]["source"] == "user"


def test_descriptions_do_not_leak_internal_ids(dropper_apk, torch_apk, suspicious_apk):
    """Technical ids belong in the technical view, not in plain-language texts."""
    for apk in (dropper_apk, torch_apk, suspicious_apk):
        report = analyze_apk(apk)
        known = {f.id for f in report.findings}
        for finding in report.findings:
            for lang in SUPPORTED:
                text = render_finding(finding, lang)
                for part in ("title", "description", "advice"):
                    assert not any(fid in text[part] for fid in known), (finding.id, lang, text[part])
