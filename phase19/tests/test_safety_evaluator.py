from phase19.evaluation.safety_evaluator import evaluate_safety


def _base() -> dict:
    return {
        "apply_scope": "sandbox_only",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_promote_to_next": True,
        "blocked_files": [],
    }


def test_safety_fail_when_apply_scope_invalid() -> None:
    payload = _base()
    payload["apply_scope"] = "live"
    result = evaluate_safety(payload)
    assert result["safety_status"] == "FAIL"


def test_safety_fail_when_mode_not_dry_run() -> None:
    payload = _base()
    payload["mode"] = "LIVE"
    result = evaluate_safety(payload)
    assert result["safety_status"] == "FAIL"


def test_safety_fail_when_human_approval_required_false() -> None:
    payload = _base()
    payload["human_approval_required"] = False
    result = evaluate_safety(payload)
    assert result["safety_status"] == "FAIL"


def test_safety_fail_when_policy_violation_in_blocked_files() -> None:
    payload = _base()
    payload["blocked_files"] = ["POLICY_VIOLATION: outside allowlist"]
    result = evaluate_safety(payload)
    assert result["safety_status"] == "FAIL"
