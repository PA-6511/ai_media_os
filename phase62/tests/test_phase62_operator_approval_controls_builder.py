from phase62.operator_approval_design.operator_approval_controls_builder import (
    build_operator_approval_controls,
)


def test_operator_approval_controls_have_non_execute_guard() -> None:
    controls = build_operator_approval_controls({"status": "OPERATOR_APPROVAL_PACKAGE_READY"})
    assert controls["execute_allowed"] is False
    assert controls["operator_approval_controls_does_not_execute"] is True
