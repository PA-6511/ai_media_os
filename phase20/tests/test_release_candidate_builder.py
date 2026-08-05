from phase20.review.release_candidate_builder import build_release_candidate_package


def test_release_candidate_contains_do_not_apply_instruction() -> None:
    rc = build_release_candidate_package({"status": "REVIEW_READY"})
    assert rc["status"] == "RC_PACKAGE_READY"
    assert rc["apply_instruction"] == "DO_NOT_APPLY_IN_PHASE20"
