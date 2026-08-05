from pathlib import Path

from generic_inference_block_ai.src.gib_beta08_manual_approval_gate import (
    load_json,
    run_manual_approval_gate,
    validate_beta08_config,
)
from generic_inference_block_ai.src.gib_beta07_validator import validate_beta07_contract


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_beta08_manual_approval_gate.json"


def test_beta08_config_valid() -> None:
    config = load_json(CONFIG_PATH)
    issues = validate_beta08_config(config)
    assert issues == []


def test_beta08_denied_scenario_blocks_call() -> None:
    config = load_json(CONFIG_PATH)
    beta07 = validate_beta07_contract()
    gate = run_manual_approval_gate(config, beta07)

    assert gate.denied_scenario.call_allowed is False
    assert gate.denied_scenario.blocked_reason in ["manual_approval_required", "real_llm_call_allowed_false"]


def test_beta08_approved_sim_still_blocked_by_policy() -> None:
    config = load_json(CONFIG_PATH)
    beta07 = validate_beta07_contract()
    gate = run_manual_approval_gate(config, beta07)

    assert gate.approved_sim_scenario.approval_granted is True
    assert gate.approved_sim_scenario.call_allowed is False
    assert gate.approved_sim_scenario.blocked_reason == "real_llm_call_allowed_false"


def test_beta08_auto_connect_not_triggered() -> None:
    config = load_json(CONFIG_PATH)
    beta07 = validate_beta07_contract()
    gate = run_manual_approval_gate(config, beta07)

    assert gate.auto_connect_triggered is False
