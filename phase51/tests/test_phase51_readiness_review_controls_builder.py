from phase51.readiness_review_design.readiness_review_controls_builder import (
    build_readiness_review_controls,
)


def test_readiness_review_controls_have_non_execute_guard() -> None:
    controls = build_readiness_review_controls({"status": "READINESS_REVIEW_PACKAGE_READY"})
    assert controls["status"] == "READINESS_REVIEW_CONTROLS_READY"
    assert controls["readiness_review_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
