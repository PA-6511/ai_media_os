import json
from pathlib import Path

from generic_block_ai.app.core_submission_release_candidate_marker import (
    run_ir26_submission_release_candidate_marker_dryrun,
)
from generic_block_ai.app.core_release_candidate_integrity_verifier import (
    run_ir27_release_candidate_integrity_verifier_dryrun,
    write_ir27_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_ir25_allow_report(base: Path) -> Path:
    report = {
        "schema_version": "ir25_submission_change_approval_gate_v1",
        "phase": "IR25",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_task_id": "ir25_fixture",
        "decision": "ALLOW",
        "decision_reasons": ["no_diff_detected"],
        "validation_failed_checks": [],
        "validation_warnings": [],
        "policy": {
            "allowed_addition_patterns": [
                "generic_block_ai/reports/ir19_policy_drift_detector_report_*.json"
            ]
        },
        "summary": {
            "decision": "ALLOW",
            "reason_count": 1,
            "failed_check_count": 0,
            "warning_count": 0,
        },
        "artifacts": {
            "ir24_diff_report": "generic_block_ai/reports/ir24_submission_version_diff_audit_report_ir24_live_trial.json"
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }
    path = base / "reports" / "ir25_submission_change_approval_gate_report_ir25_fixture.json"
    _write(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return path


def _prepare_ir26(base: Path) -> Path:
    ir25_path = _create_ir25_allow_report(base)
    ir26 = run_ir26_submission_release_candidate_marker_dryrun(
        base_path=base,
        source_task_id="ir26_for_ir27",
        ir25_gate_report_path=ir25_path,
    )
    return Path(ir26["path"])


def test_ir27_pass_with_valid_marker(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir26_path = _prepare_ir26(base)

    out = run_ir27_release_candidate_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir27_pass",
        ir26_marker_report_path=ir26_path,
    )

    report = out["integrity_report"]
    assert report["validation_result"] == "PASS"


def test_ir27_fail_when_ir26_report_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    out = run_ir27_release_candidate_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir27_missing",
        ir26_marker_report_path=tmp_path / "not_found.json",
    )
    report = out["integrity_report"]
    assert report["validation_result"] == "FAIL"


def test_ir27_detect_snapshot_hash_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir26_path = _prepare_ir26(base)

    ir26 = json.loads(ir26_path.read_text(encoding="utf-8"))
    snapshot_path = base.parent / Path(ir26["artifacts"]["approval_snapshot"])
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["ir25"]["decision_reasons"] = ["tampered"]
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir27_release_candidate_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir27_hash_mismatch",
        ir26_marker_report_path=ir26_path,
    )

    report = out["integrity_report"]
    assert report["validation_result"] == "FAIL"
    assert report["integrity"]["tamper_flags"]["snapshot_hash_mismatch"] is True


def test_ir27_detect_immutable_policy_tamper(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir26_path = _prepare_ir26(base)

    ir26 = json.loads(ir26_path.read_text(encoding="utf-8"))
    marker_path = base.parent / Path(ir26["artifacts"]["immutable_marker"])
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["immutable"]["marker_locked"] = False
    marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir27_release_candidate_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir27_policy_tamper",
        ir26_marker_report_path=ir26_path,
    )

    report = out["integrity_report"]
    assert report["validation_result"] == "FAIL"
    assert report["integrity"]["tamper_flags"]["immutable_policy_mismatch"] is True


def test_ir27_detect_reference_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir26_path = _prepare_ir26(base)

    ir26 = json.loads(ir26_path.read_text(encoding="utf-8"))
    snapshot_path = base.parent / Path(ir26["artifacts"]["approval_snapshot"])
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["ir25"]["artifacts"]["ir24_diff_report"] = "generic_block_ai/reports/wrong_ir24.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir27_release_candidate_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir27_ref_mismatch",
        ir26_marker_report_path=ir26_path,
    )

    report = out["integrity_report"]
    assert report["validation_result"] == "FAIL"
    assert report["integrity"]["tamper_flags"]["reference_mismatch"] is True


def test_write_ir27_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir26_path = _prepare_ir26(base)

    ir27 = run_ir27_release_candidate_integrity_verifier_dryrun(
        base_path=base,
        source_task_id="ir27_complete",
        ir26_marker_report_path=ir26_path,
    )

    completion = write_ir27_completion_report(
        base_path=base,
        ir27_output=ir27,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 217, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 27"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
