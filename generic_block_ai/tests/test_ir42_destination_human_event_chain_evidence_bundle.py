import json
from pathlib import Path

from generic_block_ai.app.core_destination_human_event_chain_evidence_bundle import (
    run_ir42_destination_human_event_chain_evidence_bundle_dryrun,
    write_ir42_completion_report,
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


def _base_ir41_payload() -> dict:
    return {
        "schema_version": "ir41_destination_human_event_chain_integrity_v1",
        "phase": "IR41",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "destination_human_event_chain_integrity": [
            {
                "destination": "regulatory_audit",
                "chain": [
                    {
                        "sequence_no": 1,
                        "event": "APPROVE",
                        "actor_id": "HUMAN_APPROVER_REQUIRED",
                        "lock_state": "EVIDENCE_LOCKED_APPROVED",
                        "chain_hash": "881a2d751cb9d3b45841b1f671e4984b6ca97e0bacceb57bdd4704c0747b7821",
                    }
                ],
            },
            {
                "destination": "internal_review_board",
                "chain": [
                    {
                        "sequence_no": 1,
                        "event": "APPROVE",
                        "actor_id": "HUMAN_APPROVER_REQUIRED",
                        "lock_state": "EVIDENCE_LOCKED_APPROVED",
                        "chain_hash": "072ad9c550d8e7ff74ab1a6e662a1b0344e5d7f696e52ec0ccbf9478d061e8e8",
                    }
                ],
            },
            {
                "destination": "compliance_archive",
                "chain": [
                    {
                        "sequence_no": 1,
                        "event": "APPROVE",
                        "actor_id": "HUMAN_APPROVER_REQUIRED",
                        "lock_state": "EVIDENCE_LOCKED_APPROVED",
                        "chain_hash": "fbf166942a72e7496df4c6db872d2402cf9434f92ef335d788e6b1998f1e9a55",
                    }
                ],
            },
        ],
    }


def _prepare_inputs(
    base: Path,
    ir39_payload: dict | None = None,
    ir40_payload: dict | None = None,
    ir41_payload: dict | None = None,
) -> tuple[Path, Path, Path]:
    reports = base / "reports"
    ir39_path = reports / "ir39_human_approval_event_simulator_for_destinations_report_fixture.json"
    ir40_path = reports / "ir40_human_event_audit_replay_for_destinations_report_fixture.json"
    ir41_path = reports / "ir41_destination_human_event_chain_integrity_report_fixture.json"
    _write(ir39_path, ir39_payload or _base_ir39_payload())
    _write(ir40_path, ir40_payload or _base_ir40_payload())
    _write(ir41_path, ir41_payload or _base_ir41_payload())
    return ir39_path, ir40_path, ir41_path


def test_ir42_pass_evidence_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir39_path, ir40_path, ir41_path = _prepare_inputs(base)

    out = run_ir42_destination_human_event_chain_evidence_bundle_dryrun(
        base_path=base,
        source_task_id="ir42_pass",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
        ir41_chain_report_path=ir41_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3
    assert report["summary"]["bundle_pass_count"] == 3


def test_ir42_fail_on_missing_destination(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir41_payload = _base_ir41_payload()
    ir41_payload["destination_human_event_chain_integrity"] = ir41_payload["destination_human_event_chain_integrity"][:2]
    ir39_path, ir40_path, ir41_path = _prepare_inputs(base, ir41_payload=ir41_payload)

    out = run_ir42_destination_human_event_chain_evidence_bundle_dryrun(
        base_path=base,
        source_task_id="ir42_missing_dest",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
        ir41_chain_report_path=ir41_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_chain_evidence_bundle"] if r["destination"] == "compliance_archive"][0]
    assert row["review_status"] == "FAIL"


def test_ir42_fail_on_chain_hash_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir41_payload = _base_ir41_payload()
    ir41_payload["destination_human_event_chain_integrity"][0]["chain"][0]["chain_hash"] = "bad_hash"
    ir39_path, ir40_path, ir41_path = _prepare_inputs(base, ir41_payload=ir41_payload)

    out = run_ir42_destination_human_event_chain_evidence_bundle_dryrun(
        base_path=base,
        source_task_id="ir42_hash_mismatch",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
        ir41_chain_report_path=ir41_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_chain_evidence_bundle"] if r["destination"] == "regulatory_audit"][0]
    assert row["integrity_checks"]["hash_ok"] is False


def test_ir42_fail_on_event_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir40_payload = _base_ir40_payload()
    ir40_payload["destination_human_event_audit_replay"][1]["selected_event"] = "REQUEST_FIX"
    ir39_path, ir40_path, ir41_path = _prepare_inputs(base, ir40_payload=ir40_payload)

    out = run_ir42_destination_human_event_chain_evidence_bundle_dryrun(
        base_path=base,
        source_task_id="ir42_event_mismatch",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
        ir41_chain_report_path=ir41_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_human_event_chain_evidence_bundle"] if r["destination"] == "internal_review_board"][0]
    assert row["integrity_checks"]["event_ok"] is False


def test_ir42_fail_when_input_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir42_destination_human_event_chain_evidence_bundle_dryrun(
        base_path=base,
        source_task_id="ir42_missing",
        ir39_event_report_path=tmp_path / "missing_ir39.json",
        ir40_replay_report_path=tmp_path / "missing_ir40.json",
        ir41_chain_report_path=tmp_path / "missing_ir41.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir42_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir39_path, ir40_path, ir41_path = _prepare_inputs(base)
    ir42 = run_ir42_destination_human_event_chain_evidence_bundle_dryrun(
        base_path=base,
        source_task_id="ir42_completion",
        ir39_event_report_path=ir39_path,
        ir40_replay_report_path=ir40_path,
        ir41_chain_report_path=ir41_path,
    )

    completion = write_ir42_completion_report(
        base_path=base,
        ir42_output=ir42,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 307, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 42"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_approval_decision"] == "APPROVE_DRY_RUN"