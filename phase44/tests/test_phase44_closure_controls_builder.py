from phase44.closure_design.closure_controls_builder import build_closure_controls


def test_closure_controls_have_non_execute_guard() -> None:
    controls = build_closure_controls({"status": "CLOSURE_PACKAGE_READY"})
    assert controls["status"] == "CLOSURE_CONTROLS_READY"
    assert controls["closure_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
