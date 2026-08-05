import json
from pathlib import Path

from generic_block_ai.app.core_decision_queue_simulator import run_ir12_core_decision_queue_dryrun
from generic_block_ai.app.core_manual_approval_event_simulator import run_ir13_manual_approval_event_dryrun
from generic_block_ai.app.core_manual_event_role_guard import run_ir15_manual_event_role_guard_dryrun
from generic_block_ai.app.core_role_policy_versioning import (
    run_ir17_role_policy_versioning_dryrun,
    validate_role_policy_schema,
    write_ir17_completion_report,
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


def _prepare_ir15_reports(tmp_path: Path) -> list[str]:
    targets = [
        ("PASS", "APPROVE", "human_reviewer_pass", "approver"),
        ("WARN", "REQUEST_FIX", "human_reviewer_warn", "reviewer"),
        ("FAIL", "REJECT", "human_reviewer_fail", "reviewer"),
        ("ABORT", "APPROVE", "human_reviewer_abort", "admin"),
    ]

    paths: list[str] = []
    for judgment, event, actor, role in targets:
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
        ir15 = run_ir15_manual_event_role_guard_dryrun(
            base_path=tmp_path,
            source_task_id=f"ir15_{judgment.lower()}",
            ir13_report=ir13["ir13_report"],
            actor_roles={actor: role},
        )
        paths.append(ir15["path"])
    return paths


def test_validate_role_policy_schema_pass() -> None:
    result = validate_role_policy_schema(
        {
            "APPROVE": ["approver", "admin"],
            "REJECT": ["reviewer", "admin"],
            "REQUEST_FIX": ["reviewer"],
        }
    )
    assert result["result"] == "PASS"
    assert not result["failed_checks"]


def test_ir17_versioning_pass_with_aligned_ir15(tmp_path: Path) -> None:
    ir15_paths = _prepare_ir15_reports(tmp_path)
    out = run_ir17_role_policy_versioning_dryrun(
        base_path=tmp_path,
        source_task_id="ir17_pass",
        ir15_report_paths=ir15_paths,
    )
    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["validation_result"] == "PASS"
    assert loaded["ir15_alignment"]["checked_reports"] == 4


def test_ir17_detects_ir15_hash_mismatch(tmp_path: Path) -> None:
    ir15_paths = _prepare_ir15_reports(tmp_path)

    target = Path(ir15_paths[0])
    report = json.loads(target.read_text(encoding="utf-8"))
    report["role_policy_hash"] = "deadbeef"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir17_role_policy_versioning_dryrun(
        base_path=tmp_path,
        source_task_id="ir17_hash_mismatch",
        ir15_report_paths=ir15_paths,
    )
    result = out["versioning_report"]
    assert result["validation_result"] == "FAIL"
    assert any("role_policy_hash mismatch" in item for item in result["validation_failed_checks"])


def test_ir17_writes_change_audit_and_detects_update(tmp_path: Path) -> None:
    ir15_paths = _prepare_ir15_reports(tmp_path)

    first = run_ir17_role_policy_versioning_dryrun(
        base_path=tmp_path,
        source_task_id="ir17_first",
        ir15_report_paths=ir15_paths,
    )
    assert first["versioning_report"]["change_audit"]["change_type"] == "initial"

    second_policy = {
        "APPROVE": ["admin"],
        "REJECT": ["reviewer", "admin"],
        "REQUEST_FIX": ["reviewer", "admin"],
    }
    second = run_ir17_role_policy_versioning_dryrun(
        base_path=tmp_path,
        source_task_id="ir17_second",
        role_policy=second_policy,
        ir15_report_paths=ir15_paths,
    )
    assert second["versioning_report"]["change_audit"]["change_type"] == "updated"


def test_write_ir17_completion_report(tmp_path: Path) -> None:
    ir15_paths = _prepare_ir15_reports(tmp_path)
    ir17 = run_ir17_role_policy_versioning_dryrun(
        base_path=tmp_path,
        source_task_id="ir17_complete",
        ir15_report_paths=ir15_paths,
    )
    completion = write_ir17_completion_report(
        base_path=tmp_path,
        ir17_output=ir17,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 166, "failed": 0},
    )
    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 17"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
