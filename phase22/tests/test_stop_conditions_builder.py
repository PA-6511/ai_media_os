from phase22.design.stop_conditions_builder import build_stop_conditions


def test_stop_conditions_contains_required_conditions() -> None:
    result = build_stop_conditions({})
    assert result["status"] == "STOP_CONDITIONS_READY"
    assert "target_files_count_exceeds_1" in result["conditions"]
    assert "any_delete_instruction_detected" in result["conditions"]
