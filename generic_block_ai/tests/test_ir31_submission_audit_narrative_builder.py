import json
from pathlib import Path

from generic_block_ai.app.core_submission_audit_narrative_builder import (
    run_ir31_submission_audit_narrative_builder_dryrun,
    write_ir31_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir30(base: Path, *, decision: str = "READY_FOR_SUBMISSION_SUMMARY", send_invariant_ok: bool = True) -> Path:
    reports = base / "reports"
    table = {
        "schema_version": "ir30_submission_decision_summary_v1",
        "phase": "IR30",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_task_id": "ir30_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": decision,
        "decision_reasons": ["dryrun_submission_summary_ready"],
    }
    table_path = reports / "ir30_submission_decision_table_ir30_live_trial.json"
    _write(table_path, json.dumps(table, ensure_ascii=False, indent=2) + "\n")

    report = {
        "schema_version": "ir30_submission_decision_summary_v1",
        "phase": "IR30",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_task_id": "ir30_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": decision,
        "validation_result": "PASS",
        "validation_failed_checks": [],
        "validation_warnings": [],
        "summary": {
            "final_submission_decision": decision,
            "reason_count": 1,
            "failed_check_count": 0,
            "warning_count": 0,
            "send_allowed_invariant_ok": send_invariant_ok,
        },
        "artifacts": {
            "submission_decision_table": "generic_block_ai/reports/ir30_submission_decision_table_ir30_live_trial.json",
        },
    }
    report_path = reports / "ir30_submission_decision_summary_report_ir30_live_trial.json"
    _write(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report_path


def test_ir31_build_narrative_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir30_path = _prepare_ir30(base)

    out = run_ir31_submission_audit_narrative_builder_dryrun(
        base_path=base,
        source_task_id="ir31_pass",
        ir30_decision_report_path=ir30_path,
    )

    report = out["narrative_report"]
    assert report["validation_result"] == "PASS"
    assert report["final_submission_decision"] == "READY_FOR_SUBMISSION_SUMMARY"


def test_ir31_fail_when_ir30_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir31_submission_audit_narrative_builder_dryrun(
        base_path=base,
        source_task_id="ir31_missing",
        ir30_decision_report_path=tmp_path / "not_found.json",
    )

    report = out["narrative_report"]
    assert report["validation_result"] == "FAIL"


def test_ir31_fail_when_decision_table_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir30_path = _prepare_ir30(base)
    (base / "reports" / "ir30_submission_decision_table_ir30_live_trial.json").unlink()

    out = run_ir31_submission_audit_narrative_builder_dryrun(
        base_path=base,
        source_task_id="ir31_table_missing",
        ir30_decision_report_path=ir30_path,
    )

    report = out["narrative_report"]
    assert report["validation_result"] == "FAIL"


def test_ir31_warn_when_send_invariant_not_ok(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir30_path = _prepare_ir30(base, send_invariant_ok=False)

    out = run_ir31_submission_audit_narrative_builder_dryrun(
        base_path=base,
        source_task_id="ir31_warn",
        ir30_decision_report_path=ir30_path,
    )

    report = out["narrative_report"]
    assert report["validation_result"] == "WARN"


def test_ir31_warn_when_decision_hold(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir30_path = _prepare_ir30(base, decision="HOLD")

    out = run_ir31_submission_audit_narrative_builder_dryrun(
        base_path=base,
        source_task_id="ir31_hold",
        ir30_decision_report_path=ir30_path,
    )

    report = out["narrative_report"]
    assert report["validation_result"] == "WARN"


def test_write_ir31_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir30_path = _prepare_ir30(base)

    ir31 = run_ir31_submission_audit_narrative_builder_dryrun(
        base_path=base,
        source_task_id="ir31_complete",
        ir30_decision_report_path=ir30_path,
    )

    completion = write_ir31_completion_report(
        base_path=base,
        ir31_output=ir31,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 241, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 31"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
