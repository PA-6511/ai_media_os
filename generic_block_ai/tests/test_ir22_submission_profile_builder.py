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


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir20_ir21(tmp_path: Path) -> Path:
    root = tmp_path
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
        _write(root / rel, f"{{\"id\":{idx}}}\n")

    _write(root / "generic_block_ai/reports/ir15_manual_event_role_guard_ir15_pass_live_trial.json", '{"x":1}\n')
    _write(root / "generic_block_ai/reports/ir21_evidence_pack_verifier_report_ir21_live_trial.json", '{"x":2}\n')

    ir20 = run_ir20_cross_phase_evidence_bundler_dryrun(
        base_path=base,
        source_task_id="ir20_for_ir22",
        required_artifacts=required,
        optional_globs=["ir15_manual_event_role_guard_*.json", "ir21_evidence_pack_verifier_report_*.json"],
    )
    write_ir20_completion_report(
        base_path=base,
        ir20_output=ir20,
        focused_tests={"passed": 1, "failed": 0},
        full_regression={"passed": 1, "failed": 0},
    )

    ir21 = run_ir21_evidence_pack_verifier_dryrun(
        base_path=base,
        source_task_id="ir21_for_ir22",
        bundle_report_path=Path(ir20["path"]),
        completion_report_path=base / "reports" / "implementation_restart_phase20_completion_report.json",
    )
    write_ir21_completion_report(
        base_path=base,
        ir21_output=ir21,
        focused_tests={"passed": 1, "failed": 0},
        full_regression={"passed": 1, "failed": 0},
    )

    return base


def test_ir22_build_audit_submission_profile_pass(tmp_path: Path) -> None:
    base = _prepare_ir20_ir21(tmp_path)
    out = run_ir22_submission_profile_builder_dryrun(
        base_path=base,
        source_task_id="ir22_audit",
        profile_name="audit_submission",
        ir20_bundle_report_path=base / "reports" / "ir20_cross_phase_evidence_bundle_ir20_for_ir22.json",
        ir21_verifier_report_path=base / "reports" / "ir21_evidence_pack_verifier_report_ir21_for_ir22.json",
    )
    report = out["profile_report"]
    assert report["validation_result"] in {"PASS", "WARN"}
    assert report["selected_artifact_count"] > 0


def test_ir22_detects_missing_prerequisite_reports(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    out = run_ir22_submission_profile_builder_dryrun(
        base_path=base,
        source_task_id="ir22_missing_prereq",
        profile_name="audit_submission",
    )
    report = out["profile_report"]
    assert report["validation_result"] == "FAIL"


def test_ir22_profile_warn_when_pattern_not_matched(tmp_path: Path) -> None:
    base = _prepare_ir20_ir21(tmp_path)

    out = run_ir22_submission_profile_builder_dryrun(
        base_path=base,
        source_task_id="ir22_policy_focus",
        profile_name="policy_focus",
        ir20_bundle_report_path=base / "reports" / "ir20_cross_phase_evidence_bundle_ir20_for_ir22.json",
        ir21_verifier_report_path=base / "reports" / "ir21_evidence_pack_verifier_report_ir21_for_ir22.json",
    )
    report = out["profile_report"]
    assert report["validation_result"] in {"PASS", "WARN"}


def test_ir22_profile_fails_when_ir21_not_pass(tmp_path: Path) -> None:
    base = _prepare_ir20_ir21(tmp_path)

    ir21_path = base / "reports" / "ir21_evidence_pack_verifier_report_ir21_for_ir22.json"
    ir21 = json.loads(ir21_path.read_text(encoding="utf-8"))
    ir21["validation_result"] = "FAIL"
    ir21_path.write_text(json.dumps(ir21, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir22_submission_profile_builder_dryrun(
        base_path=base,
        source_task_id="ir22_prereq_fail",
        profile_name="audit_submission",
        ir20_bundle_report_path=base / "reports" / "ir20_cross_phase_evidence_bundle_ir20_for_ir22.json",
        ir21_verifier_report_path=ir21_path,
    )
    report = out["profile_report"]
    assert report["validation_result"] == "FAIL"


def test_write_ir22_completion_report(tmp_path: Path) -> None:
    base = _prepare_ir20_ir21(tmp_path)
    outputs = [
        run_ir22_submission_profile_builder_dryrun(
            base_path=base,
            source_task_id="ir22_complete_audit",
            profile_name="audit_submission",
            ir20_bundle_report_path=base / "reports" / "ir20_cross_phase_evidence_bundle_ir20_for_ir22.json",
            ir21_verifier_report_path=base / "reports" / "ir21_evidence_pack_verifier_report_ir21_for_ir22.json",
        ),
        run_ir22_submission_profile_builder_dryrun(
            base_path=base,
            source_task_id="ir22_complete_review",
            profile_name="review_minimal",
            ir20_bundle_report_path=base / "reports" / "ir20_cross_phase_evidence_bundle_ir20_for_ir22.json",
            ir21_verifier_report_path=base / "reports" / "ir21_evidence_pack_verifier_report_ir21_for_ir22.json",
        ),
    ]

    completion = write_ir22_completion_report(
        base_path=base,
        ir22_outputs=outputs,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 190, "failed": 0},
    )
    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 22"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] in {"PASS", "WARN"}
