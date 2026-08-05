import json
from pathlib import Path

from generic_block_ai.app.core_ir136_140_reference_reverification_batch import (
    run_ir136_140_batch_dryrun,
    run_ir139_dry_run_final_retention_gate,
    write_ir136_140_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir135_payload() -> dict:
    return {
        "schema_version": "ir135_phase_131_135_completion_bundle_v1",
        "phase": "IR135",
        "generated_at": "2026-05-25T11:00:00+00:00",
        "source_task_id": "ir135_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir133_result": {
            "non_submission_ledger": {
                "ledger_entries": [
                    {"freeze_item_id": "frz_1", "item": "go_decision_document", "non_submission_status": "NOT_SUBMITTED_DRY_RUN", "submission_executed": False},
                    {"freeze_item_id": "frz_2", "item": "release_approver_signature", "non_submission_status": "NOT_SUBMITTED_DRY_RUN", "submission_executed": False},
                    {"freeze_item_id": "frz_3", "item": "safety_redeclaration_record", "non_submission_status": "NOT_SUBMITTED_DRY_RUN", "submission_executed": False},
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
            "ir135_completion_bundle": "generic_block_ai/reports/ir131_135/ir135_completion_bundle.json",
            "ir131_135_live_status": "generic_block_ai/reports/ir131_135/ir131_135_live_status.md",
            "ir131_135_completion_table": "generic_block_ai/reports/ir131_135/ir131_135_completion_table.md",
        },
    }


def _prepare_ir135(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir131_135" / "ir135_completion_bundle.json"
    _write(target, payload or _base_ir135_payload())
    return target


def test_ir136_pass_for_valid_ir135_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir135_path = _prepare_ir135(base)

    out = run_ir136_140_batch_dryrun(
        base_path=base,
        source_task_id="ir136_pass",
        ir135_completion_bundle_path=ir135_path,
    )

    ir136 = out["ir136_result"]
    assert ir136["validation_result"] == "PASS"
    assert ir136["reference_snapshot_reverification"]["entry_count"] > 0
    assert ir136["reference_snapshot_reverification"]["unlock_eligible"] is False


def test_ir137_pass_and_ledger_closed(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir135_path = _prepare_ir135(base)

    out = run_ir136_140_batch_dryrun(
        base_path=base,
        source_task_id="ir137_pass",
        ir135_completion_bundle_path=ir135_path,
    )

    ir137 = out["ir137_result"]
    assert ir137["validation_result"] == "PASS"
    assert ir137["non_submission_ledger_closure"]["closure_count"] > 0
    assert ir137["non_submission_ledger_closure"]["all_closed"] is True


def test_ir138_pass_and_index_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir135_path = _prepare_ir135(base)

    out = run_ir136_140_batch_dryrun(
        base_path=base,
        source_task_id="ir138_pass",
        ir135_completion_bundle_path=ir135_path,
    )

    ir138 = out["ir138_result"]
    assert ir138["validation_result"] == "PASS"
    assert ir138["retention_evidence_index"]["index_count"] > 0
    assert ir138["retention_evidence_index"]["index_ready"] is True


def test_ir139_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir135_path = _prepare_ir135(base)

    out = run_ir136_140_batch_dryrun(
        base_path=base,
        source_task_id="ir139_abort",
        ir135_completion_bundle_path=ir135_path,
    )

    ir138_with_risk = dict(out["ir138_result"])
    ir138_with_risk["safety_gate_snapshot"] = dict(ir138_with_risk["safety_gate_snapshot"])
    ir138_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir139 = run_ir139_dry_run_final_retention_gate(
        ir138_report=ir138_with_risk,
        ir137_report=out["ir137_result"],
        source_task_id="ir139_abort",
    )
    assert ir139["dry_run_final_retention_gate_decision"] == "ABORT"


def test_ir139_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir135_path = _prepare_ir135(base)

    out = run_ir136_140_batch_dryrun(
        base_path=base,
        source_task_id="ir139_pass",
        ir135_completion_bundle_path=ir135_path,
    )

    ir139 = out["ir139_result"]
    assert ir139["validation_result"] == "PASS"
    assert ir139["dry_run_final_retention_gate_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir140_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir135_path = _prepare_ir135(base)

    out = run_ir136_140_batch_dryrun(
        base_path=base,
        source_task_id="ir140_pass",
        ir135_completion_bundle_path=ir135_path,
    )

    result = write_ir136_140_completion_bundle(
        base_path=base,
        ir136_140_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 464, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir140_phase_136_140_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
