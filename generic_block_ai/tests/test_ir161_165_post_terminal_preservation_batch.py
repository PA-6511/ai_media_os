import json
from pathlib import Path

from generic_block_ai.app.core_ir161_165_post_terminal_preservation_batch import (
    run_ir161_165_batch_dryrun,
    run_ir164_terminal_post_check_attestation,
    write_ir161_165_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir160_payload() -> dict:
    return {
        "schema_version": "ir160_phase_156_160_completion_bundle_v1",
        "phase": "IR160",
        "generated_at": "2026-05-26T02:00:00+00:00",
        "source_task_id": "ir160_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir158_result": {
            "immutable_audit_index": {
                "index_entries": [
                    {"index_item_id": "immutable_1", "meta_item": "new_cycle_start", "immutability_status": "IMMUTABLE", "index_ref": "immutable://1"},
                    {"index_item_id": "immutable_2", "meta_item": "governance_preparation", "immutability_status": "IMMUTABLE", "index_ref": "immutable://2"},
                    {"index_item_id": "immutable_3", "meta_item": "cycle_summary", "immutability_status": "IMMUTABLE", "index_ref": "immutable://3"},
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
            "ir160_completion_bundle": "generic_block_ai/reports/ir156_160/ir160_completion_bundle.json",
            "ir156_160_live_status": "generic_block_ai/reports/ir156_160/ir156_160_live_status.md",
            "ir156_160_completion_table": "generic_block_ai/reports/ir156_160/ir156_160_completion_table.md",
        },
    }


def _prepare_ir160(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir156_160" / "ir160_completion_bundle.json"
    _write(target, payload or _base_ir160_payload())
    return target


def test_ir161_pass_for_valid_ir160_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir160_path = _prepare_ir160(base)

    out = run_ir161_165_batch_dryrun(
        base_path=base,
        source_task_id="ir161_pass",
        ir160_completion_bundle_path=ir160_path,
    )

    ir161 = out["ir161_result"]
    assert ir161["validation_result"] == "PASS"
    assert ir161["post_terminal_integrity_verification"]["entry_count"] > 0
    assert ir161["post_terminal_integrity_verification"]["unlock_eligible"] is False


def test_ir162_pass_and_preserved(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir160_path = _prepare_ir160(base)

    out = run_ir161_165_batch_dryrun(
        base_path=base,
        source_task_id="ir162_pass",
        ir160_completion_bundle_path=ir160_path,
    )

    ir162 = out["ir162_result"]
    assert ir162["validation_result"] == "PASS"
    assert ir162["read_only_preservation_check"]["entry_count"] > 0
    assert ir162["read_only_preservation_check"]["all_preserved"] is True


def test_ir163_pass_and_continuity_confirmed(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir160_path = _prepare_ir160(base)

    out = run_ir161_165_batch_dryrun(
        base_path=base,
        source_task_id="ir163_pass",
        ir160_completion_bundle_path=ir160_path,
    )

    ir163 = out["ir163_result"]
    assert ir163["validation_result"] == "PASS"
    assert ir163["immutable_reference_continuity_snapshot"]["entry_count"] > 0
    assert ir163["immutable_reference_continuity_snapshot"]["continuity_confirmed"] is True


def test_ir164_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir160_path = _prepare_ir160(base)

    out = run_ir161_165_batch_dryrun(
        base_path=base,
        source_task_id="ir164_abort",
        ir160_completion_bundle_path=ir160_path,
    )

    ir163_with_risk = dict(out["ir163_result"])
    ir163_with_risk["safety_gate_snapshot"] = dict(ir163_with_risk["safety_gate_snapshot"])
    ir163_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir164 = run_ir164_terminal_post_check_attestation(
        ir163_report=ir163_with_risk,
        ir162_report=out["ir162_result"],
        source_task_id="ir164_abort",
    )
    assert ir164["terminal_post_check_attestation_decision"] == "ABORT"


def test_ir164_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir160_path = _prepare_ir160(base)

    out = run_ir161_165_batch_dryrun(
        base_path=base,
        source_task_id="ir164_pass",
        ir160_completion_bundle_path=ir160_path,
    )

    ir164 = out["ir164_result"]
    assert ir164["validation_result"] == "PASS"
    assert ir164["terminal_post_check_attestation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir165_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir160_path = _prepare_ir160(base)

    out = run_ir161_165_batch_dryrun(
        base_path=base,
        source_task_id="ir165_pass",
        ir160_completion_bundle_path=ir160_path,
    )

    result = write_ir161_165_completion_bundle(
        base_path=base,
        ir161_165_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 494, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir165_phase_161_165_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
