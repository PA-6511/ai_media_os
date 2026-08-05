import json
from pathlib import Path

from generic_block_ai.app.core_human_approval_event_simulator_for_destinations import (
    run_ir39_human_approval_event_simulator_for_destinations_dryrun,
    write_ir39_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir38_payload() -> dict:
    return {
        "schema_version": "ir38_human_input_evidence_lock_runbook_v1",
        "phase": "IR38",
        "source_task_id": "ir38_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "destination_human_input_evidence_lock": [
            {
                "destination": "regulatory_audit",
                "approval_decision": "APPROVE_DRY_RUN",
                "approver_record_required": True,
                "source_reasons": [],
                "source_warnings": [],
                "manifest_path": "generic_block_ai/reports/x/regulatory_audit/destination_package_manifest.json",
            },
            {
                "destination": "internal_review_board",
                "approval_decision": "APPROVE_DRY_RUN",
                "approver_record_required": True,
                "source_reasons": [],
                "source_warnings": [],
                "manifest_path": "generic_block_ai/reports/x/internal_review_board/destination_package_manifest.json",
            },
            {
                "destination": "compliance_archive",
                "approval_decision": "APPROVE_DRY_RUN",
                "approver_record_required": True,
                "source_reasons": [],
                "source_warnings": [],
                "manifest_path": "generic_block_ai/reports/x/compliance_archive/destination_package_manifest.json",
            },
        ],
    }


def _prepare_ir38(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir38_human_input_evidence_lock_runbook_report_fixture.json"
    _write(target, payload or _base_ir38_payload())
    return target


def test_ir39_pass_simulation_from_all_approve(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir38_path = _prepare_ir38(base)

    out = run_ir39_human_approval_event_simulator_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir39_pass",
        ir38_runbook_report_path=ir38_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3
    assert report["summary"]["approve_event_count"] == 3


def test_ir39_request_fix_event_for_review_decision(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir38_payload()
    payload["overall_approval_decision"] = "HUMAN_REVIEW_REQUIRED"
    payload["destination_human_input_evidence_lock"][1]["approval_decision"] = "HUMAN_REVIEW_REQUIRED"
    ir38_path = _prepare_ir38(base, payload)

    out = run_ir39_human_approval_event_simulator_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir39_review",
        ir38_runbook_report_path=ir38_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_human_event_simulation"] if r["destination"] == "internal_review_board"][0]
    assert row["selected_event"] == "REQUEST_FIX"
    assert row["state_transition"]["to_state"] == "EVIDENCE_LOCKED_NEEDS_FIX"


def test_ir39_reject_event_for_reject_decision(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir38_payload()
    payload["overall_approval_decision"] = "REJECT"
    payload["destination_human_input_evidence_lock"][2]["approval_decision"] = "REJECT"
    ir38_path = _prepare_ir38(base, payload)

    out = run_ir39_human_approval_event_simulator_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir39_reject",
        ir38_runbook_report_path=ir38_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_human_event_simulation"] if r["destination"] == "compliance_archive"][0]
    assert row["selected_event"] == "REJECT"
    assert row["state_transition"]["to_state"] == "EVIDENCE_LOCKED_REJECTED"


def test_ir39_abort_ack_event_for_abort_decision(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir38_payload()
    payload["overall_approval_decision"] = "ABORT"
    payload["destination_human_input_evidence_lock"][0]["approval_decision"] = "ABORT"
    ir38_path = _prepare_ir38(base, payload)

    out = run_ir39_human_approval_event_simulator_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir39_abort",
        ir38_runbook_report_path=ir38_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_human_event_simulation"] if r["destination"] == "regulatory_audit"][0]
    assert row["selected_event"] == "ABORT_ACK"
    assert row["state_transition"]["to_state"] == "EVIDENCE_LOCKED_ABORT_ACKED"


def test_ir39_fail_when_ir38_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir39_human_approval_event_simulator_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir39_missing",
        ir38_runbook_report_path=tmp_path / "missing_ir38.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir39_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir38_path = _prepare_ir38(base)
    ir39 = run_ir39_human_approval_event_simulator_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir39_completion",
        ir38_runbook_report_path=ir38_path,
    )

    completion = write_ir39_completion_report(
        base_path=base,
        ir39_output=ir39,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 24, "failed": 0},
        scoped_regression={"passed": 289, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 39"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_approval_decision"] == "APPROVE_DRY_RUN"
