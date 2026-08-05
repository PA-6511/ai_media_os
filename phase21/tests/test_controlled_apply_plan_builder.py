from phase21.planning.controlled_apply_plan_builder import build_controlled_apply_plan


def test_builder_fails_when_phase20_not_ready() -> None:
    plan = build_controlled_apply_plan({"readiness_status": "NOT_READY", "can_apply": False})
    assert plan["status"] == "FAIL"


def test_builder_fails_when_phase20_can_apply_true() -> None:
    plan = build_controlled_apply_plan(
        {"readiness_status": "READY_FOR_PHASE21_PLANNING", "can_apply": True}
    )
    assert plan["status"] == "FAIL"


def test_builder_returns_draft_when_valid_input() -> None:
    plan = build_controlled_apply_plan(
        {
            "readiness_status": "READY_FOR_PHASE21_PLANNING",
            "can_apply": False,
            "planned_target_files": ["phase20/rc.json", "phase20/extra.json"],
        }
    )
    assert plan["status"] == "CONTROLLED_APPLY_PLAN_DRAFT"
    assert plan["max_files_to_apply"] == 1
    assert len(plan["planned_target_files"]) <= 1
