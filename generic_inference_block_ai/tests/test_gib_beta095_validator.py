from generic_inference_block_ai.src.gib_beta095_validator import validate_beta095_contract


def test_beta095_contract_passes() -> None:
    report = validate_beta095_contract()

    assert report["final_status"] == "PASS_DRY_RUN_BETA095_APPROVAL_EVIDENCE_FORMAT_ONLY"
    assert report["status"] == "DRY_RUN_APPROVAL_EVIDENCE_FORMAT_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["manual_approval_required"] is True
    assert report["real_llm_call_allowed"] is False
    assert report["execution_allowed"] is False
    assert report["generate_call_allowed"] is False
    assert report["chat_call_allowed"] is False
    assert report["token_format_valid"] is True
    assert report["change_id_format_valid"] is True
    assert report["secret_value_handling_allowed"] is False
    assert report["beta09_prereq_ok"] is True


def test_beta095_beta09_snapshot_safe() -> None:
    report = validate_beta095_contract()
    snap = report["beta09_snapshot"]

    assert snap["final_status"] == "PASS_DRY_RUN_BETA09_FIRST_CALL_HANDOFF_NO_EXECUTION"
    assert snap["production_status"] == "NO_GO"
    assert snap["can_execute_now"] is False
