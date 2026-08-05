from phase33.approval_design.final_approval_controls_builder import (
    build_final_approval_controls,
)


def test_final_approval_controls_have_non_execute_guard() -> None:
    controls = build_final_approval_controls(
        {"status": "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY"}
    )
    assert controls["status"] == "FINAL_APPROVAL_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["final_approval_controls_does_not_execute"] is True
