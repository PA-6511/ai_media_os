from phase48.staging_design.staging_controls_builder import build_staging_controls


def test_staging_controls_have_non_execute_guard() -> None:
    controls = build_staging_controls({"status": "STAGING_PACKAGE_READY"})
    assert controls["status"] == "STAGING_CONTROLS_READY"
    assert controls["staging_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
