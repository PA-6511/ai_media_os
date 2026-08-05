from phase22.design.pre_apply_checklist_builder import build_pre_apply_checklist


def test_checklist_contains_required_items() -> None:
    result = build_pre_apply_checklist({})
    assert result["status"] == "CHECKLIST_READY"
    assert "confirm_single_file_scope" in result["items"]
    assert "confirm_no_delete_operation" in result["items"]
    assert "confirm_manual_approval_present" in result["items"]
