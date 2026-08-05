import json
from pathlib import Path

from generic_block_ai.app.core_ir131_135_retention_receipt_closure_batch import (
    run_ir131_135_batch_dryrun,
    run_ir134_long_term_reference_snapshot,
    write_ir131_135_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir130_payload() -> dict:
    return {
        "schema_version": "ir130_phase_126_130_completion_bundle_v1",
        "phase": "IR130",
        "generated_at": "2026-05-25T10:00:00+00:00",
        "source_task_id": "ir130_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir126_result": {
            "pre_submission_package_freeze": {
                "freeze_entries": [
                    {"freeze_item_id": "frz_1", "item": "go_decision_document", "manifest_ref": "evidence://ret_1", "freeze_status": "FROZEN", "mutable": False},
                    {"freeze_item_id": "frz_2", "item": "release_approver_signature", "manifest_ref": "evidence://ret_2", "freeze_status": "FROZEN", "mutable": False},
                    {"freeze_item_id": "frz_3", "item": "safety_redeclaration_record", "manifest_ref": "evidence://ret_3", "freeze_status": "FROZEN", "mutable": False},
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
            "ir130_completion_bundle": "generic_block_ai/reports/ir126_130/ir130_completion_bundle.json",
            "ir126_130_live_status": "generic_block_ai/reports/ir126_130/ir126_130_live_status.md",
            "ir126_130_completion_table": "generic_block_ai/reports/ir126_130/ir126_130_completion_table.md",
        },
    }


def _prepare_ir130(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir126_130" / "ir130_completion_bundle.json"
    _write(target, payload or _base_ir130_payload())
    return target


def test_ir131_pass_for_valid_ir130_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir130_path = _prepare_ir130(base)

    out = run_ir131_135_batch_dryrun(
        base_path=base,
        source_task_id="ir131_pass",
        ir130_completion_bundle_path=ir130_path,
    )

    ir131 = out["ir131_result"]
    assert ir131["validation_result"] == "PASS"
    assert ir131["long_term_retention_receipt_confirmation"]["receipt_count"] > 0
    assert ir131["long_term_retention_receipt_confirmation"]["unlock_eligible"] is False


def test_ir132_pass_and_closed(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir130_path = _prepare_ir130(base)

    out = run_ir131_135_batch_dryrun(
        base_path=base,
        source_task_id="ir132_pass",
        ir130_completion_bundle_path=ir130_path,
    )

    ir132 = out["ir132_result"]
    assert ir132["validation_result"] == "PASS"
    assert ir132["freeze_manifest_closure"]["closure_count"] > 0
    assert ir132["freeze_manifest_closure"]["all_closed"] is True


def test_ir133_pass_and_non_submission_logged(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir130_path = _prepare_ir130(base)

    out = run_ir131_135_batch_dryrun(
        base_path=base,
        source_task_id="ir133_pass",
        ir130_completion_bundle_path=ir130_path,
    )

    ir133 = out["ir133_result"]
    assert ir133["validation_result"] == "PASS"
    assert ir133["non_submission_ledger"]["entry_count"] > 0
    assert ir133["non_submission_ledger"]["all_non_submitted"] is True


def test_ir134_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir130_path = _prepare_ir130(base)

    out = run_ir131_135_batch_dryrun(
        base_path=base,
        source_task_id="ir134_abort",
        ir130_completion_bundle_path=ir130_path,
    )

    ir133_with_risk = dict(out["ir133_result"])
    ir133_with_risk["safety_gate_snapshot"] = dict(ir133_with_risk["safety_gate_snapshot"])
    ir133_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir134 = run_ir134_long_term_reference_snapshot(
        ir133_report=ir133_with_risk,
        ir132_report=out["ir132_result"],
        source_task_id="ir134_abort",
    )
    assert ir134["long_term_reference_snapshot_decision"] == "ABORT"


def test_ir134_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir130_path = _prepare_ir130(base)

    out = run_ir131_135_batch_dryrun(
        base_path=base,
        source_task_id="ir134_pass",
        ir130_completion_bundle_path=ir130_path,
    )

    ir134 = out["ir134_result"]
    assert ir134["validation_result"] == "PASS"
    assert ir134["long_term_reference_snapshot_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir135_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir130_path = _prepare_ir130(base)

    out = run_ir131_135_batch_dryrun(
        base_path=base,
        source_task_id="ir135_pass",
        ir130_completion_bundle_path=ir130_path,
    )

    result = write_ir131_135_completion_bundle(
        base_path=base,
        ir131_135_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 458, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir135_phase_131_135_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
