from phase51.readiness_review_design.readiness_review_stop_conditions_builder import (
    build_readiness_review_stop_conditions,
)


def test_readiness_review_stop_conditions_are_blocking() -> None:
    data = build_readiness_review_stop_conditions({"status": "READINESS_REVIEW_PACKAGE_READY"})
    assert data["status"] == "READINESS_REVIEW_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["readiness_review_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
