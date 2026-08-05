import json
from pathlib import Path

from generic_block_ai.app.core_ir191_195_terminal_archive_consistency_reverification_batch import (
    run_ir191_195_batch_dryrun,
    run_ir194_dry_run_final_reverification_attestation,
    write_ir191_195_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir190_payload() -> dict:
    return {
        "schema_version": "ir190_phase_186_190_completion_bundle_v1",
        "phase": "IR190",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir190_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "completion_table": [
            {"phase": "IR186", "content": "Retention Refix Evidence Snapshot", "judgement": "完了"},
            {"phase": "IR187", "content": "Reference Consistency Terminal Registry", "judgement": "完了"},
            {"phase": "IR188", "content": "Terminal Digest Refix", "judgement": "完了"},
            {"phase": "IR189", "content": "Dry-Run Terminal Audit Attestation", "judgement": "完了"},
            {"phase": "IR190", "content": "Phase 186-190 Completion Bundle", "judgement": "完了"},
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
            "ir190_completion_bundle": "generic_block_ai/reports/ir186_190/ir190_completion_bundle.json",
            "ir186_190_live_status": "generic_block_ai/reports/ir186_190/ir186_190_live_status.md",
            "ir186_190_completion_table": "generic_block_ai/reports/ir186_190/ir186_190_completion_table.md",
        },
    }


def _prepare_ir190(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir186_190" / "ir190_completion_bundle.json"
    _write(target, payload or _base_ir190_payload())
    return target


def test_ir191_pass_for_valid_ir190_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir190_path = _prepare_ir190(base)

    out = run_ir191_195_batch_dryrun(
        base_path=base,
        source_task_id="ir191_pass",
        ir190_completion_bundle_path=ir190_path,
    )

    ir191 = out["ir191_result"]
    assert ir191["validation_result"] == "PASS"
    assert ir191["terminal_archive_organization_snapshot"]["entry_count"] > 0
    assert ir191["terminal_archive_organization_snapshot"]["archive_organization_ready"] is True


def test_ir192_pass_and_final_reference_consistent(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir190_path = _prepare_ir190(base)

    out = run_ir191_195_batch_dryrun(
        base_path=base,
        source_task_id="ir192_pass",
        ir190_completion_bundle_path=ir190_path,
    )

    ir192 = out["ir192_result"]
    assert ir192["validation_result"] == "PASS"
    assert ir192["final_reference_consistency_reverification_registry"]["entry_count"] > 0
    assert ir192["final_reference_consistency_reverification_registry"]["all_final_consistent_reference_only"] is True


def test_ir193_pass_and_final_digest_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir190_path = _prepare_ir190(base)

    out = run_ir191_195_batch_dryrun(
        base_path=base,
        source_task_id="ir193_pass",
        ir190_completion_bundle_path=ir190_path,
    )

    ir193 = out["ir193_result"]
    assert ir193["validation_result"] == "PASS"
    assert ir193["final_consistency_digest_refix"]["entry_count"] > 0
    assert ir193["final_consistency_digest_refix"]["final_consistency_digest_refix_ready"] is True


def test_ir194_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir190_path = _prepare_ir190(base)

    out = run_ir191_195_batch_dryrun(
        base_path=base,
        source_task_id="ir194_abort",
        ir190_completion_bundle_path=ir190_path,
    )

    ir193_with_risk = dict(out["ir193_result"])
    ir193_with_risk["safety_gate_snapshot"] = dict(ir193_with_risk["safety_gate_snapshot"])
    ir193_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir194 = run_ir194_dry_run_final_reverification_attestation(
        ir193_report=ir193_with_risk,
        ir192_report=out["ir192_result"],
        source_task_id="ir194_abort",
    )
    assert ir194["dry_run_final_reverification_attestation_decision"] == "ABORT"


def test_ir194_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir190_path = _prepare_ir190(base)

    out = run_ir191_195_batch_dryrun(
        base_path=base,
        source_task_id="ir194_pass",
        ir190_completion_bundle_path=ir190_path,
    )

    ir194 = out["ir194_result"]
    assert ir194["validation_result"] == "PASS"
    assert ir194["dry_run_final_reverification_attestation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir195_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir190_path = _prepare_ir190(base)

    out = run_ir191_195_batch_dryrun(
        base_path=base,
        source_task_id="ir195_pass",
        ir190_completion_bundle_path=ir190_path,
    )

    result = write_ir191_195_completion_bundle(
        base_path=base,
        ir191_195_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 530, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir195_phase_191_195_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
