from phase47.integration_design.integration_controls_builder import build_integration_controls


def test_integration_controls_have_non_execute_guard() -> None:
    controls = build_integration_controls({"status": "INTEGRATION_PACKAGE_READY"})
    assert controls["status"] == "INTEGRATION_CONTROLS_READY"
    assert controls["integration_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
