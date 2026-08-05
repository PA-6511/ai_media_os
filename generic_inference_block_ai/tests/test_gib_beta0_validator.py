from generic_inference_block_ai.src.gib_beta0_validator import validate_beta0_contract


def test_beta0_contract_passes() -> None:
    report = validate_beta0_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA0_LOCAL_OLLAMA_HARNESS"
    assert report["status"] == "DRY_RUN_HARNESS_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["runtime_target"] == "ollama"
    assert report["probe_would_call"] is False
    assert report["probe_blocked_reason"] == "real_llm_call_allowed_false"
    assert report["fallback_runtime"] == "stub"
    assert report["all_samples_fully_valid"] is True
    assert report["all_samples_probe_blocked"] is True
    assert report["all_samples_runtime_non_exec"] is True
    assert report["sample_request_count"] == 7


def test_beta0_safety_flags_stay_restricted() -> None:
    report = validate_beta0_contract()
    flags = report["safety_flags"]

    assert flags["execution_allowed"] is False
    assert flags["credential_access_allowed"] is False
    assert flags["wordpress_write_allowed"] is False
    assert flags["systemd_operation_allowed"] is False
    assert flags["real_llm_call_allowed"] is False
    assert flags["model_runtime_enabled"] is True
