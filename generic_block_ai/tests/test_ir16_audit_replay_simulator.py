import json
from pathlib import Path

from generic_block_ai.app.core_audit_replay_simulator import (
    run_ir16_audit_replay_dryrun,
    write_ir16_completion_report,
)
from generic_block_ai.app.core_decision_queue_simulator import run_ir12_core_decision_queue_dryrun
from generic_block_ai.app.core_manual_approval_event_simulator import run_ir13_manual_approval_event_dryrun
from generic_block_ai.app.core_manual_event_role_guard import run_ir15_manual_event_role_guard_dryrun


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


def _prepare_ir12_ir13_ir15(tmp_path: Path) -> tuple[list[str], list[str]]:
    ir13_paths: list[str] = []
    ir15_paths: list[str] = []

    event_map = {
        "PASS": ("APPROVE", "human_reviewer_pass", "approver"),
        "WARN": ("REQUEST_FIX", "human_reviewer_warn", "reviewer"),
        "FAIL": ("REJECT", "human_reviewer_fail", "reviewer"),
        "ABORT": ("APPROVE", "human_reviewer_abort", "admin"),
    }

    for judgment in ["PASS", "WARN", "FAIL", "ABORT"]:
        ir12 = run_ir12_core_decision_queue_dryrun(
            base_path=tmp_path,
            source_task_id=f"ir12_{judgment.lower()}",
            receiver_report=_receiver_report(judgment),
        )
        event, actor, role = event_map[judgment]
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
        ir13_paths.append(ir13["path"])
        ir15_paths.append(ir15["path"])

    return ir13_paths, ir15_paths


def test_ir16_replay_pass(tmp_path: Path) -> None:
    ir13_paths, ir15_paths = _prepare_ir12_ir13_ir15(tmp_path)
    out = run_ir16_audit_replay_dryrun(
        base_path=tmp_path,
        source_task_id="ir16_pass",
        ir13_report_paths=ir13_paths,
        ir15_report_paths=ir15_paths,
    )
    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["validation_result"] == "PASS"
    assert loaded["summary"]["state_mismatch_count"] == 0


def test_ir16_detects_manual_log_state_mismatch(tmp_path: Path) -> None:
    ir13_paths, ir15_paths = _prepare_ir12_ir13_ir15(tmp_path)

    manual_log = tmp_path / "reports" / "ir13_manual_approval_audit.log"
    entries = [json.loads(line) for line in manual_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    for entry in entries:
        if entry.get("queue_item_id", "").endswith("_warn"):
            entry["to"] = "APPROVED_DRY_RUN_PENDING_RELEASE"
            break
    manual_log.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n", encoding="utf-8")

    out = run_ir16_audit_replay_dryrun(
        base_path=tmp_path,
        source_task_id="ir16_mismatch",
        ir13_report_paths=ir13_paths,
        ir15_report_paths=ir15_paths,
    )
    report = out["replay_report"]
    assert report["validation_result"] == "FAIL"
    assert any("state mismatch" in item for item in report["validation_failed_checks"])


def test_ir16_detects_unknown_queue_item_in_manual_log(tmp_path: Path) -> None:
    ir13_paths, ir15_paths = _prepare_ir12_ir13_ir15(tmp_path)

    manual_log = tmp_path / "reports" / "ir13_manual_approval_audit.log"
    entries = [json.loads(line) for line in manual_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries.append(
        {
            "event": "manual_approval_event_applied",
            "at": "2026-01-01T00:00:01+00:00",
            "source_task_id": "tamper",
            "queue_item_id": "queue_unknown",
            "manual_event": "APPROVE",
            "actor": "tamper",
            "from": "READY_FOR_DRY_RUN_REVIEW",
            "to": "APPROVED_DRY_RUN_PENDING_RELEASE",
            "result": "PASS",
            "execution_triggered": False,
            "external_write_executed": False,
            "production_release": False,
        }
    )
    manual_log.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n", encoding="utf-8")

    out = run_ir16_audit_replay_dryrun(
        base_path=tmp_path,
        source_task_id="ir16_unknown_queue",
        ir13_report_paths=ir13_paths,
        ir15_report_paths=ir15_paths,
    )
    report = out["replay_report"]
    assert report["validation_result"] == "FAIL"
    assert any("unknown queue_item_id" in item for item in report["validation_failed_checks"])


def test_ir16_detects_ir15_actor_mismatch(tmp_path: Path) -> None:
    ir13_paths, ir15_paths = _prepare_ir12_ir13_ir15(tmp_path)

    ir15_path = Path(ir15_paths[0])
    altered = json.loads(ir15_path.read_text(encoding="utf-8"))
    altered["actor"] = "different_actor"
    ir15_path.write_text(json.dumps(altered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir16_audit_replay_dryrun(
        base_path=tmp_path,
        source_task_id="ir16_actor_mismatch",
        ir13_report_paths=ir13_paths,
        ir15_report_paths=ir15_paths,
    )
    report = out["replay_report"]
    assert report["validation_result"] == "FAIL"
    assert any("actor mismatch" in item for item in report["validation_failed_checks"])


def test_write_ir16_completion_report(tmp_path: Path) -> None:
    ir13_paths, ir15_paths = _prepare_ir12_ir13_ir15(tmp_path)
    ir16 = run_ir16_audit_replay_dryrun(
        base_path=tmp_path,
        source_task_id="ir16_complete",
        ir13_report_paths=ir13_paths,
        ir15_report_paths=ir15_paths,
    )
    completion = write_ir16_completion_report(
        base_path=tmp_path,
        ir16_output=ir16,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 161, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 16"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
