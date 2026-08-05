from phase60.runbook_design.runbook_stop_conditions_builder import (
    build_runbook_stop_conditions,
)


def test_runbook_stop_conditions_are_blocking() -> None:
    data = build_runbook_stop_conditions({"status": "RUNBOOK_PACKAGE_READY"})
    assert data["status"] == "RUNBOOK_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["runbook_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
