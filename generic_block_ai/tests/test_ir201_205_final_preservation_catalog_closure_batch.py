import json
from pathlib import Path

from generic_block_ai.app.core_ir201_205_final_preservation_catalog_closure_batch import (
    run_ir201_205_batch_dryrun,
    run_ir204_dry_run_final_preservation_declaration,
    write_ir201_205_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir200_payload() -> dict:
    return {
        "schema_version": "ir200_phase_196_200_completion_bundle_v1",
        "phase": "IR200",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir200_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "completion_table": [
            {"phase": "IR196", "content": "Terminal Audit Seal Snapshot", "judgement": "完了"},
            {"phase": "IR197", "content": "Long-Term Reference Catalog Lock", "judgement": "完了"},
            {"phase": "IR198", "content": "Final Immutable Digest", "judgement": "完了"},
            {"phase": "IR199", "content": "Dry-Run Terminal Preservation Declaration", "judgement": "完了"},
            {"phase": "IR200", "content": "Phase 196-200 Completion Bundle", "judgement": "完了"},
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
            "ir200_completion_bundle": "generic_block_ai/reports/ir196_200/ir200_completion_bundle.json",
            "ir196_200_live_status": "generic_block_ai/reports/ir196_200/ir196_200_live_status.md",
            "ir196_200_completion_table": "generic_block_ai/reports/ir196_200/ir196_200_completion_table.md",
        },
    }


def _prepare_ir200(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir196_200" / "ir200_completion_bundle.json"
    _write(target, payload or _base_ir200_payload())
    return target


def test_ir201_pass_for_valid_ir200_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir200_path = _prepare_ir200(base)

    out = run_ir201_205_batch_dryrun(
        base_path=base,
        source_task_id="ir201_pass",
        ir200_completion_bundle_path=ir200_path,
    )

    ir201 = out["ir201_result"]
    assert ir201["validation_result"] == "PASS"
    assert ir201["final_preservation_snapshot"]["entry_count"] > 0
    assert ir201["final_preservation_snapshot"]["final_preservation_ready"] is True


def test_ir202_pass_and_catalog_closed(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir200_path = _prepare_ir200(base)

    out = run_ir201_205_batch_dryrun(
        base_path=base,
        source_task_id="ir202_pass",
        ir200_completion_bundle_path=ir200_path,
    )

    ir202 = out["ir202_result"]
    assert ir202["validation_result"] == "PASS"
    assert ir202["closed_reference_catalog_registry"]["entry_count"] > 0
    assert ir202["closed_reference_catalog_registry"]["all_closed_reference_catalog"] is True


def test_ir203_pass_and_final_catalog_digest_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir200_path = _prepare_ir200(base)

    out = run_ir201_205_batch_dryrun(
        base_path=base,
        source_task_id="ir203_pass",
        ir200_completion_bundle_path=ir200_path,
    )

    ir203 = out["ir203_result"]
    assert ir203["validation_result"] == "PASS"
    assert ir203["final_catalog_digest"]["entry_count"] > 0
    assert ir203["final_catalog_digest"]["final_catalog_digest_ready"] is True


def test_ir204_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir200_path = _prepare_ir200(base)

    out = run_ir201_205_batch_dryrun(
        base_path=base,
        source_task_id="ir204_abort",
        ir200_completion_bundle_path=ir200_path,
    )

    ir203_with_risk = dict(out["ir203_result"])
    ir203_with_risk["safety_gate_snapshot"] = dict(ir203_with_risk["safety_gate_snapshot"])
    ir203_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir204 = run_ir204_dry_run_final_preservation_declaration(
        ir203_report=ir203_with_risk,
        ir202_report=out["ir202_result"],
        source_task_id="ir204_abort",
    )
    assert ir204["dry_run_final_preservation_declaration_decision"] == "ABORT"


def test_ir204_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir200_path = _prepare_ir200(base)

    out = run_ir201_205_batch_dryrun(
        base_path=base,
        source_task_id="ir204_pass",
        ir200_completion_bundle_path=ir200_path,
    )

    ir204 = out["ir204_result"]
    assert ir204["validation_result"] == "PASS"
    assert ir204["dry_run_final_preservation_declaration_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir205_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir200_path = _prepare_ir200(base)

    out = run_ir201_205_batch_dryrun(
        base_path=base,
        source_task_id="ir205_pass",
        ir200_completion_bundle_path=ir200_path,
    )

    result = write_ir201_205_completion_bundle(
        base_path=base,
        ir201_205_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 542, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir205_phase_201_205_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
