import json
from pathlib import Path

from generic_block_ai.app.core_ir76_80_execution_governance_batch import (
    run_ir76_80_batch_dryrun,
    run_ir79_legacy_reference_linkage_verifier,
    write_ir76_80_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir75_payload() -> dict:
    return {
        "schema_version": "ir75_phase_71_75_completion_bundle_v1",
        "phase": "IR75",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir75_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "FROZEN_REFERENCE_ONLY",
        "legacy_cycle_frozen_reference_only": True,
        "completion_table": [
            {"phase": "IR71", "content": "New Cycle Design Approval Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR72", "content": "Cycle Approver Attestation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR73", "content": "Dry-Run Unlock Policy Declaration", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR74", "content": "Legacy Artifact Freeze Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR75", "content": "Phase 71-75 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
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
            "ir75_completion_bundle": "generic_block_ai/reports/ir71_75/ir75_completion_bundle.json",
            "ir71_75_live_status": "generic_block_ai/reports/ir71_75/ir71_75_live_status.md",
            "ir71_75_completion_table": "generic_block_ai/reports/ir71_75/ir71_75_completion_table.md",
        },
    }


def _prepare_ir75(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir71_75" / "ir75_completion_bundle.json"
    _write(target, payload or _base_ir75_payload())
    return target


def test_ir76_pass_for_valid_ir75_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir75_path = _prepare_ir75(base)

    out = run_ir76_80_batch_dryrun(
        base_path=base,
        source_task_id="ir76_pass",
        ir75_completion_bundle_path=ir75_path,
    )

    ir76 = out["ir76_result"]
    assert ir76["validation_result"] == "PASS"
    assert ir76["execution_boundary_policy"]["execution_mode"] == "dry_run_only"
    assert ir76["execution_boundary_policy"]["allow_live_execution"] is False


def test_ir77_pass_and_unlock_blocked(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir75_path = _prepare_ir75(base)

    out = run_ir76_80_batch_dryrun(
        base_path=base,
        source_task_id="ir77_pass",
        ir75_completion_bundle_path=ir75_path,
    )

    ir77 = out["ir77_result"]
    assert ir77["validation_result"] == "PASS"
    assert ir77["precondition_verification"]["verification_result"] == "LOCKED_BY_PRECONDITIONS"
    assert ir77["precondition_verification"]["unlock_blocked"] is True


def test_ir78_pass_scope_registry(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir75_path = _prepare_ir75(base)

    out = run_ir76_80_batch_dryrun(
        base_path=base,
        source_task_id="ir78_pass",
        ir75_completion_bundle_path=ir75_path,
    )

    ir78 = out["ir78_result"]
    assert ir78["validation_result"] == "PASS"
    assert ir78["approval_scope_registry"]["scope_mode"] == "governance_only"
    assert ir78["approval_scope_registry"]["unlock_authority_delegated"] is False


def test_ir79_hold_when_artifacts_empty(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir75_payload()
    payload["artifacts"] = {}
    ir75_path = _prepare_ir75(base, payload)

    out = run_ir76_80_batch_dryrun(
        base_path=base,
        source_task_id="ir79_hold",
        ir75_completion_bundle_path=ir75_path,
    )

    ir79 = out["ir79_result"]
    assert ir79["validation_result"] == "FAIL"
    assert ir79["legacy_reference_linkage_decision"] == "HOLD"


def test_ir79_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir75_path = _prepare_ir75(base)

    out = run_ir76_80_batch_dryrun(
        base_path=base,
        source_task_id="ir79_abort",
        ir75_completion_bundle_path=ir75_path,
    )

    ir78_with_risk = dict(out["ir78_result"])
    ir78_with_risk["safety_gate_snapshot"] = dict(ir78_with_risk["safety_gate_snapshot"])
    ir78_with_risk["safety_gate_snapshot"]["execution_policy_execute"] = True

    ir79 = run_ir79_legacy_reference_linkage_verifier(
        ir75_report=json.loads(ir75_path.read_text(encoding="utf-8")),
        ir78_report=ir78_with_risk,
        source_task_id="ir79_abort",
    )
    assert ir79["legacy_reference_linkage_decision"] == "ABORT"


def test_ir80_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir75_path = _prepare_ir75(base)

    out = run_ir76_80_batch_dryrun(
        base_path=base,
        source_task_id="ir80_pass",
        ir75_completion_bundle_path=ir75_path,
    )

    result = write_ir76_80_completion_bundle(
        base_path=base,
        ir76_80_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 30, "failed": 0},
        scoped_regression={"passed": 392, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir80_phase_76_80_completion_bundle_v1"
    assert report["final_decision"] == "GOVERNANCE_READY_DRY_RUN_ONLY"
    assert report["governance_ready_dry_run_only"] is True
    assert report["safety_gate_summary"]["external_write_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
