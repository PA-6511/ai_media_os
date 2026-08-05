from phase37.trigger_design.trigger_controls_builder import build_trigger_controls


def test_trigger_controls_have_non_execute_guard() -> None:
    controls = build_trigger_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY"}
    )
    assert controls["status"] == "TRIGGER_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["trigger_controls_does_not_execute"] is True
