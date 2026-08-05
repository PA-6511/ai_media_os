from pathlib import Path

from generic_inference_block_ai.src.gib_beta07_simulation import (
    load_json,
    run_ready_simulation,
    validate_beta07_config,
)
from generic_inference_block_ai.src.gib_beta06_validator import validate_beta06_contract


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_beta07_ready_simulation.json"


def test_beta07_config_valid() -> None:
    config = load_json(CONFIG_PATH)
    issues = validate_beta07_config(config)
    assert issues == []


def test_beta07_simulation_makes_ready_true() -> None:
    config = load_json(CONFIG_PATH)
    beta06_report = validate_beta06_contract()
    result = run_ready_simulation(config, beta06_report)

    assert result.base_ready_conditions_ok is False
    assert result.simulated_ready_conditions_ok is True


def test_beta07_simulation_does_not_auto_connect() -> None:
    config = load_json(CONFIG_PATH)
    beta06_report = validate_beta06_contract()
    result = run_ready_simulation(config, beta06_report)

    assert result.auto_connect_triggered is False
