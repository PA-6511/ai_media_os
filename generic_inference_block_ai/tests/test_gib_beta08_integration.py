from generic_inference_block_ai.src.gib_beta07_validator import validate_beta07_contract
from generic_inference_block_ai.src.gib_beta08_validator import validate_beta08_contract


def test_beta08_uses_beta07_ready_snapshot() -> None:
    beta07 = validate_beta07_contract()
    beta08 = validate_beta08_contract()

    assert beta08["beta07_snapshot"]["final_status"] == beta07["final_status"]
    assert beta08["beta07_snapshot"]["simulated_ready_conditions_ok"] is True


def test_beta08_keeps_no_go_and_no_exec() -> None:
    beta08 = validate_beta08_contract()

    assert beta08["production_status"] == "NO_GO"
    assert beta08["real_llm_call_allowed"] is False
    assert beta08["execution_allowed"] is False
