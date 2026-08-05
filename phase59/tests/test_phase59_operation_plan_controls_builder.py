from phase59.operation_plan_design.operation_plan_controls_builder import (
    build_operation_plan_controls,
)


def test_operation_plan_controls_have_non_execute_guard() -> None:
    controls = build_operation_plan_controls({"status": "OPERATION_PLAN_PACKAGE_READY"})
    assert controls["status"] == "OPERATION_PLAN_CONTROLS_READY"
    assert controls["operation_plan_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
