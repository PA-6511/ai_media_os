import json
from pathlib import Path

from generic_block_ai.app.core_ir91_95_gap_remediation_batch import (
    run_ir91_95_batch_dryrun,
    run_ir94_unlock_prohibition_continuity_gate,
    write_ir91_95_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir90_payload() -> dict:
    return {
        "schema_version": "ir90_phase_86_90_completion_bundle_v1",
        "phase": "IR90",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir90_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "UNLOCK_EXCEPTION_PROHIBITED_DRY_RUN_ONLY",
        "unlock_exception_prohibited_confirmed": True,
        "ir87_result": {
            "approval_delta_analysis": {
                "approval_delta_status": "GAP_REMAINS",
                "unlock_eligible": False,
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
            "ir90_completion_bundle": "generic_block_ai/reports/ir86_90/ir90_completion_bundle.json",
            "ir86_90_live_status": "generic_block_ai/reports/ir86_90/ir86_90_live_status.md",
            "ir86_90_completion_table": "generic_block_ai/reports/ir86_90/ir86_90_completion_table.md",
        },
    }


def _prepare_ir90(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir86_90" / "ir90_completion_bundle.json"
    _write(target, payload or _base_ir90_payload())
    return target


def test_ir91_pass_for_valid_ir90_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir90_path = _prepare_ir90(base)

    out = run_ir91_95_batch_dryrun(
        base_path=base,
        source_task_id="ir91_pass",
        ir90_completion_bundle_path=ir90_path,
    )

    ir91 = out["ir91_result"]
    assert ir91["validation_result"] == "PASS"
    assert ir91["gap_remediation_plan"]["all_items_planned"] is True
    assert ir91["gap_remediation_plan"]["all_items_completed"] is False


def test_ir92_pass_and_ready_for_re_review(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir90_path = _prepare_ir90(base)

    out = run_ir91_95_batch_dryrun(
        base_path=base,
        source_task_id="ir92_pass",
        ir90_completion_bundle_path=ir90_path,
    )

    ir92 = out["ir92_result"]
    assert ir92["validation_result"] == "PASS"
    assert ir92["approval_delta_correction_proposal"]["ready_for_re_review"] is True


def test_ir93_pass_and_queue_prepared(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir90_path = _prepare_ir90(base)

    out = run_ir91_95_batch_dryrun(
        base_path=base,
        source_task_id="ir93_pass",
        ir90_completion_bundle_path=ir90_path,
    )

    ir93 = out["ir93_result"]
    assert ir93["validation_result"] == "PASS"
    assert ir93["re_review_queue_registry"]["queue_size"] > 0


def test_ir94_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir90_path = _prepare_ir90(base)

    out = run_ir91_95_batch_dryrun(
        base_path=base,
        source_task_id="ir94_abort",
        ir90_completion_bundle_path=ir90_path,
    )

    ir93_with_risk = dict(out["ir93_result"])
    ir93_with_risk["safety_gate_snapshot"] = dict(ir93_with_risk["safety_gate_snapshot"])
    ir93_with_risk["safety_gate_snapshot"]["external_write_executed"] = True

    ir94 = run_ir94_unlock_prohibition_continuity_gate(
        ir93_report=ir93_with_risk,
        ir92_report=out["ir92_result"],
        source_task_id="ir94_abort",
    )
    assert ir94["unlock_prohibition_continuity_decision"] == "ABORT"


def test_ir94_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir90_path = _prepare_ir90(base)

    out = run_ir91_95_batch_dryrun(
        base_path=base,
        source_task_id="ir94_pass",
        ir90_completion_bundle_path=ir90_path,
    )

    ir94 = out["ir94_result"]
    assert ir94["validation_result"] == "PASS"
    assert ir94["unlock_prohibition_continuity_decision"] == "UNLOCK_PROHIBITION_CONTINUED_DRY_RUN_ONLY"


def test_ir95_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir90_path = _prepare_ir90(base)

    out = run_ir91_95_batch_dryrun(
        base_path=base,
        source_task_id="ir95_pass",
        ir90_completion_bundle_path=ir90_path,
    )

    result = write_ir91_95_completion_bundle(
        base_path=base,
        ir91_95_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 48, "failed": 0},
        scoped_regression={"passed": 410, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir95_phase_91_95_completion_bundle_v1"
    assert report["final_decision"] == "UNLOCK_PROHIBITION_CONTINUED_DRY_RUN_ONLY"
    assert report["unlock_prohibition_continuity_confirmed"] is True
    assert report["re_review_queue_prepared"] is True
    assert report["safety_gate_summary"]["network_transmission_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
