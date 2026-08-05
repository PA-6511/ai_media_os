from phase58.execution_plan_design.execution_plan_controls_builder import (
    build_execution_plan_controls,
)


def test_execution_plan_controls_have_non_execute_guard() -> None:
    controls = build_execution_plan_controls({"status": "EXECUTION_PLAN_PACKAGE_READY"})
    assert controls["status"] == "EXECUTION_PLAN_CONTROLS_READY"
    assert controls["execution_plan_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
