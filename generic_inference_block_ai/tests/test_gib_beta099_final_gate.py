from pathlib import Path

from generic_inference_block_ai.src.gib_beta099_final_gate import (
    evaluate_final_gate,
    load_json,
    validate_beta099_config,
)
from generic_inference_block_ai.src.gib_beta095_validator import validate_beta095_contract


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_beta099_final_approval_gate.json"


def test_beta099_config_valid() -> None:
    config = load_json(CONFIG_PATH)
    issues = validate_beta099_config(config)
    assert issues == []


def test_beta099_denied_scenario_blocks_call() -> None:
    config = load_json(CONFIG_PATH)
    beta095 = validate_beta095_contract()
    result = evaluate_final_gate(config, beta095)

    assert result.denied_scenario.call_allowed is False
    assert result.denied_scenario.blocked_reason == "final_manual_approval_required"


def test_beta099_approved_sim_still_blocked_by_policy() -> None:
    config = load_json(CONFIG_PATH)
    beta095 = validate_beta095_contract()
    result = evaluate_final_gate(config, beta095)

    assert result.approved_sim_scenario.approval_granted is True
    assert result.approved_sim_scenario.call_allowed is False
    assert result.approved_sim_scenario.blocked_reason == "real_llm_call_allowed_false"
