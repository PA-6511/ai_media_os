from generic_inference_block_ai.src.gib_alpha45_promotion_gate import (
    evaluate_promotion_gate,
    load_json,
    validate_checklist_schema,
)
from pathlib import Path


CONFIG_PATH = Path(__file__).parent.parent / "config" / "gib_alpha45_beta0_promotion_checklist.json"


def test_alpha45_schema_validation_passes() -> None:
    config = load_json(CONFIG_PATH)
    issues = validate_checklist_schema(config)
    assert issues == []


def test_alpha45_checklist_decisions_are_filled() -> None:
    config = load_json(CONFIG_PATH)
    result = evaluate_promotion_gate(config)

    assert result.checklist_valid is True
    assert result.all_decisions_made is True
    assert result.missing_decisions == []
    assert result.beta0_ready is False
    assert "promotion_checklist_not_fully_decided" not in result.blocked_reasons


def test_alpha45_rejects_beta0_ready_true_in_alpha() -> None:
    config = load_json(CONFIG_PATH)
    modified = dict(config)
    modified["beta0_ready"] = True

    issues = validate_checklist_schema(modified)
    assert any("beta0_ready" in issue for issue in issues)
