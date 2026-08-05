from phase38.confirmation_design.confirmation_controls_builder import build_confirmation_controls


def test_confirmation_controls_have_non_execute_guard() -> None:
    controls = build_confirmation_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY"}
    )
    assert controls["status"] == "CONFIRMATION_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["confirmation_controls_does_not_execute"] is True
