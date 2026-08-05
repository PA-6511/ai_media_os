from phase41.certification_design.manual_gate_certification_builder import (
    build_manual_gate_certification,
)


def test_manual_gate_certification_allows_phase42_planning_only() -> None:
    gate = build_manual_gate_certification(
        {"status": "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_CERTIFICATION_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE42_PLANNING_ONLY" in gate["allowed_decisions"]
