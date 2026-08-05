from phase39.authorization_design.authorization_controls_builder import build_authorization_controls


def test_authorization_controls_have_non_execute_guard() -> None:
    controls = build_authorization_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY"}
    )
    assert controls["status"] == "AUTHORIZATION_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["authorization_controls_does_not_execute"] is True
