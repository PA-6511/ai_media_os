import json
from pathlib import Path

from generic_block_ai.app.affiliate_integration_trial import (
    build_ir10_core_phase_decision_package,
    run_ir10_phase_decision_package_dryrun,
    write_ir10_completion_report,
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
                            "quality_score": 88,
                            "risk_weight_total": 12,
                            "risk_flags": [],
                            "review_required": False,
                            "blocked_reason": None,
                            "decision": "PASS",
                        },
                        {
                            "index": 1,
                            "quality_score": 65,
                            "risk_weight_total": 35,
                            "risk_flags": ["price_volatility"],
                            "review_required": True,
                            "blocked_reason": None,
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


def test_build_ir10_core_phase_decision_package_maps_warn() -> None:
    output = build_ir10_core_phase_decision_package(
        roundtrip_output=_roundtrip_output_with_judgment("WARN"),
        source_task_id="ir10_map_warn",
    )
    assert output["schema_version"] == "ir10_core_phase_decision_v1"
    assert output["quality_gate_judgment"] == "WARN"
    assert output["mapping_rule"]["recommended_decision"] == "REQUIRE_HUMAN_REVIEW"
    assert output["mapping_rule"]["core_receive_rule"] == "HUMAN_REVIEW_REQUIRED"
    assert output["validation_result"] in {"PASS", "WARN"}


def test_run_ir10_phase_decision_package_dryrun_warn_creates_human_review(tmp_path: Path) -> None:
    ir10 = run_ir10_phase_decision_package_dryrun(
        base_path=tmp_path,
        source_task_id="ir10_warn",
        roundtrip_output=_roundtrip_output_with_judgment("WARN"),
    )
    assert Path(ir10["path"]).exists()
    assert ir10["human_review_package_path"] is not None
    assert Path(ir10["human_review_package_path"]).exists()
    assert ir10["abort_evidence_bundle_path"] is None



def test_run_ir10_phase_decision_package_dryrun_abort_creates_evidence_bundle(tmp_path: Path) -> None:
    ir10 = run_ir10_phase_decision_package_dryrun(
        base_path=tmp_path,
        source_task_id="ir10_abort",
        roundtrip_output=_roundtrip_output_with_judgment("ABORT"),
    )
    assert Path(ir10["path"]).exists()
    assert ir10["abort_evidence_bundle_path"] is not None
    assert Path(ir10["abort_evidence_bundle_path"]).exists()



def test_write_ir10_completion_report(tmp_path: Path) -> None:
    ir10 = run_ir10_phase_decision_package_dryrun(
        base_path=tmp_path,
        source_task_id="ir10_complete",
        roundtrip_output=_roundtrip_output_with_judgment("PASS"),
    )
    completion = write_ir10_completion_report(
        base_path=tmp_path,
        ir10_output=ir10,
        focused_tests={"passed": 12, "failed": 0},
        full_regression={"passed": 126, "failed": 0},
    )
    assert completion["external_write_executed"] is False
    path = Path(completion["path"])
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 10"
    assert loaded["status"] == "COMPLETED"
    assert loaded["core_receive_rule"] == "ACCEPT_DRY_RUN_REVIEW_QUEUE"
