import json
from pathlib import Path

from generic_block_ai.app.core_destination_review_queue_integrity_verifier import (
    run_ir46_destination_review_queue_integrity_verifier_dryrun,
    write_ir46_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_row(destination: str) -> dict:
    return {
        "destination": destination,
        "submission_gate_decision": "READY_FOR_REVIEW",
        "review_queue_status": "QUEUED_FOR_REVIEW",
        "review_items": [
            {
                "item_id": f"{destination}-R1",
                "title": "Verify hash manifest and summary link consistency",
                "owner_role": "destination_reviewer",
                "required": True,
            },
            {
                "item_id": f"{destination}-R2",
                "title": "Confirm evidence digest and bundle hash correspondence",
                "owner_role": "integrity_reviewer",
                "required": True,
            },
        ],
        "owner_checklist": [
            "Confirm hash manifest path is reachable.",
            "Confirm review summary reflects gate decision.",
            "Confirm evidence digest and bundle hash references are attached.",
        ],
        "evidence_reference_links": {
            "hash_manifest": f"generic_block_ai/reports/test/{destination}/hash_manifest.json",
            "review_summary": f"generic_block_ai/reports/test/{destination}/review_summary.md",
            "gate_report": "generic_block_ai/reports/ir44_destination_evidence_bundle_submission_gate_report_fixture.json",
        },
    }


def _prepare_link_files(base: Path, row: dict) -> None:
    parent = base.parent
    links = row["evidence_reference_links"]
    hash_manifest = parent / links["hash_manifest"]
    review_summary = parent / links["review_summary"]
    gate_report = parent / links["gate_report"]
    hash_manifest.parent.mkdir(parents=True, exist_ok=True)
    review_summary.parent.mkdir(parents=True, exist_ok=True)
    gate_report.parent.mkdir(parents=True, exist_ok=True)
    hash_manifest.write_text("{}\n", encoding="utf-8")
    review_summary.write_text("# summary\n", encoding="utf-8")
    gate_report.write_text("{}\n", encoding="utf-8")


def _base_ir45_payload(base: Path) -> dict:
    rows = [
        _base_row("regulatory_audit"),
        _base_row("internal_review_board"),
        _base_row("compliance_archive"),
    ]
    for row in rows:
        _prepare_link_files(base, row)
    return {
        "schema_version": "ir45_destination_review_queue_builder_v1",
        "phase": "IR45",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "overall_submission_gate_decision": "READY_FOR_REVIEW",
        "destination_review_queue": rows,
    }


def _prepare_ir45(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir45_destination_review_queue_builder_report_fixture.json"
    _write(target, payload or _base_ir45_payload(base))
    return target


def test_ir46_pass_integrity_verifier(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir45_path = _prepare_ir45(base)

    out = run_ir46_destination_review_queue_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir46_pass",
        ir45_review_queue_report_path=ir45_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3
    assert report["summary"]["integrity_pass_count"] == 3


def test_ir46_fail_on_duplicate_item_id(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir45_payload(base)
    payload["destination_review_queue"][1]["review_items"][1]["item_id"] = payload["destination_review_queue"][1]["review_items"][0]["item_id"]
    ir45_path = _prepare_ir45(base, payload)

    out = run_ir46_destination_review_queue_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir46_dup_item",
        ir45_review_queue_report_path=ir45_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"


def test_ir46_fail_on_missing_links(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir45_payload(base)
    payload["destination_review_queue"][0]["evidence_reference_links"]["hash_manifest"] = "generic_block_ai/reports/test/missing/hash_manifest.json"
    ir45_path = _prepare_ir45(base, payload)

    out = run_ir46_destination_review_queue_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir46_missing_links",
        ir45_review_queue_report_path=ir45_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"


def test_ir46_fail_on_wrong_item_count_for_hold(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir45_payload(base)
    payload["destination_review_queue"][2]["review_queue_status"] = "HOLD_FOR_HUMAN_REVIEW"
    ir45_path = _prepare_ir45(base, payload)

    out = run_ir46_destination_review_queue_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir46_hold_count",
        ir45_review_queue_report_path=ir45_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"


def test_ir46_fail_when_ir45_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir46_destination_review_queue_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir46_missing",
        ir45_review_queue_report_path=tmp_path / "missing_ir45.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir46_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir45_path = _prepare_ir45(base)
    ir46 = run_ir46_destination_review_queue_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir46_completion",
        ir45_review_queue_report_path=ir45_path,
    )

    completion = write_ir46_completion_report(
        base_path=base,
        ir46_output=ir46,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 19, "failed": 0},
        scoped_regression={"passed": 332, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 46"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_submission_gate_decision"] == "READY_FOR_REVIEW"