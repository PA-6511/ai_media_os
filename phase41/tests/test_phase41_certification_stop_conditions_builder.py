from phase41.certification_design.certification_stop_conditions_builder import (
    build_certification_stop_conditions,
)


def test_certification_stop_conditions_are_blocking_and_non_execute() -> None:
    data = build_certification_stop_conditions(
        {"status": "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY"}
    )
    assert data["status"] == "CERTIFICATION_STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["certification_stop_conditions_does_not_execute"] is True
