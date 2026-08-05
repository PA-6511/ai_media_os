from pathlib import Path

from generic_inference_block_ai.src.gib_beta05_preflight import (
    check_endpoint,
    load_and_run,
    load_json,
    run_preflight,
    validate_preflight_config,
)


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_beta05_local_ollama_preflight.json"


def test_beta05_config_valid() -> None:
    config = load_json(CONFIG_PATH)
    issues = validate_preflight_config(config)
    assert issues == []


def test_endpoint_check_localhost_valid() -> None:
    result = check_endpoint(
        "http://127.0.0.1:11434/api/tags",
        ["127.0.0.1", "localhost"],
        [11434],
    )
    assert result.valid is True


def test_endpoint_check_forbidden_host_invalid() -> None:
    result = check_endpoint(
        "http://example.com:11434/api/tags",
        ["127.0.0.1", "localhost"],
        [11434],
    )
    assert result.host_allowed is False
    assert result.valid is False


def test_preflight_never_calls_generate_or_chat() -> None:
    config = load_json(CONFIG_PATH)
    result = run_preflight(config)
    assert result.generate_api_called is False
    assert result.chat_api_called is False


def test_preflight_model_allowlist_match() -> None:
    config = load_json(CONFIG_PATH)
    result = run_preflight(config)
    assert result.model_allowed is True


def test_load_and_run_returns_valid_structure() -> None:
    config, result = load_and_run(CONFIG_PATH)
    assert config["beta_version"] == "beta0.5"
    assert result.config_valid is True
