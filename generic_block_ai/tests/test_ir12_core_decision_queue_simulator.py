import json
from pathlib import Path

from generic_block_ai.app.core_decision_queue_simulator import (
    build_core_decision_queue_item,
    run_ir12_core_decision_queue_dryrun,
    write_ir12_completion_report,
)


def _receiver_report(judgment: str) -> dict:
    mapping = {
        "PASS": "ACCEPT_DRY_RUN_REVIEW_QUEUE",
        "WARN": "HUMAN_REVIEW_REQUIRED",
        "FAIL": "REJECT_AND_KEEP_NO_GO",
        "ABORT": "BLOCK_AND_PRESERVE_AUDIT_EVIDENCE",
    }
    return {
        "schema_version": "ir11_core_receiver_v1",
        "phase": "IR11",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_task_id": f"receiver_{judgment.lower()}",
        "quality_gate_judgment": judgment,
        "core_receive_rule": mapping[judgment],
        "validation_result": "PASS",
        "validation_failed_checks": [],
        "validation_warnings": [],
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }


def test_build_core_decision_queue_item_pass() -> None:
    output = build_core_decision_queue_item(
        receiver_report=_receiver_report("PASS"),
        source_task_id="ir12_build_pass",
    )
    item = output["queue_item"]
    assert item["quality_gate_judgment"] == "PASS"
    assert item["queue_state"] == "READY_FOR_DRY_RUN_REVIEW"
    assert item["execution_allowed"] is False
    assert len(output["state_transitions"]) == 2


def test_run_ir12_core_decision_queue_dryrun_all_judgments(tmp_path: Path) -> None:
    expected_states = {
        "PASS": "READY_FOR_DRY_RUN_REVIEW",
        "WARN": "WAITING_HUMAN_REVIEW",
        "FAIL": "REJECTED_NO_GO",
        "ABORT": "ABORT_EVIDENCE_LOCKED",
    }

    for judgment, state in expected_states.items():
        output = run_ir12_core_decision_queue_dryrun(
            base_path=tmp_path,
            source_task_id=f"ir12_{judgment.lower()}",
            receiver_report=_receiver_report(judgment),
        )
        loaded = json.loads(Path(output["path"]).read_text(encoding="utf-8"))
        assert loaded["quality_gate_judgment"] == judgment
        assert loaded["queue_item"]["queue_state"] == state
        assert loaded["execution_policy"]["execute"] is False
        assert loaded["queue_validation_result"] == "PASS"

    audit_log = tmp_path / "reports" / "ir12_core_decision_queue_audit.log"
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 4


def test_run_ir12_core_decision_queue_dryrun_detects_receiver_rule_mismatch(tmp_path: Path) -> None:
    receiver = _receiver_report("PASS")
    receiver["core_receive_rule"] = "HUMAN_REVIEW_REQUIRED"
    output = run_ir12_core_decision_queue_dryrun(
        base_path=tmp_path,
        source_task_id="ir12_mismatch",
        receiver_report=receiver,
    )
    loaded = json.loads(Path(output["path"]).read_text(encoding="utf-8"))
    assert loaded["queue_validation_result"] == "FAIL"
    assert loaded["queue_validation_failed_checks"]


def test_write_ir12_completion_report(tmp_path: Path) -> None:
    outputs = [
        run_ir12_core_decision_queue_dryrun(
            base_path=tmp_path,
            source_task_id="ir12_complete_warn",
            receiver_report=_receiver_report("WARN"),
        ),
        run_ir12_core_decision_queue_dryrun(
            base_path=tmp_path,
            source_task_id="ir12_complete_abort",
            receiver_report=_receiver_report("ABORT"),
        ),
    ]
    completion = write_ir12_completion_report(
        base_path=tmp_path,
        ir12_outputs=outputs,
        focused_tests={"passed": 10, "failed": 0},
        full_regression={"passed": 138, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 12"
    assert loaded["status"] == "COMPLETED"
    assert loaded["summary"]["execution_triggered"] is False
    assert loaded["test_result"]["focused_tests"]["passed"] == 10
