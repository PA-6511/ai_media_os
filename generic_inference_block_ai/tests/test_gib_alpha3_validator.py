from generic_inference_block_ai.src.gib_alpha3_validator import validate_alpha3_contract


def test_alpha3_contract_passes() -> None:
    report = validate_alpha3_contract()

    assert report["final_status"] == "PASS_DESIGN_ONLY_ALPHA3_RUNTIME_BLUEPRINT"
    assert report["production_status"] == "NO_GO"
    assert report["execution_allowed"] is False
    assert report["external_network_allowed"] is False
    assert report["credential_access_allowed"] is False
    assert report["wordpress_write_allowed"] is False
    assert report["systemd_operation_allowed"] is False
    assert report["model_runtime_enabled"] is False
    assert report["real_llm_call_allowed"] is False
    assert report["active_runtime_locked"] == "stub"
    assert report["all_samples_fully_valid"] is True
    assert report["all_samples_no_runtime_call"] is True
    assert report["sample_request_count"] == 7


def test_alpha3_sample_results_are_safe() -> None:
    report = validate_alpha3_contract()
    for item in report["sample_results"]:
        assert item["runtime"] == "stub"
        assert item["runtime_would_call"] is False
        assert item["execution_effect"] == "none"
        assert item["model_runtime"] == "stub_no_model_loaded"
