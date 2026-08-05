import json
from pathlib import Path

from generic_block_ai.app.core_ir156_160_archive_terminal_batch import (
    run_ir156_160_batch_dryrun,
    run_ir159_terminal_declaration_package,
    write_ir156_160_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir155_payload() -> dict:
    return {
        "schema_version": "ir155_phase_151_155_completion_bundle_v1",
        "phase": "IR155",
        "generated_at": "2026-05-26T01:00:00+00:00",
        "source_task_id": "ir155_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir153_result": {
            "governance_trace_digest": {
                "digest_entries": [
                    {"meta_item": "new_cycle_start", "digest_id": "aaa", "digest_status": "DIGESTED"},
                    {"meta_item": "governance_preparation", "digest_id": "bbb", "digest_status": "DIGESTED"},
                    {"meta_item": "cycle_summary", "digest_id": "ccc", "digest_status": "DIGESTED"},
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
            "ir155_completion_bundle": "generic_block_ai/reports/ir151_155/ir155_completion_bundle.json",
            "ir151_155_live_status": "generic_block_ai/reports/ir151_155/ir151_155_live_status.md",
            "ir151_155_completion_table": "generic_block_ai/reports/ir151_155/ir151_155_completion_table.md",
        },
    }


def _prepare_ir155(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir151_155" / "ir155_completion_bundle.json"
    _write(target, payload or _base_ir155_payload())
    return target


def test_ir156_pass_for_valid_ir155_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir155_path = _prepare_ir155(base)

    out = run_ir156_160_batch_dryrun(
        base_path=base,
        source_task_id="ir156_pass",
        ir155_completion_bundle_path=ir155_path,
    )

    ir156 = out["ir156_result"]
    assert ir156["validation_result"] == "PASS"
    assert ir156["archive_final_seal"]["seal_count"] > 0
    assert ir156["archive_final_seal"]["unlock_eligible"] is False


def test_ir157_pass_and_reference_only_enforced(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir155_path = _prepare_ir155(base)

    out = run_ir156_160_batch_dryrun(
        base_path=base,
        source_task_id="ir157_pass",
        ir155_completion_bundle_path=ir155_path,
    )

    ir157 = out["ir157_result"]
    assert ir157["validation_result"] == "PASS"
    assert ir157["reference_only_enforcement_registry"]["entry_count"] > 0
    assert ir157["reference_only_enforcement_registry"]["all_reference_only_enforced"] is True


def test_ir158_pass_and_immutable_index_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir155_path = _prepare_ir155(base)

    out = run_ir156_160_batch_dryrun(
        base_path=base,
        source_task_id="ir158_pass",
        ir155_completion_bundle_path=ir155_path,
    )

    ir158 = out["ir158_result"]
    assert ir158["validation_result"] == "PASS"
    assert ir158["immutable_audit_index"]["index_count"] > 0
    assert ir158["immutable_audit_index"]["immutable_index_ready"] is True


def test_ir159_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir155_path = _prepare_ir155(base)

    out = run_ir156_160_batch_dryrun(
        base_path=base,
        source_task_id="ir159_abort",
        ir155_completion_bundle_path=ir155_path,
    )

    ir158_with_risk = dict(out["ir158_result"])
    ir158_with_risk["safety_gate_snapshot"] = dict(ir158_with_risk["safety_gate_snapshot"])
    ir158_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir159 = run_ir159_terminal_declaration_package(
        ir158_report=ir158_with_risk,
        ir157_report=out["ir157_result"],
        source_task_id="ir159_abort",
    )
    assert ir159["terminal_declaration_decision"] == "ABORT"


def test_ir159_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir155_path = _prepare_ir155(base)

    out = run_ir156_160_batch_dryrun(
        base_path=base,
        source_task_id="ir159_pass",
        ir155_completion_bundle_path=ir155_path,
    )

    ir159 = out["ir159_result"]
    assert ir159["validation_result"] == "PASS"
    assert ir159["terminal_declaration_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir160_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir155_path = _prepare_ir155(base)

    out = run_ir156_160_batch_dryrun(
        base_path=base,
        source_task_id="ir160_pass",
        ir155_completion_bundle_path=ir155_path,
    )

    result = write_ir156_160_completion_bundle(
        base_path=base,
        ir156_160_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 488, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir160_phase_156_160_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
