from pathlib import Path

from generic_inference_block_ai.src.gib_beta0_harness import (
    build_probe_plan,
    load_json,
    load_and_validate_beta0_config,
    validate_beta0_harness_config,
)


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_beta0_local_ollama_harness.json"


def test_beta0_harness_config_valid() -> None:
    config = load_and_validate_beta0_config()

    assert config["status"] == "DRY_RUN_HARNESS_ONLY"
    assert config["production_status"] == "NO_GO"
    assert config["runtime_target"] == "ollama"
    assert config["fallback_runtime"] == "stub"


def test_beta0_harness_safety_flags_locked() -> None:
    config = load_and_validate_beta0_config()
    flags = config["safety_flags"]

    assert flags["execution_allowed"] is False
    assert flags["credential_access_allowed"] is False
    assert flags["wordpress_write_allowed"] is False
    assert flags["systemd_operation_allowed"] is False
    assert flags["real_llm_call_allowed"] is False
    assert flags["model_runtime_enabled"] is True


def test_beta0_probe_plan_blocked_by_policy() -> None:
    config = load_and_validate_beta0_config()
    plan = build_probe_plan(config)

    assert plan.would_call is False
    assert plan.blocked_reason == "real_llm_call_allowed_false"
    assert plan.runtime_target == "ollama"
    assert plan.fallback_runtime == "stub"


def test_beta0_validator_rejects_non_localhost_base_url() -> None:
    config = load_json(CONFIG_PATH)
    modified = dict(config)
    modified_design = dict(config["ollama_design"])
    modified_design["base_url"] = "http://10.0.0.10:11434"
    modified["ollama_design"] = modified_design

    issues = validate_beta0_harness_config(modified)
    assert any("base_url" in issue for issue in issues)
