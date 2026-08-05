from generic_inference_block_ai.src.gib_alpha45_validator import validate_alpha45_contract


def test_alpha45_contract_passes() -> None:
    report = validate_alpha45_contract()

    assert report["final_status"] == "PASS_DESIGN_ONLY_ALPHA45_PROMOTION_CHECKLIST_FIXED"
    assert report["design_status"] == "DESIGN_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["checklist_valid"] is True
    assert report["beta0_ready"] is False
    assert report["all_decisions_made"] is True


def test_alpha45_guardrails_fixed() -> None:
    report = validate_alpha45_contract()
    g = report["beta0_guardrails"]

    assert g["wordpress_write_allowed"] is False
    assert g["credential_access_allowed"] is False
    assert g["execution_allowed"] is False
    assert g["model_runtime_enabled"] is True
    assert g["real_llm_call_allowed"] is False
