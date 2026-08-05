from phase25.planning.dry_run_execution_plan_builder import build_dry_run_execution_plan


def test_plan_fails_when_phase24_not_ready() -> None:
    result = build_dry_run_execution_plan(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_plan_fails_when_phase24_can_execute_true() -> None:
    result = build_dry_run_execution_plan(
        {"readiness_status": "READY_FOR_PHASE25_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_plan_enforces_single_file_and_execute_disabled() -> None:
    result = build_dry_run_execution_plan(
        {
            "readiness_status": "READY_FOR_PHASE25_PLANNING_ONLY",
            "can_execute": False,
            "planned_target_files": ["a", "b"],
        }
    )
    assert result["status"] == "DRY_RUN_EXECUTION_PLAN_READY"
    assert result["max_files_to_execute"] == 1
    assert len(result["planned_target_files"]) <= 1
    assert result["execute_allowed"] is False
