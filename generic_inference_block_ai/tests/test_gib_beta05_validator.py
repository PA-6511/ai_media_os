from generic_inference_block_ai.src.gib_beta05_validator import validate_beta05_contract


def test_beta05_contract_passes() -> None:
    report = validate_beta05_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA05_LOCAL_OLLAMA_PREFLIGHT_NO_GENERATE_CALL"
    assert report["status"] == "DRY_RUN_PREFLIGHT_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["real_llm_call_allowed"] is False
    assert report["execution_allowed"] is False
    assert report["generate_call_allowed"] is False
    assert report["chat_call_allowed"] is False
    assert report["all_endpoints_valid"] is True
    assert report["model_allowed"] is True
    assert report["forbidden_host_rejected"] is True
    assert report["generate_api_called"] is False
    assert report["chat_api_called"] is False


def test_beta05_endpoint_checks_all_valid() -> None:
    report = validate_beta05_contract()
    assert report["endpoint_checks"]
    assert all(item["valid"] is True for item in report["endpoint_checks"])
