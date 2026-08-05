import json
from pathlib import Path

from generic_block_ai.app.core_release_candidate_trace_bundle import (
    run_ir28_release_candidate_trace_bundle_dryrun,
    write_ir28_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_chain(base: Path) -> Path:
    reports = base / "reports"

    for phase in range(20, 28):
        _write(
            reports / f"implementation_restart_phase{phase}_completion_report.json",
            json.dumps({"phase": phase, "status": "COMPLETED"}, ensure_ascii=False, indent=2) + "\n",
        )

    _write(reports / "ir20_cross_phase_evidence_bundle_ir20_live_trial.json", '{"phase":"IR20"}\n')
    _write(reports / "ir21_evidence_pack_verifier_report_ir21_live_trial.json", '{"phase":"IR21"}\n')
    _write(reports / "implementation_restart_phase22_completion_report.json", '{"phase":"IR22"}\n')
    _write(reports / "ir22_submission_profile_report_audit_submission_ir22_live_audit.json", '{"phase":"IR22"}\n')
    _write(reports / "ir22_submission_profile_report_review_minimal_ir22_live_review.json", '{"phase":"IR22"}\n')
    _write(reports / "ir22_submission_profile_report_policy_focus_ir22_live_policy.json", '{"phase":"IR22"}\n')

    ir23 = {
        "schema_version": "ir23_evidence_pack_lifecycle_audit_v1",
        "phase": "IR23",
        "validation_result": "PASS",
        "traceability": {
            "ir20_bundle_report": "generic_block_ai/reports/ir20_cross_phase_evidence_bundle_ir20_live_trial.json",
            "ir21_verifier_report": "generic_block_ai/reports/ir21_evidence_pack_verifier_report_ir21_live_trial.json",
            "ir22_completion_report": "generic_block_ai/reports/implementation_restart_phase22_completion_report.json",
            "ir22_profile_reports": [
                "generic_block_ai/reports/ir22_submission_profile_report_audit_submission_ir22_live_audit.json",
                "generic_block_ai/reports/ir22_submission_profile_report_review_minimal_ir22_live_review.json",
                "generic_block_ai/reports/ir22_submission_profile_report_policy_focus_ir22_live_policy.json",
            ],
        },
    }
    _write(reports / "ir23_evidence_pack_lifecycle_audit_report_ir23_live_trial.json", json.dumps(ir23, ensure_ascii=False, indent=2) + "\n")
    _write(reports / "ir23_evidence_pack_lifecycle_audit_report_ir23_resubmission_trial.json", json.dumps(ir23, ensure_ascii=False, indent=2) + "\n")

    ir24 = {
        "schema_version": "ir24_submission_version_diff_audit_v1",
        "phase": "IR24",
        "validation_result": "PASS",
        "diff_audit": {
            "baseline_ir23_report": "generic_block_ai/reports/ir23_evidence_pack_lifecycle_audit_report_ir23_live_trial.json",
            "candidate_ir23_report": "generic_block_ai/reports/ir23_evidence_pack_lifecycle_audit_report_ir23_resubmission_trial.json",
        },
    }
    _write(reports / "ir24_submission_version_diff_audit_report_ir24_live_trial.json", json.dumps(ir24, ensure_ascii=False, indent=2) + "\n")

    ir25 = {
        "schema_version": "ir25_submission_change_approval_gate_v1",
        "phase": "IR25",
        "decision": "ALLOW",
        "artifacts": {
            "ir24_diff_report": "generic_block_ai/reports/ir24_submission_version_diff_audit_report_ir24_live_trial.json",
        },
    }
    _write(reports / "ir25_submission_change_approval_gate_report_ir25_live_trial.json", json.dumps(ir25, ensure_ascii=False, indent=2) + "\n")

    marker_dir = reports / "ir26_release_candidate_marker_ir26_live_trial"
    _write(marker_dir / "approval_snapshot.json", '{"schema_version":"ir26_submission_release_candidate_marker_v1"}\n')
    _write(
        marker_dir / "immutable_marker.json",
        json.dumps(
            {
                "schema_version": "ir26_submission_release_candidate_marker_v1",
                "release_candidate_id": "rc_20260523T155148Z_ir26_live_trial_b940393b490b",
                "approval_snapshot_hash": "dummy",
                "immutable": {
                    "marker_locked": True,
                    "mutation_policy": "append_only_no_overwrite",
                    "marker_rewrite_allowed": False,
                },
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )
    _write(marker_dir / "README.md", "# marker\n")

    ir26 = {
        "schema_version": "ir26_submission_release_candidate_marker_v1",
        "phase": "IR26",
        "marker_result": "PASS",
        "release_candidate_id": "rc_20260523T155148Z_ir26_live_trial_b940393b490b",
        "artifacts": {
            "ir25_gate_report": "generic_block_ai/reports/ir25_submission_change_approval_gate_report_ir25_live_trial.json",
            "approval_snapshot": "generic_block_ai/reports/ir26_release_candidate_marker_ir26_live_trial/approval_snapshot.json",
            "immutable_marker": "generic_block_ai/reports/ir26_release_candidate_marker_ir26_live_trial/immutable_marker.json",
            "readme": "generic_block_ai/reports/ir26_release_candidate_marker_ir26_live_trial/README.md",
        },
    }
    _write(reports / "ir26_submission_release_candidate_marker_report_ir26_live_trial.json", json.dumps(ir26, ensure_ascii=False, indent=2) + "\n")

    ir27 = {
        "schema_version": "ir27_release_candidate_integrity_verifier_v1",
        "phase": "IR27",
        "validation_result": "PASS",
        "release_candidate_id": "rc_20260523T155148Z_ir26_live_trial_b940393b490b",
        "artifacts": {
            "ir26_marker_report": "generic_block_ai/reports/ir26_submission_release_candidate_marker_report_ir26_live_trial.json",
        },
    }
    ir27_path = reports / "ir27_release_candidate_integrity_verifier_report_ir27_live_trial.json"
    _write(ir27_path, json.dumps(ir27, ensure_ascii=False, indent=2) + "\n")

    return ir27_path


def test_ir28_build_trace_bundle_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir27_path = _prepare_chain(base)

    out = run_ir28_release_candidate_trace_bundle_dryrun(
        base_path=base,
        source_task_id="ir28_pass",
        ir27_integrity_report_path=ir27_path,
    )

    report = out["trace_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["included_artifact_count"] >= 10


def test_ir28_fail_when_ir27_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    out = run_ir28_release_candidate_trace_bundle_dryrun(
        base_path=base,
        source_task_id="ir28_missing",
        ir27_integrity_report_path=tmp_path / "not_found.json",
    )

    report = out["trace_report"]
    assert report["validation_result"] == "FAIL"


def test_ir28_fail_when_ir27_not_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir27_path = _prepare_chain(base)

    ir27 = json.loads(ir27_path.read_text(encoding="utf-8"))
    ir27["validation_result"] = "FAIL"
    ir27_path.write_text(json.dumps(ir27, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir28_release_candidate_trace_bundle_dryrun(
        base_path=base,
        source_task_id="ir28_ir27_fail",
        ir27_integrity_report_path=ir27_path,
    )

    report = out["trace_report"]
    assert report["validation_result"] == "FAIL"


def test_ir28_fail_when_release_candidate_id_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir27_path = _prepare_chain(base)

    ir26_path = base / "reports" / "ir26_submission_release_candidate_marker_report_ir26_live_trial.json"
    ir26 = json.loads(ir26_path.read_text(encoding="utf-8"))
    ir26["release_candidate_id"] = "rc_mismatch"
    ir26_path.write_text(json.dumps(ir26, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir28_release_candidate_trace_bundle_dryrun(
        base_path=base,
        source_task_id="ir28_rc_mismatch",
        ir27_integrity_report_path=ir27_path,
    )

    report = out["trace_report"]
    assert report["validation_result"] == "FAIL"


def test_ir28_fail_when_referenced_artifact_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir27_path = _prepare_chain(base)

    missing_target = base / "reports" / "ir24_submission_version_diff_audit_report_ir24_live_trial.json"
    missing_target.unlink()

    out = run_ir28_release_candidate_trace_bundle_dryrun(
        base_path=base,
        source_task_id="ir28_ref_missing",
        ir27_integrity_report_path=ir27_path,
    )

    report = out["trace_report"]
    assert report["validation_result"] == "FAIL"


def test_write_ir28_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir27_path = _prepare_chain(base)

    ir28 = run_ir28_release_candidate_trace_bundle_dryrun(
        base_path=base,
        source_task_id="ir28_complete",
        ir27_integrity_report_path=ir27_path,
    )

    completion = write_ir28_completion_report(
        base_path=base,
        ir28_output=ir28,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 223, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 28"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
