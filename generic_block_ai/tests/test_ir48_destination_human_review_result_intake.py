import json
from pathlib import Path

from generic_block_ai.app.core_destination_human_review_result_intake import (
    run_ir48_destination_human_review_result_intake_dryrun,
    write_ir48_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_row(destination: str) -> dict:
    return {
        "destination": destination,
        "review_queue_approval_decision": "READY_FOR_HUMAN_REVIEW",
        "approval_reasons": ["integrity passed and queue ready for human review"],
        "review_queue_status": "QUEUED_FOR_REVIEW",
        "integrity_result": "PASS",
        "integrity_checks": {
            "queue_status_ok": True,
            "missing_items": False,
            "duplicate_destination": False,
            "duplicate_item_ids": False,
            "item_count_ok": True,
            "checklist_ok": True,
            "evidence_links_ok": True,
        },
        "review_item_ids": [f"{destination}-R1", f"{destination}-R2"],
        "integrity_failed_reasons": [],
        "evidence_reference_links": {
            "hash_manifest": "generic_block_ai/reports/test/hash_manifest.json",
            "review_summary": "generic_block_ai/reports/test/review_summary.md",
            "gate_report": "generic_block_ai/reports/ir44_destination_evidence_bundle_submission_gate_report_fixture.json",
        },
    }


def _base_ir47_payload() -> dict:
    return {
        "schema_version": "ir47_destination_review_queue_approval_gate_v1",
        "phase": "IR47",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "overall_submission_gate_decision": "READY_FOR_REVIEW",
        "overall_review_queue_approval_decision": "READY_FOR_HUMAN_REVIEW",
        "destination_review_queue_approval_gate": [
            _base_row("regulatory_audit"),
            _base_row("internal_review_board"),
            _base_row("compliance_archive"),
        ],
    }


def _prepare_ir47(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir47_destination_review_queue_approval_gate_report_fixture.json"
    _write(target, payload or _base_ir47_payload())
    return target


def test_ir48_pass_when_all_reviews_approved(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir47_path = _prepare_ir47(base)

    out = run_ir48_destination_human_review_result_intake_dryrun(
        base_path=base,
        source_task_id="ir48_pass",
        ir47_approval_gate_report_path=ir47_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["overall_human_review_result"] == "APPROVE"
    assert report["summary"]["approve_count"] == 3


def test_ir48_request_fix_when_hold_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir47_payload()
    payload["destination_review_queue_approval_gate"][1]["review_queue_approval_decision"] = "HOLD"
    payload["destination_review_queue_approval_gate"][1]["approval_reasons"] = ["integrity failed; hold for remediation before review"]
    ir47_path = _prepare_ir47(base, payload)

    out = run_ir48_destination_human_review_result_intake_dryrun(
        base_path=base,
        source_task_id="ir48_request_fix",
        ir47_approval_gate_report_path=ir47_path,
    )

    report = out["runbook_report"]
    assert report["overall_human_review_result"] == "REQUEST_FIX"


def test_ir48_reject_when_reject_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir47_payload()
    payload["destination_review_queue_approval_gate"][0]["review_queue_approval_decision"] = "REJECT"
    payload["destination_review_queue_approval_gate"][0]["approval_reasons"] = ["integrity failed and queue already rejected"]
    ir47_path = _prepare_ir47(base, payload)

    out = run_ir48_destination_human_review_result_intake_dryrun(
        base_path=base,
        source_task_id="ir48_reject",
        ir47_approval_gate_report_path=ir47_path,
    )

    report = out["runbook_report"]
    assert report["overall_human_review_result"] == "REJECT"


def test_ir48_abort_ack_when_abort_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir47_payload()
    payload["destination_review_queue_approval_gate"][2]["review_queue_approval_decision"] = "ABORT"
    payload["destination_review_queue_approval_gate"][2]["approval_reasons"] = ["critical integrity issue detected; abort required"]
    ir47_path = _prepare_ir47(base, payload)

    out = run_ir48_destination_human_review_result_intake_dryrun(
        base_path=base,
        source_task_id="ir48_abort_ack",
        ir47_approval_gate_report_path=ir47_path,
    )

    report = out["runbook_report"]
    assert report["overall_human_review_result"] == "ABORT_ACK"


def test_ir48_fail_when_ir47_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir48_destination_human_review_result_intake_dryrun(
        base_path=base,
        source_task_id="ir48_missing",
        ir47_approval_gate_report_path=tmp_path / "missing_ir47.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir48_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir47_path = _prepare_ir47(base)
    ir48 = run_ir48_destination_human_review_result_intake_dryrun(
        base_path=base,
        source_task_id="ir48_completion",
        ir47_approval_gate_report_path=ir47_path,
    )

    completion = write_ir48_completion_report(
        base_path=base,
        ir48_output=ir48,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 344, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 48"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_human_review_result"] == "APPROVE"