from phase17.approval.approval_schema import validate_decision_package


def test_validate_decision_package_missing_keys_fails() -> None:
    package = {
        "phase": "17",
        "mode": "DRY_RUN",
    }

    result = validate_decision_package(package)

    assert result["status"] == "FAIL"
    assert len(result["missing_keys"]) > 0


def test_validate_decision_package_passes_when_complete() -> None:
    package = {
        "phase": "17",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "selected_candidate_id": "minimal",
        "risks": ["candidate_not_applied"],
        "reject_reasons": [],
        "approve_instructions": ["APPROVE allows only next dry-run stage"],
        "comparison_result": {"selected_candidate_id": "minimal"},
    }

    result = validate_decision_package(package)

    assert result["status"] == "PASS"
    assert result["missing_keys"] == []
