import json
from pathlib import Path

from generic_block_ai.app.core_ir86_90_preop_governance_batch import (
    run_ir86_90_batch_dryrun,
    run_ir88_exception_request_prohibition_gate,
    write_ir86_90_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir85_payload() -> dict:
    return {
        "schema_version": "ir85_phase_81_85_completion_bundle_v1",
        "phase": "IR85",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir85_fixture",
        "new_cycle_id": "IR71_PLUS_CYCLE_A",
        "final_decision": "UNLOCK_PROHIBITION_CONFIRMED_DRY_RUN_ONLY",
        "unlock_prohibition_confirmed": True,
        "ir81_result": {
            "unlock_preconditions_ledger": {
                "unlock_preconditions": [
                    {"item": "explicit_go_decision_recorded", "required": True, "satisfied": False},
                    {"item": "named_release_approver_recorded", "required": True, "satisfied": False},
                    {"item": "safety_gate_redeclaration_completed", "required": True, "satisfied": False},
                    {"item": "full_test_matrix_reexecuted", "required": True, "satisfied": False},
                    {"item": "external_execution_authorized", "required": True, "satisfied": False},
                ]
            }
        },
        "ir82_result": {
            "approval_evidence_record": {
                "evidence_entries": [
                    {"evidence_type": "go_decision_document", "present": False, "reference": "PENDING"},
                    {"evidence_type": "release_approver_signature", "present": False, "reference": "PENDING"},
                    {"evidence_type": "safety_redeclaration_record", "present": False, "reference": "PENDING"},
                    {"evidence_type": "full_test_matrix_record", "present": False, "reference": "PENDING"},
                    {"evidence_type": "execution_authorization_record", "present": False, "reference": "PENDING"},
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
            "ir85_completion_bundle": "generic_block_ai/reports/ir81_85/ir85_completion_bundle.json",
            "ir81_85_live_status": "generic_block_ai/reports/ir81_85/ir81_85_live_status.md",
            "ir81_85_completion_table": "generic_block_ai/reports/ir81_85/ir81_85_completion_table.md",
        },
    }


def _prepare_ir85(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir81_85" / "ir85_completion_bundle.json"
    _write(target, payload or _base_ir85_payload())
    return target


def test_ir86_pass_for_valid_ir85_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir85_path = _prepare_ir85(base)

    out = run_ir86_90_batch_dryrun(
        base_path=base,
        source_task_id="ir86_pass",
        ir85_completion_bundle_path=ir85_path,
    )

    ir86 = out["ir86_result"]
    assert ir86["validation_result"] == "PASS"
    assert ir86["pre_operational_audit_review"]["unlock_state"] == "PROHIBITED"


def test_ir87_pass_and_gap_remains(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir85_path = _prepare_ir85(base)

    out = run_ir86_90_batch_dryrun(
        base_path=base,
        source_task_id="ir87_pass",
        ir85_completion_bundle_path=ir85_path,
    )

    ir87 = out["ir87_result"]
    assert ir87["validation_result"] == "PASS"
    assert ir87["approval_delta_analysis"]["approval_delta_status"] == "GAP_REMAINS"
    assert ir87["approval_delta_analysis"]["unlock_eligible"] is False


def test_ir88_confirmed_in_normal_path(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir85_path = _prepare_ir85(base)

    out = run_ir86_90_batch_dryrun(
        base_path=base,
        source_task_id="ir88_pass",
        ir85_completion_bundle_path=ir85_path,
    )

    ir88 = out["ir88_result"]
    assert ir88["validation_result"] == "PASS"
    assert ir88["exception_request_gate_decision"] == "UNLOCK_EXCEPTION_PROHIBITED_DRY_RUN_ONLY"


def test_ir88_abort_when_external_flag_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir85_path = _prepare_ir85(base)

    out = run_ir86_90_batch_dryrun(
        base_path=base,
        source_task_id="ir88_abort",
        ir85_completion_bundle_path=ir85_path,
    )

    ir87_with_risk = dict(out["ir87_result"])
    ir87_with_risk["safety_gate_snapshot"] = dict(ir87_with_risk["safety_gate_snapshot"])
    ir87_with_risk["safety_gate_snapshot"]["execution_policy_execute"] = True

    ir88 = run_ir88_exception_request_prohibition_gate(
        ir87_report=ir87_with_risk,
        source_task_id="ir88_abort",
    )
    assert ir88["exception_request_gate_decision"] == "ABORT"


def test_ir89_pass_candidate_package(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir85_path = _prepare_ir85(base)

    out = run_ir86_90_batch_dryrun(
        base_path=base,
        source_task_id="ir89_pass",
        ir85_completion_bundle_path=ir85_path,
    )

    ir89 = out["ir89_result"]
    assert ir89["validation_result"] == "PASS"
    assert ir89["final_transition_candidate_package"]["unlock_included"] is False
    assert ir89["final_transition_candidate_package"]["production_release_included"] is False


def test_ir90_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir85_path = _prepare_ir85(base)

    out = run_ir86_90_batch_dryrun(
        base_path=base,
        source_task_id="ir90_pass",
        ir85_completion_bundle_path=ir85_path,
    )

    result = write_ir86_90_completion_bundle(
        base_path=base,
        ir86_90_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 42, "failed": 0},
        scoped_regression={"passed": 404, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir90_phase_86_90_completion_bundle_v1"
    assert report["final_decision"] == "UNLOCK_EXCEPTION_PROHIBITED_DRY_RUN_ONLY"
    assert report["unlock_exception_prohibited_confirmed"] is True
    assert report["transition_candidate_package_prepared"] is True
    assert report["safety_gate_summary"]["execution_policy_execute"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
