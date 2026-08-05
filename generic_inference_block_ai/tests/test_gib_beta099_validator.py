from generic_inference_block_ai.src.gib_beta099_validator import validate_beta099_contract


def test_beta099_contract_passes() -> None:
    report = validate_beta099_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA099_FINAL_APPROVAL_GATE_NO_EXECUTION"
    assert report["status"] == "DRY_RUN_FINAL_APPROVAL_GATE_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["final_approval_required"] is True
    assert report["final_approval_granted"] is False
    assert report["target_runtime"] == "ollama"
    assert report["target_model"] == "gemma-4-qat-e2b"
    assert report["switch_conditions_ok"] is True
    assert report["can_execute_now"] is False


def test_beta099_guardrails_and_scenarios() -> None:
    report = validate_beta099_contract()

    assert report["current_guardrails"]["real_llm_call_allowed"] is False
    assert report["current_guardrails"]["execution_allowed"] is False
    assert report["current_guardrails"]["generate_call_allowed"] is False
    assert report["current_guardrails"]["chat_call_allowed"] is False
    assert report["denied_scenario"]["call_allowed"] is False
    assert report["approved_sim_scenario"]["call_allowed"] is False
