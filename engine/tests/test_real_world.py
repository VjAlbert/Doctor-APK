"""Regressions found by analysing a real, ad-supported app (an IPTV player from a third-party store)."""

import pytest

import apkbuilder as b
from apkguard.models import Finding, Report, Severity
from apkguard.pipeline import analyze_apk
from apkguard.scoring import profiles, verdict


def ids(report):
    return {f.id for f in report.findings}


def perm_findings(report):
    return {f.params["permission"]: f for f in report.findings if f.id == "manifest.permission"}


def build(work, keystore, name, *, permissions=(), components=(), dex=None, extra=None, label="Test App", package=None):
    tree = b.manifest_tree(package or f"com.example.{name}", permissions=permissions, components=components, label=label)
    return b.build_apk(work / f"{name}.apk", tree, keystore, dex=dex, extra=extra)


def service(permission):
    return ("service", {"android:name": ".Role", "android:permission": f"android.permission.{permission}"}, [])


# --- permissions ----------------------------------------------------------------

def test_vendor_launcher_permissions_are_not_platform_permissions(work, good_keystore):
    apk = build(work, good_keystore, "badges", permissions=(
        "com.huawei.android.launcher.permission.WRITE_SETTINGS", "com.oppo.launcher.permission.WRITE_SETTINGS",
        "com.htc.launcher.permission.READ_SETTINGS", "me.everything.badger.permission.BADGE_COUNT_READ"))
    assert "WRITE_SETTINGS" not in perm_findings(analyze_apk(apk))


def test_the_real_platform_permission_is_still_reported_once(work, good_keystore):
    apk = build(work, good_keystore, "settings", permissions=(
        "WRITE_SETTINGS", "com.huawei.android.launcher.permission.WRITE_SETTINGS"))
    report = analyze_apk(apk)
    assert [f.params["permission"] for f in report.findings if f.id == "manifest.permission"] == ["WRITE_SETTINGS"]


def test_roles_declared_on_components_are_found(work, good_keystore):
    apk = build(work, good_keystore, "a11y", components=(service("BIND_ACCESSIBILITY_SERVICE"),))
    report = analyze_apk(apk)
    finding = perm_findings(report)["BIND_ACCESSIBILITY_SERVICE"]
    assert finding.params["via"] == "component" and finding.severity >= Severity.HIGH
    assert report.stats["component_permissions"] == ["BIND_ACCESSIBILITY_SERVICE"]


def test_component_role_plus_overlay_and_sms_is_a_banking_trojan(work, good_keystore):
    apk = build(work, good_keystore, "banker", permissions=("SYSTEM_ALERT_WINDOW", "RECEIVE_SMS"),
                components=(service("BIND_ACCESSIBILITY_SERVICE"),))
    report = analyze_apk(apk)
    assert "combo.banker" in ids(report) and report.verdict["id"] == "do_not_install"


# --- API findings need the matching role ------------------------------------------------

API_DEX = {
    "accessibility": ("Landroid/view/accessibility/AccessibilityNodeInfo;", "performAction", "dex.accessibility_control"),
    "admin": ("Landroid/app/admin/DevicePolicyManager;", "lockNow", "dex.device_admin_abuse"),
    "sms": ("Landroid/telephony/SmsManager;", "sendTextMessage", "dex.sms_api"),
}


@pytest.mark.parametrize("key", API_DEX)
def test_library_code_without_the_role_is_not_a_capability(work, good_keystore, key):
    cls, method, fid = API_DEX[key]
    apk = build(work, good_keystore, f"lib_{key}", dex=b.build_dex(methods=[(cls, method)]))
    assert fid not in ids(analyze_apk(apk))


@pytest.mark.parametrize("key,role", [("accessibility", "BIND_ACCESSIBILITY_SERVICE"), ("admin", "BIND_DEVICE_ADMIN")])
def test_the_same_api_with_the_role_is_reported(work, good_keystore, key, role):
    cls, method, fid = API_DEX[key]
    apk = build(work, good_keystore, f"role_{key}", dex=b.build_dex(methods=[(cls, method)]),
                components=(service(role),))
    assert fid in ids(analyze_apk(apk))


def test_sms_api_with_an_sms_permission_is_reported(work, good_keystore):
    cls, method, fid = API_DEX["sms"]
    apk = build(work, good_keystore, "sms_ok", permissions=("SEND_SMS",), dex=b.build_dex(methods=[(cls, method)]))
    assert fid in ids(analyze_apk(apk))


# --- bundled SDK code --------------------------------------------------------------------

def test_known_sdk_code_is_not_a_hidden_payload(work, good_keystore):
    dex = b.build_dex(methods=[("Ldalvik/system/DexClassLoader;", "<init>")])
    apk = build(work, good_keystore, "sdk", dex=dex, extra={"assets/audience_network/classes.dex": b.build_dex()})
    report = analyze_apk(apk)
    found = {f.id: f for f in report.findings}
    assert found["payloads.known_sdk_code"].severity == Severity.LOW
    assert found["payloads.known_sdk_code"].params["sdks"] == ["Meta Audience Network"]
    assert "payloads.embedded_dex" not in found and "combo.dropper" not in found


def test_the_same_code_elsewhere_is_still_a_hidden_payload(work, good_keystore):
    dex = b.build_dex(methods=[("Ldalvik/system/DexClassLoader;", "<init>")])
    apk = build(work, good_keystore, "notsdk", dex=dex, extra={"assets/updates/classes.dex": b.build_dex()})
    report = analyze_apk(apk)
    assert {"payloads.embedded_dex", "combo.dropper"} <= ids(report) and report.verdict["id"] == "do_not_install"


# --- indicators --------------------------------------------------------------------------

def test_public_dns_resolvers_are_not_command_servers(work, good_keystore):
    dex = b.build_dex(strings=["http://8.8.8.8/dns", "http://1.1.1.1/", "https://example.com/"])
    report = analyze_apk(build(work, good_keystore, "dns", dex=dex))
    assert "strings.ip_endpoint" not in ids(report)
    assert {"8.8.8.8", "1.1.1.1"} <= set(report.iocs["ips"])        # still listed as indicators
    dex = b.build_dex(strings=["http://93.184.216.34/gate"])
    assert "strings.ip_endpoint" in ids(analyze_apk(build(work, good_keystore, "ip", dex=dex)))


# --- profiles and verdict ------------------------------------------------------------------

def test_location_is_not_escalated_but_contacts_are():
    r = Report(app={"package": "x"})
    for name, sev in (("ACCESS_FINE_LOCATION", Severity.MEDIUM), ("READ_CONTACTS", Severity.MEDIUM)):
        r.add(Finding("manifest.permission", sev, "manifest", {"permission": name}))
    profiles.apply(r, {"id": "media_player", "confidence": "high"})
    by = {f.params["permission"]: f for f in r.findings if f.id == "manifest.permission"}
    assert by["ACCESS_FINE_LOCATION"].severity == Severity.MEDIUM and by["ACCESS_FINE_LOCATION"].params["profile"] == "neutral"
    assert by["READ_CONTACTS"].severity == Severity.HIGH and by["READ_CONTACTS"].params["profile"] == "anomalous"


def compute(findings):
    r = Report()
    for f in findings:
        r.add(f)
    return verdict.compute(r)


def test_many_weak_signals_never_mean_do_not_install():
    weak = [Finding(f"m{i}", Severity.MEDIUM, "x") for i in range(14)] + [Finding(f"l{i}", Severity.LOW, "x") for i in range(10)]
    v = compute(weak)
    assert v["score"] >= verdict.REFUSE_AT and v["id"] == "caution"


def test_two_serious_signals_with_a_high_score_still_refuse():
    assert compute([Finding(f"h{i}", Severity.HIGH, "x") for i in range(3)])["id"] == "do_not_install"
    assert compute([Finding("one", Severity.HIGH, "x")] + [Finding(f"m{i}", Severity.MEDIUM, "x") for i in range(14)])["id"] == "caution"


# --- the real case ---------------------------------------------------------------------------

def test_an_ad_supported_media_player_is_a_caution_at_most(work, good_keystore):
    """Mirrors the findings of the analysed IPTV player: ad-SDK behaviour, vendor badge permissions."""
    dex = b.build_dex(
        strings=["ro.kernel.qemu", "goldfish", "/system/xbin/su", "eu.chainfire.supersu", "http://8.8.8.8/dns"],
        methods=[("Ldalvik/system/DexClassLoader;", "<init>"), ("Ljava/lang/Runtime;", "exec"),
                 ("Landroid/view/accessibility/AccessibilityNodeInfo;", "performAction"),
                 ("Landroid/telephony/TelephonyManager;", "getDeviceId")])
    apk = build(work, good_keystore, "iptv", package="app.iptvplayer.live", label="IPTV Player",
                permissions=("INTERNET", "ACCESS_FINE_LOCATION", "READ_EXTERNAL_STORAGE", "RECEIVE_BOOT_COMPLETED",
                             "com.huawei.android.launcher.permission.WRITE_SETTINGS",
                             "com.oppo.launcher.permission.WRITE_SETTINGS"),
                dex=dex, extra={"assets/audience_network/classes.dex": b.build_dex(),
                                "assets/audience_network/classes2.dex": b.build_dex()})
    report = analyze_apk(apk)
    assert report.verdict["id"] != "do_not_install"
    assert not [f for f in report.findings if f.severity == Severity.CRITICAL]
    assert "WRITE_SETTINGS" not in perm_findings(report) and "dex.accessibility_control" not in ids(report)
    assert "payloads.embedded_dex" not in ids(report) and "combo.dropper" not in ids(report)
