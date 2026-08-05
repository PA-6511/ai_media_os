from phase31.control_design.phase31_policy import evaluate_phase31_policy


def _base_control_design() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execute_allowed": False,
        "can_execute": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
    }


def _base_stop_conditions() -> dict:
    return {
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "stop_conditions_does_not_execute": True,
    }


def _base_evidence_requirements() -> dict:
    return {
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "evidence_does_not_execute": True,
    }


def _base_manual_gate() -> dict:
    return {
        "approval_required": True,
        "allow_does_not_execute": True,
    }


def test_policy_fails_when_max_files_invalid() -> None:
    control_design = _base_control_design()
    control_design["max_files_to_execute"] = 2
    result = evaluate_phase31_policy(
        control_design,
        _base_stop_conditions(),
        _base_evidence_requirements(),
        _base_manual_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_can_execute_true() -> None:
    control_design = _base_control_design()
    control_design["can_execute"] = True
    result = evaluate_phase31_policy(
        control_design,
        _base_stop_conditions(),
        _base_evidence_requirements(),
        _base_manual_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_stop_conditions_non_execute_false() -> None:
    stop_conditions = _base_stop_conditions()
    stop_conditions["stop_conditions_does_not_execute"] = False
    result = evaluate_phase31_policy(
        _base_control_design(),
        stop_conditions,
        _base_evidence_requirements(),
        _base_manual_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_evidence_non_execute_false() -> None:
    evidence_requirements = _base_evidence_requirements()
    evidence_requirements["evidence_does_not_execute"] = False
    result = evaluate_phase31_policy(
        _base_control_design(),
        _base_stop_conditions(),
        evidence_requirements,
        _base_manual_gate(),
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_allow_does_not_execute_false() -> None:
    manual_gate = _base_manual_gate()
    manual_gate["allow_does_not_execute"] = False
    result = evaluate_phase31_policy(
        _base_control_design(),
        _base_stop_conditions(),
        _base_evidence_requirements(),
        manual_gate,
    )
    assert result["policy_status"] == "FAIL"
