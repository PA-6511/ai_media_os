from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_sample_dry_run_is_redacted(
    tmp_path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output = tmp_path / "slack_dry_run.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_slack_approval_dry_run.py",
            "--sample",
            "--output",
            str(output),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output.exists()

    document = json.loads(
        output.read_text(encoding="utf-8")
    )

    serialized = json.dumps(
        document,
        ensure_ascii=False,
    )

    assert document["dry_run"] is True
    assert document["network_called"] is False
    assert (
        document["action_tokens_redacted"]
        is True
    )
    assert "[REDACTED]" in serialized
    assert (
        "sample-approval-token-"
        "never-use-in-production"
        not in serialized
    )
