import json
from pathlib import Path

from generic_block_ai.app.core_multistep_replay_consistency import (
    run_ir18_multistep_replay_consistency_dryrun,
    write_ir18_completion_report,
)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n", encoding="utf-8")


def _prepare_multistep_artifacts(tmp_path: Path) -> tuple[Path, Path, list[str]]:
    reports = tmp_path / "reports"
    queue_log = reports / "ir12_core_decision_queue_audit.log"
    manual_log = reports / "ir13_manual_approval_audit.log"

    queue_id = "queue_chain_warn"
    queue_entries = [
        {
            "event": "queue_item_recorded",
            "at": "2026-01-01T00:00:00+00:00",
            "queue_item_id": queue_id,
            "source_task_id": "ir12_chain",
            "quality_gate_judgment": "WARN",
            "queue_state": "WAITING_HUMAN_REVIEW",
            "execution_triggered": False,
            "external_write_executed": False,
            "production_release": False,
        }
    ]
    _write_jsonl(queue_log, queue_entries)

    manual_entries = [
        {
            "event": "manual_approval_event_applied",
            "at": "2026-01-01T00:00:01+00:00",
            "source_task_id": "ir13_chain_1",
            "queue_item_id": queue_id,
            "manual_event": "REQUEST_FIX",
            "actor": "reviewer_a",
            "from": "WAITING_HUMAN_REVIEW",
            "to": "NEEDS_FIX_REWORK",
            "result": "PASS",
            "execution_triggered": False,
            "external_write_executed": False,
            "production_release": False,
        },
        {
            "event": "manual_approval_event_applied",
            "at": "2026-01-01T00:00:02+00:00",
            "source_task_id": "ir13_chain_2",
            "queue_item_id": queue_id,
            "manual_event": "APPROVE",
            "actor": "approver_a",
            "from": "NEEDS_FIX_REWORK",
            "to": "APPROVED_DRY_RUN_PENDING_RELEASE",
            "result": "PASS",
            "execution_triggered": False,
            "external_write_executed": False,
            "production_release": False,
        },
    ]
    _write_jsonl(manual_log, manual_entries)

    report1 = {
        "schema_version": "ir13_manual_approval_v1",
        "generated_at": "2026-01-01T00:00:01+00:00",
        "source_task_id": "ir13_chain_1",
        "queue_item": {
            "queue_item_id": queue_id,
            "queue_state": "NEEDS_FIX_REWORK",
        },
        "state_transitions": [
            {
                "from": "NEW",
                "to": "RECEIVED",
                "event": "receiver_report_ingested",
                "at": "2026-01-01T00:00:00+00:00",
            },
            {
                "from": "RECEIVED",
                "to": "WAITING_HUMAN_REVIEW",
                "event": "judgment_warn_mapped",
                "at": "2026-01-01T00:00:00+00:00",
            },
            {
                "from": "WAITING_HUMAN_REVIEW",
                "to": "NEEDS_FIX_REWORK",
                "event": "manual_request_fix",
                "at": "2026-01-01T00:00:01+00:00",
            },
        ],
    }
    report2 = {
        "schema_version": "ir13_manual_approval_v1",
        "generated_at": "2026-01-01T00:00:02+00:00",
        "source_task_id": "ir13_chain_2",
        "queue_item": {
            "queue_item_id": queue_id,
            "queue_state": "APPROVED_DRY_RUN_PENDING_RELEASE",
        },
        "state_transitions": [
            {
                "from": "NEW",
                "to": "RECEIVED",
                "event": "receiver_report_ingested",
                "at": "2026-01-01T00:00:00+00:00",
            },
            {
                "from": "RECEIVED",
                "to": "WAITING_HUMAN_REVIEW",
                "event": "judgment_warn_mapped",
                "at": "2026-01-01T00:00:00+00:00",
            },
            {
                "from": "WAITING_HUMAN_REVIEW",
                "to": "NEEDS_FIX_REWORK",
                "event": "manual_request_fix",
                "at": "2026-01-01T00:00:01+00:00",
            },
            {
                "from": "NEEDS_FIX_REWORK",
                "to": "APPROVED_DRY_RUN_PENDING_RELEASE",
                "event": "manual_approve",
                "at": "2026-01-01T00:00:02+00:00",
            },
        ],
    }

    p1 = reports / "ir13_manual_approval_event_chain_step1.json"
    p2 = reports / "ir13_manual_approval_event_chain_step2.json"
    _write_json(p1, report1)
    _write_json(p2, report2)

    return queue_log, manual_log, [str(p1), str(p2)]


def test_ir18_multistep_pass(tmp_path: Path) -> None:
    queue_log, manual_log, ir13_reports = _prepare_multistep_artifacts(tmp_path)
    out = run_ir18_multistep_replay_consistency_dryrun(
        base_path=tmp_path,
        source_task_id="ir18_pass",
        ir12_audit_log_path=queue_log,
        ir13_audit_log_path=manual_log,
        ir13_report_paths=ir13_reports,
    )
    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["validation_result"] == "PASS"
    assert loaded["summary"]["multi_step_queue_items"] == 1


def test_ir18_detects_from_state_mismatch(tmp_path: Path) -> None:
    queue_log, manual_log, ir13_reports = _prepare_multistep_artifacts(tmp_path)
    entries = [json.loads(line) for line in manual_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries[1]["from"] = "WAITING_HUMAN_REVIEW"
    _write_jsonl(manual_log, entries)

    out = run_ir18_multistep_replay_consistency_dryrun(
        base_path=tmp_path,
        source_task_id="ir18_from_mismatch",
        ir12_audit_log_path=queue_log,
        ir13_audit_log_path=manual_log,
        ir13_report_paths=ir13_reports,
    )
    report = out["consistency_report"]
    assert report["validation_result"] == "FAIL"
    assert any("from-state mismatch" in item for item in report["validation_failed_checks"])


def test_ir18_detects_fail_state_change(tmp_path: Path) -> None:
    queue_log, manual_log, ir13_reports = _prepare_multistep_artifacts(tmp_path)
    entries = [json.loads(line) for line in manual_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries[1]["result"] = "FAIL"
    entries[1]["to"] = "APPROVED_DRY_RUN_PENDING_RELEASE"
    _write_jsonl(manual_log, entries)

    out = run_ir18_multistep_replay_consistency_dryrun(
        base_path=tmp_path,
        source_task_id="ir18_fail_state_change",
        ir12_audit_log_path=queue_log,
        ir13_audit_log_path=manual_log,
        ir13_report_paths=ir13_reports,
    )
    report = out["consistency_report"]
    assert report["validation_result"] == "FAIL"
    assert any("FAIL result changed state" in item for item in report["validation_failed_checks"])


def test_ir18_detects_history_prefix_break(tmp_path: Path) -> None:
    queue_log, manual_log, ir13_reports = _prepare_multistep_artifacts(tmp_path)
    report2_path = Path(ir13_reports[1])
    report2 = json.loads(report2_path.read_text(encoding="utf-8"))
    report2["state_transitions"][1]["to"] = "BROKEN_STATE"
    _write_json(report2_path, report2)

    out = run_ir18_multistep_replay_consistency_dryrun(
        base_path=tmp_path,
        source_task_id="ir18_prefix_break",
        ir12_audit_log_path=queue_log,
        ir13_audit_log_path=manual_log,
        ir13_report_paths=ir13_reports,
    )
    report = out["consistency_report"]
    assert report["validation_result"] == "FAIL"
    assert any("prefix mismatch" in item for item in report["validation_failed_checks"])


def test_write_ir18_completion_report(tmp_path: Path) -> None:
    queue_log, manual_log, ir13_reports = _prepare_multistep_artifacts(tmp_path)
    ir18 = run_ir18_multistep_replay_consistency_dryrun(
        base_path=tmp_path,
        source_task_id="ir18_complete",
        ir12_audit_log_path=queue_log,
        ir13_audit_log_path=manual_log,
        ir13_report_paths=ir13_reports,
    )
    completion = write_ir18_completion_report(
        base_path=tmp_path,
        ir18_output=ir18,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 171, "failed": 0},
    )
    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 18"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
