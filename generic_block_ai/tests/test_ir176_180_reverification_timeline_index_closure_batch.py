import json
from pathlib import Path

from generic_block_ai.app.core_ir176_180_reverification_timeline_index_closure_batch import (
    run_ir176_180_batch_dryrun,
    run_ir179_dry_run_timeline_closure_attestation,
    write_ir176_180_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir175_payload() -> dict:
    return {
        "schema_version": "ir175_phase_171_175_completion_bundle_v1",
        "phase": "IR175",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir175_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "completion_table": [
            {"phase": "IR171", "content": "Periodic Reverification Snapshot", "judgement": "完了"},
            {"phase": "IR172", "content": "Zero-Change Audit Registry", "judgement": "完了"},
            {"phase": "IR173", "content": "Tracking Digest Refix", "judgement": "完了"},
            {"phase": "IR174", "content": "DRY_RUN Continuity Evidence", "judgement": "完了"},
            {"phase": "IR175", "content": "Phase 171-175 Completion Bundle", "judgement": "完了"},
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
            "ir175_completion_bundle": "generic_block_ai/reports/ir171_175/ir175_completion_bundle.json",
            "ir171_175_live_status": "generic_block_ai/reports/ir171_175/ir171_175_live_status.md",
            "ir171_175_completion_table": "generic_block_ai/reports/ir171_175/ir171_175_completion_table.md",
        },
    }


def _prepare_ir175(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir171_175" / "ir175_completion_bundle.json"
    _write(target, payload or _base_ir175_payload())
    return target


def test_ir176_pass_for_valid_ir175_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir175_path = _prepare_ir175(base)

    out = run_ir176_180_batch_dryrun(
        base_path=base,
        source_task_id="ir176_pass",
        ir175_completion_bundle_path=ir175_path,
    )

    ir176 = out["ir176_result"]
    assert ir176["validation_result"] == "PASS"
    assert ir176["periodic_reverification_timeline_snapshot"]["entry_count"] > 0
    assert ir176["periodic_reverification_timeline_snapshot"]["timeline_fixed"] is True


def test_ir177_pass_and_all_closed_reference_only(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir175_path = _prepare_ir175(base)

    out = run_ir176_180_batch_dryrun(
        base_path=base,
        source_task_id="ir177_pass",
        ir175_completion_bundle_path=ir175_path,
    )

    ir177 = out["ir177_result"]
    assert ir177["validation_result"] == "PASS"
    assert ir177["reaudit_reference_index_closure"]["entry_count"] > 0
    assert ir177["reaudit_reference_index_closure"]["all_closed_reference_only"] is True


def test_ir178_pass_and_timeline_digest_refix_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir175_path = _prepare_ir175(base)

    out = run_ir176_180_batch_dryrun(
        base_path=base,
        source_task_id="ir178_pass",
        ir175_completion_bundle_path=ir175_path,
    )

    ir178 = out["ir178_result"]
    assert ir178["validation_result"] == "PASS"
    assert ir178["timeline_digest_refix"]["entry_count"] > 0
    assert ir178["timeline_digest_refix"]["timeline_digest_refix_ready"] is True


def test_ir179_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir175_path = _prepare_ir175(base)

    out = run_ir176_180_batch_dryrun(
        base_path=base,
        source_task_id="ir179_abort",
        ir175_completion_bundle_path=ir175_path,
    )

    ir178_with_risk = dict(out["ir178_result"])
    ir178_with_risk["safety_gate_snapshot"] = dict(ir178_with_risk["safety_gate_snapshot"])
    ir178_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir179 = run_ir179_dry_run_timeline_closure_attestation(
        ir178_report=ir178_with_risk,
        ir177_report=out["ir177_result"],
        source_task_id="ir179_abort",
    )
    assert ir179["dry_run_timeline_closure_attestation_decision"] == "ABORT"


def test_ir179_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir175_path = _prepare_ir175(base)

    out = run_ir176_180_batch_dryrun(
        base_path=base,
        source_task_id="ir179_pass",
        ir175_completion_bundle_path=ir175_path,
    )

    ir179 = out["ir179_result"]
    assert ir179["validation_result"] == "PASS"
    assert ir179["dry_run_timeline_closure_attestation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir180_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir175_path = _prepare_ir175(base)

    out = run_ir176_180_batch_dryrun(
        base_path=base,
        source_task_id="ir180_pass",
        ir175_completion_bundle_path=ir175_path,
    )

    result = write_ir176_180_completion_bundle(
        base_path=base,
        ir176_180_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 512, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir180_phase_176_180_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
