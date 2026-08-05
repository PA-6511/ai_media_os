import json
from pathlib import Path

from generic_block_ai.app.core_destination_evidence_bundle_submission_gate import (
    run_ir44_destination_evidence_bundle_submission_gate_dryrun,
    write_ir44_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_row(destination: str) -> dict:
    return {
        "destination": destination,
        "verification_status": "PASS",
        "bundle_hash": "hash",
        "evidence_digest": "digest",
        "verification_checks": {
            "hash_manifest_exists": True,
            "summary_exists": True,
            "manifest_hash_ok": True,
            "recompute_ok": True,
            "summary_ok": True,
            "completeness_ok": True,
        },
        "hash_manifest_path": "generic_block_ai/reports/x/hash.json",
        "review_summary_path": "generic_block_ai/reports/x/summary.md",
    }


def _base_ir43_payload() -> dict:
    return {
        "schema_version": "ir43_destination_evidence_bundle_verifier_v1",
        "phase": "IR43",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "destination_evidence_bundle_verification": [
            _base_row("regulatory_audit"),
            _base_row("internal_review_board"),
            _base_row("compliance_archive"),
        ],
    }


def _prepare_ir43(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir43_destination_evidence_bundle_verifier_report_fixture.json"
    _write(target, payload or _base_ir43_payload())
    return target


def test_ir44_ready_for_review_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir43_path = _prepare_ir43(base)

    out = run_ir44_destination_evidence_bundle_submission_gate_dryrun(
        base_path=base,
        source_task_id="ir44_pass",
        ir43_verifier_report_path=ir43_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["overall_submission_gate_decision"] == "READY_FOR_REVIEW"
    assert report["summary"]["ready_for_review_count"] == 3


def test_ir44_human_review_required(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir43_payload()
    payload["destination_evidence_bundle_verification"][1]["verification_checks"]["recompute_ok"] = False
    ir43_path = _prepare_ir43(base, payload)

    out = run_ir44_destination_evidence_bundle_submission_gate_dryrun(
        base_path=base,
        source_task_id="ir44_human_review",
        ir43_verifier_report_path=ir43_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_submission_gate"] if r["destination"] == "internal_review_board"][0]
    assert row["submission_gate_decision"] == "HUMAN_REVIEW_REQUIRED"


def test_ir44_reject_on_manifest_or_summary_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir43_payload()
    payload["destination_evidence_bundle_verification"][0]["verification_checks"]["manifest_hash_ok"] = False
    ir43_path = _prepare_ir43(base, payload)

    out = run_ir44_destination_evidence_bundle_submission_gate_dryrun(
        base_path=base,
        source_task_id="ir44_reject",
        ir43_verifier_report_path=ir43_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_submission_gate"] if r["destination"] == "regulatory_audit"][0]
    assert row["submission_gate_decision"] == "REJECT"


def test_ir44_abort_on_missing_artifact(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir43_payload()
    payload["destination_evidence_bundle_verification"][2]["verification_checks"]["summary_exists"] = False
    ir43_path = _prepare_ir43(base, payload)

    out = run_ir44_destination_evidence_bundle_submission_gate_dryrun(
        base_path=base,
        source_task_id="ir44_abort",
        ir43_verifier_report_path=ir43_path,
    )

    report = out["runbook_report"]
    row = [r for r in report["destination_submission_gate"] if r["destination"] == "compliance_archive"][0]
    assert row["submission_gate_decision"] == "ABORT"
    assert report["overall_submission_gate_decision"] == "ABORT"


def test_ir44_fail_when_ir43_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir44_destination_evidence_bundle_submission_gate_dryrun(
        base_path=base,
        source_task_id="ir44_missing",
        ir43_verifier_report_path=tmp_path / "missing_ir43.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir44_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir43_path = _prepare_ir43(base)
    ir44 = run_ir44_destination_evidence_bundle_submission_gate_dryrun(
        base_path=base,
        source_task_id="ir44_completion",
        ir43_verifier_report_path=ir43_path,
    )

    completion = write_ir44_completion_report(
        base_path=base,
        ir44_output=ir44,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 19, "failed": 0},
        scoped_regression={"passed": 320, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 44"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_submission_gate_decision"] == "READY_FOR_REVIEW"