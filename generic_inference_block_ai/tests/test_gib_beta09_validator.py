from generic_inference_block_ai.src.gib_beta09_validator import validate_beta09_contract


def test_beta09_contract_passes() -> None:
    report = validate_beta09_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA09_FIRST_CALL_HANDOFF_NO_EXECUTION"
    assert report["status"] == "DRY_RUN_FIRST_CALL_HANDOFF_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["manual_approval_required"] is True
    assert report["manual_approval_granted"] is False
    assert report["target_runtime"] == "ollama"
    assert report["target_host"] in ["localhost", "127.0.0.1"]
    assert report["target_port"] == 11434
    assert report["target_valid"] is True
    assert report["promotion_conditions_documented"] is True
    assert report["can_execute_now"] is False


def test_beta09_guardrails_stay_false() -> None:
    report = validate_beta09_contract()
    g = report["current_guardrails"]

    assert g["real_llm_call_allowed"] is False
    assert g["execution_allowed"] is False
    assert g["generate_call_allowed"] is False
    assert g["chat_call_allowed"] is False
    assert g["wordpress_write_allowed"] is False
    assert g["credential_access_allowed"] is False
