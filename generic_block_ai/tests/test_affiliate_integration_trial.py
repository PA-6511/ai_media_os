import json
from pathlib import Path

from generic_block_ai.app.affiliate_integration_trial import (
    build_handshake_from_affiliate_runner_result,
    freeze_generated_affiliate_block_package,
    run_generic_affiliate_generic_core_roundtrip_dryrun,
    run_affiliate_generic_core_dryrun_trial,
    write_ir9_completion_report,
    write_ir8_practical_runbook,
    write_ir7_integration_runbook,
)
from generic_block_ai.app.block_skeleton_validator import validate_block_skeleton
from generic_block_ai.app.block_template_builder import write_block_skeleton_dryrun
from generic_block_ai.app.block_template_spec import AFFILIATE_BLOCK_SPEC


REPO_GENERIC_ROOT = Path(__file__).resolve().parent.parent


def _prepare_generated_affiliate(tmp_path: Path) -> None:
    skeleton = write_block_skeleton_dryrun(AFFILIATE_BLOCK_SPEC, base_path=tmp_path)
    validation = validate_block_skeleton(skeleton)
    assert validation.result == "PASS"


def test_freeze_generated_package_ok(tmp_path: Path) -> None:
    _prepare_generated_affiliate(tmp_path)
    output = freeze_generated_affiliate_block_package(base_path=tmp_path)
    assert output["descriptor"]["_meta"]["status"] == "OK"
    assert output["external_write_executed"] is False
    assert Path(output["path"]).exists()


def test_freeze_generated_package_detects_missing_file(tmp_path: Path) -> None:
    _prepare_generated_affiliate(tmp_path)
    runner_path = tmp_path / "reports" / "generated_skeleton_affiliate_block" / "app" / "runner.py"
    runner_path.unlink()
    output = freeze_generated_affiliate_block_package(base_path=tmp_path)
    assert output["descriptor"]["_meta"]["status"] == "ERROR"
    assert "app/runner.py" in output["descriptor"]["package"]["missing_files"]


def test_build_handshake_from_affiliate_runner_result_pass() -> None:
    runner_result = {
        "status": "success",
        "decision": "human_review",
        "summary": "dry-run processed candidates=2, selected=2",
        "recommended_candidates": [{"id": 1}, {"id": 2}],
    }
    output = build_handshake_from_affiliate_runner_result(
        runner_result,
        source_task_id="ir7_t2_test",
    )
    assert output["validation_result"] == "PASS"
    assert output["handshake_package"]["connection_status"] == "HANDSHAKE_READY_DRY_RUN"


def test_build_handshake_from_affiliate_runner_result_pending_review() -> None:
    runner_result = {
        "status": "success",
        "decision": "human_review",
        "summary": "dry-run processed candidates=0, selected=0",
        "recommended_candidates": [],
    }
    output = build_handshake_from_affiliate_runner_result(
        runner_result,
        source_task_id="ir7_t2_test_empty",
    )
    assert output["validation_result"] == "PASS"
    assert output["handshake_package"]["connection_status"] == "HANDSHAKE_PENDING_REVIEW"


def test_three_party_dryrun_trial_ok(tmp_path: Path) -> None:
    _prepare_generated_affiliate(tmp_path)
    output = run_affiliate_generic_core_dryrun_trial(
        base_path=tmp_path,
        source_task_id="ir7_trial_ok",
        affiliate_input_payload={"task_candidates": [{"id": 1}, {"id": 2}, {"id": 3}]},
        generic_runtime_base_path=REPO_GENERIC_ROOT,
        persist_human_review_artifacts=False,
    )
    trial = output["trial_result"]
    assert trial["_meta"]["status"] == "OK"
    assert trial["affiliate_stage"]["runner_to_core_handshake"]["validation_result"] == "PASS"
    assert trial["generic_stage"]["result"]["core_ai_handshake"]["validation_result"] in {"PASS", "WARN"}
    assert output["external_write_executed"] is False
    assert Path(output["path"]).exists()


def test_three_party_dryrun_trial_errors_when_package_not_ready(tmp_path: Path) -> None:
    output = run_affiliate_generic_core_dryrun_trial(
        base_path=tmp_path,
        source_task_id="ir7_trial_error",
        affiliate_input_payload={"task_candidates": []},
        generic_runtime_base_path=REPO_GENERIC_ROOT,
        persist_human_review_artifacts=False,
    )
    assert output["_meta"]["status"] == "ERROR"


def test_write_ir7_integration_runbook(tmp_path: Path) -> None:
    output = write_ir7_integration_runbook(base_path=tmp_path)
    assert output["external_write_executed"] is False
    runbook_path = Path(output["path"])
    assert runbook_path.exists()
    loaded = json.loads(runbook_path.read_text(encoding="utf-8"))
    assert loaded["_meta"]["phase"] == "IR7-T4"
    assert loaded["safeguards"]["mode"] == "dry_run"


def test_ir8_roundtrip_dryrun_ok(tmp_path: Path) -> None:
    _prepare_generated_affiliate(tmp_path)
    records = [
        {
            "source": "official_api",
            "title": "Practical Product A",
            "asin": "B0TEST1001",
            "url": "https://example.com/items/a",
            "campaign_type": "seasonal",
            "risk_flags": [],
        },
        {
            "source": "approved_feed",
            "title": "Practical Product B",
            "asin": "B0TEST1002",
            "url": "https://example.com/items/b",
            "campaign_type": "standard",
            "risk_flags": ["price_volatility"],
        },
    ]
    output = run_generic_affiliate_generic_core_roundtrip_dryrun(
        base_path=tmp_path,
        source_task_id="ir8_roundtrip_ok",
        affiliate_records=records,
        generic_runtime_base_path=REPO_GENERIC_ROOT,
        persist_human_review_artifacts=False,
    )
    result = output["roundtrip_result"]
    assert result["_meta"]["status"] == "OK"
    assert result["input_validation"]["result"] in {"PASS", "WARN"}
    assert result["affiliate"]["candidate_validation"]["result"] in {"PASS", "WARN"}
    assert result["affiliate"]["quality_gate"]["status"] in {"PASS", "WARN", "FAIL", "ABORT"}
    assert result["quality_gate_judgment"] in {"PASS", "WARN", "FAIL", "ABORT"}
    assert result["affiliate"]["runner_to_core_handshake"]["validation_result"] == "PASS"
    assert Path(output["path"]).exists()


def test_ir8_roundtrip_dryrun_fails_on_invalid_input(tmp_path: Path) -> None:
    _prepare_generated_affiliate(tmp_path)
    invalid_records = [{"source": "official_api", "title": "missing fields"}]
    output = run_generic_affiliate_generic_core_roundtrip_dryrun(
        base_path=tmp_path,
        source_task_id="ir8_roundtrip_invalid",
        affiliate_records=invalid_records,
        generic_runtime_base_path=REPO_GENERIC_ROOT,
        persist_human_review_artifacts=False,
    )
    assert output["_meta"]["status"] == "ERROR"
    assert output["_meta"]["reason"] == "invalid_affiliate_input_schema"


def test_write_ir8_practical_runbook(tmp_path: Path) -> None:
    output = write_ir8_practical_runbook(base_path=tmp_path)
    assert output["external_write_executed"] is False
    loaded = json.loads(Path(output["path"]).read_text(encoding="utf-8"))
    assert loaded["_meta"]["phase"] == "IR8-T4"
    assert loaded["safeguards"]["mode"] == "dry_run"


def test_ir9_roundtrip_dryrun_rejects_high_risk_candidate(tmp_path: Path) -> None:
    _prepare_generated_affiliate(tmp_path)
    records = [
        {
            "source": "untrusted_feed",
            "title": "Policy Risk Product",
            "asin": "B0RISK9001",
            "url": "https://example.com/items/risk",
            "campaign_type": "standard",
            "risk_flags": ["policy_violation"],
        }
    ]
    output = run_generic_affiliate_generic_core_roundtrip_dryrun(
        base_path=tmp_path,
        source_task_id="ir9_roundtrip_high_risk",
        affiliate_records=records,
        generic_runtime_base_path=REPO_GENERIC_ROOT,
        persist_human_review_artifacts=False,
    )
    result = output["roundtrip_result"]
    assert result["affiliate"]["quality_gate"]["status"] == "ABORT"
    assert result["quality_gate_judgment"] == "ABORT"
    assert result["post_generic"]["requested_actions_count"] == 0
    assert result["post_generic"]["blocked_candidates_count"] == 1


def test_write_ir9_completion_report(tmp_path: Path) -> None:
    _prepare_generated_affiliate(tmp_path)
    records = [
        {
            "source": "official_api",
            "title": "IR9 Completion Product",
            "asin": "B0IR90001",
            "url": "https://example.com/items/ir9",
            "campaign_type": "seasonal",
            "risk_flags": [],
        }
    ]
    roundtrip_output = run_generic_affiliate_generic_core_roundtrip_dryrun(
        base_path=tmp_path,
        source_task_id="ir9_completion",
        affiliate_records=records,
        generic_runtime_base_path=REPO_GENERIC_ROOT,
        persist_human_review_artifacts=False,
    )

    completion = write_ir9_completion_report(
        base_path=tmp_path,
        roundtrip_output=roundtrip_output,
        focused_tests={"passed": 43, "failed": 0},
        full_regression={"passed": 122, "failed": 0},
    )
    assert completion["external_write_executed"] is False
    path = Path(completion["path"])
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 9"
    assert loaded["status"] == "COMPLETED"
    assert loaded["test_result"]["focused_tests"]["passed"] == 43
