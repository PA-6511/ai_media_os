import json
from pathlib import Path

from generic_block_ai.app.core_destination_approval_gate_matrix import (
    run_ir36_destination_approval_gate_matrix_dryrun,
    write_ir36_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir35_payload() -> dict:
    return {
        "schema_version": "ir35_destination_package_validation_matrix_v1",
        "phase": "IR35",
        "source_task_id": "ir35_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "validation_result": "PASS",
        "validation_failed_checks": [],
        "validation_warnings": [],
        "matrix": {
            "global_checks": {
                "recomposition_executed": True,
                "external_submission_blocked": True,
                "network_transmission_blocked": True,
                "resubmission_rules_loaded": True,
                "required_resubmission_patterns_present": True,
            },
            "destinations": [
                {
                    "destination": "regulatory_audit",
                    "manifest_path": "generic_block_ai/reports/x/regulatory_audit/destination_package_manifest.json",
                    "validation_result": "PASS",
                    "failed_checks": [],
                    "warnings": [],
                },
                {
                    "destination": "internal_review_board",
                    "manifest_path": "generic_block_ai/reports/x/internal_review_board/destination_package_manifest.json",
                    "validation_result": "PASS",
                    "failed_checks": [],
                    "warnings": [],
                },
                {
                    "destination": "compliance_archive",
                    "manifest_path": "generic_block_ai/reports/x/compliance_archive/destination_package_manifest.json",
                    "validation_result": "PASS",
                    "failed_checks": [],
                    "warnings": [],
                },
            ],
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


def _prepare_ir35(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir35_destination_package_validation_matrix_report_fixture.json"
    _write(target, payload or _base_ir35_payload())
    return target


def test_ir36_pass_all_approve_dry_run(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir35_path = _prepare_ir35(base)

    out = run_ir36_destination_approval_gate_matrix_dryrun(
        base_path=base,
        source_task_id="ir36_pass",
        ir35_validation_report_path=ir35_path,
    )

    report = out["approval_report"]
    assert report["overall_approval_decision"] == "APPROVE_DRY_RUN"
    assert report["summary"]["approve_dry_run_count"] == 3
    assert report["summary"]["abort_count"] == 0


def test_ir36_warn_maps_to_human_review_required(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir35_payload()
    payload["matrix"]["destinations"][1]["validation_result"] = "WARN"
    payload["matrix"]["destinations"][1]["warnings"] = ["missing optional templates"]
    ir35_path = _prepare_ir35(base, payload)

    out = run_ir36_destination_approval_gate_matrix_dryrun(
        base_path=base,
        source_task_id="ir36_warn",
        ir35_validation_report_path=ir35_path,
    )

    report = out["approval_report"]
    assert report["overall_approval_decision"] == "HUMAN_REVIEW_REQUIRED"
    assert report["summary"]["human_review_required_count"] == 1


def test_ir36_fail_maps_to_reject(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir35_payload()
    payload["matrix"]["destinations"][2]["validation_result"] = "FAIL"
    payload["matrix"]["destinations"][2]["failed_checks"] = ["missing required templates"]
    ir35_path = _prepare_ir35(base, payload)

    out = run_ir36_destination_approval_gate_matrix_dryrun(
        base_path=base,
        source_task_id="ir36_reject",
        ir35_validation_report_path=ir35_path,
    )

    report = out["approval_report"]
    assert report["overall_approval_decision"] == "REJECT"
    assert report["summary"]["reject_count"] == 1


def test_ir36_sensitive_fail_or_safeguard_violation_maps_to_abort(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir35_payload()
    payload["safeguards"]["external_write_executed"] = True
    payload["matrix"]["destinations"][0]["validation_result"] = "FAIL"
    payload["matrix"]["destinations"][0]["failed_checks"] = ["network transmission detected"]
    ir35_path = _prepare_ir35(base, payload)

    out = run_ir36_destination_approval_gate_matrix_dryrun(
        base_path=base,
        source_task_id="ir36_abort",
        ir35_validation_report_path=ir35_path,
    )

    report = out["approval_report"]
    assert report["overall_approval_decision"] == "ABORT"
    assert report["summary"]["global_abort"] is True


def test_ir36_fail_when_ir35_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir36_destination_approval_gate_matrix_dryrun(
        base_path=base,
        source_task_id="ir36_missing",
        ir35_validation_report_path=tmp_path / "missing_ir35.json",
    )

    report = out["approval_report"]
    assert report["overall_approval_decision"] == "REJECT"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir36_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir35_path = _prepare_ir35(base)
    ir36 = run_ir36_destination_approval_gate_matrix_dryrun(
        base_path=base,
        source_task_id="ir36_completion",
        ir35_validation_report_path=ir35_path,
    )

    completion = write_ir36_completion_report(
        base_path=base,
        ir36_output=ir36,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 271, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 36"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_approval_decision"] == "APPROVE_DRY_RUN"
