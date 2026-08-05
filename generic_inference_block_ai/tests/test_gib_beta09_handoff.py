from pathlib import Path

from generic_inference_block_ai.src.gib_beta09_handoff import (
    evaluate_handoff,
    load_json,
    validate_beta09_config,
)
from generic_inference_block_ai.src.gib_beta08_validator import validate_beta08_contract


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_beta09_first_call_handoff.json"


def test_beta09_config_valid() -> None:
    config = load_json(CONFIG_PATH)
    issues = validate_beta09_config(config)
    assert issues == []


def test_beta09_target_is_valid() -> None:
    config = load_json(CONFIG_PATH)
    beta08 = validate_beta08_contract()
    result = evaluate_handoff(config, beta08)

    assert result.target_valid is True
    assert result.target_issues == []


def test_beta09_cannot_execute_now() -> None:
    config = load_json(CONFIG_PATH)
    beta08 = validate_beta08_contract()
    result = evaluate_handoff(config, beta08)

    assert result.can_execute_now is False
    assert "manual_approval_not_granted" in result.blocked_reasons
    assert "real_llm_call_allowed_false" in result.blocked_reasons
    assert "execution_allowed_false" in result.blocked_reasons
