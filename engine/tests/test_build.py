import json
import subprocess
import sys
from pathlib import Path

import apkguard
from apkguard import cli
from apkguard.pipeline import analyze_apk

STAMP = Path(__file__).resolve().parents[2] / "packaging" / "stamp_build.py"


def test_every_report_says_which_engine_made_it(benign_apk):
    report = analyze_apk(benign_apk)
    assert report.engine == apkguard.version_info() and report.engine["build"]
    assert report.to_dict()["engine"]["version"] == apkguard.__version__


def test_cli_version_shows_the_build(capsys):
    try:
        cli.main(["--version"])
    except SystemExit:
        pass
    assert f"build {apkguard.BUILD}" in capsys.readouterr().out


def test_stamp_script_writes_a_short_id(tmp_path, monkeypatch):
    target = tmp_path / "_build.py"
    source = STAMP.read_text().replace(
        'TARGET = Path(__file__).resolve().parent.parent / "engine" / "src" / "apkguard" / "_build.py"',
        f'TARGET = Path({str(target)!r})')
    script = tmp_path / "stamp.py"
    script.write_text(source)
    out = subprocess.run([sys.executable, str(script), "0123456789abcdef"], capture_output=True, text=True, check=True)
    assert "0123456" in out.stdout
    ns: dict = {}
    exec(target.read_text(), ns)
    assert ns["BUILD"] == "0123456"
