from phase35.readiness_design.readiness_controls_builder import build_readiness_controls


def test_readiness_controls_have_non_execute_guard() -> None:
    controls = build_readiness_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY"}
    )
    assert controls["status"] == "READINESS_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["readiness_controls_does_not_execute"] is True
