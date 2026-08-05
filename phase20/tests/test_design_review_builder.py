from phase20.review.design_review_builder import build_design_review_package


def test_design_review_fails_when_phase19_not_ready() -> None:
    package = build_design_review_package({"promotion_status": "NOT_READY"})
    assert package["status"] == "FAIL"


def test_design_review_ready_when_phase19_ready() -> None:
    package = build_design_review_package(
        {"promotion_status": "READY_FOR_PHASE20_DESIGN", "reasons": []}
    )
    assert package["status"] == "REVIEW_READY"
    assert package["phase"] == "20"
