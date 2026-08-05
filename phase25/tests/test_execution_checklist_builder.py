from phase25.planning.execution_checklist_builder import build_execution_checklist


def test_execution_checklist_contains_required_items() -> None:
    result = build_execution_checklist({})
    assert result["status"] == "EXECUTION_CHECKLIST_READY"
    assert "confirm_single_file_scope" in result["items"]
    assert "confirm_evidence_format_ready" in result["items"]
