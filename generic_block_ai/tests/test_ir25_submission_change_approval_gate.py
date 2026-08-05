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
)
from generic_block_ai.app.core_submission_change_approval_gate import (
    DECISION_ABORT,
    DECISION_ALLOW,
    DECISION_HUMAN_APPROVAL_REQUIRED,
    DECISION_REJECT,
    run_ir25_submission_change_approval_gate_dryrun,
    write_ir25_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_version(root: Path, tag: str, extra_ir19: bool, extra_ir17: bool) -> tuple[Path, Path]:
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
        _write(root / rel, f"{{\"id\":{idx},\"tag\":\"{tag}\"}}\n")

    _write(root / "generic_block_ai/reports/ir15_manual_event_role_guard_ir15_pass_live_trial.json", f'{{"x":1,"tag":"{tag}"}}\n')
    _write(root / "generic_block_ai/reports/ir17_role_policy_versioning_report_ir17_live_trial.json", f'{{"x":2,"tag":"{tag}"}}\n')

    if extra_ir19:
        _write(root / "generic_block_ai/reports/ir19_policy_drift_detector_report_ir19_resubmission.json", '{"extra":true}\n')
    if extra_ir17:
        _write(root / "generic_block_ai/reports/ir17_role_policy_versioning_report_ir17_patch.json", '{"extra":true}\n')

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


def _build_ir24(base: Path, baseline_ir23: Path, candidate_ir23: Path, source_task_id: str) -> Path:
    ir24 = run_ir24_submission_version_diff_audit_dryrun(
        base_path=base,
        source_task_id=source_task_id,
        baseline_ir23_report_path=baseline_ir23,
        candidate_ir23_report_path=candidate_ir23,
    )
    return Path(ir24["path"])


def test_ir25_allow_when_no_diff(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    _, baseline_ir23 = _build_version(baseline_root, "same", extra_ir19=False, extra_ir17=False)
    base, candidate_ir23 = _build_version(candidate_root, "same", extra_ir19=False, extra_ir17=False)

    ir24_path = _build_ir24(base, baseline_ir23, candidate_ir23, "ir24_same")
    out = run_ir25_submission_change_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir25_allow_no_diff",
        ir24_diff_report_path=ir24_path,
    )

    report = out["gate_report"]
    assert report["decision"] == DECISION_ALLOW


def test_ir25_allow_when_only_allowlisted_addition(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    _, baseline_ir23 = _build_version(baseline_root, "same", extra_ir19=False, extra_ir17=False)
    base, candidate_ir23 = _build_version(candidate_root, "same", extra_ir19=True, extra_ir17=False)

    ir24_path = _build_ir24(base, baseline_ir23, candidate_ir23, "ir24_allowlisted")
    out = run_ir25_submission_change_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir25_allowlisted",
        ir24_diff_report_path=ir24_path,
    )

    report = out["gate_report"]
    assert report["decision"] == DECISION_ALLOW


def test_ir25_human_approval_for_non_allowlisted_addition(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    _, baseline_ir23 = _build_version(baseline_root, "same", extra_ir19=False, extra_ir17=False)
    base, candidate_ir23 = _build_version(candidate_root, "same", extra_ir19=False, extra_ir17=True)

    ir24_path = _build_ir24(base, baseline_ir23, candidate_ir23, "ir24_non_allowlisted")
    out = run_ir25_submission_change_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir25_human",
        ir24_diff_report_path=ir24_path,
    )

    report = out["gate_report"]
    assert report["decision"] == DECISION_HUMAN_APPROVAL_REQUIRED


def test_ir25_reject_when_removal_detected(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    _, baseline_ir23 = _build_version(baseline_root, "same", extra_ir19=True, extra_ir17=False)
    base, candidate_ir23 = _build_version(candidate_root, "same", extra_ir19=False, extra_ir17=False)

    ir24_path = _build_ir24(base, baseline_ir23, candidate_ir23, "ir24_removal")
    out = run_ir25_submission_change_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir25_reject",
        ir24_diff_report_path=ir24_path,
    )

    report = out["gate_report"]
    assert report["decision"] == DECISION_REJECT


def test_ir25_abort_when_ir24_not_pass(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    _, baseline_ir23 = _build_version(baseline_root, "same", extra_ir19=False, extra_ir17=False)
    base, candidate_ir23 = _build_version(candidate_root, "same", extra_ir19=False, extra_ir17=False)

    ir24_path = _build_ir24(base, baseline_ir23, candidate_ir23, "ir24_abort")
    ir24_obj = json.loads(ir24_path.read_text(encoding="utf-8"))
    ir24_obj["validation_result"] = "FAIL"
    ir24_path.write_text(json.dumps(ir24_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir25_submission_change_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir25_abort",
        ir24_diff_report_path=ir24_path,
    )

    report = out["gate_report"]
    assert report["decision"] == DECISION_ABORT


def test_write_ir25_completion_report(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    _, baseline_ir23 = _build_version(baseline_root, "same", extra_ir19=False, extra_ir17=False)
    base, candidate_ir23 = _build_version(candidate_root, "same", extra_ir19=True, extra_ir17=False)

    ir24_path = _build_ir24(base, baseline_ir23, candidate_ir23, "ir24_complete")
    ir25 = run_ir25_submission_change_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir25_complete",
        ir24_diff_report_path=ir24_path,
    )

    completion = write_ir25_completion_report(
        base_path=base,
        ir25_output=ir25,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 206, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 25"
    assert loaded["status"] == "COMPLETED"
    assert loaded["decision"] == DECISION_ALLOW
