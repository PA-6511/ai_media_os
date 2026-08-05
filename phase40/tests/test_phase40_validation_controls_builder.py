from phase40.validation_design.validation_controls_builder import build_validation_controls


def test_validation_controls_have_non_execute_guard() -> None:
    controls = build_validation_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY"}
    )
    assert controls["status"] == "VALIDATION_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["validation_controls_does_not_execute"] is True
