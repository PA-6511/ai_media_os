from phase22.design.phase22_policy import evaluate_phase22_policy


def _base_approval_format() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "approval_required": True,
        "decision_format": ["APPROVE_PHASE23_PLANNING_ONLY", "REJECT"],
        "approve_does_not_apply": True,
    }


def _base_checklist() -> dict:
    return {"status": "CHECKLIST_READY"}


def _base_stop_conditions() -> dict:
    return {"status": "STOP_CONDITIONS_READY"}


def test_policy_fails_when_mode_invalid() -> None:
    approval_format = _base_approval_format()
    approval_format["mode"] = "LIVE"
    result = evaluate_phase22_policy(
        approval_format, _base_checklist(), _base_stop_conditions()
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_approve_does_not_apply_false() -> None:
    approval_format = _base_approval_format()
    approval_format["approve_does_not_apply"] = False
    result = evaluate_phase22_policy(
        approval_format, _base_checklist(), _base_stop_conditions()
    )
    assert result["policy_status"] == "FAIL"
