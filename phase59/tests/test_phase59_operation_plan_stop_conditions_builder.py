from phase59.operation_plan_design.operation_plan_stop_conditions_builder import (
    build_operation_plan_stop_conditions,
)


def test_operation_plan_stop_conditions_are_blocking() -> None:
    data = build_operation_plan_stop_conditions({"status": "OPERATION_PLAN_PACKAGE_READY"})
    assert data["status"] == "OPERATION_PLAN_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["operation_plan_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
