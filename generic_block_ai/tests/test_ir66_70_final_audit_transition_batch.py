import json
from pathlib import Path

from generic_block_ai.app.core_ir66_70_final_audit_transition_batch import (
    run_ir66_70_batch_dryrun,
    run_ir68_no_go_lock_gate,
    write_ir66_70_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir65_payload() -> dict:
    return {
        "schema_version": "ir65_phase_61_65_completion_bundle_v1",
        "phase": "IR65",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir65_fixture",
        "final_decision": "READY_FOR_DRY_RUN_HANDOFF_ONLY",
        "completion_table": [
            {"phase": "IR61", "content": "Post-Archive Confirmation Logger", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR62", "content": "Dry-Run Cycle Re-Verification Auditor", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR63", "content": "Final Handoff Package Assembler", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR64", "content": "Handoff Package Release Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR65", "content": "Phase 61-65 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
        ],
        "live_summary": {"ir61": "PASS", "ir62": "PASS", "ir63": "PASS", "ir64": "PASS", "ir65": "PASS"},
        "safety_gate_summary": {
            "dry_run": "maintained",
            "OBSERVE": "maintained",
            "submission_execution_blocked": True,
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
            "GitHub_push": "未実行",
        },
        "ir62_result": {
            "re_verification_result": "CYCLE_VERIFIED",
        },
        "artifacts": {
            "ir65_completion_bundle": "generic_block_ai/reports/ir61_65/ir65_completion_bundle.json",
        },
    }


def _prepare_ir65(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir61_65" / "ir65_completion_bundle.json"
    _write(target, payload or _base_ir65_payload())
    return target


def test_ir66_pass_for_valid_ir65_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir65_path = _prepare_ir65(base)

    out = run_ir66_70_batch_dryrun(
        base_path=base,
        source_task_id="ir66_70_pass",
        ir65_completion_bundle_path=ir65_path,
    )

    ir66 = out["ir66_result"]
    assert ir66["validation_result"] == "PASS"
    assert "audit_id" in ir66["audit_record"]
    assert ir66["audit_record"]["no_external_write_confirmed"] is True
    assert ir66["audit_record"]["no_live_execution_confirmed"] is True


def test_ir67_pass_when_all_criteria_met(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir65_path = _prepare_ir65(base)

    out = run_ir66_70_batch_dryrun(
        base_path=base,
        source_task_id="ir67_pass",
        ir65_completion_bundle_path=ir65_path,
    )

    ir67 = out["ir67_result"]
    assert ir67["validation_result"] == "PASS"
    assert ir67["transition_readiness"] == "DRY_RUN_TRANSITION_READY"
    assert ir67["hash_integrity"]["hash_match"] is True


def test_ir68_no_go_locked_when_all_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir65_path = _prepare_ir65(base)

    out = run_ir66_70_batch_dryrun(
        base_path=base,
        source_task_id="ir68_lock",
        ir65_completion_bundle_path=ir65_path,
    )

    ir68 = out["ir68_result"]
    assert ir68["validation_result"] == "PASS"
    assert ir68["no_go_lock_gate_decision"] == "NO_GO_LOCKED_DRY_RUN_ONLY"
    assert ir68["no_go_lock_record"]["live_execution_permanently_blocked_this_cycle"] is True


def test_ir68_abort_when_external_flags_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir65_path = _prepare_ir65(base)

    out = run_ir66_70_batch_dryrun(
        base_path=base,
        source_task_id="ir68_abort",
        ir65_completion_bundle_path=ir65_path,
    )

    ir67_with_risk = dict(out["ir67_result"])
    ir67_with_risk["safety_gate_snapshot"] = dict(ir67_with_risk["safety_gate_snapshot"])
    ir67_with_risk["safety_gate_snapshot"]["network_transmission_executed"] = True

    ir68 = run_ir68_no_go_lock_gate(
        ir67_transition_review=ir67_with_risk,
        ir66_comprehensive_audit=out["ir66_result"],
        source_task_id="ir68_abort",
    )
    assert ir68["no_go_lock_gate_decision"] == "ABORT"


def test_ir69_assembles_design_package(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir65_path = _prepare_ir65(base)

    out = run_ir66_70_batch_dryrun(
        base_path=base,
        source_task_id="ir69_design",
        ir65_completion_bundle_path=ir65_path,
    )

    ir69 = out["ir69_result"]
    assert ir69["validation_result"] == "PASS"
    assert ir69["design_package"]["assembly_execution_blocked"] is True
    assert ir69["design_package"]["external_distribution_blocked"] is True
    assert ir69["design_package"]["retention_scope"] == "dry_run_only"
    assert ir69["lock_hash_verification"]["hash_match"] is True


def test_ir70_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir65_path = _prepare_ir65(base)

    out = run_ir66_70_batch_dryrun(
        base_path=base,
        source_task_id="ir70_complete",
        ir65_completion_bundle_path=ir65_path,
    )

    result = write_ir66_70_completion_bundle(
        base_path=base,
        ir66_70_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 380, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir70_phase_66_70_completion_bundle_v1"
    assert report["final_decision"] == "NO_GO_LOCKED_DRY_RUN_ONLY"
    assert report["no_go_lock_confirmed"] is True
    assert report["safety_gate_summary"]["dry_run"] == "maintained"
    assert report["safety_gate_summary"]["execution_policy_execute"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
    bundle_file = base / "reports" / "ir66_70" / "ir70_completion_bundle.json"
    assert bundle_file.exists()
