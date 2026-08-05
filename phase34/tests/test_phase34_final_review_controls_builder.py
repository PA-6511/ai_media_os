from phase34.final_review_design.final_review_controls_builder import (
    build_final_review_controls,
)


def test_final_review_controls_have_non_execute_guard() -> None:
    controls = build_final_review_controls(
        {"status": "FINAL_PRE_EXECUTION_REVIEW_READY"}
    )
    assert controls["status"] == "FINAL_REVIEW_CONTROLS_READY"
    assert controls["single_file_scope_required"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["final_review_controls_does_not_execute"] is True
