from generic_inference_block_ai.src.gib_beta06_validator import validate_beta06_contract


def test_beta06_contract_passes() -> None:
    report = validate_beta06_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA06_ENV_PREP_CHECK_NO_GENERATE"
    assert report["status"] == "DRY_RUN_ENV_PREP_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["runtime_target"] == "ollama"
    assert report["guardrails_ok"] is True
    assert report["no_generate_call_required"] is True
    assert report["localhost_only_required"] is True
    assert report["allowlist_enforced"] is True


def test_beta06_snapshot_keeps_no_generate_chat_calls() -> None:
    report = validate_beta06_contract()
    snap = report["beta05_snapshot"]

    assert snap["generate_api_called"] is False
    assert snap["chat_api_called"] is False
    assert snap["real_llm_call_allowed"] is False
    assert snap["execution_allowed"] is False
