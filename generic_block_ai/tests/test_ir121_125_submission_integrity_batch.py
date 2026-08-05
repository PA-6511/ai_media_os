import json
from pathlib import Path

from generic_block_ai.app.core_ir121_125_submission_integrity_batch import (
    run_ir121_125_batch_dryrun,
    run_ir124_submission_prohibition_dry_run_fixation_gate,
    write_ir121_125_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir120_payload() -> dict:
    return {
        "schema_version": "ir120_phase_116_120_completion_bundle_v1",
        "phase": "IR120",
        "generated_at": "2026-05-25T08:00:00+00:00",
        "source_task_id": "ir120_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir118_result": {
            "reference_lock_integrity_gate": {
                "lock_entries": [
                    {"retention_item_id": "ret_1", "item": "go_decision_document", "lock_status": "LOCK_INTEGRITY_CONFIRMED", "reference_mutable": False},
                    {"retention_item_id": "ret_2", "item": "release_approver_signature", "lock_status": "LOCK_INTEGRITY_CONFIRMED", "reference_mutable": False},
                    {"retention_item_id": "ret_3", "item": "safety_redeclaration_record", "lock_status": "LOCK_INTEGRITY_CONFIRMED", "reference_mutable": False},
                ]
            }
        },
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
        "artifacts": {
            "ir120_completion_bundle": "generic_block_ai/reports/ir116_120/ir120_completion_bundle.json",
            "ir116_120_live_status": "generic_block_ai/reports/ir116_120/ir116_120_live_status.md",
            "ir116_120_completion_table": "generic_block_ai/reports/ir116_120/ir116_120_completion_table.md",
        },
    }


def _prepare_ir120(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir116_120" / "ir120_completion_bundle.json"
    _write(target, payload or _base_ir120_payload())
    return target


def test_ir121_pass_for_valid_ir120_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir120_path = _prepare_ir120(base)

    out = run_ir121_125_batch_dryrun(
        base_path=base,
        source_task_id="ir121_pass",
        ir120_completion_bundle_path=ir120_path,
    )

    ir121 = out["ir121_result"]
    assert ir121["validation_result"] == "PASS"
    assert ir121["audit_pre_submission_final_format"]["entry_count"] > 0
    assert ir121["audit_pre_submission_final_format"]["unlock_eligible"] is False


def test_ir122_pass_and_manifest_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir120_path = _prepare_ir120(base)

    out = run_ir121_125_batch_dryrun(
        base_path=base,
        source_task_id="ir122_pass",
        ir120_completion_bundle_path=ir120_path,
    )

    ir122 = out["ir122_result"]
    assert ir122["validation_result"] == "PASS"
    assert ir122["evidence_manifest"]["manifest_count"] > 0
    assert ir122["evidence_manifest"]["manifest_ready"] is True


def test_ir123_pass_and_consistent_index(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir120_path = _prepare_ir120(base)

    out = run_ir121_125_batch_dryrun(
        base_path=base,
        source_task_id="ir123_pass",
        ir120_completion_bundle_path=ir120_path,
    )

    ir123 = out["ir123_result"]
    assert ir123["validation_result"] == "PASS"
    assert ir123["reference_consistency_index"]["index_count"] > 0
    assert ir123["reference_consistency_index"]["all_consistent"] is True


def test_ir124_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir120_path = _prepare_ir120(base)

    out = run_ir121_125_batch_dryrun(
        base_path=base,
        source_task_id="ir124_abort",
        ir120_completion_bundle_path=ir120_path,
    )

    ir123_with_risk = dict(out["ir123_result"])
    ir123_with_risk["safety_gate_snapshot"] = dict(ir123_with_risk["safety_gate_snapshot"])
    ir123_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir124 = run_ir124_submission_prohibition_dry_run_fixation_gate(
        ir123_report=ir123_with_risk,
        ir122_report=out["ir122_result"],
        source_task_id="ir124_abort",
    )
    assert ir124["submission_prohibition_fixation_decision"] == "ABORT"


def test_ir124_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir120_path = _prepare_ir120(base)

    out = run_ir121_125_batch_dryrun(
        base_path=base,
        source_task_id="ir124_pass",
        ir120_completion_bundle_path=ir120_path,
    )

    ir124 = out["ir124_result"]
    assert ir124["validation_result"] == "PASS"
    assert ir124["submission_prohibition_fixation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir125_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir120_path = _prepare_ir120(base)

    out = run_ir121_125_batch_dryrun(
        base_path=base,
        source_task_id="ir125_pass",
        ir120_completion_bundle_path=ir120_path,
    )

    result = write_ir121_125_completion_bundle(
        base_path=base,
        ir121_125_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 446, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir125_phase_121_125_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
