import json
from pathlib import Path

from generic_block_ai.app.core_ir116_120_evidence_retention_readiness_batch import (
    run_ir116_120_batch_dryrun,
    run_ir119_audit_submission_readiness_package,
    write_ir116_120_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir115_payload() -> dict:
    return {
        "schema_version": "ir115_phase_111_115_completion_bundle_v1",
        "phase": "IR115",
        "generated_at": "2026-05-25T07:00:00+00:00",
        "source_task_id": "ir115_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir111_result": {
            "finalized_prohibition_evidence_snapshot": {
                "snapshot_entries": [
                    {"queue_item_id": "queue_1", "item": "go_decision_document", "snapshot_status": "FINALIZED_PROHIBITION_EVIDENCE_LOCKED", "locked": True, "mutable": False},
                    {"queue_item_id": "queue_2", "item": "release_approver_signature", "snapshot_status": "FINALIZED_PROHIBITION_EVIDENCE_LOCKED", "locked": True, "mutable": False},
                    {"queue_item_id": "queue_3", "item": "safety_redeclaration_record", "snapshot_status": "FINALIZED_PROHIBITION_EVIDENCE_LOCKED", "locked": True, "mutable": False},
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
            "ir115_completion_bundle": "generic_block_ai/reports/ir111_115/ir115_completion_bundle.json",
            "ir111_115_live_status": "generic_block_ai/reports/ir111_115/ir111_115_live_status.md",
            "ir111_115_completion_table": "generic_block_ai/reports/ir111_115/ir111_115_completion_table.md",
        },
    }


def _prepare_ir115(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir111_115" / "ir115_completion_bundle.json"
    _write(target, payload or _base_ir115_payload())
    return target


def test_ir116_pass_for_valid_ir115_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir115_path = _prepare_ir115(base)

    out = run_ir116_120_batch_dryrun(
        base_path=base,
        source_task_id="ir116_pass",
        ir115_completion_bundle_path=ir115_path,
    )

    ir116 = out["ir116_result"]
    assert ir116["validation_result"] == "PASS"
    assert ir116["long_term_evidence_retention_registry"]["retention_entry_count"] > 0
    assert ir116["long_term_evidence_retention_registry"]["unlock_eligible"] is False


def test_ir117_pass_and_reverified(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir115_path = _prepare_ir115(base)

    out = run_ir116_120_batch_dryrun(
        base_path=base,
        source_task_id="ir117_pass",
        ir115_completion_bundle_path=ir115_path,
    )

    ir117 = out["ir117_result"]
    assert ir117["validation_result"] == "PASS"
    assert ir117["fixed_evidence_reverification_ledger"]["verified_count"] > 0
    assert ir117["fixed_evidence_reverification_ledger"]["all_reverified"] is True


def test_ir118_pass_and_lock_integrity_confirmed(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir115_path = _prepare_ir115(base)

    out = run_ir116_120_batch_dryrun(
        base_path=base,
        source_task_id="ir118_pass",
        ir115_completion_bundle_path=ir115_path,
    )

    ir118 = out["ir118_result"]
    assert ir118["validation_result"] == "PASS"
    assert ir118["reference_lock_integrity_gate"]["lock_entry_count"] > 0
    assert ir118["reference_lock_integrity_gate"]["all_reference_locked"] is True


def test_ir119_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir115_path = _prepare_ir115(base)

    out = run_ir116_120_batch_dryrun(
        base_path=base,
        source_task_id="ir119_abort",
        ir115_completion_bundle_path=ir115_path,
    )

    ir118_with_risk = dict(out["ir118_result"])
    ir118_with_risk["safety_gate_snapshot"] = dict(ir118_with_risk["safety_gate_snapshot"])
    ir118_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir119 = run_ir119_audit_submission_readiness_package(
        ir118_report=ir118_with_risk,
        ir117_report=out["ir117_result"],
        source_task_id="ir119_abort",
    )
    assert ir119["audit_submission_readiness_decision"] == "ABORT"


def test_ir119_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir115_path = _prepare_ir115(base)

    out = run_ir116_120_batch_dryrun(
        base_path=base,
        source_task_id="ir119_pass",
        ir115_completion_bundle_path=ir115_path,
    )

    ir119 = out["ir119_result"]
    assert ir119["validation_result"] == "PASS"
    assert ir119["audit_submission_readiness_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir120_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir115_path = _prepare_ir115(base)

    out = run_ir116_120_batch_dryrun(
        base_path=base,
        source_task_id="ir120_pass",
        ir115_completion_bundle_path=ir115_path,
    )

    result = write_ir116_120_completion_bundle(
        base_path=base,
        ir116_120_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 60, "failed": 0},
        scoped_regression={"passed": 428, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir120_phase_116_120_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
