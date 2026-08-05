from phase52.go_live_review_design.go_live_review_controls_builder import (
    build_go_live_review_controls,
)


def test_go_live_review_controls_have_non_execute_guard() -> None:
    controls = build_go_live_review_controls({"status": "GO_LIVE_REVIEW_PACKAGE_READY"})
    assert controls["status"] == "GO_LIVE_REVIEW_CONTROLS_READY"
    assert controls["go_live_review_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
