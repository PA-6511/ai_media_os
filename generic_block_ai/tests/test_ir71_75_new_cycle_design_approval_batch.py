import json
from pathlib import Path

from generic_block_ai.app.core_ir71_75_new_cycle_design_approval_batch import (
    run_ir71_75_batch_dryrun,
    run_ir71_new_cycle_design_gate,
    run_ir74_legacy_artifact_freeze_registry,
    write_ir71_75_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir70_payload() -> dict:
    return {
        "schema_version": "ir70_phase_66_70_completion_bundle_v1",
        "phase": "IR70",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir70_fixture",
        "final_decision": "NO_GO_LOCKED_DRY_RUN_ONLY",
        "no_go_lock_confirmed": True,
        "completion_table": [
            {"phase": "IR66", "content": "Final DRY_RUN Comprehensive Auditor", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR67", "content": "Pre-Operational Transition Reviewer", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR68", "content": "NO-GO Lock Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR69", "content": "Next-Phase Design Package Assembler", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR70", "content": "Phase 66-70 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
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
            "ir70_completion_bundle": "generic_block_ai/reports/ir66_70/ir70_completion_bundle.json",
            "ir66_70_live_status": "generic_block_ai/reports/ir66_70/ir66_70_live_status.md",
            "ir66_70_completion_table": "generic_block_ai/reports/ir66_70/ir66_70_completion_table.md",
        },
    }


def _prepare_ir70(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir66_70" / "ir70_completion_bundle.json"
    _write(target, payload or _base_ir70_payload())
    return target


def test_ir71_pass_for_valid_ir70_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir70_path = _prepare_ir70(base)
    ir70 = json.loads(ir70_path.read_text(encoding="utf-8"))

    ir71 = run_ir71_new_cycle_design_gate(
        ir70_completion_bundle=ir70,
        source_task_id="ir71_ok",
        new_cycle_id="IR71_PLUS_CYCLE_A",
        design_owner="design_owner_a",
    )

    assert ir71["validation_result"] == "PASS"
    assert ir71["new_cycle_design_gate_decision"] == "NEW_CYCLE_DESIGN_APPROVED"


def test_ir71_hold_if_prior_cycle_not_locked(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir70_payload()
    payload["no_go_lock_confirmed"] = False
    ir70_path = _prepare_ir70(base, payload)
    ir70 = json.loads(ir70_path.read_text(encoding="utf-8"))

    ir71 = run_ir71_new_cycle_design_gate(
        ir70_completion_bundle=ir70,
        source_task_id="ir71_hold",
        new_cycle_id="IR71_PLUS_CYCLE_A",
        design_owner="design_owner_a",
    )

    assert ir71["validation_result"] == "FAIL"
    assert ir71["new_cycle_design_gate_decision"] == "HOLD"


def test_ir72_ir73_pass_in_batch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir70_path = _prepare_ir70(base)

    out = run_ir71_75_batch_dryrun(
        base_path=base,
        source_task_id="ir72_73_ok",
        new_cycle_id="IR71_PLUS_CYCLE_A",
        design_owner="design_owner_a",
        approver="approver_a",
        ir70_completion_bundle_path=ir70_path,
    )

    assert out["ir72_result"]["validation_result"] == "PASS"
    assert out["ir73_result"]["validation_result"] == "PASS"
    assert out["ir73_result"]["policy_declaration"]["execution_unlock_blocked_by_default"] is True


def test_ir74_freeze_registry_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir70_path = _prepare_ir70(base)

    out = run_ir71_75_batch_dryrun(
        base_path=base,
        source_task_id="ir74_ok",
        new_cycle_id="IR71_PLUS_CYCLE_A",
        design_owner="design_owner_a",
        approver="approver_a",
        ir70_completion_bundle_path=ir70_path,
    )

    ir74 = out["ir74_result"]
    assert ir74["validation_result"] == "PASS"
    assert ir74["legacy_artifact_freeze_decision"] == "FROZEN_REFERENCE_ONLY"
    assert ir74["freeze_registry"]["freeze_scope"] == "reference_only"


def test_ir74_hold_when_artifacts_empty(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir70_payload = _base_ir70_payload()
    ir70_payload["artifacts"] = {}
    ir70_path = _prepare_ir70(base, ir70_payload)

    out = run_ir71_75_batch_dryrun(
        base_path=base,
        source_task_id="ir74_hold",
        new_cycle_id="IR71_PLUS_CYCLE_A",
        design_owner="design_owner_a",
        approver="approver_a",
        ir70_completion_bundle_path=ir70_path,
    )

    ir74 = run_ir74_legacy_artifact_freeze_registry(
        ir70_completion_bundle=json.loads(ir70_path.read_text(encoding="utf-8")),
        ir73_policy_report=out["ir73_result"],
        source_task_id="ir74_hold",
    )
    assert ir74["validation_result"] == "FAIL"
    assert ir74["legacy_artifact_freeze_decision"] == "HOLD"


def test_ir75_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir70_path = _prepare_ir70(base)

    out = run_ir71_75_batch_dryrun(
        base_path=base,
        source_task_id="ir75_ok",
        new_cycle_id="IR71_PLUS_CYCLE_A",
        design_owner="design_owner_a",
        approver="approver_a",
        ir70_completion_bundle_path=ir70_path,
    )

    result = write_ir71_75_completion_bundle(
        base_path=base,
        ir71_75_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 24, "failed": 0},
        scoped_regression={"passed": 386, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir75_phase_71_75_completion_bundle_v1"
    assert report["final_decision"] == "FROZEN_REFERENCE_ONLY"
    assert report["legacy_cycle_frozen_reference_only"] is True
    assert report["safety_gate_summary"]["execution_policy_execute"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
