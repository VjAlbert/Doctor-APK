"""Bundled SDKs known to ship their own code inside assets, so it is not flagged as a hidden payload."""

# path prefix inside the APK -> SDK name
KNOWN_SDK_PAYLOADS: dict[str, str] = {
    "assets/audience_network/": "Meta Audience Network",
    "assets/audience_network.dex": "Meta Audience Network",
}
