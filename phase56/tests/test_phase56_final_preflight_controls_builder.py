from phase56.final_preflight_design.final_preflight_controls_builder import (
    build_final_preflight_controls,
)


def test_final_preflight_controls_have_non_execute_guard() -> None:
    controls = build_final_preflight_controls({"status": "FINAL_PREFLIGHT_PACKAGE_READY"})
    assert controls["status"] == "FINAL_PREFLIGHT_CONTROLS_READY"
    assert controls["final_preflight_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
