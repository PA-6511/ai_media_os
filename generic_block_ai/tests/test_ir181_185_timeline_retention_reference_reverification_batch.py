import json
from pathlib import Path

from generic_block_ai.app.core_ir181_185_timeline_retention_reference_reverification_batch import (
    run_ir181_185_batch_dryrun,
    run_ir184_dry_run_retention_consistency_attestation,
    write_ir181_185_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir180_payload() -> dict:
    return {
        "schema_version": "ir180_phase_176_180_completion_bundle_v1",
        "phase": "IR180",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir180_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "completion_table": [
            {"phase": "IR176", "content": "Periodic Reverification Timeline Snapshot", "judgement": "完了"},
            {"phase": "IR177", "content": "Re-Audit Reference Index Closure", "judgement": "完了"},
            {"phase": "IR178", "content": "Timeline Digest Refix", "judgement": "完了"},
            {"phase": "IR179", "content": "Dry-Run Timeline Closure Attestation", "judgement": "完了"},
            {"phase": "IR180", "content": "Phase 176-180 Completion Bundle", "judgement": "完了"},
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
            "ir180_completion_bundle": "generic_block_ai/reports/ir176_180/ir180_completion_bundle.json",
            "ir176_180_live_status": "generic_block_ai/reports/ir176_180/ir176_180_live_status.md",
            "ir176_180_completion_table": "generic_block_ai/reports/ir176_180/ir176_180_completion_table.md",
        },
    }


def _prepare_ir180(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir176_180" / "ir180_completion_bundle.json"
    _write(target, payload or _base_ir180_payload())
    return target


def test_ir181_pass_for_valid_ir180_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir180_path = _prepare_ir180(base)

    out = run_ir181_185_batch_dryrun(
        base_path=base,
        source_task_id="ir181_pass",
        ir180_completion_bundle_path=ir180_path,
    )

    ir181 = out["ir181_result"]
    assert ir181["validation_result"] == "PASS"
    assert ir181["timeline_retention_audit_snapshot"]["entry_count"] > 0
    assert ir181["timeline_retention_audit_snapshot"]["retention_audit_ready"] is True


def test_ir182_pass_and_reference_consistent(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir180_path = _prepare_ir180(base)

    out = run_ir181_185_batch_dryrun(
        base_path=base,
        source_task_id="ir182_pass",
        ir180_completion_bundle_path=ir180_path,
    )

    ir182 = out["ir182_result"]
    assert ir182["validation_result"] == "PASS"
    assert ir182["post_terminal_reference_consistency_registry"]["entry_count"] > 0
    assert ir182["post_terminal_reference_consistency_registry"]["all_consistent_reference_only"] is True


def test_ir183_pass_and_consistency_digest_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir180_path = _prepare_ir180(base)

    out = run_ir181_185_batch_dryrun(
        base_path=base,
        source_task_id="ir183_pass",
        ir180_completion_bundle_path=ir180_path,
    )

    ir183 = out["ir183_result"]
    assert ir183["validation_result"] == "PASS"
    assert ir183["consistency_digest_refix"]["entry_count"] > 0
    assert ir183["consistency_digest_refix"]["consistency_digest_refix_ready"] is True


def test_ir184_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir180_path = _prepare_ir180(base)

    out = run_ir181_185_batch_dryrun(
        base_path=base,
        source_task_id="ir184_abort",
        ir180_completion_bundle_path=ir180_path,
    )

    ir183_with_risk = dict(out["ir183_result"])
    ir183_with_risk["safety_gate_snapshot"] = dict(ir183_with_risk["safety_gate_snapshot"])
    ir183_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir184 = run_ir184_dry_run_retention_consistency_attestation(
        ir183_report=ir183_with_risk,
        ir182_report=out["ir182_result"],
        source_task_id="ir184_abort",
    )
    assert ir184["dry_run_retention_consistency_attestation_decision"] == "ABORT"


def test_ir184_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir180_path = _prepare_ir180(base)

    out = run_ir181_185_batch_dryrun(
        base_path=base,
        source_task_id="ir184_pass",
        ir180_completion_bundle_path=ir180_path,
    )

    ir184 = out["ir184_result"]
    assert ir184["validation_result"] == "PASS"
    assert ir184["dry_run_retention_consistency_attestation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir185_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir180_path = _prepare_ir180(base)

    out = run_ir181_185_batch_dryrun(
        base_path=base,
        source_task_id="ir185_pass",
        ir180_completion_bundle_path=ir180_path,
    )

    result = write_ir181_185_completion_bundle(
        base_path=base,
        ir181_185_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 518, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir185_phase_181_185_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
