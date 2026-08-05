from generic_inference_block_ai.src.gib_beta05_validator import validate_beta05_contract
from generic_inference_block_ai.src.gib_beta06_validator import validate_beta06_contract


def test_beta06_aligned_with_beta05_policy() -> None:
    beta05 = validate_beta05_contract()
    beta06 = validate_beta06_contract()

    assert beta05["production_status"] == "NO_GO"
    assert beta06["production_status"] == "NO_GO"
    assert beta06["beta05_snapshot"]["real_llm_call_allowed"] is False
    assert beta06["beta05_snapshot"]["execution_allowed"] is False


def test_beta06_does_not_require_generate_or_chat_calls() -> None:
    beta06 = validate_beta06_contract()

    assert beta06["no_generate_call_required"] is True
    assert beta06["beta05_snapshot"]["generate_api_called"] is False
    assert beta06["beta05_snapshot"]["chat_api_called"] is False
