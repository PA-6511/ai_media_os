from phase45.handoff_design.handoff_controls_builder import build_handoff_controls


def test_handoff_controls_have_non_execute_guard() -> None:
    controls = build_handoff_controls({"status": "HANDOFF_PACKAGE_READY"})
    assert controls["status"] == "HANDOFF_CONTROLS_READY"
    assert controls["handoff_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
