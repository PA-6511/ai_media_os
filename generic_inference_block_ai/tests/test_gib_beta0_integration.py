from generic_inference_block_ai.src.gib_alpha45_validator import validate_alpha45_contract
from generic_inference_block_ai.src.gib_beta0_validator import validate_beta0_contract


def test_beta0_uses_alpha45_decisions() -> None:
    alpha45 = validate_alpha45_contract()
    beta0 = validate_beta0_contract()

    assert alpha45["all_decisions_made"] is True
    assert beta0["alpha45_all_decisions_made"] is True


def test_beta0_keeps_no_go_and_no_exec() -> None:
    beta0 = validate_beta0_contract()

    assert beta0["production_status"] == "NO_GO"
    assert beta0["safety_flags"]["execution_allowed"] is False
    assert beta0["safety_flags"]["real_llm_call_allowed"] is False
    assert beta0["probe_would_call"] is False
