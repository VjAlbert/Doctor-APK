"""Builds tiny, harmless APKs for tests.

An APK here is a ZIP holding a hand-encoded binary AndroidManifest.xml, signed
with `jarsigner` (v1). No code is included: the files cannot run anywhere, they
only exercise the manifest and certificate analyzers.
"""

from __future__ import annotations

import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

ANDROID_NS = "http://schemas.android.com/apk/res/android"
NO_INDEX = 0xFFFFFFFF

# Attribute names that carry a framework resource id, in pool order.
RES_IDS = {
    "label": 0x01010001,
    "name": 0x01010003,
    "permission": 0x01010006,
    "debuggable": 0x0101000F,
    "exported": 0x01010010,
    "minSdkVersion": 0x0101020C,
    "targetSdkVersion": 0x01010270,
    "versionCode": 0x0101021B,
    "versionName": 0x0101021C,
}


class _Pool:
    def __init__(self) -> None:
        self.strings: list[str] = []

    def add(self, text: str) -> int:
        if text not in self.strings:
            self.strings.append(text)
        return self.strings.index(text)

    def chunk(self) -> bytes:
        data = bytearray()
        offsets = []
        for s in self.strings:
            offsets.append(len(data))
            data += struct.pack("<H", len(s)) + s.encode("utf-16-le") + b"\0\0"
        while len(data) % 4:
            data += b"\0"
        start = 28 + 4 * len(self.strings)
        size = start + len(data)
        head = struct.pack("<HHIIIIII", 0x0001, 28, size, len(self.strings), 0, 0, start, 0)
        return head + b"".join(struct.pack("<I", o) for o in offsets) + bytes(data)


def _attr_sort(item: tuple[str, object]):
    key = item[0].split(":")[-1]
    return (0, RES_IDS[key]) if key in RES_IDS else (1, key)


def build_manifest(root: tuple) -> bytes:
    """Encode (tag, {attr: value}, [children]) as binary XML.

    Attributes prefixed `android:` use the android namespace; values may be
    str, int or bool.
    """
    pool = _Pool()
    for name in RES_IDS:
        pool.add(name)
    prefix, uri = pool.add("android"), pool.add(ANDROID_NS)

    def walk(node):
        tag, attrs, children = node
        pool.add(tag)
        for key, value in attrs.items():
            pool.add(key.split(":")[-1])
            if isinstance(value, str):
                pool.add(value)
        for child in children:
            walk(child)

    walk(root)
    body = bytearray()
    body += struct.pack("<HHIIIII", 0x0100, 16, 24, 1, NO_INDEX, prefix, uri)

    def emit(node):
        tag, attrs, children = node
        items = sorted(attrs.items(), key=_attr_sort)
        size = 36 + 20 * len(items)
        body.extend(struct.pack("<HHIII", 0x0102, 16, size, 1, NO_INDEX))
        body.extend(struct.pack("<II", NO_INDEX, pool.add(tag)))
        body.extend(struct.pack("<HHHHHH", 20, 20, len(items), 0, 0, 0))
        for key, value in items:
            ns = uri if key.startswith("android:") else NO_INDEX
            name = pool.add(key.split(":")[-1])
            if isinstance(value, bool):
                raw, vtype, data = NO_INDEX, 0x12, 0xFFFFFFFF if value else 0
            elif isinstance(value, int):
                raw, vtype, data = NO_INDEX, 0x10, value
            else:
                raw = data = pool.add(value)
                vtype = 0x03
            body.extend(struct.pack("<IIIHBBI", ns, name, raw, 8, 0, vtype, data))
        for child in children:
            emit(child)
        body.extend(struct.pack("<HHIII", 0x0103, 16, 24, 1, NO_INDEX))
        body.extend(struct.pack("<II", NO_INDEX, pool.add(tag)))

    emit(root)
    body += struct.pack("<HHIIIII", 0x0101, 16, 24, 1, NO_INDEX, prefix, uri)

    res_map = struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(RES_IDS)) + b"".join(
        struct.pack("<I", rid) for rid in RES_IDS.values()
    )
    pool_chunk = pool.chunk()
    total = 8 + len(pool_chunk) + len(res_map) + len(body)
    return struct.pack("<HHI", 0x0003, 8, total) + pool_chunk + res_map + bytes(body)


def manifest_tree(
    package: str,
    *,
    permissions: tuple[str, ...] = (),
    target_sdk: int = 34,
    debuggable: bool = False,
    exported_service: bool = False,
) -> tuple:
    app_attrs: dict[str, object] = {"android:label": "Test App"}
    if debuggable:
        app_attrs["android:debuggable"] = True
    app_children = []
    if exported_service:
        app_children.append(
            ("service", {"android:name": ".SyncService"},
             [("intent-filter", {}, [("action", {"android:name": "com.example.SYNC"}, [])])])
        )
    children = [
        ("uses-sdk", {"android:minSdkVersion": 21, "android:targetSdkVersion": target_sdk}, []),
    ]
    children += [("uses-permission", {"android:name": f"android.permission.{p}"}, []) for p in permissions]
    children.append(("application", app_attrs, app_children))
    return (
        "manifest",
        {"package": package, "android:versionCode": 7, "android:versionName": "1.2.3"},
        children,
    )


def make_keystore(path: Path, dname: str) -> None:
    subprocess.run(
        ["keytool", "-genkeypair", "-keystore", str(path), "-storepass", "testpass",
         "-keypass", "testpass", "-alias", "key", "-keyalg", "RSA", "-keysize", "2048",
         "-validity", "10000", "-dname", dname],
        check=True, capture_output=True,
    )


def build_apk(path: Path, tree: tuple, keystore: Path | None) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("AndroidManifest.xml", build_manifest(tree))
        zf.writestr("classes.dex", b"")
    if keystore is not None:
        subprocess.run(
            ["jarsigner", "-keystore", str(keystore), "-storepass", "testpass",
             "-sigalg", "SHA256withRSA", "-digestalg", "SHA-256", str(path), "key"],
            check=True, capture_output=True,
        )
    return path


def build_xapk(path: Path, base_apk: Path) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(base_apk, "base.apk")
        zf.writestr("manifest.json", '{"split_apks": [{"id": "base", "file": "base.apk"}]}')
    return path


__all__ = ["build_apk", "build_xapk", "make_keystore", "manifest_tree", "shutil"]
