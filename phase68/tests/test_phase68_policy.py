from phase68.preparation_review_design.phase68_policy import evaluate_phase68_policy


def _base_package() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
    }


def _base_controls() -> dict:
    return {"review_controls_does_not_execute": True}


def _base_checks() -> dict:
    return {
        "evidence_checks_required": True,
        "missing_evidence_blocks_progress": True,
        "review_evidence_checks_does_not_execute": True,
    }


def _base_gate() -> dict:
    return {"gate_required": True, "manual_review_gate_does_not_execute": True}


def test_policy_fails_when_can_execute_true() -> None:
    package = _base_package()
    package["can_execute"] = True
    result = evaluate_phase68_policy(package, _base_controls(), _base_checks(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    package = _base_package()
    package["execute_allowed"] = True
    result = evaluate_phase68_policy(package, _base_controls(), _base_checks(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_controls_guard_false() -> None:
    controls = _base_controls()
    controls["review_controls_does_not_execute"] = False
    result = evaluate_phase68_policy(_base_package(), controls, _base_checks(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_checks_guard_false() -> None:
    checks = _base_checks()
    checks["review_evidence_checks_does_not_execute"] = False
    result = evaluate_phase68_policy(_base_package(), _base_controls(), checks, _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_pass_with_valid_inputs() -> None:
    result = evaluate_phase68_policy(
        _base_package(), _base_controls(), _base_checks(), _base_gate()
    )
    assert result["policy_status"] == "PASS"
