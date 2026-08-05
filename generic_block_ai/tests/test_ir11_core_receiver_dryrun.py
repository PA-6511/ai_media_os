import json
from pathlib import Path

from generic_block_ai.app.affiliate_integration_trial import run_ir10_phase_decision_package_dryrun
from generic_block_ai.app.core_ai_receiver_dryrun import (
    run_ir11_core_receiver_dryrun,
    validate_ir10_phase_decision_package_for_core,
    write_ir11_completion_report,
)


def _roundtrip_output_with_judgment(judgment: str) -> dict:
    return {
        "path": f"generic_block_ai/reports/ir9_roundtrip_{judgment.lower()}.json",
        "roundtrip_result": {
            "quality_gate_judgment": judgment,
            "affiliate": {
                "quality_gate": {
                    "status": judgment,
                    "summary": {
                        "overall_status": judgment,
                        "candidate_count": 2,
                        "pass_count": 1 if judgment in {"PASS", "WARN"} else 0,
                        "warn_count": 1 if judgment == "WARN" else 0,
                        "fail_count": 1 if judgment == "FAIL" else 0,
                        "abort_count": 1 if judgment == "ABORT" else 0,
                    },
                    "items": [
                        {
                            "index": 0,
                            "quality_score": 90,
                            "risk_weight_total": 10,
                            "risk_flags": [],
                            "review_required": False,
                            "blocked_reason": None,
                            "decision": "PASS",
                        },
                        {
                            "index": 1,
                            "quality_score": 64,
                            "risk_weight_total": 36,
                            "risk_flags": ["price_volatility"],
                            "review_required": True,
                            "blocked_reason": "policy_violation" if judgment == "ABORT" else None,
                            "decision": judgment if judgment in {"WARN", "FAIL", "ABORT"} else "PASS",
                        },
                    ],
                    "warnings": [],
                }
            },
            "safeguards": {
                "mode": "dry_run",
                "operation_mode": "OBSERVE",
                "external_write_executed": False,
                "actual_auto_execute": False,
                "production_release": False,
            },
        },
    }


def test_validate_ir10_phase_decision_package_for_core_maps_all_judgments(tmp_path: Path) -> None:
    expected_rules = {
        "PASS": "ACCEPT_DRY_RUN_REVIEW_QUEUE",
        "WARN": "HUMAN_REVIEW_REQUIRED",
        "FAIL": "REJECT_AND_KEEP_NO_GO",
        "ABORT": "BLOCK_AND_PRESERVE_AUDIT_EVIDENCE",
    }

    for judgment, expected_rule in expected_rules.items():
        ir10 = run_ir10_phase_decision_package_dryrun(
            base_path=tmp_path,
            source_task_id=f"ir11_map_{judgment.lower()}",
            roundtrip_output=_roundtrip_output_with_judgment(judgment),
        )
        package = ir10["decision_package"]
        result = validate_ir10_phase_decision_package_for_core(
            phase_decision_package=package,
            source_task_id=f"ir11_map_{judgment.lower()}",
        )

        assert result.result in {"PASS", "WARN"}
        assert not result.failed_checks
        assert package["mapping_rule"]["core_receive_rule"] == expected_rule


def test_run_ir11_core_receiver_dryrun_warn_validates_human_review(tmp_path: Path) -> None:
    source_task_id = "ir11_warn_receiver"
    ir10 = run_ir10_phase_decision_package_dryrun(
        base_path=tmp_path,
        source_task_id=source_task_id,
        roundtrip_output=_roundtrip_output_with_judgment("WARN"),
    )

    human_review_package = json.loads(Path(ir10["human_review_package_path"]).read_text(encoding="utf-8"))
    ir11 = run_ir11_core_receiver_dryrun(
        base_path=tmp_path,
        source_task_id=source_task_id,
        phase_decision_package=ir10["decision_package"],
        human_review_package=human_review_package,
    )

    loaded = json.loads(Path(ir11["path"]).read_text(encoding="utf-8"))
    assert loaded["quality_gate_judgment"] == "WARN"
    assert loaded["sub_validations"]["warn_human_review_package"]["result"] in {"PASS", "WARN"}
    assert loaded["validation_result"] in {"PASS", "WARN"}


def test_run_ir11_core_receiver_dryrun_abort_validates_evidence_bundle(tmp_path: Path) -> None:
    source_task_id = "ir11_abort_receiver"
    ir10 = run_ir10_phase_decision_package_dryrun(
        base_path=tmp_path,
        source_task_id=source_task_id,
        roundtrip_output=_roundtrip_output_with_judgment("ABORT"),
    )

    abort_bundle = json.loads(Path(ir10["abort_evidence_bundle_path"]).read_text(encoding="utf-8"))
    ir11 = run_ir11_core_receiver_dryrun(
        base_path=tmp_path,
        source_task_id=source_task_id,
        phase_decision_package=ir10["decision_package"],
        abort_evidence_bundle=abort_bundle,
    )

    loaded = json.loads(Path(ir11["path"]).read_text(encoding="utf-8"))
    assert loaded["quality_gate_judgment"] == "ABORT"
    assert loaded["sub_validations"]["abort_evidence_bundle"]["result"] in {"PASS", "WARN"}
    assert loaded["validation_result"] in {"PASS", "WARN"}


def test_write_ir11_completion_report(tmp_path: Path) -> None:
    source_task_id = "ir11_completion"
    ir10 = run_ir10_phase_decision_package_dryrun(
        base_path=tmp_path,
        source_task_id=source_task_id,
        roundtrip_output=_roundtrip_output_with_judgment("PASS"),
    )
    ir11 = run_ir11_core_receiver_dryrun(
        base_path=tmp_path,
        source_task_id=source_task_id,
        phase_decision_package=ir10["decision_package"],
    )

    completion = write_ir11_completion_report(
        base_path=tmp_path,
        ir11_output=ir11,
        focused_tests={"passed": 9, "failed": 0},
        full_regression={"passed": 130, "failed": 0},
    )

    assert completion["external_write_executed"] is False
    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 11"
    assert loaded["status"] == "COMPLETED"
    assert loaded["test_result"]["focused_tests"]["passed"] == 9
