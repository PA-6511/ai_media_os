import json
from pathlib import Path

from generic_block_ai.app.core_submission_decision_summary import (
    DECISION_HOLD,
    DECISION_NOT_ALLOWED,
    DECISION_READY_FOR_SUBMISSION_SUMMARY,
    run_ir30_submission_decision_summary_dryrun,
    write_ir30_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir29(base: Path, *, validation_result: str = "PASS", send_executed: bool = False, warning_count: int = 0) -> Path:
    warnings = ["needs review"] if warning_count > 0 else []
    report = {
        "schema_version": "ir29_release_candidate_submission_dryrun_v1",
        "phase": "IR29",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_task_id": "ir29_fixture",
        "release_candidate_id": "rc_fixture",
        "validation_result": validation_result,
        "validation_failed_checks": [] if validation_result == "PASS" else ["x"],
        "validation_warnings": warnings,
        "summary": {
            "included_artifact_count": 22,
            "failed_check_count": 0 if validation_result == "PASS" else 1,
            "warning_count": warning_count,
            "send_allowed": False,
            "send_executed": send_executed,
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
            "network_transmission_executed": False,
        },
    }
    path = base / "reports" / "ir29_release_candidate_submission_dryrun_report_ir29_live_trial.json"
    _write(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return path


def test_ir30_ready_for_submission_summary_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir29_path = _prepare_ir29(base)

    out = run_ir30_submission_decision_summary_dryrun(
        base_path=base,
        source_task_id="ir30_ready",
        ir29_submission_report_path=ir29_path,
    )

    report = out["decision_report"]
    assert report["validation_result"] == "PASS"
    assert report["final_submission_decision"] == DECISION_READY_FOR_SUBMISSION_SUMMARY


def test_ir30_not_allowed_when_ir29_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir30_submission_decision_summary_dryrun(
        base_path=base,
        source_task_id="ir30_missing",
        ir29_submission_report_path=tmp_path / "not_found.json",
    )

    report = out["decision_report"]
    assert report["validation_result"] == "FAIL"
    assert report["final_submission_decision"] == DECISION_NOT_ALLOWED


def test_ir30_not_allowed_when_send_executed_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir29_path = _prepare_ir29(base, send_executed=True)

    out = run_ir30_submission_decision_summary_dryrun(
        base_path=base,
        source_task_id="ir30_send_guard_violation",
        ir29_submission_report_path=ir29_path,
    )

    report = out["decision_report"]
    assert report["final_submission_decision"] == DECISION_NOT_ALLOWED


def test_ir30_hold_when_warnings_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir29_path = _prepare_ir29(base, warning_count=1)

    out = run_ir30_submission_decision_summary_dryrun(
        base_path=base,
        source_task_id="ir30_hold",
        ir29_submission_report_path=ir29_path,
    )

    report = out["decision_report"]
    assert report["validation_result"] == "WARN"
    assert report["final_submission_decision"] == DECISION_HOLD


def test_ir30_hold_when_ir29_not_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir29_path = _prepare_ir29(base, validation_result="FAIL")

    out = run_ir30_submission_decision_summary_dryrun(
        base_path=base,
        source_task_id="ir30_ir29_fail",
        ir29_submission_report_path=ir29_path,
    )

    report = out["decision_report"]
    assert report["final_submission_decision"] == DECISION_HOLD


def test_write_ir30_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir29_path = _prepare_ir29(base)

    ir30 = run_ir30_submission_decision_summary_dryrun(
        base_path=base,
        source_task_id="ir30_complete",
        ir29_submission_report_path=ir29_path,
    )

    completion = write_ir30_completion_report(
        base_path=base,
        ir30_output=ir30,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 235, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 30"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
