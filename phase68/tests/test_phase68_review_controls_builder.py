from phase68.preparation_review_design.review_controls_builder import build_review_controls


def test_review_controls_have_non_execute_guard() -> None:
    controls = build_review_controls({"status": "PREPARATION_REVIEW_PACKAGE_READY"})
    assert controls["execute_allowed"] is False
    assert controls["review_controls_does_not_execute"] is True
