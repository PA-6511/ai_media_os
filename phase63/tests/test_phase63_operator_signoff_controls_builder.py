from phase63.operator_signoff_design.operator_signoff_controls_builder import (
    build_operator_signoff_controls,
)


def test_operator_signoff_controls_have_non_execute_guard() -> None:
    controls = build_operator_signoff_controls({"status": "OPERATOR_SIGNOFF_PACKAGE_READY"})
    assert controls["execute_allowed"] is False
    assert controls["operator_signoff_controls_does_not_execute"] is True
