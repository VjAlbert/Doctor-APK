import os
import signal
import subprocess
import sys
import textwrap
import time

import pytest

from apkguard import lifecycle

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="process-tree test uses POSIX signals")


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_parent_alive_for_this_process_and_a_dead_one():
    assert lifecycle.parent_alive(os.getpid())
    assert not lifecycle.parent_alive(0) and not lifecycle.parent_alive(-5)
    done = subprocess.Popen([sys.executable, "-c", "pass"])
    done.wait()
    time.sleep(0.2)
    assert not lifecycle.parent_alive(done.pid)


def test_the_engine_exits_when_its_launcher_is_killed(tmp_path):
    """Reproduces the single-file layout: app -> launcher -> engine. Killing the launcher used to leave the engine."""
    pidfile = tmp_path / "engine.pid"
    launcher_code = textwrap.dedent(f"""
        import subprocess, sys, time
        child = subprocess.Popen([sys.executable, "-c", '''
        import os, time
        from apkguard.lifecycle import exit_with_parent
        open({str(pidfile)!r}, "w").write(str(os.getpid()))
        exit_with_parent(interval=0.2)
        time.sleep(60)
        '''])
        time.sleep(60)
    """)
    launcher = subprocess.Popen([sys.executable, "-c", launcher_code])
    for _ in range(100):
        if pidfile.exists() and pidfile.read_text():
            break
        time.sleep(0.1)
    engine_pid = int(pidfile.read_text())
    assert alive(engine_pid)

    launcher.send_signal(signal.SIGKILL)       # what the desktop app does when it closes
    launcher.wait()
    for _ in range(50):
        if not alive(engine_pid):
            break
        time.sleep(0.1)
    try:
        assert not alive(engine_pid), "the engine outlived its launcher"
    finally:
        if alive(engine_pid):
            os.kill(engine_pid, signal.SIGKILL)


def test_serve_accepts_the_flag():
    from apkguard.cli import _build_parser
    args = _build_parser().parse_args(["serve", "--port", "0", "--exit-with-parent"])
    assert args.exit_with_parent is True
