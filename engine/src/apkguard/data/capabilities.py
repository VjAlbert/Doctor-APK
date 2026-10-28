"""What an app can *do*, found through the framework APIs its code references.

Unlike the risk rules in apis.py these are descriptive: most are normal. The
sensitive ones share their ids with the risk rules so both views line up.
"""

from .apis import API_RULES

# (capability id, {class descriptor: {method names}})
NEUTRAL_RULES: list[tuple[str, dict[str, set[str]]]] = [
    ("net.http", {
        "Ljava/net/HttpURLConnection;": {"getOutputStream", "getInputStream", "connect"},
        "Ljava/net/URL;": {"openConnection", "openStream"},
        "Lokhttp3/OkHttpClient;": {"newCall"},
    }),
    ("location", {
        "Landroid/location/LocationManager;": {"getLastKnownLocation", "requestLocationUpdates"},
    }),
    ("camera", {
        "Landroid/hardware/Camera;": {"open"},
        "Landroid/hardware/camera2/CameraManager;": {"openCamera"},
    }),
    ("microphone", {
        "Landroid/media/AudioRecord;": {"startRecording"},
        "Landroid/media/MediaRecorder;": {"start"},
    }),
    ("apps_list", {
        "Landroid/content/pm/PackageManager;": {"getInstalledPackages", "getInstalledApplications"},
    }),
    ("webview", {
        "Landroid/webkit/WebView;": {"loadUrl", "addJavascriptInterface", "evaluateJavascript"},
    }),
    ("crypto", {
        "Ljavax/crypto/Cipher;": {"doFinal", "getInstance"},
    }),
    ("clipboard", {
        "Landroid/content/ClipboardManager;": {"getPrimaryClip", "setPrimaryClip"},
    }),
    ("files", {
        "Ljava/io/FileOutputStream;": {"<init>"},
        "Ljava/io/FileInputStream;": {"<init>"},
    }),
]

SENSITIVE_IDS = [fid for fid, _, _ in API_RULES]
RULES: list[tuple[str, dict[str, set[str]]]] = [
    (fid, targets) for fid, _, targets in API_RULES
] + NEUTRAL_RULES

# Code under these prefixes is almost always a bundled SDK, not the app's own logic.
THIRD_PARTY_PREFIXES = (
    "Landroidx/", "Landroid/support/", "Lcom/google/", "Lcom/facebook/", "Lkotlin/", "Lkotlinx/",
    "Lokhttp3/", "Lokio/", "Lretrofit2/", "Lcom/squareup/", "Lio/reactivex/", "Lorg/apache/",
    "Lcom/unity3d/", "Lcom/applovin/", "Lcom/adjust/", "Lcom/bumptech/", "Lorg/jetbrains/",
    "Lcom/fasterxml/", "Lorg/json/", "Lio/flutter/", "Lcom/airbnb/",
)

# Intent actions that say *when* a component runs.
TRIGGERS = {
    "android.intent.action.BOOT_COMPLETED": "boot",
    "android.provider.Telephony.SMS_RECEIVED": "sms_received",
    "android.intent.action.NEW_OUTGOING_CALL": "outgoing_call",
    "android.intent.action.PACKAGE_ADDED": "app_installed",
    "android.net.conn.CONNECTIVITY_CHANGE": "network_change",
    "android.intent.action.USER_PRESENT": "screen_unlock",
    "android.accessibilityservice.AccessibilityService": "accessibility_event",
    "android.service.notification.NotificationListenerService": "notification",
    "android.app.action.DEVICE_ADMIN_ENABLED": "device_admin",
    "android.intent.action.PHONE_STATE": "phone_state",
}
