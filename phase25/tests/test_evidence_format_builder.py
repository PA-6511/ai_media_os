from phase25.planning.evidence_format_builder import build_evidence_format


def test_evidence_format_contains_non_execute_guard() -> None:
    result = build_evidence_format({})
    assert result["status"] == "EVIDENCE_FORMAT_READY"
    assert result["evidence_does_not_execute"] is True
    assert "target_file" in result["evidence_fields"]
