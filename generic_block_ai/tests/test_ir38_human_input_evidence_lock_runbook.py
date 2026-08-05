import json
from pathlib import Path

from generic_block_ai.app.core_human_input_evidence_lock_runbook import (
    run_ir38_human_input_evidence_lock_runbook_dryrun,
    write_ir38_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir37_payload() -> dict:
    return {
        "schema_version": "ir37_destination_approval_action_runbook_v1",
        "phase": "IR37",
        "source_task_id": "ir37_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "destination_actions": [
            {
                "destination": "regulatory_audit",
                "approval_decision": "APPROVE_DRY_RUN",
                "source_reasons": [],
                "source_warnings": [],
                "manifest_path": "generic_block_ai/reports/x/regulatory_audit/destination_package_manifest.json",
            },
            {
                "destination": "internal_review_board",
                "approval_decision": "APPROVE_DRY_RUN",
                "source_reasons": [],
                "source_warnings": [],
                "manifest_path": "generic_block_ai/reports/x/internal_review_board/destination_package_manifest.json",
            },
            {
                "destination": "compliance_archive",
                "approval_decision": "APPROVE_DRY_RUN",
                "source_reasons": [],
                "source_warnings": [],
                "manifest_path": "generic_block_ai/reports/x/compliance_archive/destination_package_manifest.json",
            },
        ],
    }


def _prepare_ir37(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir37_destination_approval_action_runbook_report_fixture.json"
    _write(target, payload or _base_ir37_payload())
    return target


def test_ir38_pass_runbook_from_all_approve(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir37_path = _prepare_ir37(base)

    out = run_ir38_human_input_evidence_lock_runbook_dryrun(
        base_path=base,
        source_task_id="ir38_pass",
        ir37_runbook_report_path=ir37_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3
    assert report["summary"]["approver_record_required_count"] == 3


def test_ir38_human_review_includes_review_fields(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir37_payload()
    payload["overall_approval_decision"] = "HUMAN_REVIEW_REQUIRED"
    payload["destination_actions"][1]["approval_decision"] = "HUMAN_REVIEW_REQUIRED"
    ir37_path = _prepare_ir37(base, payload)

    out = run_ir38_human_input_evidence_lock_runbook_dryrun(
        base_path=base,
        source_task_id="ir38_review",
        ir37_runbook_report_path=ir37_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_human_input_evidence_lock"] if r["destination"] == "internal_review_board"][0]
    required = row["human_input"]["required_fields"]
    assert "review_findings" in required
    assert report["summary"]["human_review_required_count"] == 1


def test_ir38_reject_includes_resubmission_lock_steps(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir37_payload()
    payload["overall_approval_decision"] = "REJECT"
    payload["destination_actions"][2]["approval_decision"] = "REJECT"
    ir37_path = _prepare_ir37(base, payload)

    out = run_ir38_human_input_evidence_lock_runbook_dryrun(
        base_path=base,
        source_task_id="ir38_reject",
        ir37_runbook_report_path=ir37_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_human_input_evidence_lock"] if r["destination"] == "compliance_archive"][0]
    assert any("resubmission" in s.lower() for s in row["return_or_abort_lock_steps"])


def test_ir38_abort_includes_incident_lock_steps(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir37_payload()
    payload["overall_approval_decision"] = "ABORT"
    payload["destination_actions"][0]["approval_decision"] = "ABORT"
    ir37_path = _prepare_ir37(base, payload)

    out = run_ir38_human_input_evidence_lock_runbook_dryrun(
        base_path=base,
        source_task_id="ir38_abort",
        ir37_runbook_report_path=ir37_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_human_input_evidence_lock"] if r["destination"] == "regulatory_audit"][0]
    assert any("incident" in s.lower() for s in row["return_or_abort_lock_steps"])


def test_ir38_fail_when_ir37_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir38_human_input_evidence_lock_runbook_dryrun(
        base_path=base,
        source_task_id="ir38_missing",
        ir37_runbook_report_path=tmp_path / "missing_ir37.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir38_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir37_path = _prepare_ir37(base)
    ir38 = run_ir38_human_input_evidence_lock_runbook_dryrun(
        base_path=base,
        source_task_id="ir38_completion",
        ir37_runbook_report_path=ir37_path,
    )

    completion = write_ir38_completion_report(
        base_path=base,
        ir38_output=ir38,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 283, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 38"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_approval_decision"] == "APPROVE_DRY_RUN"
