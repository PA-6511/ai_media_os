import json
from pathlib import Path

from generic_block_ai.app.core_ir126_130_submission_freeze_handoff_batch import (
    run_ir126_130_batch_dryrun,
    run_ir129_long_term_retention_handoff,
    write_ir126_130_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir125_payload() -> dict:
    return {
        "schema_version": "ir125_phase_121_125_completion_bundle_v1",
        "phase": "IR125",
        "generated_at": "2026-05-25T09:00:00+00:00",
        "source_task_id": "ir125_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir122_result": {
            "evidence_manifest": {
                "manifest_entries": [
                    {"manifest_item_id": "man_1", "item": "go_decision_document", "manifest_ref": "evidence://ret_1", "manifest_status": "MANIFESTED"},
                    {"manifest_item_id": "man_2", "item": "release_approver_signature", "manifest_ref": "evidence://ret_2", "manifest_status": "MANIFESTED"},
                    {"manifest_item_id": "man_3", "item": "safety_redeclaration_record", "manifest_ref": "evidence://ret_3", "manifest_status": "MANIFESTED"},
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
            "ir125_completion_bundle": "generic_block_ai/reports/ir121_125/ir125_completion_bundle.json",
            "ir121_125_live_status": "generic_block_ai/reports/ir121_125/ir121_125_live_status.md",
            "ir121_125_completion_table": "generic_block_ai/reports/ir121_125/ir121_125_completion_table.md",
        },
    }


def _prepare_ir125(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir121_125" / "ir125_completion_bundle.json"
    _write(target, payload or _base_ir125_payload())
    return target


def test_ir126_pass_for_valid_ir125_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir125_path = _prepare_ir125(base)

    out = run_ir126_130_batch_dryrun(
        base_path=base,
        source_task_id="ir126_pass",
        ir125_completion_bundle_path=ir125_path,
    )

    ir126 = out["ir126_result"]
    assert ir126["validation_result"] == "PASS"
    assert ir126["pre_submission_package_freeze"]["freeze_count"] > 0
    assert ir126["pre_submission_package_freeze"]["unlock_eligible"] is False


def test_ir127_pass_and_reverified(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir125_path = _prepare_ir125(base)

    out = run_ir126_130_batch_dryrun(
        base_path=base,
        source_task_id="ir127_pass",
        ir125_completion_bundle_path=ir125_path,
    )

    ir127 = out["ir127_result"]
    assert ir127["validation_result"] == "PASS"
    assert ir127["manifest_reverification"]["entry_count"] > 0
    assert ir127["manifest_reverification"]["all_reverified"] is True


def test_ir128_pass_and_non_submission_confirmed(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir125_path = _prepare_ir125(base)

    out = run_ir126_130_batch_dryrun(
        base_path=base,
        source_task_id="ir128_pass",
        ir125_completion_bundle_path=ir125_path,
    )

    ir128 = out["ir128_result"]
    assert ir128["validation_result"] == "PASS"
    assert ir128["dry_run_non_submission_evidence_gate"]["gate_entry_count"] > 0
    assert ir128["dry_run_non_submission_evidence_gate"]["submission_prohibited_confirmed"] is True


def test_ir129_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir125_path = _prepare_ir125(base)

    out = run_ir126_130_batch_dryrun(
        base_path=base,
        source_task_id="ir129_abort",
        ir125_completion_bundle_path=ir125_path,
    )

    ir128_with_risk = dict(out["ir128_result"])
    ir128_with_risk["safety_gate_snapshot"] = dict(ir128_with_risk["safety_gate_snapshot"])
    ir128_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir129 = run_ir129_long_term_retention_handoff(
        ir128_report=ir128_with_risk,
        ir127_report=out["ir127_result"],
        source_task_id="ir129_abort",
    )
    assert ir129["long_term_retention_handoff_decision"] == "ABORT"


def test_ir129_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir125_path = _prepare_ir125(base)

    out = run_ir126_130_batch_dryrun(
        base_path=base,
        source_task_id="ir129_pass",
        ir125_completion_bundle_path=ir125_path,
    )

    ir129 = out["ir129_result"]
    assert ir129["validation_result"] == "PASS"
    assert ir129["long_term_retention_handoff_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir130_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir125_path = _prepare_ir125(base)

    out = run_ir126_130_batch_dryrun(
        base_path=base,
        source_task_id="ir130_pass",
        ir125_completion_bundle_path=ir125_path,
    )

    result = write_ir126_130_completion_bundle(
        base_path=base,
        ir126_130_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 452, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir130_phase_126_130_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
