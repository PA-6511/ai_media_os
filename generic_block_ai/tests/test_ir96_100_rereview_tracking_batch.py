import json
from pathlib import Path

from generic_block_ai.app.core_ir96_100_rereview_tracking_batch import (
    run_ir96_100_batch_dryrun,
    run_ir99_unlock_prohibition_reconfirmation_gate,
    write_ir96_100_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir95_payload() -> dict:
    return {
        "schema_version": "ir95_phase_91_95_completion_bundle_v1",
        "phase": "IR95",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir95_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "UNLOCK_PROHIBITION_CONTINUED_DRY_RUN_ONLY",
        "unlock_prohibition_continuity_confirmed": True,
        "ir91_result": {
            "gap_remediation_plan": {
                "all_items_completed": False,
            }
        },
        "ir93_result": {
            "re_review_queue_registry": {
                "queue_entries": [
                    {"queue_item_id": "queue_1", "item": "go_decision_document", "status": "QUEUED"},
                    {"queue_item_id": "queue_2", "item": "release_approver_signature", "status": "QUEUED"},
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
            "ir95_completion_bundle": "generic_block_ai/reports/ir91_95/ir95_completion_bundle.json",
            "ir91_95_live_status": "generic_block_ai/reports/ir91_95/ir91_95_live_status.md",
            "ir91_95_completion_table": "generic_block_ai/reports/ir91_95/ir91_95_completion_table.md",
        },
    }


def _prepare_ir95(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir91_95" / "ir95_completion_bundle.json"
    _write(target, payload or _base_ir95_payload())
    return target


def test_ir96_pass_for_valid_ir95_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir95_path = _prepare_ir95(base)

    out = run_ir96_100_batch_dryrun(
        base_path=base,
        source_task_id="ir96_pass",
        ir95_completion_bundle_path=ir95_path,
    )

    ir96 = out["ir96_result"]
    assert ir96["validation_result"] == "PASS"
    assert ir96["re_review_execution_tracker"]["tracked_count"] > 0


def test_ir97_pass_with_not_received_intake(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir95_path = _prepare_ir95(base)

    out = run_ir96_100_batch_dryrun(
        base_path=base,
        source_task_id="ir97_pass",
        ir95_completion_bundle_path=ir95_path,
    )

    ir97 = out["ir97_result"]
    assert ir97["validation_result"] == "PASS"
    assert ir97["evidence_intake_verification"]["all_required_evidence_received"] is False


def test_ir98_pass_and_delta_remains(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir95_path = _prepare_ir95(base)

    out = run_ir96_100_batch_dryrun(
        base_path=base,
        source_task_id="ir98_pass",
        ir95_completion_bundle_path=ir95_path,
    )

    ir98 = out["ir98_result"]
    assert ir98["validation_result"] == "PASS"
    assert ir98["pre_unlock_delta_audit"]["pre_unlock_delta_status"] == "DELTA_REMAINS"
    assert ir98["pre_unlock_delta_audit"]["unlock_recommended"] is False


def test_ir99_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir95_path = _prepare_ir95(base)

    out = run_ir96_100_batch_dryrun(
        base_path=base,
        source_task_id="ir99_abort",
        ir95_completion_bundle_path=ir95_path,
    )

    ir98_with_risk = dict(out["ir98_result"])
    ir98_with_risk["safety_gate_snapshot"] = dict(ir98_with_risk["safety_gate_snapshot"])
    ir98_with_risk["safety_gate_snapshot"]["production_release"] = True

    ir99 = run_ir99_unlock_prohibition_reconfirmation_gate(
        ir98_report=ir98_with_risk,
        ir97_report=out["ir97_result"],
        source_task_id="ir99_abort",
    )
    assert ir99["unlock_prohibition_reconfirmation_decision"] == "ABORT"


def test_ir99_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir95_path = _prepare_ir95(base)

    out = run_ir96_100_batch_dryrun(
        base_path=base,
        source_task_id="ir99_pass",
        ir95_completion_bundle_path=ir95_path,
    )

    ir99 = out["ir99_result"]
    assert ir99["validation_result"] == "PASS"
    assert ir99["unlock_prohibition_reconfirmation_decision"] == "UNLOCK_PROHIBITION_RECONFIRMED_DRY_RUN_ONLY"


def test_ir100_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir95_path = _prepare_ir95(base)

    out = run_ir96_100_batch_dryrun(
        base_path=base,
        source_task_id="ir100_pass",
        ir95_completion_bundle_path=ir95_path,
    )

    result = write_ir96_100_completion_bundle(
        base_path=base,
        ir96_100_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 54, "failed": 0},
        scoped_regression={"passed": 416, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir100_phase_96_100_completion_bundle_v1"
    assert report["final_decision"] == "UNLOCK_PROHIBITION_RECONFIRMED_DRY_RUN_ONLY"
    assert report["unlock_prohibition_reconfirmed"] is True
    assert report["pre_unlock_delta_still_remains"] is True
    assert report["safety_gate_summary"]["external_write_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
