from generic_inference_block_ai.src.gib_alpha4_validator import validate_alpha4_contract


def test_alpha4_contract_passes() -> None:
    report = validate_alpha4_contract()

    assert report["final_status"] == "PASS_DESIGN_ONLY_ALPHA4_RUNTIME_GATE_FIXED"
    assert report["production_status"] == "NO_GO"
    assert report["execution_mode"] == "DRY_RUN_ONLY"
    assert report["active_runtime_lock"] == "stub"
    assert report["all_scenarios_match_expected"] is True
    assert report["hard_block_for_non_stub_runtime"] is True
    assert report["scenario_count"] == 4


def test_alpha4_policy_flags_stay_disabled() -> None:
    report = validate_alpha4_contract()
    flags = report["policy_flags"]

    assert flags["model_runtime_enabled"] is False
    assert flags["real_llm_call_allowed"] is False
    assert flags["execution_allowed"] is False


def test_alpha4_scenarios_include_required_blocks() -> None:
    report = validate_alpha4_contract()
    rows = {item["requested_runtime"]: item for item in report["scenario_results"]}

    assert rows["stub"]["allowed"] is True
    assert rows["ollama"]["allowed"] is False
    assert rows["llama_cpp"]["allowed"] is False
    assert rows["unknown_runtime"]["allowed"] is False
