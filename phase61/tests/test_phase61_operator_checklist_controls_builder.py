from phase61.operator_checklist_design.operator_checklist_controls_builder import (
    build_operator_checklist_controls,
)


def test_operator_checklist_controls_have_non_execute_guard() -> None:
    controls = build_operator_checklist_controls({"status": "OPERATOR_CHECKLIST_PACKAGE_READY"})
    assert controls["execute_allowed"] is False
    assert controls["operator_checklist_controls_does_not_execute"] is True
