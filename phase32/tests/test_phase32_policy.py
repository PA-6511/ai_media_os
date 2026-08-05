from phase32.preflight_design.phase32_policy import evaluate_phase32_policy


def _base_preflight_package() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
    }


def _base_controls() -> dict:
    return {
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "preflight_controls_does_not_execute": True,
    }


def _base_stop_conditions() -> dict:
    return {
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "preflight_stop_conditions_does_not_execute": True,
    }


def _base_evidence() -> dict:
    return {
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "preflight_evidence_does_not_execute": True,
    }


def _base_gate() -> dict:
    return {
        "approval_required": True,
        "allow_does_not_execute": True,
    }


def test_policy_fails_when_max_files_invalid() -> None:
    package = _base_preflight_package()
    package["max_files_to_execute"] = 2
    result = evaluate_phase32_policy(
        package,
        _base_controls(),
        _base_stop_conditions(),
        _base_evidence(),
        _base_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    package = _base_preflight_package()
    package["execute_allowed"] = True
    result = evaluate_phase32_policy(
        package,
        _base_controls(),
        _base_stop_conditions(),
        _base_evidence(),
        _base_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_controls_non_execute_false() -> None:
    controls = _base_controls()
    controls["preflight_controls_does_not_execute"] = False
    result = evaluate_phase32_policy(
        _base_preflight_package(),
        controls,
        _base_stop_conditions(),
        _base_evidence(),
        _base_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_stop_non_execute_false() -> None:
    stop_conditions = _base_stop_conditions()
    stop_conditions["preflight_stop_conditions_does_not_execute"] = False
    result = evaluate_phase32_policy(
        _base_preflight_package(),
        _base_controls(),
        stop_conditions,
        _base_evidence(),
        _base_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_evidence_non_execute_false() -> None:
    evidence = _base_evidence()
    evidence["preflight_evidence_does_not_execute"] = False
    result = evaluate_phase32_policy(
        _base_preflight_package(),
        _base_controls(),
        _base_stop_conditions(),
        evidence,
        _base_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_allow_does_not_execute_false() -> None:
    gate = _base_gate()
    gate["allow_does_not_execute"] = False
    result = evaluate_phase32_policy(
        _base_preflight_package(),
        _base_controls(),
        _base_stop_conditions(),
        _base_evidence(),
        gate,
    )
    assert result["policy_status"] == "FAIL"
