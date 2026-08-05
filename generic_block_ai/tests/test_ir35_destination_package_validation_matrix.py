import json
from pathlib import Path

from generic_block_ai.app.core_destination_package_validation_matrix import (
    run_ir35_destination_package_validation_matrix_dryrun,
    write_ir35_completion_report,
)
from generic_block_ai.app.core_destination_submission_package_dryrun import (
    run_ir34_destination_submission_package_dryrun,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir33(base: Path, *, validation_result: str = "PASS") -> Path:
    reports = base / "reports"

    template_dir = reports / "ir32_submission_audit_template_pack_ir32_live_trial"
    _write(template_dir / "submission_cover.md", "# cover\n")
    _write(
        template_dir / "attachment_list.json",
        json.dumps({"attachments": [{"name": "a"}, {"name": "b"}]}, ensure_ascii=False, indent=2) + "\n",
    )
    _write(template_dir / "confirmation_signature_sheet.md", "# Signature Sheet\n| Signature |\n")
    _write(template_dir / "review_template.md", "# review\n")

    destination_rules = {
        "schema_version": "ir33_submission_package_recomposition_rules_v1",
        "phase": "IR33",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "destinations": {
            "regulatory_audit": {
                "required_templates": ["submission_cover", "attachment_list", "confirmation_signature_sheet"],
                "optional_templates": ["review_template"],
                "priority": 1,
            },
            "internal_review_board": {
                "required_templates": ["submission_cover", "review_template"],
                "optional_templates": ["attachment_list", "confirmation_signature_sheet"],
                "priority": 2,
            },
            "compliance_archive": {
                "required_templates": ["submission_cover", "attachment_list", "confirmation_signature_sheet", "review_template"],
                "optional_templates": [],
                "priority": 3,
            },
        },
        "template_refs": {
            "submission_cover": "generic_block_ai/reports/ir32_submission_audit_template_pack_ir32_live_trial/submission_cover.md",
            "attachment_list": "generic_block_ai/reports/ir32_submission_audit_template_pack_ir32_live_trial/attachment_list.json",
            "confirmation_signature_sheet": "generic_block_ai/reports/ir32_submission_audit_template_pack_ir32_live_trial/confirmation_signature_sheet.md",
            "review_template": "generic_block_ai/reports/ir32_submission_audit_template_pack_ir32_live_trial/review_template.md",
        },
    }
    destination_rules_path = reports / "ir33_submission_package_recomposition_rules_ir33_live_trial" / "destination_recomposition_rules.json"
    _write(destination_rules_path, json.dumps(destination_rules, ensure_ascii=False, indent=2) + "\n")

    resub_rules = {
        "schema_version": "ir33_submission_package_recomposition_rules_v1",
        "phase": "IR33",
        "rules": [{"id": "R1"}, {"id": "R2"}, {"id": "R3"}, {"id": "R4"}],
    }
    resub_rules_path = reports / "ir33_submission_package_recomposition_rules_ir33_live_trial" / "resubmission_recomposition_rules.json"
    _write(resub_rules_path, json.dumps(resub_rules, ensure_ascii=False, indent=2) + "\n")

    rollback_path = reports / "ir33_submission_package_recomposition_rules_ir33_live_trial" / "rollback_response_template.md"
    _write(rollback_path, "# rollback\n")

    ir33 = {
        "schema_version": "ir33_submission_package_recomposition_rules_v1",
        "phase": "IR33",
        "source_task_id": "ir33_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "validation_result": validation_result,
        "validation_failed_checks": [] if validation_result == "PASS" else ["x"],
        "validation_warnings": [],
        "artifacts": {
            "destination_recomposition_rules": "generic_block_ai/reports/ir33_submission_package_recomposition_rules_ir33_live_trial/destination_recomposition_rules.json",
            "resubmission_recomposition_rules": "generic_block_ai/reports/ir33_submission_package_recomposition_rules_ir33_live_trial/resubmission_recomposition_rules.json",
            "rollback_response_template": "generic_block_ai/reports/ir33_submission_package_recomposition_rules_ir33_live_trial/rollback_response_template.md",
        },
    }
    ir33_path = reports / "ir33_submission_package_recomposition_rules_report_ir33_live_trial.json"
    _write(ir33_path, json.dumps(ir33, ensure_ascii=False, indent=2) + "\n")
    return ir33_path


def _prepare_ir34(base: Path) -> Path:
    ir33_path = _prepare_ir33(base)
    ir34 = run_ir34_destination_submission_package_dryrun(
        base_path=base,
        source_task_id="ir34_fixture",
        ir33_recomposition_report_path=ir33_path,
    )
    return Path(ir34["path"])


def test_ir35_pass_matrix(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir34_path = _prepare_ir34(base)

    out = run_ir35_destination_package_validation_matrix_dryrun(
        base_path=base,
        source_task_id="ir35_pass",
        ir34_dryrun_report_path=ir34_path,
    )

    report = out["validation_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3


def test_ir35_fail_when_ir34_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    out = run_ir35_destination_package_validation_matrix_dryrun(
        base_path=base,
        source_task_id="ir35_missing",
        ir34_dryrun_report_path=tmp_path / "not_found.json",
    )
    assert out["validation_report"]["validation_result"] == "FAIL"


def test_ir35_fail_when_required_template_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir34_path = _prepare_ir34(base)

    manifest_path = (
        base
        / "reports"
        / "ir34_destination_submission_packages_ir34_fixture"
        / "regulatory_audit"
        / "destination_package_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["required_templates"] = [
        item for item in manifest["required_templates"] if item["template"] != "attachment_list"
    ]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir35_destination_package_validation_matrix_dryrun(
        base_path=base,
        source_task_id="ir35_required_missing",
        ir34_dryrun_report_path=ir34_path,
    )
    assert out["validation_report"]["validation_result"] == "FAIL"


def test_ir35_fail_when_forbidden_template_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir34_path = _prepare_ir34(base)

    manifest_path = (
        base
        / "reports"
        / "ir34_destination_submission_packages_ir34_fixture"
        / "internal_review_board"
        / "destination_package_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["optional_templates"].append(
        {
            "template": "forbidden_file",
            "path": "generic_block_ai/reports/forbidden_file.txt",
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir35_destination_package_validation_matrix_dryrun(
        base_path=base,
        source_task_id="ir35_forbidden",
        ir34_dryrun_report_path=ir34_path,
    )
    assert out["validation_report"]["validation_result"] == "FAIL"


def test_ir35_fail_when_signature_field_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir34_path = _prepare_ir34(base)

    signature_path = base / "reports" / "ir32_submission_audit_template_pack_ir32_live_trial" / "confirmation_signature_sheet.md"
    signature_path.write_text("# Confirmation Sheet\nNo signer section\n", encoding="utf-8")

    out = run_ir35_destination_package_validation_matrix_dryrun(
        base_path=base,
        source_task_id="ir35_signature_fail",
        ir34_dryrun_report_path=ir34_path,
    )
    assert out["validation_report"]["validation_result"] == "FAIL"


def test_write_ir35_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir34_path = _prepare_ir34(base)
    ir35 = run_ir35_destination_package_validation_matrix_dryrun(
        base_path=base,
        source_task_id="ir35_completion",
        ir34_dryrun_report_path=ir34_path,
    )

    completion = write_ir35_completion_report(
        base_path=base,
        ir35_output=ir35,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 265, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 35"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"