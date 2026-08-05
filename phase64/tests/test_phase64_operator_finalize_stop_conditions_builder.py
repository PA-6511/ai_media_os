from phase64.operator_finalize_design.operator_finalize_stop_conditions_builder import (
    build_operator_finalize_stop_conditions,
)


def test_operator_finalize_stop_conditions_are_blocking() -> None:
    data = build_operator_finalize_stop_conditions({"status": "OPERATOR_FINALIZE_PACKAGE_READY"})
    assert data["stop_conditions_required"] is True
    assert data["stop_on_non_dry_run"] is True
    assert data["operator_finalize_stop_conditions_does_not_execute"] is True
