from generic_inference_block_ai.src.gib_alpha3_runtime_design import (
    load_and_validate_runtime_design,
    validate_runtime_design,
)


def test_runtime_design_loads_and_is_safe() -> None:
    config = load_and_validate_runtime_design()

    assert config["design_status"] == "DESIGN_ONLY"
    assert config["production_status"] == "NO_GO"
    assert config["execution_mode"] == "DRY_RUN_ONLY"
    assert config["execution_allowed"] is False
    assert config["external_network_allowed"] is False
    assert config["credential_access_allowed"] is False
    assert config["wordpress_write_allowed"] is False
    assert config["systemd_operation_allowed"] is False
    assert config["model_runtime_enabled"] is False
    assert config["real_llm_call_allowed"] is False


def test_runtime_selection_locked_to_stub() -> None:
    config = load_and_validate_runtime_design()
    selection = config["runtime_selection"]

    assert selection["active_runtime_locked"] == "stub"
    assert selection["default_runtime"] == "stub"
    assert selection["fallback_order"] == ["stub", "ollama", "llama_cpp"]


def test_runtime_definitions_are_disabled() -> None:
    config = load_and_validate_runtime_design()

    for runtime in ["ollama", "llama_cpp"]:
        definition = config["runtime_designs"][runtime]
        assert definition["enabled"] is False
        assert definition["call_allowed"] is False
        assert definition["transport"] == "http_local_only_design"
        assert isinstance(definition["base_url"], str)
        assert isinstance(definition["timeout_ms"], int)


def test_validator_rejects_execution_allowed_true() -> None:
    config = load_and_validate_runtime_design()
    modified = dict(config)
    modified["execution_allowed"] = True

    issues = validate_runtime_design(modified)
    assert any("execution_allowed" in issue for issue in issues)
