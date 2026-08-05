import json
from pathlib import Path

from generic_block_ai.app.core_ir186_190_retention_refix_audit_terminal_batch import (
    run_ir186_190_batch_dryrun,
    run_ir189_dry_run_terminal_audit_attestation,
    write_ir186_190_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir185_payload() -> dict:
    return {
        "schema_version": "ir185_phase_181_185_completion_bundle_v1",
        "phase": "IR185",
        "generated_at": "2026-05-26T03:00:00+00:00",
        "source_task_id": "ir185_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY",
        "prohibition_continuity_finalized": True,
        "delta_closure_pending": True,
        "completion_table": [
            {"phase": "IR181", "content": "Timeline Retention Audit Snapshot", "judgement": "完了"},
            {"phase": "IR182", "content": "Post-Terminal Reference Consistency Registry", "judgement": "完了"},
            {"phase": "IR183", "content": "Consistency Digest Refix", "judgement": "完了"},
            {"phase": "IR184", "content": "Dry-Run Retention Consistency Attestation", "judgement": "完了"},
            {"phase": "IR185", "content": "Phase 181-185 Completion Bundle", "judgement": "完了"},
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
            "ir185_completion_bundle": "generic_block_ai/reports/ir181_185/ir185_completion_bundle.json",
            "ir181_185_live_status": "generic_block_ai/reports/ir181_185/ir181_185_live_status.md",
            "ir181_185_completion_table": "generic_block_ai/reports/ir181_185/ir181_185_completion_table.md",
        },
    }


def _prepare_ir185(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir181_185" / "ir185_completion_bundle.json"
    _write(target, payload or _base_ir185_payload())
    return target


def test_ir186_pass_for_valid_ir185_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir185_path = _prepare_ir185(base)

    out = run_ir186_190_batch_dryrun(
        base_path=base,
        source_task_id="ir186_pass",
        ir185_completion_bundle_path=ir185_path,
    )

    ir186 = out["ir186_result"]
    assert ir186["validation_result"] == "PASS"
    assert ir186["retention_refix_evidence_snapshot"]["entry_count"] > 0
    assert ir186["retention_refix_evidence_snapshot"]["retention_refix_ready"] is True


def test_ir187_pass_and_terminal_reference_consistent(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir185_path = _prepare_ir185(base)

    out = run_ir186_190_batch_dryrun(
        base_path=base,
        source_task_id="ir187_pass",
        ir185_completion_bundle_path=ir185_path,
    )

    ir187 = out["ir187_result"]
    assert ir187["validation_result"] == "PASS"
    assert ir187["reference_consistency_terminal_registry"]["entry_count"] > 0
    assert ir187["reference_consistency_terminal_registry"]["all_terminal_consistent_reference_only"] is True


def test_ir188_pass_and_terminal_digest_ready(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir185_path = _prepare_ir185(base)

    out = run_ir186_190_batch_dryrun(
        base_path=base,
        source_task_id="ir188_pass",
        ir185_completion_bundle_path=ir185_path,
    )

    ir188 = out["ir188_result"]
    assert ir188["validation_result"] == "PASS"
    assert ir188["terminal_digest_refix"]["entry_count"] > 0
    assert ir188["terminal_digest_refix"]["terminal_digest_refix_ready"] is True


def test_ir189_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir185_path = _prepare_ir185(base)

    out = run_ir186_190_batch_dryrun(
        base_path=base,
        source_task_id="ir189_abort",
        ir185_completion_bundle_path=ir185_path,
    )

    ir188_with_risk = dict(out["ir188_result"])
    ir188_with_risk["safety_gate_snapshot"] = dict(ir188_with_risk["safety_gate_snapshot"])
    ir188_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir189 = run_ir189_dry_run_terminal_audit_attestation(
        ir188_report=ir188_with_risk,
        ir187_report=out["ir187_result"],
        source_task_id="ir189_abort",
    )
    assert ir189["dry_run_terminal_audit_attestation_decision"] == "ABORT"


def test_ir189_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir185_path = _prepare_ir185(base)

    out = run_ir186_190_batch_dryrun(
        base_path=base,
        source_task_id="ir189_pass",
        ir185_completion_bundle_path=ir185_path,
    )

    ir189 = out["ir189_result"]
    assert ir189["validation_result"] == "PASS"
    assert ir189["dry_run_terminal_audit_attestation_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"


def test_ir190_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir185_path = _prepare_ir185(base)

    out = run_ir186_190_batch_dryrun(
        base_path=base,
        source_task_id="ir190_pass",
        ir185_completion_bundle_path=ir185_path,
    )

    result = write_ir186_190_completion_bundle(
        base_path=base,
        ir186_190_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 524, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir190_phase_186_190_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
    assert report["prohibition_continuity_finalized"] is True
    assert report["delta_closure_pending"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
