"""Builds the standalone engine executable that the desktop app ships as a sidecar.

Run from the repository root with the engine installed:  python packaging/build_engine.py
The result lands in packaging/dist/ and is copied to app/src-tauri/binaries/ under
the name Tauri expects: apkguard-<target-triple>[.exe].
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "packaging" / "dist"
BINARIES = ROOT / "app" / "src-tauri" / "binaries"


def target_triple() -> str:
    """The Rust target triple Tauri uses to pick the sidecar file."""
    rustc = shutil.which("rustc")
    if rustc:
        out = subprocess.run([rustc, "-vV"], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            if line.startswith("host:"):
                return line.split(":", 1)[1].strip()
    machine = {"AMD64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}[platform.machine()]
    system = platform.system()
    return {
        "Windows": f"{machine}-pc-windows-msvc",
        "Linux": f"{machine}-unknown-linux-gnu",
        "Darwin": f"{machine}-apple-darwin",
    }[system]


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--name", "apkguard",
        "--distpath", str(DIST), "--workpath", str(ROOT / "packaging" / "build"),
        "--specpath", str(ROOT / "packaging"),
        # androguard.pentest needs frida and exits on import, so collect only what the engine uses.
        "--collect-submodules", "androguard.core",
        "--collect-data", "androguard",
        "--exclude-module", "androguard.pentest",
        "--exclude-module", "androguard.gui",
        "--collect-data", "apkguard",
        "--hidden-import", "yara",
        "--paths", str(ROOT / "engine" / "src"),
        str(ROOT / "packaging" / "entry.py"),
    ]
    subprocess.run(cmd, check=True)
    exe = DIST / ("apkguard.exe" if platform.system() == "Windows" else "apkguard")
    BINARIES.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if exe.suffix == ".exe" else ""
    target = BINARIES / f"apkguard-{target_triple()}{suffix}"
    shutil.copy2(exe, target)
    print(f"built {exe} ({exe.stat().st_size / 1e6:.0f} MB) -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
