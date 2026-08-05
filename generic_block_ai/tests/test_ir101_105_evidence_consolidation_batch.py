import json
from pathlib import Path

from generic_block_ai.app.core_ir101_105_evidence_consolidation_batch import (
    run_ir101_105_batch_dryrun,
    run_ir104_prohibition_cycle_continuation_gate,
    write_ir101_105_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir100_payload() -> dict:
    return {
        "schema_version": "ir100_phase_96_100_completion_bundle_v1",
        "phase": "IR100",
        "generated_at": "2026-05-25T04:00:00+00:00",
        "source_task_id": "ir100_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "UNLOCK_PROHIBITION_RECONFIRMED_DRY_RUN_ONLY",
        "unlock_prohibition_reconfirmed": True,
        "pre_unlock_delta_still_remains": True,
        "ir97_result": {
            "evidence_intake_verification": {
                "intake_entries": [
                    {"queue_item_id": "queue_1", "item": "go_decision_document", "evidence_intake_status": "NOT_RECEIVED", "verified": False},
                    {"queue_item_id": "queue_2", "item": "release_approver_signature", "evidence_intake_status": "NOT_RECEIVED", "verified": False},
                    {"queue_item_id": "queue_3", "item": "safety_redeclaration_record", "evidence_intake_status": "NOT_RECEIVED", "verified": False},
                ],
                "all_required_evidence_received": False,
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
            "ir100_completion_bundle": "generic_block_ai/reports/ir96_100/ir100_completion_bundle.json",
            "ir96_100_live_status": "generic_block_ai/reports/ir96_100/ir96_100_live_status.md",
            "ir96_100_completion_table": "generic_block_ai/reports/ir96_100/ir96_100_completion_table.md",
        },
    }


def _prepare_ir100(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir96_100" / "ir100_completion_bundle.json"
    _write(target, payload or _base_ir100_payload())
    return target


def test_ir101_pass_for_valid_ir100_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir100_path = _prepare_ir100(base)

    out = run_ir101_105_batch_dryrun(
        base_path=base,
        source_task_id="ir101_pass",
        ir100_completion_bundle_path=ir100_path,
    )

    ir101 = out["ir101_result"]
    assert ir101["validation_result"] == "PASS"
    assert ir101["evidence_consolidation_status"]["consolidated_count"] > 0
    assert ir101["evidence_consolidation_status"]["all_evidence_consolidated"] is False


def test_ir102_pass_and_deltas_open(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir100_path = _prepare_ir100(base)

    out = run_ir101_105_batch_dryrun(
        base_path=base,
        source_task_id="ir102_pass",
        ir100_completion_bundle_path=ir100_path,
    )

    ir102 = out["ir102_result"]
    assert ir102["validation_result"] == "PASS"
    assert ir102["remediation_delta_progress"]["open_delta_count"] > 0
    assert ir102["remediation_delta_progress"]["all_deltas_closed"] is False
    assert ir102["remediation_delta_progress"]["unlock_eligible"] is False


def test_ir103_pass_and_next_cycle_recommended(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir100_path = _prepare_ir100(base)

    out = run_ir101_105_batch_dryrun(
        base_path=base,
        source_task_id="ir103_pass",
        ir100_completion_bundle_path=ir100_path,
    )

    ir103 = out["ir103_result"]
    assert ir103["validation_result"] == "PASS"
    assert ir103["re_review_cycle_assessment"]["cycle_status"] == "CYCLE_IN_PROGRESS"
    assert ir103["re_review_cycle_assessment"]["next_cycle_recommended"] is True
    assert ir103["re_review_cycle_assessment"]["unlock_eligible"] is False


def test_ir104_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir100_path = _prepare_ir100(base)

    out = run_ir101_105_batch_dryrun(
        base_path=base,
        source_task_id="ir104_abort",
        ir100_completion_bundle_path=ir100_path,
    )

    ir103_with_risk = dict(out["ir103_result"])
    ir103_with_risk["safety_gate_snapshot"] = dict(ir103_with_risk["safety_gate_snapshot"])
    ir103_with_risk["safety_gate_snapshot"]["production_release"] = True

    ir104 = run_ir104_prohibition_cycle_continuation_gate(
        ir103_report=ir103_with_risk,
        ir102_report=out["ir102_result"],
        source_task_id="ir104_abort",
    )
    assert ir104["prohibition_cycle_continuation_decision"] == "ABORT"


def test_ir104_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir100_path = _prepare_ir100(base)

    out = run_ir101_105_batch_dryrun(
        base_path=base,
        source_task_id="ir104_pass",
        ir100_completion_bundle_path=ir100_path,
    )

    ir104 = out["ir104_result"]
    assert ir104["validation_result"] == "PASS"
    assert ir104["prohibition_cycle_continuation_decision"] == "PROHIBITION_CYCLE_CONTINUED_DRY_RUN_ONLY"


def test_ir105_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir100_path = _prepare_ir100(base)

    out = run_ir101_105_batch_dryrun(
        base_path=base,
        source_task_id="ir105_pass",
        ir100_completion_bundle_path=ir100_path,
    )

    result = write_ir101_105_completion_bundle(
        base_path=base,
        ir101_105_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 60, "failed": 0},
        scoped_regression={"passed": 422, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir105_phase_101_105_completion_bundle_v1"
    assert report["final_decision"] == "PROHIBITION_CYCLE_CONTINUED_DRY_RUN_ONLY"
    assert report["prohibition_cycle_continued"] is True
    assert report["evidence_consolidation_pending"] is True
    assert report["safety_gate_summary"]["external_write_executed"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
