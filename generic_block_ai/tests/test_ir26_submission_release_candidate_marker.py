import json
import hashlib
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
from generic_block_ai.app.core_evidence_pack_lifecycle_audit import run_ir23_evidence_pack_lifecycle_audit_dryrun
from generic_block_ai.app.core_submission_version_diff_audit import run_ir24_submission_version_diff_audit_dryrun
from generic_block_ai.app.core_submission_change_approval_gate import run_ir25_submission_change_approval_gate_dryrun
from generic_block_ai.app.core_submission_release_candidate_marker import (
    run_ir26_submission_release_candidate_marker_dryrun,
    write_ir26_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_version(root: Path, tag: str, extra_ir19: bool) -> tuple[Path, Path]:
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

    outputs = [
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
        ir22_outputs=outputs,
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


def _build_ir25_allow(tmp_path: Path) -> tuple[Path, Path]:
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"

    _, baseline_ir23 = _build_version(baseline_root, "same", extra_ir19=False)
    base, candidate_ir23 = _build_version(candidate_root, "same", extra_ir19=False)

    ir24 = run_ir24_submission_version_diff_audit_dryrun(
        base_path=base,
        source_task_id="ir24_for_ir26",
        baseline_ir23_report_path=baseline_ir23,
        candidate_ir23_report_path=candidate_ir23,
    )

    ir25 = run_ir25_submission_change_approval_gate_dryrun(
        base_path=base,
        source_task_id="ir25_for_ir26",
        ir24_diff_report_path=Path(ir24["path"]),
    )

    return base, Path(ir25["path"])


def test_ir26_create_marker_on_allow(tmp_path: Path) -> None:
    base, ir25_path = _build_ir25_allow(tmp_path)

    out = run_ir26_submission_release_candidate_marker_dryrun(
        base_path=base,
        source_task_id="ir26_allow",
        ir25_gate_report_path=ir25_path,
    )

    report = out["marker_report"]
    assert report["marker_result"] == "PASS"
    assert report["release_candidate_id"].startswith("rc_")


def test_ir26_fail_when_ir25_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    out = run_ir26_submission_release_candidate_marker_dryrun(
        base_path=base,
        source_task_id="ir26_missing",
        ir25_gate_report_path=tmp_path / "not_found.json",
    )

    report = out["marker_report"]
    assert report["marker_result"] == "FAIL"


def test_ir26_fail_when_ir25_not_allow(tmp_path: Path) -> None:
    base, ir25_path = _build_ir25_allow(tmp_path)
    ir25 = json.loads(ir25_path.read_text(encoding="utf-8"))
    ir25["decision"] = "REJECT"
    ir25_path.write_text(json.dumps(ir25, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir26_submission_release_candidate_marker_dryrun(
        base_path=base,
        source_task_id="ir26_not_allow",
        ir25_gate_report_path=ir25_path,
    )

    report = out["marker_report"]
    assert report["marker_result"] == "FAIL"


def test_ir26_snapshot_hash_matches_marker(tmp_path: Path) -> None:
    base, ir25_path = _build_ir25_allow(tmp_path)
    out = run_ir26_submission_release_candidate_marker_dryrun(
        base_path=base,
        source_task_id="ir26_hash",
        ir25_gate_report_path=ir25_path,
    )

    report = out["marker_report"]
    marker_path = base.parent / Path(report["artifacts"]["immutable_marker"])
    snapshot_path = base.parent / Path(report["artifacts"]["approval_snapshot"])

    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    assert marker["approval_snapshot_hash"] == digest


def test_write_ir26_completion_report(tmp_path: Path) -> None:
    base, ir25_path = _build_ir25_allow(tmp_path)
    ir26 = run_ir26_submission_release_candidate_marker_dryrun(
        base_path=base,
        source_task_id="ir26_complete",
        ir25_gate_report_path=ir25_path,
    )

    completion = write_ir26_completion_report(
        base_path=base,
        ir26_output=ir26,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 211, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 26"
    assert loaded["status"] == "COMPLETED"
    assert loaded["marker_result"] == "PASS"
