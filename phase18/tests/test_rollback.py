from phase18.apply.rollback import build_rollback_plan, rollback_execution


def test_build_rollback_plan_and_dry_run_execution() -> None:
    execution_result = {
        "status": "PASS",
        "applied_files": ["/tmp/sandbox/a.txt", "/tmp/sandbox/b.txt"],
    }

    plan = build_rollback_plan(execution_result)
    assert plan["status"] == "ROLLBACK_PLAN_READY"
    assert len(plan["restore_targets"]) == 2

    rollback_result = rollback_execution(plan, dry_run=True)
    assert rollback_result["status"] == "WOULD_ROLLBACK"
    assert len(rollback_result["planned_restore_targets"]) == 2
