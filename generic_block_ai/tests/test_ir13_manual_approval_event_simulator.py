import json
from pathlib import Path

from generic_block_ai.app.core_decision_queue_simulator import run_ir12_core_decision_queue_dryrun
from generic_block_ai.app.core_manual_approval_event_simulator import (
    run_ir13_manual_approval_event_dryrun,
    validate_manual_approval_event,
    write_ir13_completion_report,
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


def _queue_report(tmp_path: Path, judgment: str, source_task_id: str) -> dict:
    out = run_ir12_core_decision_queue_dryrun(
        base_path=tmp_path,
        source_task_id=source_task_id,
        receiver_report=_receiver_report(judgment),
    )
    return out["queue_report"]


def test_validate_manual_approval_event_schema_and_event() -> None:
    report = {
        "schema_version": "ir12_core_decision_queue_v1",
        "queue_item": {"queue_state": "WAITING_HUMAN_REVIEW"},
        "queue_validation_result": "PASS",
        "execution_policy": {"execute": False},
        "safeguards": {"external_write_executed": False},
    }
    ok = validate_manual_approval_event(queue_report=report, event="APPROVE")
    assert ok["result"] == "PASS"

    ng = validate_manual_approval_event(queue_report=report, event="INVALID")
    assert ng["result"] == "FAIL"
    assert ng["failed_checks"]


def test_run_ir13_apply_approve_event(tmp_path: Path) -> None:
    queue_report = _queue_report(tmp_path, "WARN", "ir13_warn")
    out = run_ir13_manual_approval_event_dryrun(
        base_path=tmp_path,
        source_task_id="ir13_warn",
        queue_report=queue_report,
        event="APPROVE",
        actor="human_reviewer_a",
        comment="approve for dry-run queue",
    )

    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["event_validation_result"] == "PASS"
    assert loaded["queue_item"]["queue_state"] == "APPROVED_DRY_RUN_PENDING_RELEASE"
    assert loaded["execution_policy"]["execute"] is False
    assert loaded["state_transitions"][-1]["event"] == "manual_approve"


def test_run_ir13_apply_request_fix_event(tmp_path: Path) -> None:
    queue_report = _queue_report(tmp_path, "PASS", "ir13_pass")
    out = run_ir13_manual_approval_event_dryrun(
        base_path=tmp_path,
        source_task_id="ir13_pass",
        queue_report=queue_report,
        event="REQUEST_FIX",
        actor="human_reviewer_b",
        comment="needs additional safeguards",
    )
    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["event_validation_result"] == "PASS"
    assert loaded["queue_item"]["queue_state"] == "NEEDS_FIX_REWORK"


def test_run_ir13_abort_unlock_is_blocked(tmp_path: Path) -> None:
    queue_report = _queue_report(tmp_path, "ABORT", "ir13_abort")
    out = run_ir13_manual_approval_event_dryrun(
        base_path=tmp_path,
        source_task_id="ir13_abort",
        queue_report=queue_report,
        event="APPROVE",
        actor="human_reviewer_c",
        comment="attempt unlock should fail",
    )

    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["event_validation_result"] == "FAIL"
    assert loaded["queue_item"]["queue_state"] == "ABORT_EVIDENCE_LOCKED"
    assert loaded["event_validation_failed_checks"]


def test_run_ir13_invalid_transition_is_blocked(tmp_path: Path) -> None:
    queue_report = _queue_report(tmp_path, "FAIL", "ir13_fail")
    out = run_ir13_manual_approval_event_dryrun(
        base_path=tmp_path,
        source_task_id="ir13_fail",
        queue_report=queue_report,
        event="APPROVE",
        actor="human_reviewer_d",
        comment="approve from rejected state is not allowed",
    )

    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["event_validation_result"] == "FAIL"
    assert loaded["queue_item"]["queue_state"] == "REJECTED_NO_GO"


def test_write_ir13_completion_report(tmp_path: Path) -> None:
    warn_report = _queue_report(tmp_path, "WARN", "ir13_complete_warn")
    abort_report = _queue_report(tmp_path, "ABORT", "ir13_complete_abort")

    outputs = [
        run_ir13_manual_approval_event_dryrun(
            base_path=tmp_path,
            source_task_id="ir13_complete_warn",
            queue_report=warn_report,
            event="APPROVE",
            actor="human_reviewer_e",
        ),
        run_ir13_manual_approval_event_dryrun(
            base_path=tmp_path,
            source_task_id="ir13_complete_abort",
            queue_report=abort_report,
            event="APPROVE",
            actor="human_reviewer_f",
        ),
    ]

    completion = write_ir13_completion_report(
        base_path=tmp_path,
        ir13_outputs=outputs,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 144, "failed": 0},
    )
    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))

    assert loaded["phase"] == "Implementation Restart Phase 13"
    assert loaded["status"] == "COMPLETED"
    assert loaded["summary"]["abort_unlock_prevented"] is True
    assert loaded["summary"]["execution_triggered"] is False
