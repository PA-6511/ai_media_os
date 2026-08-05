from phase60.runbook_design.runbook_controls_builder import (
    build_runbook_controls,
)


def test_runbook_controls_have_non_execute_guard() -> None:
    controls = build_runbook_controls({"status": "RUNBOOK_PACKAGE_READY"})
    assert controls["status"] == "RUNBOOK_CONTROLS_READY"
    assert controls["runbook_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
