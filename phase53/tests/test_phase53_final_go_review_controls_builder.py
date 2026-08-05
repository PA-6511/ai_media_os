from phase53.final_go_review_design.final_go_review_controls_builder import (
    build_final_go_review_controls,
)


def test_final_go_review_controls_have_non_execute_guard() -> None:
    controls = build_final_go_review_controls({"status": "FINAL_GO_REVIEW_PACKAGE_READY"})
    assert controls["status"] == "FINAL_GO_REVIEW_CONTROLS_READY"
    assert controls["final_go_review_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
