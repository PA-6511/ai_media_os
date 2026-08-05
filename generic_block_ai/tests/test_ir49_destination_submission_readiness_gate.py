import json
from pathlib import Path

from generic_block_ai.app.core_destination_submission_readiness_gate import (
    run_ir49_destination_submission_readiness_gate_dryrun,
    write_ir49_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_row(destination: str) -> dict:
    return {
        "destination": destination,
        "review_queue_approval_decision": "READY_FOR_HUMAN_REVIEW",
        "human_review_result": "APPROVE",
        "reviewer_role": "human_queue_reviewer",
        "integrity_result": "PASS",
        "review_item_ids": [f"{destination}-R1", f"{destination}-R2"],
        "review_notes": ["queue approved for human review intake"],
        "evidence_reference_links": {
            "hash_manifest": "generic_block_ai/reports/test/hash_manifest.json",
            "review_summary": "generic_block_ai/reports/test/review_summary.md",
            "gate_report": "generic_block_ai/reports/ir44_destination_evidence_bundle_submission_gate_report_fixture.json",
        },
        "recorded_at": "2026-05-24T00:00:00+00:00",
        "approval_reasons": ["integrity passed and queue ready for human review"],
        "intake_record_path": f"generic_block_ai/reports/test/{destination}_human_review_result.json",
    }


def _base_ir48_payload() -> dict:
    return {
        "schema_version": "ir48_destination_human_review_result_intake_v1",
        "phase": "IR48",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "overall_submission_gate_decision": "READY_FOR_REVIEW",
        "overall_review_queue_approval_decision": "READY_FOR_HUMAN_REVIEW",
        "overall_human_review_result": "APPROVE",
        "destination_human_review_result_intake": [
            _base_row("regulatory_audit"),
            _base_row("internal_review_board"),
            _base_row("compliance_archive"),
        ],
    }


def _prepare_ir48(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir48_destination_human_review_result_intake_report_fixture.json"
    _write(target, payload or _base_ir48_payload())
    return target


def test_ir49_pass_when_all_destinations_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir48_path = _prepare_ir48(base)

    out = run_ir49_destination_submission_readiness_gate_dryrun(
        base_path=base,
        source_task_id="ir49_pass",
        ir48_human_review_result_intake_report_path=ir48_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["overall_submission_readiness_decision"] == "READY_DRY_RUN_ONLY"
    assert report["summary"]["ready_dry_run_only_count"] == 3


def test_ir49_hold_when_request_fix_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir48_payload()
    payload["destination_human_review_result_intake"][1]["human_review_result"] = "REQUEST_FIX"
    payload["destination_human_review_result_intake"][1]["review_notes"] = ["request remediation before approval"]
    ir48_path = _prepare_ir48(base, payload)

    out = run_ir49_destination_submission_readiness_gate_dryrun(
        base_path=base,
        source_task_id="ir49_hold",
        ir48_human_review_result_intake_report_path=ir48_path,
    )

    report = out["runbook_report"]
    assert report["overall_submission_readiness_decision"] == "HOLD"


def test_ir49_reject_when_reject_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir48_payload()
    payload["destination_human_review_result_intake"][0]["human_review_result"] = "REJECT"
    payload["destination_human_review_result_intake"][0]["review_notes"] = ["review queue rejected"]
    ir48_path = _prepare_ir48(base, payload)

    out = run_ir49_destination_submission_readiness_gate_dryrun(
        base_path=base,
        source_task_id="ir49_reject",
        ir48_human_review_result_intake_report_path=ir48_path,
    )

    report = out["runbook_report"]
    assert report["overall_submission_readiness_decision"] == "REJECT"


def test_ir49_abort_when_abort_ack_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir48_payload()
    payload["destination_human_review_result_intake"][2]["human_review_result"] = "ABORT_ACK"
    payload["destination_human_review_result_intake"][2]["review_notes"] = ["abort acknowledged by review intake"]
    ir48_path = _prepare_ir48(base, payload)

    out = run_ir49_destination_submission_readiness_gate_dryrun(
        base_path=base,
        source_task_id="ir49_abort",
        ir48_human_review_result_intake_report_path=ir48_path,
    )

    report = out["runbook_report"]
    assert report["overall_submission_readiness_decision"] == "ABORT"


def test_ir49_fail_when_ir48_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir49_destination_submission_readiness_gate_dryrun(
        base_path=base,
        source_task_id="ir49_missing",
        ir48_human_review_result_intake_report_path=tmp_path / "missing_ir48.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir49_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir48_path = _prepare_ir48(base)
    ir49 = run_ir49_destination_submission_readiness_gate_dryrun(
        base_path=base,
        source_task_id="ir49_completion",
        ir48_human_review_result_intake_report_path=ir48_path,
    )

    completion = write_ir49_completion_report(
        base_path=base,
        ir49_output=ir49,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 350, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 49"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_submission_readiness_decision"] == "READY_DRY_RUN_ONLY"