import json
from pathlib import Path

from generic_block_ai.app.core_audit_log_integrity_checker import (
    run_ir14_audit_log_integrity_check,
    write_ir14_completion_report,
)
from generic_block_ai.app.core_decision_queue_simulator import run_ir12_core_decision_queue_dryrun
from generic_block_ai.app.core_manual_approval_event_simulator import run_ir13_manual_approval_event_dryrun


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


def _prepare_ir12_ir13_artifacts(tmp_path: Path) -> list[str]:
    ir12_outputs = []
    for judgment in ["PASS", "WARN", "FAIL", "ABORT"]:
        out = run_ir12_core_decision_queue_dryrun(
            base_path=tmp_path,
            source_task_id=f"ir12_{judgment.lower()}",
            receiver_report=_receiver_report(judgment),
        )
        ir12_outputs.append(out)

    # Apply manual events for coverage; ABORT must stay blocked.
    event_map = {
        "PASS": "APPROVE",
        "WARN": "REQUEST_FIX",
        "FAIL": "REJECT",
        "ABORT": "APPROVE",
    }
    for output in ir12_outputs:
        queue_report = output["queue_report"]
        judgment = queue_report["quality_gate_judgment"]
        run_ir13_manual_approval_event_dryrun(
            base_path=tmp_path,
            source_task_id=f"ir13_{judgment.lower()}",
            queue_report=queue_report,
            event=event_map[judgment],
            actor=f"tester_{judgment.lower()}",
        )

    return [item["path"] for item in ir12_outputs]


def test_ir14_integrity_checker_pass(tmp_path: Path) -> None:
    queue_report_paths = _prepare_ir12_ir13_artifacts(tmp_path)
    output = run_ir14_audit_log_integrity_check(
        base_path=tmp_path,
        source_task_id="ir14_pass",
        ir12_queue_report_paths=queue_report_paths,
    )
    loaded = json.loads(Path(output["path"]).read_text(encoding="utf-8"))
    assert loaded["validation_result"] == "PASS"
    assert not loaded["validation_failed_checks"]


def test_ir14_detects_missing_queue_item(tmp_path: Path) -> None:
    queue_report_paths = _prepare_ir12_ir13_artifacts(tmp_path)

    queue_log = tmp_path / "reports" / "ir12_core_decision_queue_audit.log"
    lines = [line for line in queue_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    queue_log.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    output = run_ir14_audit_log_integrity_check(
        base_path=tmp_path,
        source_task_id="ir14_missing",
        ir12_queue_report_paths=queue_report_paths,
    )
    report = output["integrity_report"]
    assert report["validation_result"] == "FAIL"
    assert any("missing queue_item_id" in item for item in report["validation_failed_checks"])


def test_ir14_detects_duplicate_queue_record(tmp_path: Path) -> None:
    _prepare_ir12_ir13_artifacts(tmp_path)

    queue_log = tmp_path / "reports" / "ir12_core_decision_queue_audit.log"
    lines = [line for line in queue_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    queue_log.write_text("\n".join(lines + [lines[0]]) + "\n", encoding="utf-8")

    output = run_ir14_audit_log_integrity_check(
        base_path=tmp_path,
        source_task_id="ir14_duplicate",
    )
    report = output["integrity_report"]
    assert report["validation_result"] == "FAIL"
    assert any("duplicate queue_item_id" in item for item in report["validation_failed_checks"])


def test_ir14_detects_time_reversal(tmp_path: Path) -> None:
    _prepare_ir12_ir13_artifacts(tmp_path)

    manual_log = tmp_path / "reports" / "ir13_manual_approval_audit.log"
    entries = [json.loads(line) for line in manual_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries[-1]["at"] = "2000-01-01T00:00:00+00:00"
    manual_log.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n", encoding="utf-8")

    output = run_ir14_audit_log_integrity_check(
        base_path=tmp_path,
        source_task_id="ir14_time_reversal",
    )
    report = output["integrity_report"]
    assert report["validation_result"] == "FAIL"
    assert any("time reversal" in item for item in report["validation_failed_checks"])


def test_ir14_detects_abort_tampering(tmp_path: Path) -> None:
    _prepare_ir12_ir13_artifacts(tmp_path)

    manual_log = tmp_path / "reports" / "ir13_manual_approval_audit.log"
    entries = [json.loads(line) for line in manual_log.read_text(encoding="utf-8").splitlines() if line.strip()]

    # Mutate ABORT record into a false unlock success.
    for entry in entries:
        if entry.get("queue_item_id", "").endswith("_abort"):
            entry["to"] = "APPROVED_DRY_RUN_PENDING_RELEASE"
            entry["result"] = "PASS"
            break

    manual_log.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n", encoding="utf-8")

    output = run_ir14_audit_log_integrity_check(
        base_path=tmp_path,
        source_task_id="ir14_abort_tamper",
    )
    report = output["integrity_report"]
    assert report["validation_result"] == "FAIL"
    assert any("tamper detected" in item for item in report["validation_failed_checks"])


def test_write_ir14_completion_report(tmp_path: Path) -> None:
    queue_report_paths = _prepare_ir12_ir13_artifacts(tmp_path)
    ir14 = run_ir14_audit_log_integrity_check(
        base_path=tmp_path,
        source_task_id="ir14_complete",
        ir12_queue_report_paths=queue_report_paths,
    )

    completion = write_ir14_completion_report(
        base_path=tmp_path,
        ir14_output=ir14,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 150, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 14"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
