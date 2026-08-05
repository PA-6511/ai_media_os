from generic_inference_block_ai.src.gib_beta08_validator import validate_beta08_contract
from generic_inference_block_ai.src.gib_beta09_validator import validate_beta09_contract


def test_beta09_uses_beta08_snapshot() -> None:
    beta08 = validate_beta08_contract()
    beta09 = validate_beta09_contract()

    assert beta09["beta08_snapshot"]["final_status"] == beta08["final_status"]
    assert beta09["beta08_snapshot"]["auto_connect_triggered"] is False
    assert beta09["beta08_snapshot"]["real_llm_call_allowed"] is False


def test_beta09_no_go_no_execution() -> None:
    beta09 = validate_beta09_contract()

    assert beta09["production_status"] == "NO_GO"
    assert beta09["can_execute_now"] is False
