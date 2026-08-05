from phase52.go_live_review_design.go_live_review_stop_conditions_builder import (
    build_go_live_review_stop_conditions,
)


def test_go_live_review_stop_conditions_are_blocking() -> None:
    data = build_go_live_review_stop_conditions({"status": "GO_LIVE_REVIEW_PACKAGE_READY"})
    assert data["status"] == "GO_LIVE_REVIEW_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["go_live_review_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
