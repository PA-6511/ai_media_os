from pathlib import Path

from generic_inference_block_ai.src.gib_beta095_evidence_gate import (
    evaluate_evidence_gate,
    load_json,
    validate_beta095_config,
)
from generic_inference_block_ai.src.gib_beta09_validator import validate_beta09_contract


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_beta095_approval_evidence_format.json"


def test_beta095_config_valid() -> None:
    config = load_json(CONFIG_PATH)
    issues = validate_beta095_config(config)
    assert issues == []


def test_beta095_token_and_change_id_format_valid() -> None:
    config = load_json(CONFIG_PATH)
    beta09 = validate_beta09_contract()
    result = evaluate_evidence_gate(config, beta09)

    assert result.token_format_valid is True
    assert result.change_id_format_valid is True


def test_beta095_secret_handling_not_allowed() -> None:
    config = load_json(CONFIG_PATH)
    beta09 = validate_beta09_contract()
    result = evaluate_evidence_gate(config, beta09)

    assert result.secret_handling_allowed is False
    assert result.beta09_prereq_ok is True
