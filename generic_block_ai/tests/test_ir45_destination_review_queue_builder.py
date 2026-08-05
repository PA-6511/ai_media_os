import json
from pathlib import Path

from generic_block_ai.app.core_destination_review_queue_builder import (
    run_ir45_destination_review_queue_builder_dryrun,
    write_ir45_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_row(destination: str) -> dict:
    return {
        "destination": destination,
        "submission_gate_decision": "READY_FOR_REVIEW",
        "gate_reasons": ["bundle verification checks passed"],
        "verification_status": "PASS",
        "verification_checks": {
            "hash_manifest_exists": True,
            "summary_exists": True,
            "manifest_hash_ok": True,
            "recompute_ok": True,
            "summary_ok": True,
            "completeness_ok": True,
        },
        "bundle_hash": "hash",
        "evidence_digest": "digest",
        "hash_manifest_path": "generic_block_ai/reports/x/hash.json",
        "review_summary_path": "generic_block_ai/reports/x/summary.md",
    }


def _base_ir44_payload() -> dict:
    return {
        "schema_version": "ir44_destination_evidence_bundle_submission_gate_v1",
        "phase": "IR44",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "overall_submission_gate_decision": "READY_FOR_REVIEW",
        "destination_submission_gate": [
            _base_row("regulatory_audit"),
            _base_row("internal_review_board"),
            _base_row("compliance_archive"),
        ],
    }


def _prepare_ir44(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir44_destination_evidence_bundle_submission_gate_report_fixture.json"
    _write(target, payload or _base_ir44_payload())
    return target


def test_ir45_pass_queue_from_ready_destinations(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir44_path = _prepare_ir44(base)

    out = run_ir45_destination_review_queue_builder_dryrun(
        base_path=base,
        source_task_id="ir45_pass",
        ir44_submission_gate_report_path=ir44_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3
    assert report["summary"]["queued_for_review_count"] == 3


def test_ir45_human_review_queue_hold(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir44_payload()
    payload["destination_submission_gate"][1]["submission_gate_decision"] = "HUMAN_REVIEW_REQUIRED"
    ir44_path = _prepare_ir44(base, payload)

    out = run_ir45_destination_review_queue_builder_dryrun(
        base_path=base,
        source_task_id="ir45_hold",
        ir44_submission_gate_report_path=ir44_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_review_queue"] if r["destination"] == "internal_review_board"][0]
    assert row["review_queue_status"] == "HOLD_FOR_HUMAN_REVIEW"


def test_ir45_rejected_no_queue(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir44_payload()
    payload["destination_submission_gate"][0]["submission_gate_decision"] = "REJECT"
    ir44_path = _prepare_ir44(base, payload)

    out = run_ir45_destination_review_queue_builder_dryrun(
        base_path=base,
        source_task_id="ir45_reject",
        ir44_submission_gate_report_path=ir44_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_review_queue"] if r["destination"] == "regulatory_audit"][0]
    assert row["review_queue_status"] == "REJECTED_NO_QUEUE"


def test_ir45_aborted_no_queue(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir44_payload()
    payload["destination_submission_gate"][2]["submission_gate_decision"] = "ABORT"
    payload["overall_submission_gate_decision"] = "ABORT"
    ir44_path = _prepare_ir44(base, payload)

    out = run_ir45_destination_review_queue_builder_dryrun(
        base_path=base,
        source_task_id="ir45_abort",
        ir44_submission_gate_report_path=ir44_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_review_queue"] if r["destination"] == "compliance_archive"][0]
    assert row["review_queue_status"] == "ABORTED_NO_QUEUE"


def test_ir45_fail_when_ir44_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir45_destination_review_queue_builder_dryrun(
        base_path=base,
        source_task_id="ir45_missing",
        ir44_submission_gate_report_path=tmp_path / "missing_ir44.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir45_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir44_path = _prepare_ir44(base)
    ir45 = run_ir45_destination_review_queue_builder_dryrun(
        base_path=base,
        source_task_id="ir45_completion",
        ir44_submission_gate_report_path=ir44_path,
    )

    completion = write_ir45_completion_report(
        base_path=base,
        ir45_output=ir45,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 19, "failed": 0},
        scoped_regression={"passed": 326, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 45"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_submission_gate_decision"] == "READY_FOR_REVIEW"