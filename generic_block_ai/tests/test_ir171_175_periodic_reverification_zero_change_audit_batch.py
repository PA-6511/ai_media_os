import json
from pathlib import Path

from generic_block_ai.app.core_ir171_175_periodic_reverification_zero_change_audit_batch import (
    run_ir171_175_batch_dryrun,
    run_ir174_dry_run_continuity_attestation,
    write_ir171_175_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir170_payload() -> dict:
    return {
        "schema_version": "ir170_phase_166_170_completion_bundle_v1",
        "phase": "IR170",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir170_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "completion_table": [
            {"phase": "IR166", "content": "Archive Audit Long-Term Tracking Snapshot", "judgement": "完了"},
            {"phase": "IR167", "content": "Tracking Continuity Registry", "judgement": "完了"},
            {"phase": "IR168", "content": "Immutable Tracking Digest", "judgement": "完了"},
            {"phase": "IR169", "content": "Dry-Run Long-Term Tracking Attestation", "judgement": "完了"},
            {"phase": "IR170", "content": "Phase 166-170 Completion Bundle", "judgement": "完了"},
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
            "ir170_completion_bundle": "generic_block_ai/reports/ir166_170/ir170_completion_bundle.json",
            "ir166_170_live_status": "generic_block_ai/reports/ir166_170/ir166_170_live_status.md",
            "ir166_170_completion_table": "generic_block_ai/reports/ir166_170/ir166_170_completion_table.md",
        },
    }


def _prepare_ir170(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir166_170" / "ir170_completion_bundle.json"
    _write(target, payload or _base_ir170_payload())
    return target


def test_ir171_pass_for_valid_ir170_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir170_path = _prepare_ir170(base)

    out = run_ir171_175_batch_dryrun(
        base_path=base,
        source_task_id="ir171_pass",
        ir170_completion_bundle_path=ir170_path,
    )

    ir171 = out["ir171_result"]
    assert ir171["validation_result"] == "PASS"
    assert ir171["periodic_reverification_snapshot"]["entry_count"] > 0
    assert ir171["periodic_reverification_snapshot"]["unlock_eligible"] is False


def test_ir172_pass_and_zero_change(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir170_path = _prepare_ir170(base)

    out = run_ir171_175_batch_dryrun(
        base_path=base,
        source_task_id="ir172_pass",
        ir170_completion_bundle_path=ir170_path,
    )

    ir172 = out["ir172_result"]
    assert ir172["validation_result"] == "PASS"
    assert ir172["zero_change_audit_registry"]["entry_count"] > 0
    assert ir172["zero_change_audit_registry"]["all_zero_change"] is True


def test_ir173_pass_and_digest_refix_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir170_path = _prepare_ir170(base)

    out = run_ir171_175_batch_dryrun(
        base_path=base,
        source_task_id="ir173_pass",
        ir170_completion_bundle_path=ir170_path,
    )

    ir173 = out["ir173_result"]
    assert ir173["validation_result"] == "PASS"
    assert ir173["tracking_digest_refix"]["entry_count"] > 0
    assert ir173["tracking_digest_refix"]["tracking_digest_refix_ready"] is True


def test_ir174_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir170_path = _prepare_ir170(base)

    out = run_ir171_175_batch_dryrun(
        base_path=base,
        source_task_id="ir174_abort",
        ir170_completion_bundle_path=ir170_path,
    )

    ir173_with_risk = dict(out["ir173_result"])
    ir173_with_risk["safety_gate_snapshot"] = dict(ir173_with_risk["safety_gate_snapshot"])
    ir173_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir174 = run_ir174_dry_run_continuity_attestation(
        ir173_report=ir173_with_risk,
        ir172_report=out["ir172_result"],
        source_task_id="ir174_abort",
    )
    assert ir174["dry_run_continuity_evidence_decision"] == "ABORT"


def test_ir174_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir170_path = _prepare_ir170(base)

    out = run_ir171_175_batch_dryrun(
        base_path=base,
        source_task_id="ir174_pass",
        ir170_completion_bundle_path=ir170_path,
    )

    ir174 = out["ir174_result"]
    assert ir174["validation_result"] == "PASS"
    assert ir174["dry_run_continuity_evidence_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir175_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir170_path = _prepare_ir170(base)

    out = run_ir171_175_batch_dryrun(
        base_path=base,
        source_task_id="ir175_pass",
        ir170_completion_bundle_path=ir170_path,
    )

    result = write_ir171_175_completion_bundle(
        base_path=base,
        ir171_175_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 506, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir175_phase_171_175_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
