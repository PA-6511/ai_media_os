import json
from pathlib import Path

from generic_block_ai.app.core_destination_approval_action_runbook import (
    run_ir37_destination_approval_action_runbook_dryrun,
    write_ir37_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir36_payload() -> dict:
    return {
        "schema_version": "ir36_destination_approval_gate_matrix_v1",
        "phase": "IR36",
        "source_task_id": "ir36_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "validation_failed_checks": [],
        "validation_warnings": [],
        "summary": {
            "destination_count": 3,
            "approve_dry_run_count": 3,
            "human_review_required_count": 0,
            "reject_count": 0,
            "abort_count": 0,
            "global_abort": False,
        },
        "decisions": [
            {
                "destination": "regulatory_audit",
                "approval_decision": "APPROVE_DRY_RUN",
                "reasons": [],
                "warnings": [],
                "manifest_path": "generic_block_ai/reports/x/regulatory_audit/destination_package_manifest.json",
            },
            {
                "destination": "internal_review_board",
                "approval_decision": "APPROVE_DRY_RUN",
                "reasons": [],
                "warnings": [],
                "manifest_path": "generic_block_ai/reports/x/internal_review_board/destination_package_manifest.json",
            },
            {
                "destination": "compliance_archive",
                "approval_decision": "APPROVE_DRY_RUN",
                "reasons": [],
                "warnings": [],
                "manifest_path": "generic_block_ai/reports/x/compliance_archive/destination_package_manifest.json",
            },
        ],
    }


def _prepare_ir36(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir36_destination_approval_gate_matrix_report_fixture.json"
    _write(target, payload or _base_ir36_payload())
    return target


def test_ir37_pass_runbook_from_all_approve(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir36_path = _prepare_ir36(base)

    out = run_ir37_destination_approval_action_runbook_dryrun(
        base_path=base,
        source_task_id="ir37_pass",
        ir36_approval_report_path=ir36_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["overall_approval_decision"] == "APPROVE_DRY_RUN"
    assert report["summary"]["approve_dry_run_count"] == 3


def test_ir37_human_review_action_when_decision_requires_review(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir36_payload()
    payload["overall_approval_decision"] = "HUMAN_REVIEW_REQUIRED"
    payload["decisions"][1]["approval_decision"] = "HUMAN_REVIEW_REQUIRED"
    payload["decisions"][1]["warnings"] = ["missing optional templates"]
    ir36_path = _prepare_ir36(base, payload)

    out = run_ir37_destination_approval_action_runbook_dryrun(
        base_path=base,
        source_task_id="ir37_review",
        ir36_approval_report_path=ir36_path,
    )

    report = out["runbook_report"]
    assert report["summary"]["human_review_required_count"] == 1
    target = [r for r in report["destination_actions"] if r["destination"] == "internal_review_board"][0]
    assert target["requires_human_review"] is True


def test_ir37_reject_action_includes_resubmission_patterns(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir36_payload()
    payload["overall_approval_decision"] = "REJECT"
    payload["decisions"][2]["approval_decision"] = "REJECT"
    payload["decisions"][2]["reasons"] = ["missing required templates", "signature sheet mismatch"]
    ir36_path = _prepare_ir36(base, payload)

    out = run_ir37_destination_approval_action_runbook_dryrun(
        base_path=base,
        source_task_id="ir37_reject",
        ir36_approval_report_path=ir36_path,
    )

    report = out["runbook_report"]
    target = [r for r in report["destination_actions"] if r["destination"] == "compliance_archive"][0]
    assert target["requires_resubmission"] is True
    assert len(target["resubmission_patterns"]) >= 1


def test_ir37_abort_action_enforces_incident_flow(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir36_payload()
    payload["overall_approval_decision"] = "ABORT"
    payload["decisions"][0]["approval_decision"] = "ABORT"
    payload["decisions"][0]["reasons"] = ["external transmission risk detected"]
    ir36_path = _prepare_ir36(base, payload)

    out = run_ir37_destination_approval_action_runbook_dryrun(
        base_path=base,
        source_task_id="ir37_abort",
        ir36_approval_report_path=ir36_path,
    )

    report = out["runbook_report"]
    target = [r for r in report["destination_actions"] if r["destination"] == "regulatory_audit"][0]
    assert target["escalation"] == "incident_commander"
    assert report["overall_action"].startswith("Abort flow")


def test_ir37_fail_when_ir36_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir37_destination_approval_action_runbook_dryrun(
        base_path=base,
        source_task_id="ir37_missing",
        ir36_approval_report_path=tmp_path / "missing_ir36.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir37_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir36_path = _prepare_ir36(base)
    ir37 = run_ir37_destination_approval_action_runbook_dryrun(
        base_path=base,
        source_task_id="ir37_completion",
        ir36_approval_report_path=ir36_path,
    )

    completion = write_ir37_completion_report(
        base_path=base,
        ir37_output=ir37,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 277, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 37"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_approval_decision"] == "APPROVE_DRY_RUN"
