from phase41.certification_design.certification_controls_builder import build_certification_controls


def test_certification_controls_have_non_execute_guard() -> None:
    controls = build_certification_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY"}
    )
    assert controls["status"] == "CERTIFICATION_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["certification_controls_does_not_execute"] is True
