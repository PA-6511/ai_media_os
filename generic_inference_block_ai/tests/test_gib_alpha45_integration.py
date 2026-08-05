from generic_inference_block_ai.src.gib_alpha45_validator import validate_alpha45_contract
from generic_inference_block_ai.src.gib_alpha4_validator import validate_alpha4_contract


def test_alpha45_is_consistent_with_alpha4_safety() -> None:
    alpha4 = validate_alpha4_contract()
    alpha45 = validate_alpha45_contract()

    assert alpha4["production_status"] == "NO_GO"
    assert alpha45["production_status"] == "NO_GO"

    g = alpha45["beta0_guardrails"]
    assert g["execution_allowed"] is False
    assert g["real_llm_call_allowed"] is False


def test_alpha45_report_scope_is_reports_only() -> None:
    alpha45 = validate_alpha45_contract()
    assert alpha45["report_write_scope"] == ["generic_inference_block_ai/reports"]
