from phase55.final_readiness_design.final_readiness_controls_builder import (
    build_final_readiness_controls,
)


def test_final_readiness_controls_have_non_execute_guard() -> None:
    controls = build_final_readiness_controls({"status": "FINAL_READINESS_PACKAGE_READY"})
    assert controls["status"] == "FINAL_READINESS_CONTROLS_READY"
    assert controls["final_readiness_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
