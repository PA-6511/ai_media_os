from generic_inference_block_ai.src.gib_beta09_validator import validate_beta09_contract
from generic_inference_block_ai.src.gib_beta095_validator import validate_beta095_contract


def test_beta095_uses_beta09_prereq() -> None:
    beta09 = validate_beta09_contract()
    beta095 = validate_beta095_contract()

    assert beta095["beta09_snapshot"]["final_status"] == beta09["final_status"]
    assert beta095["beta09_snapshot"]["target_runtime"] == beta09["target_runtime"]


def test_beta095_keeps_no_execution_flags() -> None:
    beta095 = validate_beta095_contract()

    assert beta095["production_status"] == "NO_GO"
    assert beta095["real_llm_call_allowed"] is False
    assert beta095["execution_allowed"] is False
    assert beta095["generate_call_allowed"] is False
    assert beta095["chat_call_allowed"] is False
