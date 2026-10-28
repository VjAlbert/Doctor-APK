"""Keeps the engine from outliving the app that started it.

A single-file executable made with PyInstaller runs as two processes: a small launcher, which the
desktop app starts (and later kills), and the real engine, started by the launcher. Killing the
launcher does not kill the engine, so it used to stay behind, keep running, and lock its own file,
which stopped an upgrade from replacing it. The engine now watches its parent and exits with it.
"""

from __future__ import annotations

import os
import sys
import threading
import time

WAIT_TIMEOUT = 0x102
SYNCHRONIZE = 0x00100000


def parent_alive(pid: int) -> bool:
    """Is process `pid` still running?"""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def exit_with_parent(interval: float = 1.0) -> threading.Thread:
    """Starts a background thread that ends this process once the parent is gone."""
    parent = os.getppid()

    def watch() -> None:
        while True:
            time.sleep(interval)
            gone = not parent_alive(parent) or (sys.platform != "win32" and os.getppid() != parent)
            if gone:
                os._exit(0)

    thread = threading.Thread(target=watch, name="exit-with-parent", daemon=True)
    thread.start()
    return thread
