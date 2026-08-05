from phase43.completion_design.completion_controls_builder import build_completion_controls


def test_completion_controls_have_non_execute_guard() -> None:
    controls = build_completion_controls({"status": "COMPLETION_PACKAGE_READY"})
    assert controls["status"] == "COMPLETION_CONTROLS_READY"
    assert controls["controls_do_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
