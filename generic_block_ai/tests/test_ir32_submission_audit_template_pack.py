import json
from pathlib import Path

from generic_block_ai.app.core_submission_audit_template_pack import (
    run_ir32_submission_audit_template_pack_dryrun,
    write_ir32_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir31(base: Path, *, validation_result: str = "PASS", decision: str = "READY_FOR_SUBMISSION_SUMMARY", send_ok: bool = True) -> Path:
    reports = base / "reports"
    narrative_dir = reports / "ir31_submission_audit_narrative_ir31_live_trial"

    _write(narrative_dir / "submission_audit_narrative.md", "# narrative\n")
    _write(narrative_dir / "submission_audit_index.json", '{"x":1}\n')
    _write(narrative_dir / "reviewer_summary.json", '{"x":2}\n')

    report = {
        "schema_version": "ir31_submission_audit_narrative_v1",
        "phase": "IR31",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_task_id": "ir31_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": decision,
        "validation_result": validation_result,
        "validation_failed_checks": [] if validation_result == "PASS" else ["x"],
        "validation_warnings": [],
        "summary": {
            "reason_count": 1,
            "failed_check_count": 0 if validation_result == "PASS" else 1,
            "warning_count": 0,
            "send_allowed_invariant_ok": send_ok,
        },
        "artifacts": {
            "submission_audit_narrative": "generic_block_ai/reports/ir31_submission_audit_narrative_ir31_live_trial/submission_audit_narrative.md",
            "submission_audit_index": "generic_block_ai/reports/ir31_submission_audit_narrative_ir31_live_trial/submission_audit_index.json",
            "reviewer_summary": "generic_block_ai/reports/ir31_submission_audit_narrative_ir31_live_trial/reviewer_summary.json",
        },
    }
    report_path = reports / "ir31_submission_audit_narrative_report_ir31_live_trial.json"
    _write(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report_path


def test_ir32_build_template_pack_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir31_path = _prepare_ir31(base)

    out = run_ir32_submission_audit_template_pack_dryrun(
        base_path=base,
        source_task_id="ir32_pass",
        ir31_narrative_report_path=ir31_path,
    )

    report = out["template_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["template_file_count"] == 4


def test_ir32_fail_when_ir31_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir32_submission_audit_template_pack_dryrun(
        base_path=base,
        source_task_id="ir32_missing",
        ir31_narrative_report_path=tmp_path / "not_found.json",
    )

    report = out["template_report"]
    assert report["validation_result"] == "FAIL"


def test_ir32_fail_when_ir31_not_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir31_path = _prepare_ir31(base, validation_result="FAIL")

    out = run_ir32_submission_audit_template_pack_dryrun(
        base_path=base,
        source_task_id="ir32_ir31_fail",
        ir31_narrative_report_path=ir31_path,
    )

    report = out["template_report"]
    assert report["validation_result"] == "FAIL"


def test_ir32_fail_when_required_artifact_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir31_path = _prepare_ir31(base)
    (base / "reports" / "ir31_submission_audit_narrative_ir31_live_trial" / "reviewer_summary.json").unlink()

    out = run_ir32_submission_audit_template_pack_dryrun(
        base_path=base,
        source_task_id="ir32_artifact_missing",
        ir31_narrative_report_path=ir31_path,
    )

    report = out["template_report"]
    assert report["validation_result"] == "FAIL"


def test_ir32_warn_when_send_invariant_not_ok(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir31_path = _prepare_ir31(base, send_ok=False)

    out = run_ir32_submission_audit_template_pack_dryrun(
        base_path=base,
        source_task_id="ir32_warn",
        ir31_narrative_report_path=ir31_path,
    )

    report = out["template_report"]
    assert report["validation_result"] == "WARN"


def test_write_ir32_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir31_path = _prepare_ir31(base)

    ir32 = run_ir32_submission_audit_template_pack_dryrun(
        base_path=base,
        source_task_id="ir32_complete",
        ir31_narrative_report_path=ir31_path,
    )

    completion = write_ir32_completion_report(
        base_path=base,
        ir32_output=ir32,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 247, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 32"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
