import json
from pathlib import Path

from generic_block_ai.app.core_ir106_110_prohibition_continuity_batch import (
    run_ir106_110_batch_dryrun,
    run_ir109_prohibition_continuity_finalizer,
    write_ir106_110_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir105_payload() -> dict:
    return {
        "schema_version": "ir105_phase_101_105_completion_bundle_v1",
        "phase": "IR105",
        "generated_at": "2026-05-25T05:00:00+00:00",
        "source_task_id": "ir105_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CYCLE_CONTINUED_DRY_RUN_ONLY",
        "prohibition_cycle_continued": True,
        "evidence_consolidation_pending": True,
        "ir101_result": {
            "evidence_consolidation_status": {
                "consolidation_entries": [
                    {"queue_item_id": "queue_1", "item": "go_decision_document", "consolidation_status": "PENDING_CONSOLIDATION", "evidence_consolidated": False},
                    {"queue_item_id": "queue_2", "item": "release_approver_signature", "consolidation_status": "PENDING_CONSOLIDATION", "evidence_consolidated": False},
                    {"queue_item_id": "queue_3", "item": "safety_redeclaration_record", "consolidation_status": "PENDING_CONSOLIDATION", "evidence_consolidated": False},
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
            "ir105_completion_bundle": "generic_block_ai/reports/ir101_105/ir105_completion_bundle.json",
            "ir101_105_live_status": "generic_block_ai/reports/ir101_105/ir101_105_live_status.md",
            "ir101_105_completion_table": "generic_block_ai/reports/ir101_105/ir101_105_completion_table.md",
        },
    }


def _prepare_ir105(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir101_105" / "ir105_completion_bundle.json"
    _write(target, payload or _base_ir105_payload())
    return target


def test_ir106_pass_for_valid_ir105_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir105_path = _prepare_ir105(base)

    out = run_ir106_110_batch_dryrun(
        base_path=base,
        source_task_id="ir106_pass",
        ir105_completion_bundle_path=ir105_path,
    )

    ir106 = out["ir106_result"]
    assert ir106["validation_result"] == "PASS"
    assert ir106["consolidated_evidence_review_gate"]["review_entry_count"] > 0
    assert ir106["consolidated_evidence_review_gate"]["all_reviewed"] is False


def test_ir107_pass_and_not_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir105_path = _prepare_ir105(base)

    out = run_ir106_110_batch_dryrun(
        base_path=base,
        source_task_id="ir107_pass",
        ir105_completion_bundle_path=ir105_path,
    )

    ir107 = out["ir107_result"]
    assert ir107["validation_result"] == "PASS"
    assert ir107["delta_closure_readiness_recheck"]["not_ready_count"] > 0
    assert ir107["delta_closure_readiness_recheck"]["all_ready"] is False
    assert ir107["delta_closure_readiness_recheck"]["unlock_eligible"] is False


def test_ir108_pass_and_queue_prepared(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir105_path = _prepare_ir105(base)

    out = run_ir106_110_batch_dryrun(
        base_path=base,
        source_task_id="ir108_pass",
        ir105_completion_bundle_path=ir105_path,
    )

    ir108 = out["ir108_result"]
    assert ir108["validation_result"] == "PASS"
    assert ir108["third_re_review_queue_plan"]["queue_size"] > 0
    assert ir108["third_re_review_queue_plan"]["all_items_queued"] is True


def test_ir109_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir105_path = _prepare_ir105(base)

    out = run_ir106_110_batch_dryrun(
        base_path=base,
        source_task_id="ir109_abort",
        ir105_completion_bundle_path=ir105_path,
    )

    ir108_with_risk = dict(out["ir108_result"])
    ir108_with_risk["safety_gate_snapshot"] = dict(ir108_with_risk["safety_gate_snapshot"])
    ir108_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir109 = run_ir109_prohibition_continuity_finalizer(
        ir108_report=ir108_with_risk,
        ir107_report=out["ir107_result"],
        source_task_id="ir109_abort",
    )
    assert ir109["prohibition_continuity_finalization_decision"] == "ABORT"


def test_ir109_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir105_path = _prepare_ir105(base)

    out = run_ir106_110_batch_dryrun(
        base_path=base,
        source_task_id="ir109_pass",
        ir105_completion_bundle_path=ir105_path,
    )

    ir109 = out["ir109_result"]
    assert ir109["validation_result"] == "PASS"
    assert ir109["prohibition_continuity_finalization_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir110_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir105_path = _prepare_ir105(base)

    out = run_ir106_110_batch_dryrun(
        base_path=base,
        source_task_id="ir110_pass",
        ir105_completion_bundle_path=ir105_path,
    )

    result = write_ir106_110_completion_bundle(
        base_path=base,
        ir106_110_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 60, "failed": 0},
        scoped_regression={"passed": 428, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir110_phase_106_110_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
