from generic_inference_block_ai.src.gib_beta08_validator import validate_beta08_contract


def test_beta08_contract_passes() -> None:
    report = validate_beta08_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA08_MANUAL_APPROVAL_GATE_NO_REAL_CALL"
    assert report["status"] == "DRY_RUN_MANUAL_APPROVAL_GATE_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["manual_approval_required"] is True
    assert report["approval_granted"] is False
    assert report["real_llm_call_allowed"] is False
    assert report["execution_allowed"] is False
    assert report["generate_call_allowed"] is False
    assert report["chat_call_allowed"] is False


def test_beta08_scenarios_and_autoconnect() -> None:
    report = validate_beta08_contract()

    assert report["denied_scenario"]["call_allowed"] is False
    assert report["approved_sim_scenario"]["call_allowed"] is False
    assert report["auto_connect_on_ready"] is False
    assert report["auto_connect_triggered"] is False
