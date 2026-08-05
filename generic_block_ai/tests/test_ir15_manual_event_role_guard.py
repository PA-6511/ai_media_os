import json
from pathlib import Path

from generic_block_ai.app.core_decision_queue_simulator import run_ir12_core_decision_queue_dryrun
from generic_block_ai.app.core_manual_approval_event_simulator import run_ir13_manual_approval_event_dryrun
from generic_block_ai.app.core_manual_event_role_guard import (
    run_ir15_manual_event_role_guard_dryrun,
    validate_role_guard_input,
    write_ir15_completion_report,
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


def _ir13_report(tmp_path: Path, judgment: str, event: str, actor: str) -> dict:
    ir12 = run_ir12_core_decision_queue_dryrun(
        base_path=tmp_path,
        source_task_id=f"ir12_{judgment.lower()}",
        receiver_report=_receiver_report(judgment),
    )
    ir13 = run_ir13_manual_approval_event_dryrun(
        base_path=tmp_path,
        source_task_id=f"ir13_{judgment.lower()}",
        queue_report=ir12["queue_report"],
        event=event,
        actor=actor,
    )
    return ir13["ir13_report"]


def test_validate_role_guard_input_pass(tmp_path: Path) -> None:
    ir13_report = _ir13_report(tmp_path, "PASS", "APPROVE", "alice")
    result = validate_role_guard_input(
        ir13_report=ir13_report,
        actor_roles={"alice": "approver"},
    )
    assert result["result"] in {"PASS", "WARN"}
    assert not result["failed_checks"]
    assert "APPROVE" in result["resolved_role_policy"]


def test_role_guard_blocks_unauthorized_role(tmp_path: Path) -> None:
    ir13_report = _ir13_report(tmp_path, "PASS", "APPROVE", "bob")
    out = run_ir15_manual_event_role_guard_dryrun(
        base_path=tmp_path,
        source_task_id="ir15_unauthorized",
        ir13_report=ir13_report,
        actor_roles={"bob": "reviewer"},
    )
    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["role_guard_result"] == "FAIL"
    assert any("not allowed" in item for item in loaded["role_guard_failed_checks"])
    assert loaded["role_policy_hash"]


def test_role_guard_allows_request_fix_for_reviewer(tmp_path: Path) -> None:
    ir13_report = _ir13_report(tmp_path, "WARN", "REQUEST_FIX", "carol")
    out = run_ir15_manual_event_role_guard_dryrun(
        base_path=tmp_path,
        source_task_id="ir15_request_fix",
        ir13_report=ir13_report,
        actor_roles={"carol": "reviewer"},
    )
    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["role_guard_result"] in {"PASS", "WARN"}


def test_role_guard_blocks_missing_actor_mapping(tmp_path: Path) -> None:
    ir13_report = _ir13_report(tmp_path, "FAIL", "REJECT", "dave")
    out = run_ir15_manual_event_role_guard_dryrun(
        base_path=tmp_path,
        source_task_id="ir15_missing_actor",
        ir13_report=ir13_report,
        actor_roles={"other": "approver"},
    )
    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["role_guard_result"] == "FAIL"
    assert any("actor role is not defined" in item for item in loaded["role_guard_failed_checks"])


def test_role_guard_blocks_abort_override_even_admin(tmp_path: Path) -> None:
    ir13_report = _ir13_report(tmp_path, "ABORT", "APPROVE", "erin")
    out = run_ir15_manual_event_role_guard_dryrun(
        base_path=tmp_path,
        source_task_id="ir15_abort_override",
        ir13_report=ir13_report,
        actor_roles={"erin": "admin"},
    )
    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["role_guard_result"] == "FAIL"
    assert any("ABORT evidence lock override is prohibited" in item for item in loaded["role_guard_failed_checks"])


def test_write_ir15_completion_report(tmp_path: Path) -> None:
    outputs = [
        run_ir15_manual_event_role_guard_dryrun(
            base_path=tmp_path,
            source_task_id="ir15_complete_pass",
            ir13_report=_ir13_report(tmp_path, "PASS", "APPROVE", "frank"),
            actor_roles={"frank": "approver"},
        ),
        run_ir15_manual_event_role_guard_dryrun(
            base_path=tmp_path,
            source_task_id="ir15_complete_abort",
            ir13_report=_ir13_report(tmp_path, "ABORT", "APPROVE", "grace"),
            actor_roles={"grace": "admin"},
        ),
    ]

    completion = write_ir15_completion_report(
        base_path=tmp_path,
        ir15_outputs=outputs,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 156, "failed": 0},
    )
    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 15"
    assert loaded["status"] == "COMPLETED"
    assert loaded["summary"]["abort_override_blocked"] is True
