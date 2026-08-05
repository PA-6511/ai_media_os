import json
from pathlib import Path

from generic_block_ai.app.core_ir141_145_final_audit_catalog_batch import (
    run_ir141_145_batch_dryrun,
    run_ir144_dry_run_terminal_state_fixation,
    write_ir141_145_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir140_payload() -> dict:
    return {
        "schema_version": "ir140_phase_136_140_completion_bundle_v1",
        "phase": "IR140",
        "generated_at": "2026-05-25T12:00:00+00:00",
        "source_task_id": "ir140_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir138_result": {
            "retention_evidence_index": {
                "index_entries": [
                    {"index_item_id": "idx_1", "item": "go_decision_document", "index_ref": "retention://frz_1", "index_status": "INDEXED"},
                    {"index_item_id": "idx_2", "item": "release_approver_signature", "index_ref": "retention://frz_2", "index_status": "INDEXED"},
                    {"index_item_id": "idx_3", "item": "safety_redeclaration_record", "index_ref": "retention://frz_3", "index_status": "INDEXED"},
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
            "ir140_completion_bundle": "generic_block_ai/reports/ir136_140/ir140_completion_bundle.json",
            "ir136_140_live_status": "generic_block_ai/reports/ir136_140/ir136_140_live_status.md",
            "ir136_140_completion_table": "generic_block_ai/reports/ir136_140/ir136_140_completion_table.md",
        },
    }


def _prepare_ir140(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir136_140" / "ir140_completion_bundle.json"
    _write(target, payload or _base_ir140_payload())
    return target


def test_ir141_pass_for_valid_ir140_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir140_path = _prepare_ir140(base)

    out = run_ir141_145_batch_dryrun(
        base_path=base,
        source_task_id="ir141_pass",
        ir140_completion_bundle_path=ir140_path,
    )

    ir141 = out["ir141_result"]
    assert ir141["validation_result"] == "PASS"
    assert ir141["completion_audit_report"]["entry_count"] > 0
    assert ir141["completion_audit_report"]["unlock_eligible"] is False


def test_ir142_pass_and_index_closed(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir140_path = _prepare_ir140(base)

    out = run_ir141_145_batch_dryrun(
        base_path=base,
        source_task_id="ir142_pass",
        ir140_completion_bundle_path=ir140_path,
    )

    ir142 = out["ir142_result"]
    assert ir142["validation_result"] == "PASS"
    assert ir142["evidence_index_closure"]["closure_count"] > 0
    assert ir142["evidence_index_closure"]["all_closed"] is True


def test_ir143_pass_and_catalog_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir140_path = _prepare_ir140(base)

    out = run_ir141_145_batch_dryrun(
        base_path=base,
        source_task_id="ir143_pass",
        ir140_completion_bundle_path=ir140_path,
    )

    ir143 = out["ir143_result"]
    assert ir143["validation_result"] == "PASS"
    assert ir143["long_term_reference_catalog"]["catalog_count"] > 0
    assert ir143["long_term_reference_catalog"]["catalog_ready"] is True


def test_ir144_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir140_path = _prepare_ir140(base)

    out = run_ir141_145_batch_dryrun(
        base_path=base,
        source_task_id="ir144_abort",
        ir140_completion_bundle_path=ir140_path,
    )

    ir143_with_risk = dict(out["ir143_result"])
    ir143_with_risk["safety_gate_snapshot"] = dict(ir143_with_risk["safety_gate_snapshot"])
    ir143_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir144 = run_ir144_dry_run_terminal_state_fixation(
        ir143_report=ir143_with_risk,
        ir142_report=out["ir142_result"],
        source_task_id="ir144_abort",
    )
    assert ir144["dry_run_terminal_state_fixation_decision"] == "ABORT"


def test_ir144_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir140_path = _prepare_ir140(base)

    out = run_ir141_145_batch_dryrun(
        base_path=base,
        source_task_id="ir144_pass",
        ir140_completion_bundle_path=ir140_path,
    )

    ir144 = out["ir144_result"]
    assert ir144["validation_result"] == "PASS"
    assert ir144["dry_run_terminal_state_fixation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir145_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir140_path = _prepare_ir140(base)

    out = run_ir141_145_batch_dryrun(
        base_path=base,
        source_task_id="ir145_pass",
        ir140_completion_bundle_path=ir140_path,
    )

    result = write_ir141_145_completion_bundle(
        base_path=base,
        ir141_145_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 470, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir145_phase_141_145_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
