import json
from pathlib import Path

from generic_block_ai.app.core_submission_package_recomposition_rules import (
    run_ir33_submission_package_recomposition_rules_dryrun,
    write_ir33_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir32(base: Path, *, validation_result: str = "PASS", send_invariant_ok: bool = True) -> Path:
    reports = base / "reports"
    pack_dir = reports / "ir32_submission_audit_template_pack_ir32_live_trial"

    _write(pack_dir / "submission_cover.md", "# cover\n")
    _write(pack_dir / "attachment_list.json", '{"x":1}\n')
    _write(pack_dir / "confirmation_signature_sheet.md", "# sign\n")
    _write(pack_dir / "review_template.md", "# review\n")

    report = {
        "schema_version": "ir32_submission_audit_template_pack_v1",
        "phase": "IR32",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_task_id": "ir32_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "validation_result": validation_result,
        "validation_failed_checks": [] if validation_result == "PASS" else ["x"],
        "validation_warnings": [],
        "summary": {
            "template_file_count": 4,
            "failed_check_count": 0 if validation_result == "PASS" else 1,
            "warning_count": 0,
            "send_allowed_invariant_ok": send_invariant_ok,
        },
        "artifacts": {
            "submission_cover": "generic_block_ai/reports/ir32_submission_audit_template_pack_ir32_live_trial/submission_cover.md",
            "attachment_list": "generic_block_ai/reports/ir32_submission_audit_template_pack_ir32_live_trial/attachment_list.json",
            "confirmation_signature_sheet": "generic_block_ai/reports/ir32_submission_audit_template_pack_ir32_live_trial/confirmation_signature_sheet.md",
            "review_template": "generic_block_ai/reports/ir32_submission_audit_template_pack_ir32_live_trial/review_template.md",
        },
    }
    path = reports / "ir32_submission_audit_template_pack_report_ir32_live_trial.json"
    _write(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return path


def test_ir33_build_recomposition_rules_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir32_path = _prepare_ir32(base)

    out = run_ir33_submission_package_recomposition_rules_dryrun(
        base_path=base,
        source_task_id="ir33_pass",
        ir32_template_report_path=ir32_path,
    )

    report = out["recomposition_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_rule_count"] == 3


def test_ir33_fail_when_ir32_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir33_submission_package_recomposition_rules_dryrun(
        base_path=base,
        source_task_id="ir33_missing",
        ir32_template_report_path=tmp_path / "not_found.json",
    )

    report = out["recomposition_report"]
    assert report["validation_result"] == "FAIL"


def test_ir33_fail_when_ir32_not_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir32_path = _prepare_ir32(base, validation_result="FAIL")

    out = run_ir33_submission_package_recomposition_rules_dryrun(
        base_path=base,
        source_task_id="ir33_ir32_fail",
        ir32_template_report_path=ir32_path,
    )

    report = out["recomposition_report"]
    assert report["validation_result"] == "FAIL"


def test_ir33_fail_when_template_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir32_path = _prepare_ir32(base)
    (base / "reports" / "ir32_submission_audit_template_pack_ir32_live_trial" / "review_template.md").unlink()

    out = run_ir33_submission_package_recomposition_rules_dryrun(
        base_path=base,
        source_task_id="ir33_template_missing",
        ir32_template_report_path=ir32_path,
    )

    report = out["recomposition_report"]
    assert report["validation_result"] == "FAIL"


def test_ir33_warn_when_send_invariant_not_ok(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir32_path = _prepare_ir32(base, send_invariant_ok=False)

    out = run_ir33_submission_package_recomposition_rules_dryrun(
        base_path=base,
        source_task_id="ir33_warn",
        ir32_template_report_path=ir32_path,
    )

    report = out["recomposition_report"]
    assert report["validation_result"] == "WARN"


def test_write_ir33_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir32_path = _prepare_ir32(base)

    ir33 = run_ir33_submission_package_recomposition_rules_dryrun(
        base_path=base,
        source_task_id="ir33_complete",
        ir32_template_report_path=ir32_path,
    )

    completion = write_ir33_completion_report(
        base_path=base,
        ir33_output=ir33,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 253, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 33"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
