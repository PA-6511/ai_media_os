from generic_inference_block_ai.src.gib_beta06_validator import validate_beta06_contract
from generic_inference_block_ai.src.gib_beta07_validator import validate_beta07_contract


def test_beta07_uses_beta06_snapshot() -> None:
    beta06 = validate_beta06_contract()
    beta07 = validate_beta07_contract()

    assert beta07["beta06_snapshot"]["final_status"] == beta06["final_status"]
    assert beta07["beta06_snapshot"]["ready_conditions_ok"] == beta06["ready_conditions_ok"]


def test_beta07_keeps_no_go_and_no_exec() -> None:
    beta07 = validate_beta07_contract()

    assert beta07["production_status"] == "NO_GO"
    assert beta07["real_llm_call_allowed"] is False
    assert beta07["execution_allowed"] is False
