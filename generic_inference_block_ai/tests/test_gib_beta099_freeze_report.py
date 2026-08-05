from generic_inference_block_ai.src.gib_beta099_freeze_report import build_freeze_report


def test_freeze_report_all_pass() -> None:
    report = build_freeze_report()

    assert report["report_type"] == "BETA099_FINAL_FREEZE_REPORT"
    assert report["all_pass"] is True
    assert report["phase_count"] == 14
    assert report["failures"] == []


def test_freeze_report_safety_summary_stays_blocked() -> None:
    report = build_freeze_report()
    s = report["safety_summary"]

    assert s["real_llm_call_allowed"] is False
    assert s["execution_allowed"] is False
    assert s["generate_call_allowed"] is False
    assert s["chat_call_allowed"] is False
    assert s["production_status"] == "NO_GO"
    assert s["can_execute_now"] is False


def test_freeze_report_release_recommendation() -> None:
    report = build_freeze_report()
    assert report["release_recommendation"] == "HOLD_BETA1_UNTIL_EXPLICIT_APPROVAL_AND_FLAG_SWITCH"
