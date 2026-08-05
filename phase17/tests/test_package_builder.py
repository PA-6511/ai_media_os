from phase17.package.package_builder import build_decision_package


def test_build_decision_package_has_required_keys() -> None:
    comparison_result = {
        "selected_candidate_id": "minimal",
        "pipeline_status": "PASS_DRY_RUN_ONLY",
        "candidates_report": [
            {
                "policy": {
                    "status": "POLICY_VIOLATION",
                    "reasons": ["has_deletion=True is forbidden"],
                }
            }
        ],
    }

    package = build_decision_package(comparison_result)

    assert package["status"] == "READY_FOR_HUMAN_REVIEW"
    assert package["phase"] == "17"
    assert package["mode"] == "DRY_RUN"
    assert package["human_approval_required"] is True
    assert package["selected_candidate_id"] == "minimal"
    assert "candidate_not_applied" in package["risks"]
    assert "requires_manual_review_before_apply" in package["risks"]
    assert "has_deletion=True is forbidden" in package["reject_reasons"]


def test_build_decision_package_fails_without_selected_candidate() -> None:
    comparison_result = {
        "selected_candidate_id": None,
        "pipeline_status": "FAIL",
        "candidates_report": [],
    }

    package = build_decision_package(comparison_result)

    assert package["status"] == "FAIL"
    assert package["reason"] == "selected_candidate_id_missing"
