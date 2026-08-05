from phase64.operator_finalize_design.operator_finalize_controls_builder import (
    build_operator_finalize_controls,
)


def test_operator_finalize_controls_have_non_execute_guard() -> None:
    controls = build_operator_finalize_controls({"status": "OPERATOR_FINALIZE_PACKAGE_READY"})
    assert controls["execute_allowed"] is False
    assert controls["operator_finalize_controls_does_not_execute"] is True
