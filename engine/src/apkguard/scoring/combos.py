"""Combinations of signals that are far worse together than apart."""

from __future__ import annotations

from ..models import Finding, Report, Severity

MODULE = "scoring"
SMS_READ = {"READ_SMS", "RECEIVE_SMS"}
BANKER_PERMS = {"BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW"}
EXFIL = {"strings.telegram_bot", "strings.discord_webhook",
         "strings.ip_endpoint", "strings.dynamic_dns"}
# Categories where microphone + contacts + a network endpoint is the product.
COMMUNICATION_CATEGORIES = {"messaging"}


def detect(report: Report, category_id: str) -> None:
    ids = {f.id for f in report.findings}
    perms = {p[len("android.permission."):] for p in report.permissions if p.startswith("android.permission.")}
    perms |= set(report.stats.get("component_permissions", []))
    yara = {f.params.get("key") for f in report.findings if f.id == "yara.match"}
    exfil = sorted(ids & EXFIL)
    heavy = [f for f in report.findings
             if f.id == "manifest.permission" and f.severity >= Severity.MEDIUM]

    def add(cid: str, severity: Severity, signals: list[str]) -> None:
        report.add(Finding(cid, severity, MODULE, {"signals": sorted(set(signals))}))

    if perms & SMS_READ and exfil:
        add("combo.sms_stealer", Severity.CRITICAL, sorted(perms & SMS_READ) + exfil)

    full_banker = BANKER_PERMS <= perms and (
        perms & SMS_READ or "dex.accessibility_control" in ids)
    yara_banker = "accessibility_overlay_banker" in yara and perms & BANKER_PERMS
    if full_banker or yara_banker:
        add("combo.banker", Severity.CRITICAL, sorted(perms & BANKER_PERMS) + sorted(yara & {"accessibility_overlay_banker"}))

    hidden = ids & {"payloads.embedded_apk", "payloads.embedded_dex"}
    installer = (ids & {"dex.dynamic_loading", "dex.package_install"}) \
        | ({"REQUEST_INSTALL_PACKAGES"} & perms)
    if hidden and installer:
        add("combo.dropper", Severity.CRITICAL, sorted(hidden) + sorted(installer))

    reach = {"ACCESS_BACKGROUND_LOCATION", "READ_CALL_LOG", "READ_CONTACTS"} & perms
    if "RECORD_AUDIO" in perms and (reach or "dex.screen_capture" in ids) and exfil \
            and category_id not in COMMUNICATION_CATEGORIES:
        add("combo.spyware", Severity.HIGH, ["RECORD_AUDIO", *sorted(reach), *exfil])

    # Emulator checks and dynamic loading are routine in advertising SDKs, so they only form a
    # "loader that hides" with a packer, or together with a hidden payload that is not a known SDK's.
    evasion = ids & {"packer.known"}
    if "dex.anti_analysis" in ids and hidden:
        evasion |= {"dex.anti_analysis"}
    if "dex.dynamic_loading" in ids and evasion:
        add("combo.evasive_loader", Severity.HIGH, ["dex.dynamic_loading", *sorted(evasion)])

    if "certificate.debug" in ids and len(heavy) >= 2:
        add("combo.repackaged", Severity.HIGH,
            ["certificate.debug", *sorted(f.params["permission"] for f in heavy)])

    other_high = [f.id for f in report.findings
                  if f.severity >= Severity.HIGH and not f.id.startswith(("authenticity.", "combo."))]
    if "authenticity.mismatch" in ids and other_high:
        add("combo.tampered_known_app", Severity.CRITICAL,
            ["authenticity.mismatch", *sorted(set(other_high))[:5]])
