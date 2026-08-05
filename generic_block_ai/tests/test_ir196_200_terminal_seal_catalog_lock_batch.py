import json
from pathlib import Path

from generic_block_ai.app.core_ir196_200_terminal_seal_catalog_lock_batch import (
    run_ir196_200_batch_dryrun,
    run_ir199_dry_run_terminal_preservation_declaration,
    write_ir196_200_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir195_payload() -> dict:
    return {
        "schema_version": "ir195_phase_191_195_completion_bundle_v1",
        "phase": "IR195",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir195_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "completion_table": [
            {"phase": "IR191", "content": "Terminal Archive Organization Snapshot", "judgement": "完了"},
            {"phase": "IR192", "content": "Final Reference Consistency Reverification Registry", "judgement": "完了"},
            {"phase": "IR193", "content": "Final Consistency Digest Refix", "judgement": "完了"},
            {"phase": "IR194", "content": "Dry-Run Final Reverification Attestation", "judgement": "完了"},
            {"phase": "IR195", "content": "Phase 191-195 Completion Bundle", "judgement": "完了"},
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
            "ir195_completion_bundle": "generic_block_ai/reports/ir191_195/ir195_completion_bundle.json",
            "ir191_195_live_status": "generic_block_ai/reports/ir191_195/ir191_195_live_status.md",
            "ir191_195_completion_table": "generic_block_ai/reports/ir191_195/ir191_195_completion_table.md",
        },
    }


def _prepare_ir195(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir191_195" / "ir195_completion_bundle.json"
    _write(target, payload or _base_ir195_payload())
    return target


def test_ir196_pass_for_valid_ir195_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir195_path = _prepare_ir195(base)

    out = run_ir196_200_batch_dryrun(
        base_path=base,
        source_task_id="ir196_pass",
        ir195_completion_bundle_path=ir195_path,
    )

    ir196 = out["ir196_result"]
    assert ir196["validation_result"] == "PASS"
    assert ir196["terminal_audit_seal_snapshot"]["entry_count"] > 0
    assert ir196["terminal_audit_seal_snapshot"]["terminal_seal_ready"] is True


def test_ir197_pass_and_catalog_locked(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir195_path = _prepare_ir195(base)

    out = run_ir196_200_batch_dryrun(
        base_path=base,
        source_task_id="ir197_pass",
        ir195_completion_bundle_path=ir195_path,
    )

    ir197 = out["ir197_result"]
    assert ir197["validation_result"] == "PASS"
    assert ir197["long_term_reference_catalog_lock"]["entry_count"] > 0
    assert ir197["long_term_reference_catalog_lock"]["all_locked_closed_domain"] is True


def test_ir198_pass_and_final_immutable_digest_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir195_path = _prepare_ir195(base)

    out = run_ir196_200_batch_dryrun(
        base_path=base,
        source_task_id="ir198_pass",
        ir195_completion_bundle_path=ir195_path,
    )

    ir198 = out["ir198_result"]
    assert ir198["validation_result"] == "PASS"
    assert ir198["final_immutable_digest"]["entry_count"] > 0
    assert ir198["final_immutable_digest"]["final_immutable_digest_ready"] is True


def test_ir199_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir195_path = _prepare_ir195(base)

    out = run_ir196_200_batch_dryrun(
        base_path=base,
        source_task_id="ir199_abort",
        ir195_completion_bundle_path=ir195_path,
    )

    ir198_with_risk = dict(out["ir198_result"])
    ir198_with_risk["safety_gate_snapshot"] = dict(ir198_with_risk["safety_gate_snapshot"])
    ir198_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir199 = run_ir199_dry_run_terminal_preservation_declaration(
        ir198_report=ir198_with_risk,
        ir197_report=out["ir197_result"],
        source_task_id="ir199_abort",
    )
    assert ir199["dry_run_terminal_preservation_declaration_decision"] == "ABORT"


def test_ir199_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir195_path = _prepare_ir195(base)

    out = run_ir196_200_batch_dryrun(
        base_path=base,
        source_task_id="ir199_pass",
        ir195_completion_bundle_path=ir195_path,
    )

    ir199 = out["ir199_result"]
    assert ir199["validation_result"] == "PASS"
    assert ir199["dry_run_terminal_preservation_declaration_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir200_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir195_path = _prepare_ir195(base)

    out = run_ir196_200_batch_dryrun(
        base_path=base,
        source_task_id="ir200_pass",
        ir195_completion_bundle_path=ir195_path,
    )

    result = write_ir196_200_completion_bundle(
        base_path=base,
        ir196_200_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 536, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir200_phase_196_200_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
