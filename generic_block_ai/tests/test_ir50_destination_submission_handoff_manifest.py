import json
from pathlib import Path

from generic_block_ai.app.core_destination_submission_handoff_manifest import (
    run_ir50_destination_submission_handoff_manifest_dryrun,
    write_ir50_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_row(destination: str) -> dict:
    return {
        "destination": destination,
        "submission_readiness_decision": "READY_DRY_RUN_ONLY",
        "readiness_reasons": ["human review approved destination for dry-run submission readiness"],
        "human_review_result": "APPROVE",
        "reviewer_role": "human_queue_reviewer",
        "review_item_ids": [f"{destination}-R1", f"{destination}-R2"],
        "review_notes": ["queue approved for human review intake"],
        "intake_record_path": f"generic_block_ai/reports/test/{destination}_human_review_result.json",
        "evidence_reference_links": {
            "hash_manifest": "generic_block_ai/reports/test/hash_manifest.json",
            "review_summary": "generic_block_ai/reports/test/review_summary.md",
            "gate_report": "generic_block_ai/reports/ir44_destination_evidence_bundle_submission_gate_report_ir44_live_trial.json",
        },
    }


def _base_ir49_payload() -> dict:
    return {
        "schema_version": "ir49_destination_submission_readiness_gate_v1",
        "phase": "IR49",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "overall_submission_gate_decision": "READY_FOR_REVIEW",
        "overall_review_queue_approval_decision": "READY_FOR_HUMAN_REVIEW",
        "overall_human_review_result": "APPROVE",
        "overall_submission_readiness_decision": "READY_DRY_RUN_ONLY",
        "destination_submission_readiness": [
            _base_row("regulatory_audit"),
            _base_row("internal_review_board"),
            _base_row("compliance_archive"),
        ],
    }


def _prepare_ir49(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir49_destination_submission_readiness_gate_report_fixture.json"
    _write(target, payload or _base_ir49_payload())
    return target


def test_ir50_pass_when_all_destinations_included(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir49_path = _prepare_ir49(base)

    out = run_ir50_destination_submission_handoff_manifest_dryrun(
        base_path=base,
        source_task_id="ir50_pass",
        ir49_submission_readiness_report_path=ir49_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["overall_submission_handoff_decision"] == "READY_DRY_RUN_HANDOFF"
    assert report["summary"]["include_in_dry_run_handoff_count"] == 3
    assert report["handoff_manifest"]["submission_execution_blocked"] is True


def test_ir50_hold_when_readiness_hold_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir49_payload()
    payload["destination_submission_readiness"][1]["submission_readiness_decision"] = "HOLD"
    payload["destination_submission_readiness"][1]["readiness_reasons"] = ["submission readiness held for requested fixes"]
    ir49_path = _prepare_ir49(base, payload)

    out = run_ir50_destination_submission_handoff_manifest_dryrun(
        base_path=base,
        source_task_id="ir50_hold",
        ir49_submission_readiness_report_path=ir49_path,
    )

    report = out["runbook_report"]
    assert report["overall_submission_handoff_decision"] == "HOLD"


def test_ir50_reject_when_readiness_reject_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir49_payload()
    payload["destination_submission_readiness"][0]["submission_readiness_decision"] = "REJECT"
    payload["destination_submission_readiness"][0]["readiness_reasons"] = ["submission readiness rejected by human review"]
    ir49_path = _prepare_ir49(base, payload)

    out = run_ir50_destination_submission_handoff_manifest_dryrun(
        base_path=base,
        source_task_id="ir50_reject",
        ir49_submission_readiness_report_path=ir49_path,
    )

    report = out["runbook_report"]
    assert report["overall_submission_handoff_decision"] == "REJECT"


def test_ir50_abort_when_readiness_abort_present(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir49_payload()
    payload["destination_submission_readiness"][2]["submission_readiness_decision"] = "ABORT"
    payload["destination_submission_readiness"][2]["readiness_reasons"] = ["submission readiness aborted after abort acknowledgement"]
    ir49_path = _prepare_ir49(base, payload)

    out = run_ir50_destination_submission_handoff_manifest_dryrun(
        base_path=base,
        source_task_id="ir50_abort",
        ir49_submission_readiness_report_path=ir49_path,
    )

    report = out["runbook_report"]
    assert report["overall_submission_handoff_decision"] == "ABORT"


def test_ir50_fail_when_ir49_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir50_destination_submission_handoff_manifest_dryrun(
        base_path=base,
        source_task_id="ir50_missing",
        ir49_submission_readiness_report_path=tmp_path / "missing_ir49.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir50_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir49_path = _prepare_ir49(base)
    ir50 = run_ir50_destination_submission_handoff_manifest_dryrun(
        base_path=base,
        source_task_id="ir50_completion",
        ir49_submission_readiness_report_path=ir49_path,
    )

    completion = write_ir50_completion_report(
        base_path=base,
        ir50_output=ir50,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 356, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 50"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_submission_handoff_decision"] == "READY_DRY_RUN_HANDOFF"