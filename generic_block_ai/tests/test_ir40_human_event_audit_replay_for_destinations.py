import json
from pathlib import Path

from generic_block_ai.app.core_human_event_audit_replay_for_destinations import (
    run_ir40_human_event_audit_replay_for_destinations_dryrun,
    write_ir40_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir39_payload() -> dict:
    return {
        "schema_version": "ir39_human_approval_event_simulator_for_destinations_v1",
        "phase": "IR39",
        "source_task_id": "ir39_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "destination_human_event_simulation": [
            {
                "destination": "regulatory_audit",
                "allowed_events": ["APPROVE", "REQUEST_FIX"],
                "selected_event": "APPROVE",
                "state_transition": {
                    "from_state": "EVIDENCE_LOCK_ACTIVE",
                    "to_state": "EVIDENCE_LOCKED_APPROVED",
                    "transition_applied": True,
                },
                "approver_record_required": True,
                "manifest_path": "generic_block_ai/reports/x/regulatory_audit/destination_package_manifest.json",
            },
            {
                "destination": "internal_review_board",
                "allowed_events": ["APPROVE", "REQUEST_FIX"],
                "selected_event": "APPROVE",
                "state_transition": {
                    "from_state": "EVIDENCE_LOCK_ACTIVE",
                    "to_state": "EVIDENCE_LOCKED_APPROVED",
                    "transition_applied": True,
                },
                "approver_record_required": True,
                "manifest_path": "generic_block_ai/reports/x/internal_review_board/destination_package_manifest.json",
            },
            {
                "destination": "compliance_archive",
                "allowed_events": ["APPROVE", "REQUEST_FIX"],
                "selected_event": "APPROVE",
                "state_transition": {
                    "from_state": "EVIDENCE_LOCK_ACTIVE",
                    "to_state": "EVIDENCE_LOCKED_APPROVED",
                    "transition_applied": True,
                },
                "approver_record_required": True,
                "manifest_path": "generic_block_ai/reports/x/compliance_archive/destination_package_manifest.json",
            },
        ],
    }


def _prepare_ir39(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir39_human_approval_event_simulator_for_destinations_report_fixture.json"
    _write(target, payload or _base_ir39_payload())
    return target


def test_ir40_pass_replay_audit_from_ir39(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir39_path = _prepare_ir39(base)

    out = run_ir40_human_event_audit_replay_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir40_pass",
        ir39_event_report_path=ir39_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3
    assert report["summary"]["audit_pass_count"] == 3


def test_ir40_detects_state_mapping_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir39_payload()
    payload["destination_human_event_simulation"][1]["state_transition"]["to_state"] = "EVIDENCE_LOCKED_REJECTED"
    ir39_path = _prepare_ir39(base, payload)

    out = run_ir40_human_event_audit_replay_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir40_state_mismatch",
        ir39_event_report_path=ir39_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_audit_replay"] if r["destination"] == "internal_review_board"][0]
    assert row["audit_result"] == "FAIL"


def test_ir40_detects_disallowed_event(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir39_payload()
    payload["destination_human_event_simulation"][2]["selected_event"] = "ABORT_ACK"
    ir39_path = _prepare_ir39(base, payload)

    out = run_ir40_human_event_audit_replay_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir40_disallowed_event",
        ir39_event_report_path=ir39_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_audit_replay"] if r["destination"] == "compliance_archive"][0]
    assert row["audit_checks"]["event_allowed_ok"] is False


def test_ir40_detects_missing_approver_record_flag(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir39_payload()
    payload["destination_human_event_simulation"][0]["approver_record_required"] = False
    ir39_path = _prepare_ir39(base, payload)

    out = run_ir40_human_event_audit_replay_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir40_missing_approver",
        ir39_event_report_path=ir39_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_audit_replay"] if r["destination"] == "regulatory_audit"][0]
    assert row["audit_checks"]["approver_record_ok"] is False


def test_ir40_fail_when_ir39_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir40_human_event_audit_replay_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir40_missing",
        ir39_event_report_path=tmp_path / "missing_ir39.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir40_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir39_path = _prepare_ir39(base)
    ir40 = run_ir40_human_event_audit_replay_for_destinations_dryrun(
        base_path=base,
        source_task_id="ir40_completion",
        ir39_event_report_path=ir39_path,
    )

    completion = write_ir40_completion_report(
        base_path=base,
        ir40_output=ir40,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 295, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 40"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_approval_decision"] == "APPROVE_DRY_RUN"
