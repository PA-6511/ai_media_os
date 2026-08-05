from phase32.preflight_design.preflight_controls_builder import build_preflight_controls


def test_preflight_controls_have_non_execute_guard() -> None:
    controls = build_preflight_controls(
        {"status": "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY"}
    )
    assert controls["status"] == "PREFLIGHT_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["preflight_controls_does_not_execute"] is True
