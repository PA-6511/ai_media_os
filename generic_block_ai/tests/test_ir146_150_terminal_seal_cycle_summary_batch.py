import json
from pathlib import Path

from generic_block_ai.app.core_ir146_150_terminal_seal_cycle_summary_batch import (
    run_ir146_150_batch_dryrun,
    run_ir149_ir71_plus_cycle_summary,
    write_ir146_150_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir145_payload() -> dict:
    return {
        "schema_version": "ir145_phase_141_145_completion_bundle_v1",
        "phase": "IR145",
        "generated_at": "2026-05-26T00:00:00+00:00",
        "source_task_id": "ir145_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir143_result": {
            "long_term_reference_catalog": {
                "catalog_entries": [
                    {"catalog_item_id": "cat_1", "item": "go_decision_document", "catalog_ref": "catalog://idx_1", "catalog_status": "REGISTERED"},
                    {"catalog_item_id": "cat_2", "item": "release_approver_signature", "catalog_ref": "catalog://idx_2", "catalog_status": "REGISTERED"},
                    {"catalog_item_id": "cat_3", "item": "safety_redeclaration_record", "catalog_ref": "catalog://idx_3", "catalog_status": "REGISTERED"},
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
            "ir145_completion_bundle": "generic_block_ai/reports/ir141_145/ir145_completion_bundle.json",
            "ir141_145_live_status": "generic_block_ai/reports/ir141_145/ir141_145_live_status.md",
            "ir141_145_completion_table": "generic_block_ai/reports/ir141_145/ir141_145_completion_table.md",
        },
    }


def _prepare_ir145(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir141_145" / "ir145_completion_bundle.json"
    _write(target, payload or _base_ir145_payload())
    return target


def test_ir146_pass_for_valid_ir145_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir145_path = _prepare_ir145(base)

    out = run_ir146_150_batch_dryrun(
        base_path=base,
        source_task_id="ir146_pass",
        ir145_completion_bundle_path=ir145_path,
    )

    ir146 = out["ir146_result"]
    assert ir146["validation_result"] == "PASS"
    assert ir146["terminal_state_final_seal"]["seal_count"] > 0
    assert ir146["terminal_state_final_seal"]["unlock_eligible"] is False


def test_ir147_pass_and_catalog_consistent(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir145_path = _prepare_ir145(base)

    out = run_ir146_150_batch_dryrun(
        base_path=base,
        source_task_id="ir147_pass",
        ir145_completion_bundle_path=ir145_path,
    )

    ir147 = out["ir147_result"]
    assert ir147["validation_result"] == "PASS"
    assert ir147["long_term_catalog_consistency_check"]["entry_count"] > 0
    assert ir147["long_term_catalog_consistency_check"]["all_consistent"] is True


def test_ir148_pass_and_full_termination_evidenced(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir145_path = _prepare_ir145(base)

    out = run_ir146_150_batch_dryrun(
        base_path=base,
        source_task_id="ir148_pass",
        ir145_completion_bundle_path=ir145_path,
    )

    ir148 = out["ir148_result"]
    assert ir148["validation_result"] == "PASS"
    assert ir148["dry_run_full_termination_evidence"]["entry_count"] > 0
    assert ir148["dry_run_full_termination_evidence"]["full_termination_evidenced"] is True


def test_ir149_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir145_path = _prepare_ir145(base)

    out = run_ir146_150_batch_dryrun(
        base_path=base,
        source_task_id="ir149_abort",
        ir145_completion_bundle_path=ir145_path,
    )

    ir148_with_risk = dict(out["ir148_result"])
    ir148_with_risk["safety_gate_snapshot"] = dict(ir148_with_risk["safety_gate_snapshot"])
    ir148_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir149 = run_ir149_ir71_plus_cycle_summary(
        ir148_report=ir148_with_risk,
        ir147_report=out["ir147_result"],
        source_task_id="ir149_abort",
    )
    assert ir149["ir71_plus_cycle_summary_decision"] == "ABORT"


def test_ir149_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir145_path = _prepare_ir145(base)

    out = run_ir146_150_batch_dryrun(
        base_path=base,
        source_task_id="ir149_pass",
        ir145_completion_bundle_path=ir145_path,
    )

    ir149 = out["ir149_result"]
    assert ir149["validation_result"] == "PASS"
    assert ir149["ir71_plus_cycle_summary_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir150_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir145_path = _prepare_ir145(base)

    out = run_ir146_150_batch_dryrun(
        base_path=base,
        source_task_id="ir150_pass",
        ir145_completion_bundle_path=ir145_path,
    )

    result = write_ir146_150_completion_bundle(
        base_path=base,
        ir146_150_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 476, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir150_phase_146_150_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
