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
    write_ir23_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir20_ir21_ir22(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
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
    _write(root / "generic_block_ai/reports/ir17_role_policy_versioning_report_ir17_live_trial.json", '{"x":2}\n')

    ir20 = run_ir20_cross_phase_evidence_bundler_dryrun(
        base_path=base,
        source_task_id="ir20_for_ir23",
        required_artifacts=required,
        optional_globs=["ir15_manual_event_role_guard_*.json", "ir17_role_policy_versioning_report_*.json"],
    )
    ir20_completion = write_ir20_completion_report(
        base_path=base,
        ir20_output=ir20,
        focused_tests={"passed": 1, "failed": 0},
        full_regression={"passed": 1, "failed": 0},
    )

    ir21 = run_ir21_evidence_pack_verifier_dryrun(
        base_path=base,
        source_task_id="ir21_for_ir23",
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
            source_task_id="ir22_for_ir23_audit",
            profile_name="audit_submission",
            ir20_bundle_report_path=Path(ir20["path"]),
            ir21_verifier_report_path=Path(ir21["path"]),
        ),
        run_ir22_submission_profile_builder_dryrun(
            base_path=base,
            source_task_id="ir22_for_ir23_review",
            profile_name="review_minimal",
            ir20_bundle_report_path=Path(ir20["path"]),
            ir21_verifier_report_path=Path(ir21["path"]),
        ),
        run_ir22_submission_profile_builder_dryrun(
            base_path=base,
            source_task_id="ir22_for_ir23_policy",
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

    return base, Path(ir20["path"]), Path(ir21["path"]), Path(ir22_completion["path"])


def test_ir23_lifecycle_audit_pass(tmp_path: Path) -> None:
    base, ir20_path, ir21_path, ir22_completion_path = _prepare_ir20_ir21_ir22(tmp_path)

    out = run_ir23_evidence_pack_lifecycle_audit_dryrun(
        base_path=base,
        source_task_id="ir23_pass",
        ir20_bundle_report_path=ir20_path,
        ir21_verifier_report_path=ir21_path,
        ir22_completion_report_path=ir22_completion_path,
    )

    report = out["lifecycle_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["profiles_checked"] == 3


def test_ir23_fail_when_prerequisite_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir23_evidence_pack_lifecycle_audit_dryrun(
        base_path=base,
        source_task_id="ir23_missing",
    )

    report = out["lifecycle_report"]
    assert report["validation_result"] == "FAIL"
    assert report["summary"]["failed_check_count"] >= 1


def test_ir23_fail_when_ir21_bundle_link_mismatch(tmp_path: Path) -> None:
    base, ir20_path, ir21_path, ir22_completion_path = _prepare_ir20_ir21_ir22(tmp_path)

    ir21 = json.loads(ir21_path.read_text(encoding="utf-8"))
    ir21["artifacts"]["bundle_report"] = "generic_block_ai/reports/wrong_bundle.json"
    ir21_path.write_text(json.dumps(ir21, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir23_evidence_pack_lifecycle_audit_dryrun(
        base_path=base,
        source_task_id="ir23_link_mismatch",
        ir20_bundle_report_path=ir20_path,
        ir21_verifier_report_path=ir21_path,
        ir22_completion_report_path=ir22_completion_path,
    )

    report = out["lifecycle_report"]
    assert report["validation_result"] == "FAIL"


def test_ir23_fail_on_profile_sha_mismatch(tmp_path: Path) -> None:
    base, ir20_path, ir21_path, ir22_completion_path = _prepare_ir20_ir21_ir22(tmp_path)

    ir22_completion = json.loads(ir22_completion_path.read_text(encoding="utf-8"))
    profile_report_path = Path(ir22_completion["artifacts"]["profile_reports"][0])
    profile_report = json.loads((base.parent / profile_report_path).read_text(encoding="utf-8"))

    selected_sha_path = base.parent / Path(profile_report["selected_sha256_manifest_path"])
    selected_sha = json.loads(selected_sha_path.read_text(encoding="utf-8"))
    first_key = next(iter(selected_sha.keys()))
    selected_sha[first_key] = "0" * 64
    selected_sha_path.write_text(json.dumps(selected_sha, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir23_evidence_pack_lifecycle_audit_dryrun(
        base_path=base,
        source_task_id="ir23_sha_mismatch",
        ir20_bundle_report_path=ir20_path,
        ir21_verifier_report_path=ir21_path,
        ir22_completion_report_path=ir22_completion_path,
    )

    report = out["lifecycle_report"]
    assert report["validation_result"] == "FAIL"


def test_write_ir23_completion_report(tmp_path: Path) -> None:
    base, ir20_path, ir21_path, ir22_completion_path = _prepare_ir20_ir21_ir22(tmp_path)

    ir23 = run_ir23_evidence_pack_lifecycle_audit_dryrun(
        base_path=base,
        source_task_id="ir23_complete",
        ir20_bundle_report_path=ir20_path,
        ir21_verifier_report_path=ir21_path,
        ir22_completion_report_path=ir22_completion_path,
    )

    completion = write_ir23_completion_report(
        base_path=base,
        ir23_output=ir23,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 195, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 23"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
