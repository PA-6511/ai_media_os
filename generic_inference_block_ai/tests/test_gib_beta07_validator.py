from generic_inference_block_ai.src.gib_beta07_validator import validate_beta07_contract


def test_beta07_contract_passes() -> None:
    report = validate_beta07_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA07_READY_SIM_NO_AUTOCONNECT"
    assert report["status"] == "DRY_RUN_READY_SIMULATION_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["real_llm_call_allowed"] is False
    assert report["execution_allowed"] is False
    assert report["generate_call_allowed"] is False
    assert report["chat_call_allowed"] is False


def test_beta07_ready_transition_and_no_autoconnect() -> None:
    report = validate_beta07_contract()

    assert report["base_ready_conditions_ok"] is False
    assert report["simulated_ready_conditions_ok"] is True
    assert report["auto_connect_on_ready"] is False
    assert report["auto_connect_triggered"] is False
