import json
from pathlib import Path

from generic_block_ai.app.core_ir206_210_final_cycle_complete_declaration_batch import (
    run_ir206_210_batch_dryrun,
    run_ir209_dry_run_final_completion_declaration,
    write_ir206_210_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir205_payload() -> dict:
    return {
        "schema_version": "ir205_phase_201_205_completion_bundle_v1",
        "phase": "IR205",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir205_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "completion_table": [
            {"phase": "IR201", "content": "Final Preservation Snapshot", "judgement": "完了"},
            {"phase": "IR202", "content": "Closed Reference Catalog Registry", "judgement": "完了"},
            {"phase": "IR203", "content": "Final Catalog Digest", "judgement": "完了"},
            {"phase": "IR204", "content": "Dry-Run Final Preservation Declaration", "judgement": "完了"},
            {"phase": "IR205", "content": "Phase 201-205 Completion Bundle", "judgement": "完了"},
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
            "ir205_completion_bundle": "generic_block_ai/reports/ir201_205/ir205_completion_bundle.json",
            "ir201_205_live_status": "generic_block_ai/reports/ir201_205/ir201_205_live_status.md",
            "ir201_205_completion_table": "generic_block_ai/reports/ir201_205/ir201_205_completion_table.md",
        },
    }


def _prepare_ir205(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir201_205" / "ir205_completion_bundle.json"
    _write(target, payload or _base_ir205_payload())
    return target


def test_ir206_pass_for_valid_ir205_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir205_path = _prepare_ir205(base)

    out = run_ir206_210_batch_dryrun(
        base_path=base,
        source_task_id="ir206_pass",
        ir205_completion_bundle_path=ir205_path,
    )

    ir206 = out["ir206_result"]
    assert ir206["validation_result"] == "PASS"
    assert ir206["final_cycle_complete_declaration_snapshot"]["entry_count"] > 0
    assert ir206["final_cycle_complete_declaration_snapshot"]["final_cycle_complete_ready"] is True


def test_ir207_pass_and_read_only_closed(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir205_path = _prepare_ir205(base)

    out = run_ir206_210_batch_dryrun(
        base_path=base,
        source_task_id="ir207_pass",
        ir205_completion_bundle_path=ir205_path,
    )

    ir207 = out["ir207_result"]
    assert ir207["validation_result"] == "PASS"
    assert ir207["read_only_closed_archive_registry"]["entry_count"] > 0
    assert ir207["read_only_closed_archive_registry"]["all_read_only_closed_archived"] is True


def test_ir208_pass_and_final_summary_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir205_path = _prepare_ir205(base)

    out = run_ir206_210_batch_dryrun(
        base_path=base,
        source_task_id="ir208_pass",
        ir205_completion_bundle_path=ir205_path,
    )

    ir208 = out["ir208_result"]
    assert ir208["validation_result"] == "PASS"
    assert ir208["final_summary_digest"]["entry_count"] > 0
    assert ir208["final_summary_digest"]["final_summary_digest_ready"] is True


def test_ir209_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir205_path = _prepare_ir205(base)

    out = run_ir206_210_batch_dryrun(
        base_path=base,
        source_task_id="ir209_abort",
        ir205_completion_bundle_path=ir205_path,
    )

    ir208_with_risk = dict(out["ir208_result"])
    ir208_with_risk["safety_gate_snapshot"] = dict(ir208_with_risk["safety_gate_snapshot"])
    ir208_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir209 = run_ir209_dry_run_final_completion_declaration(
        ir208_report=ir208_with_risk,
        ir207_report=out["ir207_result"],
        source_task_id="ir209_abort",
    )
    assert ir209["dry_run_final_completion_declaration_decision"] == "ABORT"


def test_ir209_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir205_path = _prepare_ir205(base)

    out = run_ir206_210_batch_dryrun(
        base_path=base,
        source_task_id="ir209_pass",
        ir205_completion_bundle_path=ir205_path,
    )

    ir209 = out["ir209_result"]
    assert ir209["validation_result"] == "PASS"
    assert ir209["dry_run_final_completion_declaration_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir210_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir205_path = _prepare_ir205(base)

    out = run_ir206_210_batch_dryrun(
        base_path=base,
        source_task_id="ir210_pass",
        ir205_completion_bundle_path=ir205_path,
    )

    result = write_ir206_210_completion_bundle(
        base_path=base,
        ir206_210_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 548, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir210_phase_206_210_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
