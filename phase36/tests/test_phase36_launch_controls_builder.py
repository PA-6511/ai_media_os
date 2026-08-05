from phase36.launch_design.launch_controls_builder import build_launch_controls


def test_launch_controls_have_non_execute_guard() -> None:
    controls = build_launch_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_LAUNCH_PACKAGE_READY"}
    )
    assert controls["status"] == "LAUNCH_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["launch_controls_does_not_execute"] is True
