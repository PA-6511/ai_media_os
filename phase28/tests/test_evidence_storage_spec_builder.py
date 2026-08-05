from phase28.gate.evidence_storage_spec_builder import build_evidence_storage_spec


def test_evidence_spec_has_non_execute_guard() -> None:
    spec = build_evidence_storage_spec({"status": "MANUAL_DRY_RUN_GATE_READY"})
    assert spec["status"] == "EVIDENCE_STORAGE_SPEC_READY"
    assert spec["evidence_does_not_execute"] is True
    assert "policy_result" in spec["storage_fields"]
