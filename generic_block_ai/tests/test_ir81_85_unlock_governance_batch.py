import json
from pathlib import Path

from generic_block_ai.app.core_ir81_85_unlock_governance_batch import (
    run_ir81_85_batch_dryrun,
    run_ir84_unlock_prohibition_gate_revalidation,
    write_ir81_85_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir80_payload() -> dict:
    return {
        "schema_version": "ir80_phase_76_80_completion_bundle_v1",
        "phase": "IR80",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir80_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "GOVERNANCE_READY_DRY_RUN_ONLY",
        "governance_ready_dry_run_only": True,
        "completion_table": [
            {"phase": "IR76", "content": "New Cycle Execution Boundary Policy", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR77", "content": "Dry-Run Unlock Preconditions Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR78", "content": "Human Approval Scope Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR79", "content": "Legacy Reference Linkage Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR80", "content": "Phase 76-80 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
        ],
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
            "ir80_completion_bundle": "generic_block_ai/reports/ir76_80/ir80_completion_bundle.json",
            "ir76_80_live_status": "generic_block_ai/reports/ir76_80/ir76_80_live_status.md",
            "ir76_80_completion_table": "generic_block_ai/reports/ir76_80/ir76_80_completion_table.md",
        },
    }


def _prepare_ir80(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir76_80" / "ir80_completion_bundle.json"
    _write(target, payload or _base_ir80_payload())
    return target


def test_ir81_pass_for_valid_ir80_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir80_path = _prepare_ir80(base)

    out = run_ir81_85_batch_dryrun(
        base_path=base,
        source_task_id="ir81_pass",
        ir80_completion_bundle_path=ir80_path,
    )

    ir81 = out["ir81_result"]
    assert ir81["validation_result"] == "PASS"
    assert ir81["unlock_preconditions_ledger"]["unlock_ready"] is False


def test_ir82_pass_placeholder_registry(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir80_path = _prepare_ir80(base)

    out = run_ir81_85_batch_dryrun(
        base_path=base,
        source_task_id="ir82_pass",
        ir80_completion_bundle_path=ir80_path,
    )

    ir82 = out["ir82_result"]
    assert ir82["validation_result"] == "PASS"
    assert ir82["approval_evidence_record"]["all_required_evidence_present"] is False


def test_ir83_pass_and_remains_blocked(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir80_path = _prepare_ir80(base)

    out = run_ir81_85_batch_dryrun(
        base_path=base,
        source_task_id="ir83_pass",
        ir80_completion_bundle_path=ir80_path,
    )

    ir83 = out["ir83_result"]
    assert ir83["validation_result"] == "PASS"
    assert ir83["staged_unlock_simulation"]["unlock_simulation_result"] == "REMAINS_BLOCKED"
    assert ir83["staged_unlock_simulation"]["execution_unlocked"] is False


def test_ir84_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir80_path = _prepare_ir80(base)

    out = run_ir81_85_batch_dryrun(
        base_path=base,
        source_task_id="ir84_abort",
        ir80_completion_bundle_path=ir80_path,
    )

    ir83_with_risk = dict(out["ir83_result"])
    ir83_with_risk["safety_gate_snapshot"] = dict(ir83_with_risk["safety_gate_snapshot"])
    ir83_with_risk["safety_gate_snapshot"]["network_transmission_executed"] = True

    ir84 = run_ir84_unlock_prohibition_gate_revalidation(
        ir83_report=ir83_with_risk,
        ir82_report=out["ir82_result"],
        source_task_id="ir84_abort",
    )
    assert ir84["unlock_prohibition_gate_decision"] == "ABORT"


def test_ir84_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir80_path = _prepare_ir80(base)

    out = run_ir81_85_batch_dryrun(
        base_path=base,
        source_task_id="ir84_confirm",
        ir80_completion_bundle_path=ir80_path,
    )

    ir84 = out["ir84_result"]
    assert ir84["validation_result"] == "PASS"
    assert ir84["unlock_prohibition_gate_decision"] == "UNLOCK_PROHIBITION_CONFIRMED_DRY_RUN_ONLY"


def test_ir85_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir80_path = _prepare_ir80(base)

    out = run_ir81_85_batch_dryrun(
        base_path=base,
        source_task_id="ir85_pass",
        ir80_completion_bundle_path=ir80_path,
    )

    result = write_ir81_85_completion_bundle(
        base_path=base,
        ir81_85_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 36, "failed": 0},
        scoped_regression={"passed": 398, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir85_phase_81_85_completion_bundle_v1"
    assert report["final_decision"] == "UNLOCK_PROHIBITION_CONFIRMED_DRY_RUN_ONLY"
    assert report["unlock_prohibition_confirmed"] is True
    assert report["safety_gate_summary"]["production_release"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
