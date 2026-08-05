from phase21.planning.controlled_apply_plan_validator import validate_controlled_apply_plan


def _base_plan() -> dict:
    return {
        "phase": "21",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "apply_scope": "single_file_planning_only",
        "max_files_to_apply": 1,
        "controlled_apply_allowed": False,
        "auto_merge_allowed": False,
        "delete_allowed": False,
        "production_apply_allowed": False,
        "manual_approval_required_for_next": True,
        "planned_target_files": ["phase20/rc.json"],
        "status": "CONTROLLED_APPLY_PLAN_DRAFT",
    }


def test_validator_fails_when_max_files_gt_1() -> None:
    plan = _base_plan()
    plan["max_files_to_apply"] = 2
    result = validate_controlled_apply_plan(plan)
    assert result["status"] == "FAIL"


def test_validator_fails_when_target_files_over_1() -> None:
    plan = _base_plan()
    plan["planned_target_files"] = ["a", "b"]
    result = validate_controlled_apply_plan(plan)
    assert result["status"] == "FAIL"


def test_validator_fails_on_flag_violations() -> None:
    for key in [
        "controlled_apply_allowed",
        "auto_merge_allowed",
        "delete_allowed",
        "production_apply_allowed",
    ]:
        plan = _base_plan()
        plan[key] = True
        result = validate_controlled_apply_plan(plan)
        assert result["status"] == "FAIL"
