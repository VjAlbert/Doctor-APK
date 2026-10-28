"""Sensitive framework APIs, matched against the DEX method table.

Each rule is (finding id, severity, {class descriptor: {method names}}). A
method reference in the DEX proves the code *can* call the API, not that it
does, so these are signals to be weighed together in the scoring step.
"""

from ..models import Severity

API_RULES: list[tuple[str, Severity, dict[str, set[str]]]] = [
    ("dex.dynamic_loading", Severity.MEDIUM, {
        "Ldalvik/system/DexClassLoader;": {"<init>"},
        "Ldalvik/system/InMemoryDexClassLoader;": {"<init>"},
        "Ldalvik/system/DexFile;": {"loadDex", "openDexFile"},
    }),
    ("dex.shell_exec", Severity.MEDIUM, {
        "Ljava/lang/Runtime;": {"exec"},
        "Ljava/lang/ProcessBuilder;": {"start"},
    }),
    ("dex.sms_api", Severity.MEDIUM, {
        "Landroid/telephony/SmsManager;": {
            "sendTextMessage", "sendMultipartTextMessage", "sendDataMessage"},
    }),
    ("dex.device_admin_abuse", Severity.HIGH, {
        "Landroid/app/admin/DevicePolicyManager;": {
            "lockNow", "resetPassword", "wipeData", "resetPasswordWithToken"},
    }),
    ("dex.accessibility_control", Severity.MEDIUM, {
        "Landroid/accessibilityservice/AccessibilityService;": {
            "performGlobalAction", "dispatchGesture"},
        "Landroid/view/accessibility/AccessibilityNodeInfo;": {"performAction"},
    }),
    ("dex.screen_capture", Severity.MEDIUM, {
        "Landroid/media/projection/MediaProjectionManager;": {
            "createScreenCaptureIntent", "getMediaProjection"},
    }),
    ("dex.device_identifiers", Severity.LOW, {
        "Landroid/telephony/TelephonyManager;": {
            "getDeviceId", "getImei", "getSubscriberId",
            "getLine1Number", "getSimSerialNumber"},
    }),
    ("dex.package_install", Severity.MEDIUM, {
        "Landroid/content/pm/PackageInstaller$Session;": {"commit"},
    }),
]

# Class-name prefixes (DEX descriptors) left by commercial packers.
PACKER_CLASSES: dict[str, str] = {
    "Lcom/qihoo/util/StubApp": "360 Jiagu",
    "Lcom/tencent/StubShell/": "Tencent Legu",
    "Lcom/secneo/": "SecNeo",
    "Lcom/baidu/protect/": "Baidu Protect",
    "Lcom/ali/mobisecenhance/": "Alibaba Security",
    "Lcom/bangcle/": "Bangcle",
    "Ls/h/e/l/l/": "Ijiami",
}

# Native library file names left by the same packers.
PACKER_LIBS: dict[str, str] = {
    "libjiagu.so": "360 Jiagu",
    "libjiagu_a64.so": "360 Jiagu",
    "libsecexe.so": "SecNeo",
    "libsecmain.so": "SecNeo",
    "libDexHelper.so": "SecNeo",
    "libbaiduprotect.so": "Baidu Protect",
    "libmobisec.so": "Alibaba Security",
    "libexec.so": "Ijiami",
    "libexecmain.so": "Ijiami",
    "libprotectClass.so": "Bangcle",
    "libnqshield.so": "NQ Shield",
}

EMULATOR_MARKERS = (
    "ro.kernel.qemu", "goldfish", "ranchu", "vbox86", "Genymotion",
    "sdk_gphone", "generic_x86", "ro.hardware.virtual",
)

ROOT_MARKERS = (
    "/system/xbin/su", "/system/bin/su", "/sbin/su", "Superuser.apk",
    "eu.chainfire.supersu", "com.noshufou.android.su", "com.topjohnwu.magisk",
)

# Free dynamic-DNS / tunnelling services: rare in legitimate production apps.
DYNAMIC_DNS_SUFFIXES = (
    ".duckdns.org", ".no-ip.org", ".no-ip.biz", ".ddns.net", ".hopto.org",
    ".zapto.org", ".serveo.net", ".ngrok.io", ".ngrok-free.app", ".trycloudflare.com",
)

# An API finding is only meaningful when the app also holds the matching role or permission
# (requested with <uses-permission> or required by one of its own components).
API_GATES: dict[str, set[str]] = {
    "dex.accessibility_control": {"BIND_ACCESSIBILITY_SERVICE"},
    "dex.device_admin_abuse": {"BIND_DEVICE_ADMIN"},
    "dex.sms_api": {"SEND_SMS", "RECEIVE_SMS", "READ_SMS"},
    "dex.package_install": {"REQUEST_INSTALL_PACKAGES"},
}
