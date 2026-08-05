import json
from pathlib import Path

from generic_block_ai.app.core_ir151_155_cycle_a_meta_evidence_batch import (
    run_ir151_155_batch_dryrun,
    run_ir154_dry_run_terminal_closure_attestation,
    write_ir151_155_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir150_payload() -> dict:
    return {
        "schema_version": "ir150_phase_146_150_completion_bundle_v1",
        "phase": "IR150",
        "generated_at": "2026-05-26T00:30:00+00:00",
        "source_task_id": "ir150_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir149_result": {
            "ir71_plus_cycle_summary": {
                "cycle_summary_finalized": True
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
            "ir150_completion_bundle": "generic_block_ai/reports/ir146_150/ir150_completion_bundle.json",
            "ir146_150_live_status": "generic_block_ai/reports/ir146_150/ir146_150_live_status.md",
            "ir146_150_completion_table": "generic_block_ai/reports/ir146_150/ir146_150_completion_table.md",
        },
    }


def _prepare_ir150(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir146_150" / "ir150_completion_bundle.json"
    _write(target, payload or _base_ir150_payload())
    return target


def test_ir151_pass_for_valid_ir150_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir150_path = _prepare_ir150(base)

    out = run_ir151_155_batch_dryrun(
        base_path=base,
        source_task_id="ir151_pass",
        ir150_completion_bundle_path=ir150_path,
    )

    ir151 = out["ir151_result"]
    assert ir151["validation_result"] == "PASS"
    assert ir151["cycle_a_integrated_completion_report"]["item_count"] > 0
    assert ir151["cycle_a_integrated_completion_report"]["unlock_eligible"] is False


def test_ir152_pass_and_meta_locked(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir150_path = _prepare_ir150(base)

    out = run_ir151_155_batch_dryrun(
        base_path=base,
        source_task_id="ir152_pass",
        ir150_completion_bundle_path=ir150_path,
    )

    ir152 = out["ir152_result"]
    assert ir152["validation_result"] == "PASS"
    assert ir152["meta_evidence_lock"]["lock_count"] > 0
    assert ir152["meta_evidence_lock"]["all_meta_locked"] is True


def test_ir153_pass_and_digest_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir150_path = _prepare_ir150(base)

    out = run_ir151_155_batch_dryrun(
        base_path=base,
        source_task_id="ir153_pass",
        ir150_completion_bundle_path=ir150_path,
    )

    ir153 = out["ir153_result"]
    assert ir153["validation_result"] == "PASS"
    assert ir153["governance_trace_digest"]["digest_count"] > 0
    assert ir153["governance_trace_digest"]["digest_ready"] is True


def test_ir154_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir150_path = _prepare_ir150(base)

    out = run_ir151_155_batch_dryrun(
        base_path=base,
        source_task_id="ir154_abort",
        ir150_completion_bundle_path=ir150_path,
    )

    ir153_with_risk = dict(out["ir153_result"])
    ir153_with_risk["safety_gate_snapshot"] = dict(ir153_with_risk["safety_gate_snapshot"])
    ir153_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir154 = run_ir154_dry_run_terminal_closure_attestation(
        ir153_report=ir153_with_risk,
        ir152_report=out["ir152_result"],
        source_task_id="ir154_abort",
    )
    assert ir154["dry_run_terminal_closure_attestation_decision"] == "ABORT"


def test_ir154_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir150_path = _prepare_ir150(base)

    out = run_ir151_155_batch_dryrun(
        base_path=base,
        source_task_id="ir154_pass",
        ir150_completion_bundle_path=ir150_path,
    )

    ir154 = out["ir154_result"]
    assert ir154["validation_result"] == "PASS"
    assert ir154["dry_run_terminal_closure_attestation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir155_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir150_path = _prepare_ir150(base)

    out = run_ir151_155_batch_dryrun(
        base_path=base,
        source_task_id="ir155_pass",
        ir150_completion_bundle_path=ir150_path,
    )

    result = write_ir151_155_completion_bundle(
        base_path=base,
        ir151_155_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 482, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir155_phase_151_155_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
