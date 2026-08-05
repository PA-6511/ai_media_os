import json
from pathlib import Path

from generic_block_ai.app.core_cross_phase_evidence_bundler import (
    run_ir20_cross_phase_evidence_bundler_dryrun,
    write_ir20_completion_report,
)
from generic_block_ai.app.core_evidence_pack_verifier import (
    run_ir21_evidence_pack_verifier_dryrun,
    write_ir21_completion_report,
)
from generic_block_ai.app.core_submission_profile_builder import (
    run_ir22_submission_profile_builder_dryrun,
    write_ir22_completion_report,
)
from generic_block_ai.app.core_evidence_pack_lifecycle_audit import (
    run_ir23_evidence_pack_lifecycle_audit_dryrun,
)
from generic_block_ai.app.core_submission_version_diff_audit import (
    run_ir24_submission_version_diff_audit_dryrun,
    write_ir24_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_version(root: Path, tag: str, with_extra_ir19: bool) -> tuple[Path, Path]:
    base = root / "generic_block_ai"

    required = [
        "generic_block_ai/reports/implementation_restart_phase12_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase13_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase14_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase15_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase16_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase17_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase18_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase19_completion_report.json",
        "generic_block_ai/reports/ir12_core_decision_queue_audit.log",
        "generic_block_ai/reports/ir13_manual_approval_audit.log",
        "generic_block_ai/reports/ir17_role_policy_change_audit.log",
        "generic_block_ai/reports/ir19_policy_drift_detector_report_ir19_live_trial.json",
    ]

    for idx, rel in enumerate(required):
        content = f"{{\"id\":{idx},\"tag\":\"{tag}\"}}\n"
        _write(root / rel, content)

    _write(root / "generic_block_ai/reports/ir15_manual_event_role_guard_ir15_pass_live_trial.json", f'{{"x":1,"tag":"{tag}"}}\n')
    _write(root / "generic_block_ai/reports/ir17_role_policy_versioning_report_ir17_live_trial.json", f'{{"x":2,"tag":"{tag}"}}\n')

    if with_extra_ir19:
        _write(root / "generic_block_ai/reports/ir19_policy_drift_detector_report_ir19_resubmission.json", '{"extra":true}\n')

    ir20 = run_ir20_cross_phase_evidence_bundler_dryrun(
        base_path=base,
        source_task_id=f"ir20_{tag}",
        required_artifacts=required,
        optional_globs=[
            "ir15_manual_event_role_guard_*.json",
            "ir17_role_policy_versioning_report_*.json",
            "ir19_policy_drift_detector_report_*.json",
        ],
    )

    ir20_completion = write_ir20_completion_report(
        base_path=base,
        ir20_output=ir20,
        focused_tests={"passed": 1, "failed": 0},
        full_regression={"passed": 1, "failed": 0},
    )

    ir21 = run_ir21_evidence_pack_verifier_dryrun(
        base_path=base,
        source_task_id=f"ir21_{tag}",
        bundle_report_path=Path(ir20["path"]),
        completion_report_path=Path(ir20_completion["path"]),
    )

    write_ir21_completion_report(
        base_path=base,
        ir21_output=ir21,
        focused_tests={"passed": 1, "failed": 0},
        full_regression={"passed": 1, "failed": 0},
    )

    ir22_outputs = [
        run_ir22_submission_profile_builder_dryrun(
            base_path=base,
            source_task_id=f"ir22_{tag}_audit",
            profile_name="audit_submission",
            ir20_bundle_report_path=Path(ir20["path"]),
            ir21_verifier_report_path=Path(ir21["path"]),
        ),
        run_ir22_submission_profile_builder_dryrun(
            base_path=base,
            source_task_id=f"ir22_{tag}_review",
            profile_name="review_minimal",
            ir20_bundle_report_path=Path(ir20["path"]),
            ir21_verifier_report_path=Path(ir21["path"]),
        ),
        run_ir22_submission_profile_builder_dryrun(
            base_path=base,
            source_task_id=f"ir22_{tag}_policy",
            profile_name="policy_focus",
            ir20_bundle_report_path=Path(ir20["path"]),
            ir21_verifier_report_path=Path(ir21["path"]),
        ),
    ]

    ir22_completion = write_ir22_completion_report(
        base_path=base,
        ir22_outputs=ir22_outputs,
        focused_tests={"passed": 1, "failed": 0},
        full_regression={"passed": 1, "failed": 0},
    )

    ir23 = run_ir23_evidence_pack_lifecycle_audit_dryrun(
        base_path=base,
        source_task_id=f"ir23_{tag}",
        ir20_bundle_report_path=Path(ir20["path"]),
        ir21_verifier_report_path=Path(ir21["path"]),
        ir22_completion_report_path=Path(ir22_completion["path"]),
    )

    return base, Path(ir23["path"])


def test_ir24_version_diff_pass_with_detected_changes(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"

    _, baseline_ir23 = _build_version(baseline_root, "baseline", with_extra_ir19=False)
    base, candidate_ir23 = _build_version(candidate_root, "candidate", with_extra_ir19=True)

    out = run_ir24_submission_version_diff_audit_dryrun(
        base_path=base,
        source_task_id="ir24_pass",
        baseline_ir23_report_path=baseline_ir23,
        candidate_ir23_report_path=candidate_ir23,
    )

    report = out["diff_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["profiles_compared"] == 3
    assert report["summary"]["bundle_added_artifact_count"] >= 1


def test_ir24_fail_when_baseline_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    candidate_root = tmp_path / "candidate"
    _, candidate_ir23 = _build_version(candidate_root, "candidate", with_extra_ir19=False)

    out = run_ir24_submission_version_diff_audit_dryrun(
        base_path=base,
        source_task_id="ir24_missing_baseline",
        baseline_ir23_report_path=tmp_path / "not_found.json",
        candidate_ir23_report_path=candidate_ir23,
    )

    report = out["diff_report"]
    assert report["validation_result"] == "FAIL"


def test_ir24_fail_when_candidate_not_pass(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"

    _, baseline_ir23 = _build_version(baseline_root, "baseline", with_extra_ir19=False)
    base, candidate_ir23 = _build_version(candidate_root, "candidate", with_extra_ir19=False)

    candidate_obj = json.loads(candidate_ir23.read_text(encoding="utf-8"))
    candidate_obj["validation_result"] = "FAIL"
    candidate_ir23.write_text(json.dumps(candidate_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir24_submission_version_diff_audit_dryrun(
        base_path=base,
        source_task_id="ir24_candidate_fail",
        baseline_ir23_report_path=baseline_ir23,
        candidate_ir23_report_path=candidate_ir23,
    )

    report = out["diff_report"]
    assert report["validation_result"] == "FAIL"


def test_ir24_fail_when_profile_sha_missing(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"

    _, baseline_ir23 = _build_version(baseline_root, "baseline", with_extra_ir19=False)
    base, candidate_ir23 = _build_version(candidate_root, "candidate", with_extra_ir19=False)

    candidate_obj = json.loads(candidate_ir23.read_text(encoding="utf-8"))
    profile_report_rel = candidate_obj["traceability"]["ir22_profile_reports"][0]
    profile_report_path = (base.parent / Path(profile_report_rel))
    profile_report = json.loads(profile_report_path.read_text(encoding="utf-8"))
    selected_sha_path = base.parent / Path(profile_report["selected_sha256_manifest_path"])
    selected_sha_path.unlink()

    out = run_ir24_submission_version_diff_audit_dryrun(
        base_path=base,
        source_task_id="ir24_profile_sha_missing",
        baseline_ir23_report_path=baseline_ir23,
        candidate_ir23_report_path=candidate_ir23,
    )

    report = out["diff_report"]
    assert report["validation_result"] == "FAIL"


def test_write_ir24_completion_report(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"

    _, baseline_ir23 = _build_version(baseline_root, "baseline", with_extra_ir19=False)
    base, candidate_ir23 = _build_version(candidate_root, "candidate", with_extra_ir19=True)

    ir24 = run_ir24_submission_version_diff_audit_dryrun(
        base_path=base,
        source_task_id="ir24_complete",
        baseline_ir23_report_path=baseline_ir23,
        candidate_ir23_report_path=candidate_ir23,
    )

    completion = write_ir24_completion_report(
        base_path=base,
        ir24_output=ir24,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 200, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 24"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
