import json
from pathlib import Path

from generic_block_ai.app.core_destination_human_event_chain_integrity import (
    run_ir41_destination_human_event_chain_integrity_dryrun,
    write_ir41_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir39_payload() -> dict:
    return {
        "schema_version": "ir39_human_approval_event_simulator_for_destinations_v1",
        "phase": "IR39",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "destination_human_event_simulation": [
            {
                "destination": "regulatory_audit",
                "selected_event": "APPROVE",
                "approver_record_required": True,
                "state_transition": {"to_state": "EVIDENCE_LOCKED_APPROVED"},
            },
            {
                "destination": "internal_review_board",
                "selected_event": "APPROVE",
                "approver_record_required": True,
                "state_transition": {"to_state": "EVIDENCE_LOCKED_APPROVED"},
            },
            {
                "destination": "compliance_archive",
                "selected_event": "APPROVE",
                "approver_record_required": True,
                "state_transition": {"to_state": "EVIDENCE_LOCKED_APPROVED"},
            },
        ],
    }


def _base_ir40_payload() -> dict:
    return {
        "schema_version": "ir40_human_event_audit_replay_for_destinations_v1",
        "phase": "IR40",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "destination_human_event_audit_replay": [
            {
                "destination": "regulatory_audit",
                "selected_event": "APPROVE",
                "replay_sequence": ["APPROVE"],
                "replay_trace": {"to_state": "EVIDENCE_LOCKED_APPROVED"},
            },
            {
                "destination": "internal_review_board",
                "selected_event": "APPROVE",
                "replay_sequence": ["APPROVE"],
                "replay_trace": {"to_state": "EVIDENCE_LOCKED_APPROVED"},
            },
            {
                "destination": "compliance_archive",
                "selected_event": "APPROVE",
                "replay_sequence": ["APPROVE"],
                "replay_trace": {"to_state": "EVIDENCE_LOCKED_APPROVED"},
            },
        ],
    }


def _prepare_inputs(base: Path, ir39_payload: dict | None = None, ir40_payload: dict | None = None) -> tuple[Path, Path]:
    reports = base / "reports"
    ir39_path = reports / "ir39_human_approval_event_simulator_for_destinations_report_fixture.json"
    ir40_path = reports / "ir40_human_event_audit_replay_for_destinations_report_fixture.json"
    _write(ir39_path, ir39_payload or _base_ir39_payload())
    _write(ir40_path, ir40_payload or _base_ir40_payload())
    return ir39_path, ir40_path


def test_ir41_pass_chain_integrity(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir39_path, ir40_path = _prepare_inputs(base)

    out = run_ir41_destination_human_event_chain_integrity_dryrun(
        base_path=base,
        source_task_id="ir41_pass",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3
    assert report["summary"]["integrity_pass_count"] == 3


def test_ir41_fail_when_destination_missing_in_ir39(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir39_payload = _base_ir39_payload()
    ir39_payload["destination_human_event_simulation"] = ir39_payload["destination_human_event_simulation"][:2]
    ir39_path, ir40_path = _prepare_inputs(base, ir39_payload=ir39_payload)

    out = run_ir41_destination_human_event_chain_integrity_dryrun(
        base_path=base,
        source_task_id="ir41_missing_dest",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_chain_integrity"] if r["destination"] == "compliance_archive"][0]
    assert row["integrity_result"] == "FAIL"


def test_ir41_fail_on_event_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir40_payload = _base_ir40_payload()
    ir40_payload["destination_human_event_audit_replay"][1]["selected_event"] = "REQUEST_FIX"
    ir39_path, ir40_path = _prepare_inputs(base, ir40_payload=ir40_payload)

    out = run_ir41_destination_human_event_chain_integrity_dryrun(
        base_path=base,
        source_task_id="ir41_event_mismatch",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_chain_integrity"] if r["destination"] == "internal_review_board"][0]
    assert row["integrity_checks"]["event_integrity_ok"] is False


def test_ir41_fail_on_lock_state_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir40_payload = _base_ir40_payload()
    ir40_payload["destination_human_event_audit_replay"][0]["replay_trace"]["to_state"] = "EVIDENCE_LOCKED_REJECTED"
    ir39_path, ir40_path = _prepare_inputs(base, ir40_payload=ir40_payload)

    out = run_ir41_destination_human_event_chain_integrity_dryrun(
        base_path=base,
        source_task_id="ir41_lock_mismatch",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_chain_integrity"] if r["destination"] == "regulatory_audit"][0]
    assert row["integrity_checks"]["lock_state_integrity_ok"] is False


def test_ir41_fail_when_input_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir41_destination_human_event_chain_integrity_dryrun(
        base_path=base,
        source_task_id="ir41_missing",
        ir39_event_report_path=tmp_path / "missing_ir39.json",
        ir40_replay_report_path=tmp_path / "missing_ir40.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir41_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir39_path, ir40_path = _prepare_inputs(base)
    ir41 = run_ir41_destination_human_event_chain_integrity_dryrun(
        base_path=base,
        source_task_id="ir41_completion",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
    )

    completion = write_ir41_completion_report(
        base_path=base,
        ir41_output=ir41,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 301, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 41"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_approval_decision"] == "APPROVE_DRY_RUN"
