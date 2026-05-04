from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from blocks.dummy_block.block import DummyBlock
from shared.block_manifest_loader import load_block_manifest, validate_block_manifest


BASE_DIR = Path(__file__).resolve().parents[1]


def test_dummy_block_manifest_is_valid() -> None:
    manifest = load_block_manifest("blocks/dummy_block/block_manifest.json")
    result = validate_block_manifest(manifest)

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["block_id"] == "dummy_block"
    assert result["risk_level"] == "low"


def test_dummy_block_handshake() -> None:
    block = DummyBlock()
    hs = block.handshake()

    assert hs["ok"] is True
    assert hs["block_id"] == "dummy_block"
    assert hs["protocol"] == "phase2-handshake-v1"


def test_dummy_block_authority_decisions_and_log_validation(tmp_path: Path) -> None:
    block = DummyBlock()
    log_path = tmp_path / "phase2_runtime.ndjson"

    approve = block.request_execution(
        actor="tester",
        action="test",
        target="blocks/dummy_block/block.py",
        run_id="dummy-test-run",
        log_path=log_path,
        kpi={
            "failsafe_coverage": 1.0,
            "freeze_correctness": 0.96,
            "policy_deny_delta": 1.0,
            "warning_streak": 0,
        },
    )
    escalate = block.request_execution(
        actor="tester",
        action="update",
        target="core/verification/failure_report.py",
        run_id="dummy-test-run",
        log_path=log_path,
        kpi={
            "failsafe_coverage": 1.0,
            "freeze_correctness": 0.96,
            "policy_deny_delta": 1.0,
            "warning_streak": 0,
        },
    )
    deny = block.request_execution(
        actor="tester",
        action="delete",
        target="blocks/dummy_block/block.py",
        run_id="dummy-test-run",
        log_path=log_path,
        kpi={
            "failsafe_coverage": 1.0,
            "freeze_correctness": 0.96,
            "policy_deny_delta": 1.0,
            "warning_streak": 0,
        },
    )

    assert approve["decision"] == "APPROVE"
    assert escalate["decision"] == "ESCALATE"
    assert deny["decision"] == "DENY"

    proc = subprocess.run(
        [
            sys.executable,
            str(BASE_DIR / "tools" / "validate_phase2_logs.py"),
            "--input",
            str(log_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert "result=OK" in proc.stdout
