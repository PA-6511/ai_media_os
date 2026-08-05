import json
from pathlib import Path

from generic_block_ai.app.core_ir111_115_prohibition_evidence_fixation_batch import (
    run_ir111_115_batch_dryrun,
    run_ir114_dry_run_finalization_audit_gate,
    write_ir111_115_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir110_payload() -> dict:
    return {
        "schema_version": "ir110_phase_106_110_completion_bundle_v1",
        "phase": "IR110",
        "generated_at": "2026-05-25T06:00:00+00:00",
        "source_task_id": "ir110_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir106_result": {
            "consolidated_evidence_review_gate": {
                "review_entries": [
                    {"queue_item_id": "queue_1", "item": "go_decision_document", "review_status": "REVIEW_PENDING", "reviewed": False},
                    {"queue_item_id": "queue_2", "item": "release_approver_signature", "review_status": "REVIEW_PENDING", "reviewed": False},
                    {"queue_item_id": "queue_3", "item": "safety_redeclaration_record", "review_status": "REVIEW_PENDING", "reviewed": False},
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
            "ir110_completion_bundle": "generic_block_ai/reports/ir106_110/ir110_completion_bundle.json",
            "ir106_110_live_status": "generic_block_ai/reports/ir106_110/ir106_110_live_status.md",
            "ir106_110_completion_table": "generic_block_ai/reports/ir106_110/ir106_110_completion_table.md",
        },
    }


def _prepare_ir110(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir106_110" / "ir110_completion_bundle.json"
    _write(target, payload or _base_ir110_payload())
    return target


def test_ir111_pass_for_valid_ir110_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir110_path = _prepare_ir110(base)

    out = run_ir111_115_batch_dryrun(
        base_path=base,
        source_task_id="ir111_pass",
        ir110_completion_bundle_path=ir110_path,
    )

    ir111 = out["ir111_result"]
    assert ir111["validation_result"] == "PASS"
    assert ir111["finalized_prohibition_evidence_snapshot"]["snapshot_entry_count"] > 0
    assert ir111["finalized_prohibition_evidence_snapshot"]["unlock_eligible"] is False


def test_ir112_pass_and_deferred(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir110_path = _prepare_ir110(base)

    out = run_ir111_115_batch_dryrun(
        base_path=base,
        source_task_id="ir112_pass",
        ir110_completion_bundle_path=ir110_path,
    )

    ir112 = out["ir112_result"]
    assert ir112["validation_result"] == "PASS"
    assert ir112["delta_closure_deferred_registry"]["deferred_count"] > 0
    assert ir112["delta_closure_deferred_registry"]["delta_closure_deferred"] is True


def test_ir113_pass_and_handoff_prepared(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir110_path = _prepare_ir110(base)

    out = run_ir111_115_batch_dryrun(
        base_path=base,
        source_task_id="ir113_pass",
        ir110_completion_bundle_path=ir110_path,
    )

    ir113 = out["ir113_result"]
    assert ir113["validation_result"] == "PASS"
    assert ir113["third_re_review_handoff_package"]["package_size"] > 0
    assert ir113["third_re_review_handoff_package"]["all_handoff_prepared"] is True


def test_ir114_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir110_path = _prepare_ir110(base)

    out = run_ir111_115_batch_dryrun(
        base_path=base,
        source_task_id="ir114_abort",
        ir110_completion_bundle_path=ir110_path,
    )

    ir113_with_risk = dict(out["ir113_result"])
    ir113_with_risk["safety_gate_snapshot"] = dict(ir113_with_risk["safety_gate_snapshot"])
    ir113_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir114 = run_ir114_dry_run_finalization_audit_gate(
        ir113_report=ir113_with_risk,
        ir112_report=out["ir112_result"],
        source_task_id="ir114_abort",
    )
    assert ir114["dry_run_finalization_audit_decision"] == "ABORT"


def test_ir114_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir110_path = _prepare_ir110(base)

    out = run_ir111_115_batch_dryrun(
        base_path=base,
        source_task_id="ir114_pass",
        ir110_completion_bundle_path=ir110_path,
    )

    ir114 = out["ir114_result"]
    assert ir114["validation_result"] == "PASS"
    assert ir114["dry_run_finalization_audit_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir115_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir110_path = _prepare_ir110(base)

    out = run_ir111_115_batch_dryrun(
        base_path=base,
        source_task_id="ir115_pass",
        ir110_completion_bundle_path=ir110_path,
    )

    result = write_ir111_115_completion_bundle(
        base_path=base,
        ir111_115_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 60, "failed": 0},
        scoped_regression={"passed": 428, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir115_phase_111_115_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
