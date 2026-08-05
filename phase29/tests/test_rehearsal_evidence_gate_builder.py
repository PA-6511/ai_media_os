from phase29.gate.rehearsal_evidence_gate_builder import build_rehearsal_evidence_gate


def test_evidence_gate_has_non_execute_guard() -> None:
    evidence_gate = build_rehearsal_evidence_gate({"status": "REHEARSAL_GATE_INPUT_READY"})
    assert evidence_gate["status"] == "REHEARSAL_EVIDENCE_GATE_READY"
    assert evidence_gate["evidence_does_not_execute"] is True
    assert "policy_status" in evidence_gate["evidence_fields"]
