from phase26.rehearsal.evidence_review_builder import build_evidence_review


def test_evidence_review_has_non_execute_guard() -> None:
    result = build_evidence_review({})
    assert result["status"] == "EVIDENCE_REVIEW_READY"
    assert result["evidence_review_required"] is True
    assert result["evidence_does_not_execute"] is True
