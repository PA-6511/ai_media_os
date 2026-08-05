from __future__ import annotations

import json
from pathlib import Path

from generic_inference_block_ai.src.gib_beta1_prep import evaluate_beta1_prep, load_json
from generic_inference_block_ai.src.gib_beta1_prep_validator import validate_beta1_prep_contract


def test_beta1_prep_contract_passes_and_blocks_execution() -> None:
    report = validate_beta1_prep_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED"
    assert report["production_status"] == "NO_GO"
    assert report["status"] == "DRY_RUN_BETA1_PREP_ONLY"
    assert report["beta099_prereq_ok"] is True
    assert report["constraints_ok"] is True
    assert report["real_llm_call_allowed"] is False
    assert report["execution_allowed"] is False
    assert report["can_execute_now"] is False
    assert report["target_runtime"] == "ollama"
    assert report["target_host"] == "local_pc"
    assert report["target_model"] == "gemma-4-qat-e2b"


def test_beta1_prep_missing_fields_fails_validation(tmp_path: Path) -> None:
    cfg = {
        "schema_version": "gib.beta1.prep.runbook.v0.1",
        "phase": "beta1_prep",
        "status": "DRY_RUN_BETA1_PREP_ONLY",
        "production_status": "NO_GO",
        "execution_allowed": False,
        "real_llm_call_allowed": False,
        "target_runtime": "ollama",
        "target_host": "local_pc",
        "target_model": "gemma-4-qat-e2b",
        "constraints": {
            "localhost_only": True,
            "reports_only_output": True,
            "wordpress_write_allowed": False,
            "credential_access_allowed": False,
            "systemd_operation_allowed": False,
            "generate_chat_execution": False,
        },
        "required_inputs": {
            "approval_token_format_valid": True,
            "change_management_id_format_valid": True,
            "final_approval_granted": False,
        },
        "run_steps": ["a", "b", "c", "d", "e"],
        "release_gate": {
            "allow_beta1_execution_now": False,
            "required_switches_for_beta1": [
                "explicit_manual_approval",
                "real_llm_call_allowed_true",
                "execution_allowed_true",
                "change_control_ticket_bound",
            ],
        },
    }

    config_path = tmp_path / "bad.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")

    loaded = load_json(config_path)
    loaded["execution_allowed"] = True

    beta099_like = {
        "final_status": "PASS_DRY_RUN_BETA099_FINAL_APPROVAL_GATE_NO_EXECUTION",
        "can_execute_now": False,
        "production_status": "NO_GO",
        "current_guardrails": {
            "real_llm_call_allowed": False,
            "execution_allowed": False,
            "generate_call_allowed": False,
            "chat_call_allowed": False,
        },
    }

    result = evaluate_beta1_prep(loaded, beta099_like)
    assert result.config_valid is False
    assert "execution_allowed must be false" in result.config_issues


def test_beta1_prep_prereq_failure_detected(tmp_path: Path) -> None:
    cfg = {
        "schema_version": "gib.beta1.prep.runbook.v0.1",
        "phase": "beta1_prep",
        "status": "DRY_RUN_BETA1_PREP_ONLY",
        "production_status": "NO_GO",
        "execution_allowed": False,
        "real_llm_call_allowed": False,
        "target_runtime": "ollama",
        "target_host": "local_pc",
        "target_model": "gemma-4-qat-e2b",
        "constraints": {
            "localhost_only": True,
            "reports_only_output": True,
            "wordpress_write_allowed": False,
            "credential_access_allowed": False,
            "systemd_operation_allowed": False,
            "generate_chat_execution": False,
        },
        "required_inputs": {
            "approval_token_format_valid": True,
            "change_management_id_format_valid": True,
            "final_approval_granted": False,
        },
        "run_steps": ["a", "b", "c", "d", "e"],
        "release_gate": {
            "allow_beta1_execution_now": False,
            "required_switches_for_beta1": [
                "explicit_manual_approval",
                "real_llm_call_allowed_true",
                "execution_allowed_true",
                "change_control_ticket_bound",
            ],
        },
    }
    config_path = tmp_path / "ok.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")

    loaded = load_json(config_path)
    bad_beta099 = {
        "final_status": "FAIL_BETA099",
        "can_execute_now": True,
        "production_status": "GO",
        "current_guardrails": {
            "real_llm_call_allowed": True,
            "execution_allowed": True,
            "generate_call_allowed": True,
            "chat_call_allowed": True,
        },
    }

    result = evaluate_beta1_prep(loaded, bad_beta099)
    assert result.beta099_prereq_ok is False
    assert result.constraints_ok is False
    assert result.can_execute_now is False
