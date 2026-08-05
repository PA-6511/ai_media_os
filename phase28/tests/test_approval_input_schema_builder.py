from phase28.gate.approval_input_schema_builder import build_approval_input_schema


def test_approval_schema_has_non_execute_guard() -> None:
    schema = build_approval_input_schema({"status": "MANUAL_DRY_RUN_GATE_READY"})
    assert schema["status"] == "APPROVAL_INPUT_SCHEMA_READY"
    assert schema["allow_does_not_execute"] is True
    assert "ALLOW_PHASE29_PLANNING_ONLY" in schema["allowed_decisions"]
