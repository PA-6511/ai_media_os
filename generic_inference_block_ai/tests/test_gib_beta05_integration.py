from generic_inference_block_ai.src.gib_beta0_validator import validate_beta0_contract
from generic_inference_block_ai.src.gib_beta05_validator import validate_beta05_contract


def test_beta05_consistent_with_beta0_safety() -> None:
    beta0 = validate_beta0_contract()
    beta05 = validate_beta05_contract()

    assert beta0["production_status"] == "NO_GO"
    assert beta05["production_status"] == "NO_GO"
    assert beta0["safety_flags"]["real_llm_call_allowed"] is False
    assert beta05["real_llm_call_allowed"] is False


def test_beta05_is_preflight_only() -> None:
    beta05 = validate_beta05_contract()

    assert beta05["status"] == "DRY_RUN_PREFLIGHT_ONLY"
    assert beta05["generate_api_called"] is False
    assert beta05["chat_api_called"] is False
