from phase29.gate.rehearsal_gate_checklist_builder import build_rehearsal_gate_checklist


def test_checklist_has_non_execute_guard() -> None:
    checklist = build_rehearsal_gate_checklist({"status": "REHEARSAL_GATE_INPUT_READY"})
    assert checklist["status"] == "REHEARSAL_GATE_CHECKLIST_READY"
    assert checklist["checklist_does_not_execute"] is True
    assert "confirm_single_file_scope" in checklist["checklist_items"]
