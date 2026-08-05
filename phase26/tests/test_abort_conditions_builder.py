from phase26.rehearsal.abort_conditions_builder import build_abort_conditions


def test_abort_conditions_include_required_items() -> None:
    result = build_abort_conditions({})
    assert result["status"] == "ABORT_CONDITIONS_READY"
    assert "more_than_one_file_detected" in result["conditions"]
    assert "delete_instruction_detected" in result["conditions"]
