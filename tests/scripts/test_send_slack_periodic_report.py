from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_cli_requires_dry_run():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/send_slack_periodic_report.py",
            "weekly",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0


def test_cli_weekly_real_readback_dry_run():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/send_slack_periodic_report.py",
            "weekly",
            "--dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)

    assert payload["report_type"] == "weekly"
    assert payload["dry_run"] is True
    assert payload["blocks"]


def test_cli_send_without_slack_env_fails_before_network():
    env = {
        key: value
        for key, value in __import__("os").environ.items()
        if key not in {
            "SLACK_BOT_TOKEN",
            "SLACK_APPROVAL_CHANNEL_ID",
        }
    }

    result = subprocess.run(
        [
            sys.executable,
            "scripts/send_slack_periodic_report.py",
            "weekly",
            "--send",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 2
    assert (
        "SLACK_CONFIG_ERROR=INVALID_BOT_TOKEN"
        in result.stderr
    )
