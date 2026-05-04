from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from blocks.ebook_affiliate_block.block import EbookAffiliateBlock
from shared.block_manifest_loader import load_block_manifest, validate_block_manifest


BASE_DIR = Path(__file__).resolve().parents[1]


def test_ebook_affiliate_manifest_is_valid() -> None:
    manifest = load_block_manifest("blocks/ebook_affiliate_block/block_manifest.json")
    result = validate_block_manifest(manifest)

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["block_id"] == "ebook_affiliate_block"


def test_ebook_affiliate_handshake() -> None:
    block = EbookAffiliateBlock()
    hs = block.handshake()

    assert hs["ok"] is True
    assert hs["block_id"] == "ebook_affiliate_block"
    assert hs["protocol"] == "phase2-handshake-v1"


def test_ebook_affiliate_authority_and_phase2_log_pipeline(tmp_path: Path) -> None:
    block = EbookAffiliateBlock()
    log_path = tmp_path / "phase2_runtime.ndjson"

    approve = block.request_execution(
        actor="tester",
        action="test",
        target="blocks/ebook_affiliate_block/block.py",
        run_id="ebook-block-test",
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
        run_id="ebook-block-test",
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
        target="blocks/ebook_affiliate_block/block.py",
        run_id="ebook-block-test",
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

    validate_proc = subprocess.run(
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
    assert validate_proc.returncode == 0, validate_proc.stdout + "\n" + validate_proc.stderr
    assert "result=OK" in validate_proc.stdout

    kpi_proc = subprocess.run(
        [
            sys.executable,
            str(BASE_DIR / "tools" / "phase2_kpi_report.py"),
            "--input",
            str(log_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert kpi_proc.returncode == 0, kpi_proc.stdout + "\n" + kpi_proc.stderr
    assert "final_decision=CONTINUE" in kpi_proc.stdout
