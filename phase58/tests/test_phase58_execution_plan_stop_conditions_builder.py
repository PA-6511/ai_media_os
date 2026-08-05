from phase58.execution_plan_design.execution_plan_stop_conditions_builder import (
    build_execution_plan_stop_conditions,
)


def test_execution_plan_stop_conditions_are_blocking() -> None:
    data = build_execution_plan_stop_conditions({"status": "EXECUTION_PLAN_PACKAGE_READY"})
    assert data["status"] == "EXECUTION_PLAN_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["execution_plan_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
