from __future__ import annotations

import json
from pathlib import Path
import subprocess

from tests.test_x_core_advisory_contract import phase2_report, write_report


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv/bin/python"


def test_export_and_read_cli(tmp_path: Path) -> None:
    report = phase2_report()
    source = write_report(tmp_path, report)
    export_root = tmp_path / "export"
    exported = subprocess.run(
        [
            str(PYTHON),
            "scripts/export_x_core_advisory.py",
            "--x-summary",
            str(source),
            "--weekly",
            str(source),
            "--monthly",
            str(source),
            "--output-root",
            str(export_root),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert exported.returncode == 0, exported.stderr
    assert json.loads(exported.stdout)["count"] == 3

    read = subprocess.run(
        [
            str(PYTHON),
            "scripts/read_x_core_advisory.py",
            "--latest",
            "weekly",
            "--root",
            str(export_root),
            "--now",
            str(report["aggregation"]["as_of"]),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert read.returncode == 0, read.stderr
    payload = json.loads(read.stdout)
    assert payload["status"] == "OK"
    assert payload["snapshot"]["advisory_only"] is True