from phase46.transition_design.transition_controls_builder import build_transition_controls


def test_transition_controls_have_non_execute_guard() -> None:
    controls = build_transition_controls({"status": "TRANSITION_PACKAGE_READY"})
    assert controls["status"] == "TRANSITION_CONTROLS_READY"
    assert controls["transition_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
