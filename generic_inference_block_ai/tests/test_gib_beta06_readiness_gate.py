from pathlib import Path

from generic_inference_block_ai.src.gib_beta06_readiness_gate import (
    evaluate_beta06_gate,
    load_json,
    validate_beta06_config,
)


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_beta06_env_prep_gate.json"


def test_beta06_config_validation_passes() -> None:
    config = load_json(CONFIG_PATH)
    issues = validate_beta06_config(config)
    assert issues == []


def test_beta06_gate_not_ready_when_binary_missing() -> None:
    config = load_json(CONFIG_PATH)
    beta05_report = {
        "real_llm_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "ollama_binary_found": False,
        "all_endpoints_valid": True,
        "model_allowed": True,
        "forbidden_host_rejected": True,
        "generate_api_called": False,
        "chat_api_called": False,
    }
    result = evaluate_beta06_gate(config, beta05_report)

    assert result.guardrails_ok is True
    assert result.ready_for_connecting_stage is False
    assert "ollama_binary_found" in result.missing_true_conditions


def test_beta06_gate_ready_when_all_conditions_met() -> None:
    config = load_json(CONFIG_PATH)
    beta05_report = {
        "real_llm_call_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "ollama_binary_found": True,
        "all_endpoints_valid": True,
        "model_allowed": True,
        "forbidden_host_rejected": True,
        "generate_api_called": False,
        "chat_api_called": False,
    }
    result = evaluate_beta06_gate(config, beta05_report)

    assert result.guardrails_ok is True
    assert result.ready_conditions_ok is True
    assert result.ready_for_connecting_stage is True
