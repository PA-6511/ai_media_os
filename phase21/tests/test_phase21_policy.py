from phase21.planning.phase21_policy import evaluate_phase21_policy


def _base_plan() -> dict:
    return {
        "mode": "DRY_RUN",
        "max_files_to_apply": 1,
        "planned_target_files": ["phase20/rc.json"],
        "controlled_apply_allowed": False,
        "auto_merge_allowed": False,
        "delete_allowed": False,
        "production_apply_allowed": False,
    }


def _base_approval() -> dict:
    return {
        "approval_required": True,
        "approve_does_not_apply": True,
    }


def test_policy_fails_when_max_files_gt_1() -> None:
    plan = _base_plan()
    plan["max_files_to_apply"] = 2
    result = evaluate_phase21_policy(plan, _base_approval())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_approval_required_false() -> None:
    approval = _base_approval()
    approval["approval_required"] = False
    result = evaluate_phase21_policy(_base_plan(), approval)
    assert result["policy_status"] == "FAIL"
