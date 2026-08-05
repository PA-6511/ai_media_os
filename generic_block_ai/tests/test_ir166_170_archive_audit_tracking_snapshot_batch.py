import json
from pathlib import Path

from generic_block_ai.app.core_ir166_170_archive_audit_tracking_snapshot_batch import (
    run_ir166_170_batch_dryrun,
    run_ir169_dry_run_long_term_tracking_attestation,
    write_ir166_170_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir165_payload() -> dict:
    return {
        "schema_version": "ir165_phase_161_165_completion_bundle_v1",
        "phase": "IR165",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir165_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "ir163_result": {
            "immutable_reference_continuity_snapshot": {
                "snapshot_entries": [
                    {"snapshot_item_id": "snapshot_1", "index_item_id": "immutable_1", "meta_item": "new_cycle_start", "continuity_status": "CONTINUOUS"},
                    {"snapshot_item_id": "snapshot_2", "index_item_id": "immutable_2", "meta_item": "governance_preparation", "continuity_status": "CONTINUOUS"},
                    {"snapshot_item_id": "snapshot_3", "index_item_id": "immutable_3", "meta_item": "cycle_summary", "continuity_status": "CONTINUOUS"},
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
            "ir165_completion_bundle": "generic_block_ai/reports/ir161_165/ir165_completion_bundle.json",
            "ir161_165_live_status": "generic_block_ai/reports/ir161_165/ir161_165_live_status.md",
            "ir161_165_completion_table": "generic_block_ai/reports/ir161_165/ir161_165_completion_table.md",
        },
    }


def _prepare_ir165(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir161_165" / "ir165_completion_bundle.json"
    _write(target, payload or _base_ir165_payload())
    return target


def test_ir166_pass_for_valid_ir165_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir165_path = _prepare_ir165(base)

    out = run_ir166_170_batch_dryrun(
        base_path=base,
        source_task_id="ir166_pass",
        ir165_completion_bundle_path=ir165_path,
    )

    ir166 = out["ir166_result"]
    assert ir166["validation_result"] == "PASS"
    assert ir166["archive_audit_long_term_tracking_snapshot"]["entry_count"] > 0
    assert ir166["archive_audit_long_term_tracking_snapshot"]["unlock_eligible"] is False


def test_ir167_pass_and_continuous(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir165_path = _prepare_ir165(base)

    out = run_ir166_170_batch_dryrun(
        base_path=base,
        source_task_id="ir167_pass",
        ir165_completion_bundle_path=ir165_path,
    )

    ir167 = out["ir167_result"]
    assert ir167["validation_result"] == "PASS"
    assert ir167["tracking_continuity_registry"]["entry_count"] > 0
    assert ir167["tracking_continuity_registry"]["all_continuous"] is True


def test_ir168_pass_and_digest_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir165_path = _prepare_ir165(base)

    out = run_ir166_170_batch_dryrun(
        base_path=base,
        source_task_id="ir168_pass",
        ir165_completion_bundle_path=ir165_path,
    )

    ir168 = out["ir168_result"]
    assert ir168["validation_result"] == "PASS"
    assert ir168["immutable_tracking_digest"]["entry_count"] > 0
    assert ir168["immutable_tracking_digest"]["immutable_digest_ready"] is True


def test_ir169_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir165_path = _prepare_ir165(base)

    out = run_ir166_170_batch_dryrun(
        base_path=base,
        source_task_id="ir169_abort",
        ir165_completion_bundle_path=ir165_path,
    )

    ir168_with_risk = dict(out["ir168_result"])
    ir168_with_risk["safety_gate_snapshot"] = dict(ir168_with_risk["safety_gate_snapshot"])
    ir168_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir169 = run_ir169_dry_run_long_term_tracking_attestation(
        ir168_report=ir168_with_risk,
        ir167_report=out["ir167_result"],
        source_task_id="ir169_abort",
    )
    assert ir169["dry_run_long_term_tracking_attestation_decision"] == "ABORT"


def test_ir169_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir165_path = _prepare_ir165(base)

    out = run_ir166_170_batch_dryrun(
        base_path=base,
        source_task_id="ir169_pass",
        ir165_completion_bundle_path=ir165_path,
    )

    ir169 = out["ir169_result"]
    assert ir169["validation_result"] == "PASS"
    assert ir169["dry_run_long_term_tracking_attestation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir170_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir165_path = _prepare_ir165(base)

    out = run_ir166_170_batch_dryrun(
        base_path=base,
        source_task_id="ir170_pass",
        ir165_completion_bundle_path=ir165_path,
    )

    result = write_ir166_170_completion_bundle(
        base_path=base,
        ir166_170_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 500, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir170_phase_166_170_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
