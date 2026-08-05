from phase23.execution_design.phase23_policy import evaluate_phase23_policy


def _base_design() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "planned_target_files": ["target.py"],
        "execute_allowed": False,
        "auto_merge_allowed": False,
        "delete_allowed": False,
        "production_execute_allowed": False,
    }


def _base_gate() -> dict:
    return {"approval_required": True, "approve_does_not_execute": True}


def test_policy_fails_when_max_files_invalid() -> None:
    design = _base_design()
    design["max_files_to_execute"] = 2
    result = evaluate_phase23_policy(design, _base_gate(), {"status": "PASS"})
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    design = _base_design()
    design["execute_allowed"] = True
    result = evaluate_phase23_policy(design, _base_gate(), {"status": "PASS"})
    assert result["policy_status"] == "FAIL"
