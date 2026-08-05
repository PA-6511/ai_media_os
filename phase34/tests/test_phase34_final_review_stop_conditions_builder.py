from phase34.final_review_design.final_review_stop_conditions_builder import (
    build_final_review_stop_conditions,
)


def test_final_review_stop_conditions_are_blocking_and_non_execute() -> None:
    data = build_final_review_stop_conditions(
        {"status": "FINAL_PRE_EXECUTION_REVIEW_READY"}
    )
    assert data["status"] == "FINAL_REVIEW_STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["final_review_stop_conditions_does_not_execute"] is True
