from phase54.final_authorization_design.final_authorization_controls_builder import (
    build_final_authorization_controls,
)


def test_final_authorization_controls_have_non_execute_guard() -> None:
    controls = build_final_authorization_controls({"status": "FINAL_AUTHORIZATION_PACKAGE_READY"})
    assert controls["status"] == "FINAL_AUTHORIZATION_CONTROLS_READY"
    assert controls["final_authorization_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
