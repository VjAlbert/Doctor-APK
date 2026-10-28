import zipfile

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
