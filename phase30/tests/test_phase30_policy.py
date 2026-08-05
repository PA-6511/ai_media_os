from phase30.execution_design.phase30_policy import evaluate_phase30_policy


def _base_design() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "sandbox_scope_required": True,
    }


def _base_constraints() -> dict:
    return {
        "sandbox_only": True,
        "allowlist_within_sandbox": True,
        "constraints_does_not_execute": True,
    }


def _base_gate() -> dict:
    return {
        "approval_required": True,
        "allow_does_not_execute": True,
    }


def test_policy_fails_when_max_files_invalid() -> None:
    design = _base_design()
    design["max_files_to_execute"] = 2
    result = evaluate_phase30_policy(design, _base_constraints(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    design = _base_design()
    design["execute_allowed"] = True
    result = evaluate_phase30_policy(design, _base_constraints(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_sandbox_only_false() -> None:
    constraints = _base_constraints()
    constraints["sandbox_only"] = False
    result = evaluate_phase30_policy(_base_design(), constraints, _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_allow_does_not_execute_false() -> None:
    gate = _base_gate()
    gate["allow_does_not_execute"] = False
    result = evaluate_phase30_policy(_base_design(), _base_constraints(), gate)
    assert result["policy_status"] == "FAIL"
