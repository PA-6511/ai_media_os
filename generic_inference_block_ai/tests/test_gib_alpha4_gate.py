from generic_inference_block_ai.src.gib_alpha4_gate import (
    evaluate_runtime_gate,
    get_alpha_policy_flags,
    load_and_validate_gate_config,
    validate_gate_config,
)


def test_gate_config_loads() -> None:
    config = load_and_validate_gate_config()

    assert config["schema_version"] == "gib.alpha4.runtime_gate.v0.1"
    assert config["design_status"] == "DESIGN_ONLY"
    assert config["production_status"] == "NO_GO"
    assert config["execution_mode"] == "DRY_RUN_ONLY"
    assert config["active_runtime_lock"] == "stub"


def test_gate_validator_rejects_wrong_runtime_lock() -> None:
    config = load_and_validate_gate_config()
    modified = dict(config)
    modified["active_runtime_lock"] = "ollama"

    issues = validate_gate_config(modified)
    assert any("active_runtime_lock" in issue for issue in issues)


def test_stub_runtime_allowed() -> None:
    config = load_and_validate_gate_config()
    flags = get_alpha_policy_flags()

    decision = evaluate_runtime_gate("stub", flags, config)
    assert decision.allowed is True
    assert decision.active_runtime == "stub"
    assert decision.blocked_reason is None


def test_ollama_blocked_when_real_llm_disallowed() -> None:
    config = load_and_validate_gate_config()
    flags = {
        "model_runtime_enabled": False,
        "real_llm_call_allowed": False,
        "execution_allowed": False,
    }

    decision = evaluate_runtime_gate("ollama", flags, config)
    assert decision.allowed is False
    assert decision.active_runtime == "stub"
    assert decision.blocked_reason == "runtime_call_not_allowed_by_policy_flags"
    assert "real_llm_call_allowed" in decision.missing_flags


def test_llama_cpp_blocked_when_real_llm_disallowed() -> None:
    config = load_and_validate_gate_config()
    flags = {
        "model_runtime_enabled": False,
        "real_llm_call_allowed": False,
        "execution_allowed": False,
    }

    decision = evaluate_runtime_gate("llama_cpp", flags, config)
    assert decision.allowed is False
    assert decision.active_runtime == "stub"
    assert decision.blocked_reason == "runtime_call_not_allowed_by_policy_flags"
    assert "real_llm_call_allowed" in decision.missing_flags


def test_unknown_runtime_blocked() -> None:
    config = load_and_validate_gate_config()
    flags = get_alpha_policy_flags()

    decision = evaluate_runtime_gate("unknown_runtime", flags, config)
    assert decision.allowed is False
    assert decision.blocked_reason == "unsupported_runtime"
