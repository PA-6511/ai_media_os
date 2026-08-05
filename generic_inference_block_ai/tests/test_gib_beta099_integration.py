from generic_inference_block_ai.src.gib_beta095_validator import validate_beta095_contract
from generic_inference_block_ai.src.gib_beta099_validator import validate_beta099_contract


def test_beta099_uses_beta095_prereq() -> None:
    beta095 = validate_beta095_contract()
    beta099 = validate_beta099_contract()

    assert beta099["beta095_snapshot"]["final_status"] == beta095["final_status"]
    assert beta099["beta095_snapshot"]["token_format_valid"] is True
    assert beta099["beta095_snapshot"]["change_id_format_valid"] is True


def test_beta099_stays_no_go_no_exec() -> None:
    beta099 = validate_beta099_contract()

    assert beta099["production_status"] == "NO_GO"
    assert beta099["can_execute_now"] is False
