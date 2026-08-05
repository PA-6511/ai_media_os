from phase30.execution_design.sandbox_execution_constraints_builder import (
    build_sandbox_execution_constraints,
)


def test_constraints_have_non_execute_guard() -> None:
    constraints = build_sandbox_execution_constraints(
        {"status": "LIMITED_DRY_RUN_DESIGN_READY"}
    )
    assert constraints["status"] == "SANDBOX_EXECUTION_CONSTRAINTS_READY"
    assert constraints["sandbox_only"] is True
    assert constraints["allowlist_within_sandbox"] is True
    assert constraints["constraints_does_not_execute"] is True
