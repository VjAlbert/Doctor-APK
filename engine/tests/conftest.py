import os
import zipfile
from pathlib import Path

import pytest

import apkbuilder as b

pytest_plugins: list[str] = []


@pytest.fixture(scope="session")
def work(tmp_path_factory):
    return tmp_path_factory.mktemp("apks")


@pytest.fixture(scope="session")
def good_keystore(work):
    path = work / "good.jks"
    b.make_keystore(path, "CN=Test Developer, O=Example, C=IT")
    return path


@pytest.fixture(scope="session")
def debug_keystore(work):
    path = work / "debug.jks"
    b.make_keystore(path, "CN=Android Debug, O=Android, C=US")
    return path


@pytest.fixture(scope="session")
def benign_apk(work, good_keystore):
    tree = b.manifest_tree("com.example.benign", permissions=("INTERNET",))
    return b.build_apk(work / "benign.apk", tree, good_keystore)


@pytest.fixture(scope="session")
def suspicious_apk(work, debug_keystore):
    tree = b.manifest_tree(
        "com.example.flashlight",
        permissions=("INTERNET", "READ_SMS", "SEND_SMS", "SYSTEM_ALERT_WINDOW"),
        target_sdk=21,
        debuggable=True,
        exported_service=True,
    )
    return b.build_apk(work / "suspicious.apk", tree, debug_keystore)


@pytest.fixture(scope="session")
def dropper_apk(work, debug_keystore):
    """Harmless APK that *looks* like a dropper to the static analyzers."""
    dex = b.build_dex(
        strings=[
            "https://api.telegram.org/bot123:ABC/sendMessage",
            "http://8.8.8.8/gate.php",
            "http://evil-host.duckdns.org/c2",
            "content://sms/inbox",
            "ro.kernel.qemu", "goldfish",
            "https://example.com/privacy",
        ],
        methods=[
            ("Ldalvik/system/DexClassLoader;", "<init>"),
            ("Ljava/lang/Runtime;", "exec"),
            ("Landroid/telephony/SmsManager;", "sendTextMessage"),
        ],
    )
    inner = work / "inner.apk"
    b.build_apk(inner, b.manifest_tree("com.example.inner"), None)
    extra = {
        "assets/logo.png": inner.read_bytes(),
        "assets/payload.dat": os.urandom(120_000),  # high entropy, no known type
        "assets/helper.bin": b"\x7fELF" + b"\0" * 64,
        "assets/stage2": dex,
        "lib/arm64-v8a/libjiagu.so": b"\x7fELF" + b"\0" * 64,
    }
    tree = b.manifest_tree("com.example.dropper", permissions=("RECEIVE_SMS",))
    return b.build_apk(work / "dropper.apk", tree, debug_keystore, dex=dex, extra=extra)


@pytest.fixture(scope="session")
def messenger_apk(work, good_keystore):
    perms = ("READ_SMS", "SEND_SMS", "RECEIVE_SMS", "READ_CONTACTS", "CAMERA", "INTERNET")
    tree = b.manifest_tree("com.example.chat", permissions=perms, label="Secure Chat")
    return b.build_apk(work / "messenger.apk", tree, good_keystore)


@pytest.fixture(scope="session")
def torch_apk(work, good_keystore):
    perms = ("READ_SMS", "SEND_SMS", "READ_CONTACTS", "SYSTEM_ALERT_WINDOW", "CAMERA")
    tree = b.manifest_tree("com.example.torch", permissions=perms, label="Super Torch")
    return b.build_apk(work / "torch.apk", tree, good_keystore)


@pytest.fixture(scope="session")
def unsigned_apk(work):
    tree = b.manifest_tree("com.example.unsigned")
    return b.build_apk(work / "unsigned.apk", tree, None)


@pytest.fixture(scope="session")
def xapk(work, benign_apk):
    return b.build_xapk(work / "bundle.xapk", benign_apk)


@pytest.fixture(scope="session")
def traversal_zip(work, benign_apk):
    path = work / "traversal.apk"
    with zipfile.ZipFile(benign_apk) as src, zipfile.ZipFile(path, "w") as dst:
        for info in src.infolist():
            dst.writestr(info.filename, src.read(info.filename))
        dst.writestr("../../evil.txt", b"x")
    return path


@pytest.fixture(scope="session")
def zip_bomb(work):
    path = work / "bomb.apk"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("AndroidManifest.xml", b"\0" * (60 * 1024 * 1024))
    return path


@pytest.fixture
def plain_text(work):
    path = work / "note.apk"
    path.write_text("not a zip")
    return path


DEMO_DEX = Path(__file__).parent / "data" / "demo" / "classes.dex"


@pytest.fixture(scope="session")
def demo_apk(work, good_keystore):
    """An APK around real compiled code (see tests/data/demo/build.sh)."""
    components = (
        ("activity", {"android:name": "com.example.demo.Notes"},
         [("intent-filter", {}, [("action", {"android:name": "android.intent.action.MAIN"}, []),
                                 ("category", {"android:name": "android.intent.category.LAUNCHER"}, [])])]),
        ("receiver", {"android:name": "com.example.demo.SmsForwarder", "android:exported": True},
         [("intent-filter", {}, [("action", {"android:name": "android.provider.Telephony.SMS_RECEIVED"}, [])])]),
    )
    tree = b.manifest_tree("com.example.demo", permissions=("INTERNET", "RECEIVE_SMS"), components=components,
                           label="Demo Notes")
    return b.build_apk(work / "demo.apk", tree, good_keystore, dex=DEMO_DEX.read_bytes())
