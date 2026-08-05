from phase57.final_check_design.final_check_controls_builder import (
    build_final_check_controls,
)


def test_final_check_controls_have_non_execute_guard() -> None:
    controls = build_final_check_controls({"status": "FINAL_CHECK_PACKAGE_READY"})
    assert controls["status"] == "FINAL_CHECK_CONTROLS_READY"
    assert controls["final_check_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
