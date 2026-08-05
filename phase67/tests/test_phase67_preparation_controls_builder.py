from phase67.preparation_evidence_design.preparation_controls_builder import (
    build_preparation_controls,
)


def test_controls_have_non_execute_guard() -> None:
    controls = build_preparation_controls({"status": "PREPARATION_EVIDENCE_PACKAGE_READY"})
    assert controls["execute_allowed"] is False
    assert controls["preparation_controls_does_not_execute"] is True
