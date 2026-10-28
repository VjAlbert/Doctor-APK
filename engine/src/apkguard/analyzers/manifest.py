"""AndroidManifest analysis: app identity, permissions, risky flags."""

from __future__ import annotations

from androguard.core.apk import APK

from ..data.permissions import SENSITIVE_PERMISSIONS
from ..models import Finding, Report, Severity

MODULE = "manifest"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
OLD_TARGET_SDK = 23  # below this, permissions are granted at install time


def _attr(element, name: str):
    return element.get(ANDROID_NS + name)


def _as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _exported_components(xml) -> dict[str, list[str]]:
    """Non-activity components reachable by other apps without a permission."""
    exposed: dict[str, list[str]] = {}
    app = xml.find("application")
    if app is None:
        return exposed
    for tag in ("service", "receiver", "provider"):
        for comp in app.findall(tag):
            exported = _attr(comp, "exported")
            if exported is None:
                # Pre-Android 12 default: exported iff it declares intent filters.
                exported = "true" if comp.find("intent-filter") is not None else "false"
            guard = _attr(comp, "permission")
            if exported == "true" and not guard:
                exposed.setdefault(tag, []).append(_attr(comp, "name") or "?")
    return exposed


def analyze(apk: APK, report: Report) -> None:
    permissions = sorted(set(apk.get_permissions()))
    report.permissions = permissions
    min_sdk = _as_int(apk.get_min_sdk_version())
    target_sdk = _as_int(apk.get_target_sdk_version())
    report.app = {
        "package": apk.get_package(),
        "name": apk.get_app_name(),
        "version_name": apk.get_androidversion_name(),
        "version_code": apk.get_androidversion_code(),
        "min_sdk": min_sdk,
        "target_sdk": target_sdk,
    }

    for permission in permissions:
        short = permission.rsplit(".", 1)[-1]
        severity = SENSITIVE_PERMISSIONS.get(short)
        if severity is not None:
            report.add(
                Finding(
                    "manifest.permission",
                    severity,
                    MODULE,
                    {"permission": short, "full_name": permission},
                )
            )

    xml = apk.get_android_manifest_xml()
    app = xml.find("application")
    if app is not None:
        if _attr(app, "debuggable") == "true":
            report.add(Finding("manifest.debuggable", Severity.MEDIUM, MODULE))
        if _attr(app, "usesCleartextTraffic") == "true":
            report.add(Finding("manifest.cleartext_traffic", Severity.LOW, MODULE))

    exposed = _exported_components(xml)
    if exposed:
        count = sum(len(v) for v in exposed.values())
        report.add(
            Finding(
                "manifest.exported_components",
                Severity.LOW,
                MODULE,
                {"count": count, "kinds": sorted(exposed), "names": sum(exposed.values(), [])[:10]},
            )
        )

    if target_sdk is not None and target_sdk < OLD_TARGET_SDK:
        report.add(
            Finding(
                "manifest.old_target_sdk",
                Severity.MEDIUM,
                MODULE,
                {"target_sdk": target_sdk},
            )
        )
