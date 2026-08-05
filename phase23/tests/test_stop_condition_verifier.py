from phase23.execution_design.stop_condition_verifier import verify_stop_conditions


def test_stop_condition_verifier_fails_when_missing_condition() -> None:
    result = verify_stop_conditions(
        {
            "conditions": [
                "target_files_count_exceeds_1",
                "manual_approval_missing",
            ]
        }
    )
    assert result["status"] == "FAIL"


def test_stop_condition_verifier_passes_when_all_present() -> None:
    result = verify_stop_conditions(
        {
            "conditions": [
                "target_files_count_exceeds_1",
                "manual_approval_missing",
                "policy_violation_detected",
                "dry_run_disabled",
                "any_delete_instruction_detected",
                "any_production_instruction_detected",
            ]
        }
    )
    assert result["status"] == "PASS"
