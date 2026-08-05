from phase42.finalization_design.finalization_controls_builder import build_finalization_controls


def test_finalization_controls_have_non_execute_guard() -> None:
    controls = build_finalization_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_FINALIZATION_PACKAGE_READY"}
    )
    assert controls["status"] == "FINALIZATION_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["finalization_controls_does_not_execute"] is True
