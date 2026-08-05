import json
from pathlib import Path

from generic_block_ai.app.core_destination_review_queue_approval_gate import (
    run_ir47_destination_review_queue_approval_gate_dryrun,
    write_ir47_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_row(destination: str) -> dict:
    return {
        "destination": destination,
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
        "failed_reasons": [],
        "evidence_reference_links": {
            "hash_manifest": "generic_block_ai/reports/test/hash_manifest.json",
            "review_summary": "generic_block_ai/reports/test/review_summary.md",
            "gate_report": "generic_block_ai/reports/ir44_destination_evidence_bundle_submission_gate_report_fixture.json",
        },
    }


def _base_ir46_payload() -> dict:
    return {
        "schema_version": "ir46_destination_review_queue_integrity_verifier_v1",
        "phase": "IR46",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "overall_submission_gate_decision": "READY_FOR_REVIEW",
        "destination_review_queue_integrity": [
            _base_row("regulatory_audit"),
            _base_row("internal_review_board"),
            _base_row("compliance_archive"),
        ],
    }


def _prepare_ir46(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir46_destination_review_queue_integrity_verifier_report_fixture.json"
    _write(target, payload or _base_ir46_payload())
    return target


def test_ir47_pass_when_all_ready_for_human_review(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir46_path = _prepare_ir46(base)

    out = run_ir47_destination_review_queue_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir47_pass",
        ir46_integrity_verifier_report_path=ir46_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["overall_review_queue_approval_decision"] == "READY_FOR_HUMAN_REVIEW"
    assert report["summary"]["ready_for_human_review_count"] == 3


def test_ir47_hold_when_integrity_fails_noncritical(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir46_payload()
    payload["destination_review_queue_integrity"][1]["integrity_result"] = "FAIL"
    payload["destination_review_queue_integrity"][1]["failed_reasons"] = ["review item count mismatch for queue status"]
    ir46_path = _prepare_ir46(base, payload)

    out = run_ir47_destination_review_queue_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir47_hold",
        ir46_integrity_verifier_report_path=ir46_path,
    )

    report = out["runbook_report"]
    assert report["overall_review_queue_approval_decision"] == "HOLD"
    row = [r for r in report["destination_review_queue_approval_gate"] if r["destination"] == "internal_review_board"][0]
    assert row["review_queue_approval_decision"] == "HOLD"


def test_ir47_reject_when_failed_and_rejected_status(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir46_payload()
    payload["destination_review_queue_integrity"][0]["integrity_result"] = "FAIL"
    payload["destination_review_queue_integrity"][0]["review_queue_status"] = "REJECTED_NO_QUEUE"
    payload["destination_review_queue_integrity"][0]["failed_reasons"] = ["duplicate review item id detected"]
    ir46_path = _prepare_ir46(base, payload)

    out = run_ir47_destination_review_queue_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir47_reject",
        ir46_integrity_verifier_report_path=ir46_path,
    )

    report = out["runbook_report"]
    assert report["overall_review_queue_approval_decision"] == "REJECT"


def test_ir47_abort_when_critical_integrity_issue(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir46_payload()
    payload["destination_review_queue_integrity"][2]["integrity_result"] = "FAIL"
    payload["destination_review_queue_integrity"][2]["failed_reasons"] = ["evidence reference link missing or unresolved"]
    ir46_path = _prepare_ir46(base, payload)

    out = run_ir47_destination_review_queue_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir47_abort",
        ir46_integrity_verifier_report_path=ir46_path,
    )

    report = out["runbook_report"]
    assert report["overall_review_queue_approval_decision"] == "ABORT"


def test_ir47_fail_when_ir46_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir47_destination_review_queue_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir47_missing",
        ir46_integrity_verifier_report_path=tmp_path / "missing_ir46.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir47_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir46_path = _prepare_ir46(base)
    ir47 = run_ir47_destination_review_queue_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir47_completion",
        ir46_integrity_verifier_report_path=ir46_path,
    )

    completion = write_ir47_completion_report(
        base_path=base,
        ir47_output=ir47,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 338, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 47"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_review_queue_approval_decision"] == "READY_FOR_HUMAN_REVIEW"
