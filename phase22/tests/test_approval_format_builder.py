from phase22.design.approval_format_builder import build_phase22_approval_format


def test_approval_format_fails_when_phase21_not_ready() -> None:
    result = build_phase22_approval_format(
        {"readiness_status": "NOT_READY", "can_apply": False}
    )
    assert result["status"] == "FAIL"


def test_approval_format_fails_when_phase21_can_apply_true() -> None:
    result = build_phase22_approval_format(
        {"readiness_status": "READY_FOR_PHASE22_PLANNING_ONLY", "can_apply": True}
    )
    assert result["status"] == "FAIL"


def test_approval_format_includes_approve_does_not_apply() -> None:
    result = build_phase22_approval_format(
        {
            "readiness_status": "READY_FOR_PHASE22_PLANNING_ONLY",
            "can_apply": False,
        }
    )
    assert result["status"] == "APPROVAL_FORMAT_READY"
    assert result["approve_does_not_apply"] is True
